# Dashboard verification (2026-11-09 18:32 UTC)

* dashboard `Readmissions & HRRP Executive (Cedarbrook Health)` id `01f1dc5df28f1375969046237b7df646`, lifecycle **ACTIVE**, published revision 2026-11-09T16:52:28.853Z, warehouse `12444b712298f9ac`
* 9 datasets, 15 widgets (definition read back from the workspace, not from the repo)

## Dataset queries (executed on the SQL warehouse)

### `ds_kpi`: ✅ 1 rows

```sql
SELECT h.estimated_penalty, h.largest_condition_contribution AS hf_line, h.largest_condition_err AS hf_err,
  u.last_20w_rate_pct AS sixn_last20, u.prior_20w_rate_pct AS sixn_prior20
FROM cedarbrook_rcc.gold.hrrp_hospital_penalty h CROSS JOIN cedarbrook_rcc.gold.unit_period_summary u
WHERE h.hospital_id = 'CUMC' AND u.unit_id = 'CUMC-6N' AND u.condition = 'HF'
```

| estimated_penalty | hf_line | hf_err | sixn_last20 | sixn_prior20 |
|---|---|---|---|---|
| 1620000.0 | 1139986.98 | 1.19 | 23.9 | 14.8 |

(1 rows)

### `ds_units`: ✅ 16 rows

```sql
SELECT concat(unit_name, ' (', hospital_id, ')') AS unit, delta_pts, prior_20w_rate_pct, last_20w_rate_pct FROM cedarbrook_rcc.gold.unit_period_summary WHERE condition = 'ALL'
```

| unit | delta_pts | prior_20w_rate_pct | last_20w_rate_pct |
|---|---|---|---|
| 3B Orthopedics (FCH) | -0.3 | 6.1 | 5.8 |
| 2A Medical (FCH) | 0.2 | 15.5 | 15.6 |
| 3 North Orthopedics (CUMC) | 0.7 | 5.1 | 5.8 |
| 7 West Medicine (CUMC) | 0.3 | 14.7 | 15.0 |
| 2 West Step-Down (CUMC) | 0.7 | 14.5 | 15.3 |
| Telemetry (PHMC) | 0.9 | 18.9 | 19.9 |
| 3A Telemetry (FCH) | -0.5 | 19.1 | 18.7 |
| 8 East CV Surgery (CUMC) | -0.2 | 11.5 | 11.3 |

(16 rows, first 8 shown)

### `ds_weekly`: ✅ 82 rows

```sql
SELECT discharge_week, CASE WHEN unit_id = 'CUMC-6N' THEN '6 North Telemetry' ELSE 'All other units' END AS unit_group,
  sum(readmissions) AS readmissions, sum(index_admissions) AS index_admissions,
  round(100 * sum(readmissions) / sum(index_admissions), 1) AS readmit_rate_pct
FROM cedarbrook_rcc.gold.unit_weekly_readmissions WHERE condition = 'HF' AND discharge_week >= '2025-12-29' GROUP BY ALL
```

| discharge_week | unit_group | readmissions | index_admissions | readmit_rate_pct |
|---|---|---|---|---|
| 2026-02-02 | 6 North Telemetry | 2 | 11 | 18.2 |
| 2026-02-16 | All other units | 3 | 16 | 18.8 |
| 2026-06-01 | All other units | 2 | 9 | 22.2 |
| 2026-07-27 | 6 North Telemetry | 2 | 8 | 25.0 |
| 2026-08-31 | All other units | 2 | 13 | 15.4 |
| 2026-04-06 | All other units | 2 | 9 | 22.2 |
| 2026-05-11 | All other units | 4 | 11 | 36.4 |
| 2026-08-17 | All other units | 2 | 14 | 14.3 |

(82 rows, first 8 shown)

### `ds_gap`: ✅ 4 rows

```sql
SELECT discharge_day_type, period, fu7_booked_pct, discharges FROM cedarbrook_rcc.gold.followup_gap WHERE unit_id = 'CUMC-6N' AND condition = 'HF'
```

| discharge_day_type | period | fu7_booked_pct | discharges |
|---|---|---|---|
| Weekend (Fri-Sun) | since_2026-06-19 | 17.7 | 62 |
| Weekday (Mon-Thu) | before_2026-06-19 | 71.9 | 416 |
| Weekend (Fri-Sun) | before_2026-06-19 | 69.2 | 234 |
| Weekday (Mon-Thu) | since_2026-06-19 | 68.6 | 137 |

(4 rows)

### `ds_penalty`: ✅ 16 rows

```sql
SELECT hospital_id, hrrp_condition, err, penalty_contribution, observed_rate, expected_readmission_rate, index_admissions, readmissions FROM cedarbrook_rcc.gold.hrrp_condition_err
```

| hospital_id | hrrp_condition | err | penalty_contribution | observed_rate | expected_readmission_rate | index_admissions | readmissions |
|---|---|---|---|---|---|---|---|
| FCH | AMI | 1.02 | 13999.58 | 0.1642 | 0.16096 | 67 | 11 |
| CUMC | PN | 1.05 | 200003.76 | 0.1605 | 0.15287 | 623 | 100 |
| PHMC | HF | 1.09 | 171002.73 | 0.2661 | 0.244123 | 233 | 62 |
| PHMC | COPD | 1.05 | 60001.18 | 0.2148 | 0.204538 | 149 | 32 |
| CUMC | THA_TKA | 0.94 | 0.0 | 0.0429 | 0.045633 | 373 | 16 |
| FCH | HF | 1.06 | 143999.38 | 0.2652 | 0.250143 | 264 | 70 |
| CUMC | CABG | 1.03 | 60004.26 | 0.1216 | 0.118079 | 148 | 18 |
| CUMC | COPD | 1.08 | 280000.49 | 0.1916 | 0.177397 | 428 | 82 |

