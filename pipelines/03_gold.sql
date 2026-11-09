-- =====================================================================
-- GOLD: HRRP-style readmission facts, unit trends, follow-up gap,
-- risk factors and the HRRP penalty estimate. Consumed by the ML
-- notebooks, Lakebase synced tables, Genie, the dashboard and the app.
--
-- Definitions (documented for Genie and the app):
--   index admission  = inpatient discharge, not EXPIRED/AMA, and not itself a
--                      readmission (admitted within 30 days of a prior discharge)
--   readmit_30d      = any admission for the same patient within 30 days of discharge
--   outcome_complete = discharge date <= as_of_date - 30 (full 30-day window observed)
--   weekend          = Friday, Saturday or Sunday discharge
--   fu7_booked       = follow-up visit within 7 days, booked before the patient left
--   last_20w / prior_20w = the last 20 complete Mon-Sun weeks with full outcomes,
--                          and the 20 weeks before that
-- =====================================================================

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.gold.encounters_enriched
COMMENT 'All valid inpatient encounters joined to HRRP condition, unit, hospital and patient age.'
AS SELECT
  e.*,
  coalesce(m.hrrp_condition, 'OTHER') AS condition,
  m.hrrp_condition IS NOT NULL AS is_hrrp_condition,
  u.unit_name, u.service_line, h.hospital_name,
  CAST(floor(months_between(e.discharge_ts, p.date_of_birth) / 12) AS INT) AS age_at_discharge,
  p.sex, p.primary_language, p.zip_code
FROM ${catalog}.silver.encounters e
LEFT JOIN ${catalog}.silver.icd10_hrrp_map m ON e.principal_dx_code = m.icd10_code
LEFT JOIN ${catalog}.silver.units u ON e.unit_id = u.unit_id
LEFT JOIN ${catalog}.silver.hospitals h ON e.hospital_id = h.hospital_id
LEFT JOIN ${catalog}.silver.patients p ON e.patient_id = p.patient_id;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.gold.index_admissions
COMMENT 'One row per index admission with 30-day readmission outcome, 7-day follow-up status, AI note signals and reporting-period flags.'
AS WITH seq AS (
  SELECT *,
    lag(discharge_ts) OVER (PARTITION BY patient_id ORDER BY admit_ts) AS prev_discharge_ts,
    lead(admit_ts) OVER (PARTITION BY patient_id ORDER BY admit_ts) AS next_admit_ts,
    lead(encounter_id) OVER (PARTITION BY patient_id ORDER BY admit_ts) AS next_encounter_id,
    lead(principal_dx_desc) OVER (PARTITION BY patient_id ORDER BY admit_ts) AS next_dx_desc
  FROM ${catalog}.gold.encounters_enriched
),
asof AS (
  SELECT CAST(max(discharge_ts) AS DATE) AS as_of_date FROM ${catalog}.silver.encounters
),
bounds AS (
  SELECT as_of_date,
         date_sub(date_sub(as_of_date, 30), dayofweek(date_sub(as_of_date, 30)) - 1) AS complete_end
  FROM asof
),
chg AS (
  SELECT min(event_date) AS change_date FROM ${catalog}.silver.staffing_events WHERE scope_id = 'CUMC-6N'
),
fu AS (
  SELECT f.encounter_id,
    max(CASE WHEN f.booked_ts <= e.discharge_ts AND datediff(f.appointment_ts, e.discharge_ts) BETWEEN 0 AND 7
             THEN 1 ELSE 0 END) = 1 AS fu7_booked,
    min(f.appointment_ts) AS first_followup_ts
  FROM ${catalog}.silver.followup_appointments f
  JOIN ${catalog}.silver.encounters e ON f.encounter_id = e.encounter_id
  GROUP BY f.encounter_id
)
SELECT
  s.encounter_id, s.patient_id, s.hospital_id, s.hospital_name, s.unit_id, s.unit_name, s.service_line,
  s.condition, s.is_hrrp_condition, s.principal_dx_code, s.principal_dx_desc, s.drg_code,
  s.admit_ts, s.discharge_ts, CAST(s.discharge_ts AS DATE) AS discharge_date,
  CAST(date_trunc('week', s.discharge_ts) AS DATE) AS discharge_week,
  date_format(s.discharge_ts, 'EEEE') AS discharge_dow,
  dayofweek(s.discharge_ts) IN (6, 7, 1) AS weekend_discharge,
  s.los_days, s.age_at_discharge, s.sex, s.payer, s.admission_source, s.discharge_disposition,
  s.prior_admissions_12m, s.comorbidity_count, s.comorbidities,
  coalesce(fu.fu7_booked, false) AS fu7_booked,
  fu.first_followup_ts,
  coalesce(sig.ai_lives_alone, false) AS ai_lives_alone,
  coalesce(sig.ai_transport_barrier, false) AS ai_transport_barrier,
  sig.ai_followup_status,
  -- verbatim evidence quotes are NOT exposed here (analyst-facing); they live in silver and in the masked gold.patient_risk_scores.ai_evidence
  coalesce(s.next_admit_ts > s.discharge_ts AND s.next_admit_ts <= s.discharge_ts + INTERVAL 30 DAYS, false) AS readmit_30d,
  CASE WHEN s.next_admit_ts > s.discharge_ts AND s.next_admit_ts <= s.discharge_ts + INTERVAL 30 DAYS
       THEN s.next_encounter_id END AS readmit_encounter_id,
  CASE WHEN s.next_admit_ts > s.discharge_ts AND s.next_admit_ts <= s.discharge_ts + INTERVAL 30 DAYS
       THEN datediff(s.next_admit_ts, s.discharge_ts) END AS days_to_readmit,
  CAST(s.discharge_ts AS DATE) <= date_sub(b.as_of_date, 30) AS outcome_complete,
  CASE
    WHEN CAST(s.discharge_ts AS DATE) BETWEEN date_sub(b.complete_end, 139) AND b.complete_end THEN 'last_20w'
    WHEN CAST(s.discharge_ts AS DATE) BETWEEN date_sub(b.complete_end, 279) AND date_sub(b.complete_end, 140) THEN 'prior_20w'
  END AS period_20w,
  CAST(s.discharge_ts AS DATE) BETWEEN date_sub(b.complete_end, 364) AND b.complete_end AS trailing_12m,
  CAST(s.discharge_ts AS DATE) >= c.change_date AS after_6n_staffing_change,
  b.as_of_date, b.complete_end AS outcome_complete_through
