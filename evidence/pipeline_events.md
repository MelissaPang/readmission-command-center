# Lakeflow pipeline evidence: rcc_pipeline

* pipeline_id: `16d1c31b-07b3-4d62-8b02-19f82336f501` (serverless, Lakeflow Declarative Pipelines, SQL)
* source: `pipelines/01_bronze.sql`, `02_silver.sql`, `03_gold.sql`

## Recent updates

| update_id | state | full_refresh | full_refresh_selection | cause |
|---|---|---|---|---|
| 24a45c9a-feba-40b3-96be-5edeb5987ce2 | COMPLETED | False |  | JOB_TASK |
| 29e5a90c-1309-46de-9247-239fce052852 | COMPLETED | False |  | API_CALL |
| a3a33e90-22b1-4671-8dcf-bc9861b6e4fc | COMPLETED | False | cedarbrook_rcc.bronze.encounters,cedarbrook_rcc.bronze.patients,cedarbrook_rcc.b | API_CALL |
| 51f0cf91-7308-4a6e-8bf7-f8941d46d43c | COMPLETED | True |  | JOB_TASK |

### Rows written per flow (latest successful update of each table)


```sql
WITH ev AS (
  SELECT origin.update_id, origin.flow_name, timestamp,
         details:flow_progress.metrics.num_output_rows::bigint AS rows_out,
         details:flow_progress.status::string AS status
  FROM event_log('16d1c31b-07b3-4d62-8b02-19f82336f501') WHERE event_type = 'flow_progress')
SELECT flow_name, max_by(rows_out, timestamp) AS last_num_output_rows, max(timestamp) AS last_completed
FROM ev WHERE status = 'COMPLETED' AND rows_out IS NOT NULL
GROUP BY flow_name ORDER BY flow_name
```

| flow_name | last_num_output_rows | last_completed |
|---|---|---|
| cedarbrook_rcc.gold.encounters_enriched | 16584 | 2026-11-09T17:52:39.435Z |
| cedarbrook_rcc.gold.followup_gap | 160 | 2026-11-09T17:53:15.409Z |
| cedarbrook_rcc.gold.hrrp_condition_err | 16 | 2026-11-09T17:53:06.350Z |
| cedarbrook_rcc.gold.hrrp_hospital_penalty | 3 | 2026-11-09T17:53:17.902Z |
| cedarbrook_rcc.gold.index_admissions | 14475 | 2026-11-09T17:52:50.747Z |
| cedarbrook_rcc.gold.readmission_risk_factors | 56 | 2026-11-09T17:53:15.376Z |
| cedarbrook_rcc.gold.unit_period_summary | 56 | 2026-11-09T17:53:15.394Z |
| cedarbrook_rcc.gold.unit_weekly_readmissions | 2825 | 2026-11-09T17:53:15.389Z |
| cedarbrook_rcc.silver.cms_hrrp_reference | 16 | 2026-11-09T17:52:19.436Z |
| cedarbrook_rcc.silver.encounters | 16584 | 2026-11-09T17:52:19.482Z |
| cedarbrook_rcc.silver.followup_appointments | 11329 | 2026-11-09T17:52:19.490Z |
| cedarbrook_rcc.silver.hospitals | 3 | 2026-11-09T17:52:21.357Z |
| cedarbrook_rcc.silver.icd10_hrrp_map | 23 | 2026-11-09T17:52:23.816Z |
| cedarbrook_rcc.silver.patients | 14615 | 2026-11-09T17:52:21.495Z |
| cedarbrook_rcc.silver.staffing_events | 4 | 2026-11-09T17:52:19.476Z |
| cedarbrook_rcc.silver.units | 16 | 2026-11-09T17:52:19.450Z |

(16 rows)

### Data-quality expectations (all updates)

Summed over all pipeline updates (3 recomputes of silver, so each planted defect is counted 3 times). Planted defects: 6 encounters with discharge before admit are dropped (18 = 6 x 3); 45 duplicate encounter rows are removed by the QUALIFY de-dup.
```sql
SELECT origin.flow_name AS flow, e.name AS expectation, sum(e.passed_records) AS passed, sum(e.failed_records) AS failed
FROM event_log('16d1c31b-07b3-4d62-8b02-19f82336f501')
LATERAL VIEW explode(from_json(details:flow_progress.data_quality.expectations,
  'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) x AS e
WHERE event_type = 'flow_progress' AND details:flow_progress.data_quality.expectations IS NOT NULL
GROUP BY ALL ORDER BY flow, expectation
```