(16 rows, first 8 shown)

### `ds_whatif`: ✅ 13 rows

```sql
SELECT fu7_target_pct, readmissions_avoided, penalty_saved, hf_err_scenario FROM cedarbrook_rcc.gold.hrrp_whatif WHERE scope = '6N weekend HF'
```

| fu7_target_pct | readmissions_avoided | penalty_saved | hf_err_scenario |
|---|---|---|---|
| 40 | 0.0 | 0.0 | 1.19 |
| 45 | 0.0 | 0.0 | 1.19 |
| 50 | 0.0 | 0.0 | 1.19 |
| 55 | 0.0 | 0.0 | 1.19 |
| 60 | 1.28 | 0.0 | 1.1802 |
| 65 | 2.59 | 58644.11 | 1.1702 |
| 70 | 3.9 | 118575.46 | 1.1602 |
| 75 | 5.21 | 178506.81 | 1.1502 |

(13 rows, first 8 shown)

### `ds_factors`: ✅ 6 rows

```sql
SELECT concat(factor, ' = ', value) AS factor_value, readmit_rate_pct, index_admissions
FROM cedarbrook_rcc.gold.readmission_risk_factors WHERE condition = 'HF' AND factor IN ('fu7_booked', 'ai_lives_alone', 'ai_transport_barrier')
```

| factor_value | readmit_rate_pct | index_admissions |
|---|---|---|
| ai_transport_barrier = true | 33.0 | 115 |
| ai_transport_barrier = false | 21.0 | 1188 |
| ai_lives_alone = true | 33.1 | 157 |
| ai_lives_alone = false | 20.6 | 1146 |
| fu7_booked = false | 29.8 | 554 |
| fu7_booked = true | 16.4 | 749 |

(6 rows)

### `ds_tiers`: ✅ 3 rows

```sql
SELECT risk_tier, count(*) AS index_admissions, round(100 * avg(CAST(readmit_30d AS INT)), 1) AS observed_readmit_pct
FROM cedarbrook_rcc.gold.patient_risk_scores WHERE outcome_complete GROUP BY risk_tier
```

| risk_tier | index_admissions | observed_readmit_pct |
|---|---|---|
| High | 1119 | 39.9 |
| Medium | 2462 | 22.4 |
| Low | 10135 | 8.9 |

(3 rows)

### `ds_whatif80`: ✅ 1 rows

```sql
SELECT fu7_target_pct, readmissions_avoided, penalty_saved, hf_err_scenario FROM cedarbrook_rcc.gold.hrrp_whatif WHERE scope = '6N weekend HF' AND fu7_target_pct = 80
```

| fu7_target_pct | readmissions_avoided | penalty_saved | hf_err_scenario |
|---|---|---|---|
| 80 | 6.52 | 238438.15 | 1.1403 |

(1 rows)

## Widget → dataset field check

| widget | type | title | dataset | fields | resolved |
|---|---|---|---|---|---|
| hdr | text | (header) | | | ✅ |
| k1 | counter | CUMC est. HRRP penalty ($, 3% cap) | ds_kpi | estimated_penalty | ✅ |
| k2 | counter | Heart-failure penalty line ($) | ds_kpi | hf_line | ✅ |
| k3 | counter | CUMC HF excess readmission ratio | ds_kpi | hf_err | ✅ |
| k4 | counter | 6N HF readmit %, prior 20 weeks | ds_kpi | sixn_prior20 | ✅ |
| k5 | counter | 6N HF readmit %, last 20 weeks | ds_kpi | sixn_last20 | ✅ |
| k6 | counter | Penalty saved if 6N books 80% of weekend HF follow-ups ($) | ds_whatif80 | penalty_saved | ✅ |
| c_weekly | line | Weekly HF 30-day readmission rate: 6 North vs all other units | ds_weekly | discharge_week, readmit_rate_pct, unit_group | ✅ |
| c_gap | bar | 6 North HF: % discharged with a booked 7-day follow-up | ds_gap | discharge_day_type, fu7_booked_pct, period | ✅ |
| c_units | bar | Change in all-cause readmission rate, last 20 vs prior 20 weeks (pts) | ds_units | delta_pts, unit | ✅ |
| c_pen | bar | HRRP penalty contribution by condition ($) | ds_penalty | hospital_id, hrrp_condition, penalty_contribution | ✅ |
| c_whatif | line | What-if: penalty saved vs 6N weekend follow-up booking target (%) | ds_whatif | fu7_target_pct, penalty_saved | ✅ |
| c_factors | bar | HF 30-day readmission % by risk factor (trailing 12m; AI = from note text) | ds_factors | factor_value, readmit_rate_pct | ✅ |
| c_tiers | bar | Model risk tier vs observed readmission % | ds_tiers | observed_readmit_pct, risk_tier | ✅ |
| t_err | table | Excess readmission ratio by hospital and condition | ds_penalty | err, expected_readmission_rate, hospital_id, hrrp_condition, index_admissions, observed_rate, penalty_contribution, readmissions | ✅ |

**Overall: PASS ✅**