FROM seq s
CROSS JOIN bounds b
CROSS JOIN chg c
LEFT JOIN fu ON s.encounter_id = fu.encounter_id
LEFT JOIN ${catalog}.silver.discharge_note_signals sig ON s.encounter_id = sig.encounter_id
WHERE s.discharge_disposition NOT IN ('EXPIRED', 'AMA')
  AND NOT coalesce(s.prev_discharge_ts <= s.admit_ts AND s.admit_ts <= s.prev_discharge_ts + INTERVAL 30 DAYS, false);

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.gold.unit_weekly_readmissions
COMMENT 'Weekly 30-day readmission rate per hospital unit and condition (index admissions with complete outcomes), split weekend vs weekday.'
AS SELECT
  hospital_id, hospital_name, unit_id, unit_name, condition, discharge_week,
  count(*) AS index_admissions,
  sum(CAST(readmit_30d AS INT)) AS readmissions,
  round(100 * avg(CAST(readmit_30d AS INT)), 2) AS readmit_rate_pct,
  sum(CAST(weekend_discharge AS INT)) AS weekend_discharges,
  sum(CASE WHEN weekend_discharge THEN CAST(readmit_30d AS INT) END) AS weekend_readmissions,
  sum(CAST(fu7_booked AS INT)) AS fu7_booked
FROM ${catalog}.gold.index_admissions
WHERE outcome_complete
GROUP BY ALL;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.gold.unit_period_summary
COMMENT 'Prior-20-week vs last-20-week readmission rate per unit, for all conditions (ALL) and per HRRP condition. delta_pts = last - prior.'
AS WITH base AS (
  SELECT hospital_id, hospital_name, unit_id, unit_name, 'ALL' AS condition, period_20w, readmit_30d FROM ${catalog}.gold.index_admissions WHERE period_20w IS NOT NULL
  UNION ALL
  SELECT hospital_id, hospital_name, unit_id, unit_name, condition, period_20w, readmit_30d FROM ${catalog}.gold.index_admissions WHERE period_20w IS NOT NULL
)
SELECT hospital_id, hospital_name, unit_id, unit_name, condition,
  count_if(period_20w = 'prior_20w') AS prior_20w_index,
  count_if(period_20w = 'prior_20w' AND readmit_30d) AS prior_20w_readmits,
  round(100 * count_if(period_20w = 'prior_20w' AND readmit_30d) / nullif(count_if(period_20w = 'prior_20w'), 0), 1) AS prior_20w_rate_pct,
  count_if(period_20w = 'last_20w') AS last_20w_index,
  count_if(period_20w = 'last_20w' AND readmit_30d) AS last_20w_readmits,
  round(100 * count_if(period_20w = 'last_20w' AND readmit_30d) / nullif(count_if(period_20w = 'last_20w'), 0), 1) AS last_20w_rate_pct,
  round(100 * count_if(period_20w = 'last_20w' AND readmit_30d) / nullif(count_if(period_20w = 'last_20w'), 0)
      - 100 * count_if(period_20w = 'prior_20w' AND readmit_30d) / nullif(count_if(period_20w = 'prior_20w'), 0), 1) AS delta_pts