| flow | expectation | passed | failed |
|---|---|---|---|
| cedarbrook_rcc.silver.cms_hrrp_reference | expected_rate_valid | 48 | 0 |
| cedarbrook_rcc.silver.discharge_notes | note_has_text | 16584 | 0 |
| cedarbrook_rcc.silver.encounters | discharge_after_admit | 49752 | 18 |
| cedarbrook_rcc.silver.encounters | encounter_id_present | 49770 | 0 |
| cedarbrook_rcc.silver.encounters | patient_id_present | 49770 | 0 |
| cedarbrook_rcc.silver.encounters | unit_present | 49770 | 0 |
| cedarbrook_rcc.silver.followup_appointments | appointment_has_encounter | 33987 | 0 |
| cedarbrook_rcc.silver.patients | patient_id_present | 43845 | 0 |

(8 rows)

### Dropped rows per dataset (data_quality.dropped_records)


```sql
SELECT origin.flow_name AS flow, sum(details:flow_progress.data_quality.dropped_records::bigint) AS dropped_records
FROM event_log('16d1c31b-07b3-4d62-8b02-19f82336f501') WHERE event_type = 'flow_progress' AND details:flow_progress.data_quality.dropped_records IS NOT NULL
GROUP BY ALL ORDER BY flow
```

| flow | dropped_records |
|---|---|
| cedarbrook_rcc.bronze.cms_hrrp_reference | 0 |
| cedarbrook_rcc.bronze.discharge_notes | 0 |
| cedarbrook_rcc.bronze.encounters | 0 |
| cedarbrook_rcc.bronze.followup_appointments | 0 |
| cedarbrook_rcc.bronze.hospitals | 0 |
| cedarbrook_rcc.bronze.icd10_hrrp_map | 0 |
| cedarbrook_rcc.bronze.patients | 0 |
| cedarbrook_rcc.bronze.staffing_events | 0 |
| cedarbrook_rcc.bronze.units | 0 |
| cedarbrook_rcc.gold.encounters_enriched | 0 |
| cedarbrook_rcc.gold.followup_gap | 0 |
| cedarbrook_rcc.gold.hrrp_condition_err | 0 |
| cedarbrook_rcc.gold.hrrp_hospital_penalty | 0 |
| cedarbrook_rcc.gold.index_admissions | 0 |
| cedarbrook_rcc.gold.readmission_risk_factors | 0 |
| cedarbrook_rcc.gold.unit_period_summary | 0 |
| cedarbrook_rcc.gold.unit_weekly_readmissions | 0 |
| cedarbrook_rcc.silver.cms_hrrp_reference | 0 |
| cedarbrook_rcc.silver.discharge_note_signals | 0 |
| cedarbrook_rcc.silver.discharge_notes | 0 |
| cedarbrook_rcc.silver.encounters | 18 |
| cedarbrook_rcc.silver.followup_appointments | 0 |
| cedarbrook_rcc.silver.hospitals | 0 |
| cedarbrook_rcc.silver.icd10_hrrp_map | 0 |
| cedarbrook_rcc.silver.patients | 0 |
| cedarbrook_rcc.silver.staffing_events | 0 |
| cedarbrook_rcc.silver.units | 0 |

(27 rows)

### Row counts bronze -> silver -> gold


```sql
SELECT 'bronze.encounters' AS t, count(*) AS n FROM cedarbrook_rcc.bronze.encounters UNION ALL
SELECT 'silver.encounters (dedup + DQ)', count(*) FROM cedarbrook_rcc.silver.encounters UNION ALL
SELECT 'gold.index_admissions', count(*) FROM cedarbrook_rcc.gold.index_admissions UNION ALL
SELECT 'bronze.discharge_notes', count(*) FROM cedarbrook_rcc.bronze.discharge_notes UNION ALL
SELECT 'silver.discharge_note_signals (AI)', count(*) FROM cedarbrook_rcc.silver.discharge_note_signals UNION ALL
SELECT 'silver.discharge_note_signals ai_error', count_if(ai_error IS NOT NULL) FROM cedarbrook_rcc.silver.discharge_note_signals UNION ALL
SELECT 'gold.patient_risk_scores', count(*) FROM cedarbrook_rcc.gold.patient_risk_scores UNION ALL
SELECT 'gold.discharge_worklist', count(*) FROM cedarbrook_rcc.gold.discharge_worklist
```

| t | n |
|---|---|
| silver.encounters (dedup + DQ) | 16584 |
| silver.discharge_note_signals ai_error | 0 |
| gold.patient_risk_scores | 14475 |
| bronze.encounters | 16635 |
| gold.index_admissions | 14475 |
| bronze.discharge_notes | 16584 |
| silver.discharge_note_signals (AI) | 16584 |
| gold.discharge_worklist | 705 |

(8 rows)