FROM base
GROUP BY ALL;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.gold.followup_gap
COMMENT '7-day follow-up booked at discharge, by unit, condition, weekend vs weekday, before vs after the 6 North staffing change (2026-06-19).'
AS SELECT
  hospital_id, unit_id, unit_name, condition,
  CASE WHEN weekend_discharge THEN 'Weekend (Fri-Sun)' ELSE 'Weekday (Mon-Thu)' END AS discharge_day_type,
  CASE WHEN after_6n_staffing_change THEN 'since_2026-06-19' ELSE 'before_2026-06-19' END AS period,
  count(*) AS discharges,
  sum(CAST(fu7_booked AS INT)) AS fu7_booked,
  round(100 * avg(CAST(fu7_booked AS INT)), 1) AS fu7_booked_pct
FROM ${catalog}.gold.index_admissions
GROUP BY ALL;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.gold.readmission_risk_factors
COMMENT 'Trailing-12-month 30-day readmission rate by risk factor (7-day follow-up, AI-extracted lives alone / transportation barrier, weekend discharge), all hospitals, per condition.'
AS WITH t AS (SELECT * FROM ${catalog}.gold.index_admissions WHERE trailing_12m),
f AS (
  SELECT condition, 'fu7_booked' AS factor, CAST(fu7_booked AS STRING) AS value, readmit_30d FROM t
  UNION ALL SELECT condition, 'ai_lives_alone', CAST(ai_lives_alone AS STRING), readmit_30d FROM t
  UNION ALL SELECT condition, 'ai_transport_barrier', CAST(ai_transport_barrier AS STRING), readmit_30d FROM t
  UNION ALL SELECT condition, 'weekend_discharge', CAST(weekend_discharge AS STRING), readmit_30d FROM t
)
SELECT condition, factor, value, count(*) AS index_admissions, sum(CAST(readmit_30d AS INT)) AS readmissions,
       round(100 * avg(CAST(readmit_30d AS INT)), 1) AS readmit_rate_pct
FROM f GROUP BY ALL;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.gold.hrrp_condition_err
COMMENT 'HRRP excess readmission ratio (ERR = observed rate / CMS expected rate) and penalty contribution per hospital x condition over the trailing-12-month performance window. Penalty line = condition base DRG payments x max(0, ERR-1) x neutrality modifier.'
AS WITH obs AS (
  SELECT hospital_id, hospital_name, condition, count(*) AS index_admissions,
         sum(CAST(readmit_30d AS INT)) AS readmissions
  FROM ${catalog}.gold.index_admissions
  WHERE trailing_12m AND is_hrrp_condition
  GROUP BY ALL
)
SELECT o.hospital_id, o.hospital_name, o.condition AS hrrp_condition, o.index_admissions, o.readmissions,
  round(o.readmissions / o.index_admissions, 4) AS observed_rate,
  r.expected_readmission_rate,
  round((o.readmissions / o.index_admissions) / r.expected_readmission_rate, 4) AS err,
  r.base_op_drg_payments_condition,
  round(r.base_op_drg_payments_condition * greatest(0, (o.readmissions / o.index_admissions) / r.expected_readmission_rate - 1)
        * r.neutrality_modifier, 2) AS penalty_contribution,
  r.total_base_op_drg_payments, r.penalty_cap, r.program_year
FROM obs o JOIN ${catalog}.silver.cms_hrrp_reference r
  ON o.hospital_id = r.hospital_id AND o.condition = r.hrrp_condition;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.gold.hrrp_hospital_penalty
COMMENT 'Estimated HRRP penalty per hospital: sum of condition contributions, capped at 3% of total base operating DRG payments.'
AS SELECT hospital_id, hospital_name,
  round(sum(penalty_contribution), 2) AS uncapped_penalty,
  max(total_base_op_drg_payments) AS total_base_op_drg_payments,
  max(total_base_op_drg_payments * penalty_cap) AS penalty_cap_amount,
  round(least(sum(penalty_contribution), max(total_base_op_drg_payments * penalty_cap)), 2) AS estimated_penalty,
  sum(penalty_contribution) > max(total_base_op_drg_payments * penalty_cap) AS at_cap,
  max_by(hrrp_condition, penalty_contribution) AS largest_condition,
  round(max(penalty_contribution), 2) AS largest_condition_contribution,
  round(max_by(err, penalty_contribution), 4) AS largest_condition_err
FROM ${catalog}.gold.hrrp_condition_err
GROUP BY hospital_id, hospital_name;
