# Query results (SQL warehouse, gold tables)

Every number in the customer story, queried from the gold layer.

### 6 North vs every other unit: prior 20 weeks vs last 20 weeks


```sql
SELECT hospital_id, unit_name, condition, prior_20w_index, prior_20w_rate_pct, last_20w_index, last_20w_rate_pct, delta_pts FROM cedarbrook_rcc.gold.unit_period_summary WHERE condition = 'ALL' OR (unit_id = 'CUMC-6N' AND condition = 'HF') ORDER BY condition DESC, delta_pts DESC
```

| hospital_id | unit_name | condition | prior_20w_index | prior_20w_rate_pct | last_20w_index | last_20w_rate_pct | delta_pts |
|---|---|---|---|---|---|---|---|
| CUMC | 6 North Telemetry | HF | 230 | 14.8 | 209 | 23.9 | 9.1 |
| CUMC | 6 North Telemetry | ALL | 408 | 14.2 | 377 | 19.1 | 4.9 |
| PHMC | Telemetry | ALL | 206 | 18.9 | 151 | 19.9 | 0.9 |
| CUMC | 3 North Orthopedics | ALL | 236 | 5.1 | 242 | 5.8 | 0.7 |
| CUMC | 2 West Step-Down | ALL | 165 | 14.5 | 216 | 15.3 | 0.7 |
| PHMC | ICU / Step-Down | ALL | 119 | 15.1 | 109 | 15.6 | 0.5 |
| CUMC | 7 West Medicine | ALL | 293 | 14.7 | 293 | 15.0 | 0.3 |
| PHMC | Med-Surg 1 | ALL | 300 | 15.7 | 244 | 16.0 | 0.3 |
| FCH | 2A Medical | ALL | 323 | 15.5 | 294 | 15.6 | 0.2 |
| CUMC | 8 East CV Surgery | ALL | 139 | 11.5 | 141 | 11.3 | -0.2 |
| FCH | 3B Orthopedics | ALL | 147 | 6.1 | 171 | 5.8 | -0.3 |
| CUMC | 9 North General Medicine | ALL | 314 | 15.0 | 265 | 14.7 | -0.3 |
| CUMC | 4 South Pulmonary | ALL | 259 | 16.2 | 245 | 15.9 | -0.3 |
| FCH | 2B Surgical | ALL | 157 | 8.3 | 202 | 7.9 | -0.4 |
| FCH | 3A Telemetry | ALL | 251 | 19.1 | 241 | 18.7 | -0.5 |
| CUMC | 5 East Cardiology | ALL | 244 | 15.2 | 234 | 14.5 | -0.6 |
| PHMC | Med-Surg 2 | ALL | 201 | 10.0 | 203 | 8.9 | -1.1 |

(17 rows)

### 7-day follow-up gap on 6 North (HF)


```sql
SELECT * FROM cedarbrook_rcc.gold.followup_gap WHERE unit_id = 'CUMC-6N' AND condition = 'HF' ORDER BY period, discharge_day_type
```

| hospital_id | unit_id | unit_name | condition | discharge_day_type | period | discharges | fu7_booked | fu7_booked_pct |
|---|---|---|---|---|---|---|---|---|
| CUMC | CUMC-6N | 6 North Telemetry | HF | Weekday (Mon-Thu) | before_2026-06-19 | 416 | 299 | 71.9 |
| CUMC | CUMC-6N | 6 North Telemetry | HF | Weekend (Fri-Sun) | before_2026-06-19 | 234 | 162 | 69.2 |
| CUMC | CUMC-6N | 6 North Telemetry | HF | Weekday (Mon-Thu) | since_2026-06-19 | 137 | 94 | 68.6 |
| CUMC | CUMC-6N | 6 North Telemetry | HF | Weekend (Fri-Sun) | since_2026-06-19 | 62 | 11 | 17.7 |

(4 rows)

### HF readmission by risk factor, trailing 12 months, all hospitals


```sql
SELECT factor, value, index_admissions, readmissions, readmit_rate_pct FROM cedarbrook_rcc.gold.readmission_risk_factors WHERE condition = 'HF' ORDER BY factor, value
```

| factor | value | index_admissions | readmissions | readmit_rate_pct |
|---|---|---|---|---|
| ai_lives_alone | false | 1146 | 236 | 20.6 |
| ai_lives_alone | true | 157 | 52 | 33.1 |
| ai_transport_barrier | false | 1188 | 250 | 21.0 |
| ai_transport_barrier | true | 115 | 38 | 33.0 |
| fu7_booked | false | 554 | 165 | 29.8 |
| fu7_booked | true | 749 | 123 | 16.4 |
| weekend_discharge | false | 855 | 179 | 20.9 |
| weekend_discharge | true | 448 | 109 | 24.3 |

(8 rows)

### HRRP ERR and penalty contribution


```sql
SELECT hospital_id, hrrp_condition, index_admissions, readmissions, observed_rate, expected_readmission_rate, err, base_op_drg_payments_condition, penalty_contribution FROM cedarbrook_rcc.gold.hrrp_condition_err ORDER BY hospital_id, penalty_contribution DESC
```

| hospital_id | hrrp_condition | index_admissions | readmissions | observed_rate | expected_readmission_rate | err | base_op_drg_payments_condition | penalty_contribution |
|---|---|---|---|---|---|---|---|---|
| CUMC | HF | 806 | 156 | 0.1935 | 0.162646 | 1.19 | 6000000.0 | 1139986.98 |
| CUMC | COPD | 428 | 82 | 0.1916 | 0.177397 | 1.08 | 3500000.0 | 280000.49 |
| CUMC | PN | 623 | 100 | 0.1605 | 0.15287 | 1.05 | 4000000.0 | 200003.76 |
| CUMC | CABG | 148 | 18 | 0.1216 | 0.118079 | 1.03 | 2000000.0 | 60004.26 |
| CUMC | THA_TKA | 373 | 16 | 0.0429 | 0.045633 | 0.94 | 5100000.0 | 0.0 |
| CUMC | AMI | 305 | 46 | 0.1508 | 0.155484 | 0.97 | 3200000.0 | 0.0 |
| FCH | HF | 264 | 70 | 0.2652 | 0.250143 | 1.06 | 2400000.0 | 143999.38 |
| FCH | COPD | 153 | 30 | 0.1961 | 0.188537 | 1.04 | 1300000.0 | 51999.66 |
| FCH | AMI | 67 | 11 | 0.1642 | 0.16096 | 1.02 | 700000.0 | 13999.58 |
| FCH | THA_TKA | 257 | 13 | 0.0506 | 0.052691 | 0.96 | 1900000.0 | 0.0 |
| FCH | PN | 204 | 36 | 0.1765 | 0.178253 | 0.99 | 1600000.0 | 0.0 |
| PHMC | HF | 233 | 62 | 0.2661 | 0.244123 | 1.09 | 1900000.0 | 171002.73 |
| PHMC | COPD | 149 | 32 | 0.2148 | 0.204538 | 1.05 | 1200000.0 | 60001.18 |
| PHMC | PN | 262 | 45 | 0.1718 | 0.170055 | 1.01 | 1400000.0 | 14001.44 |
| PHMC | THA_TKA | 106 | 5 | 0.0472 | 0.05072 | 0.93 | 600000.0 | 0.0 |
| PHMC | AMI | 46 | 7 | 0.1522 | 0.15528 | 0.98 | 500000.0 | 0.0 |

(16 rows)

### Estimated HRRP penalty per hospital


```sql
SELECT * FROM cedarbrook_rcc.gold.hrrp_hospital_penalty ORDER BY estimated_penalty DESC
```

| hospital_id | hospital_name | uncapped_penalty | total_base_op_drg_payments | penalty_cap_amount | estimated_penalty | at_cap | largest_condition | largest_condition_contribution | largest_condition_err |
|---|---|---|---|---|---|---|---|---|---|
| CUMC | Cedarbrook University Medical Center | 1679995.49 | 5.4E7 | 1620000.0 | 1620000.0 | true | HF | 1139986.98 | 1.19 |
| PHMC | Pine Hollow Medical Center | 245005.35 | 1.68E7 | 504000.0 | 245005.35 | false | HF | 171002.73 | 1.09 |
| FCH | Fairhaven Community Hospital | 209998.62 | 2.15E7 | 645000.0 | 209998.62 | false | HF | 143999.38 | 1.06 |

(3 rows)

### Deterministic what-if (selected targets)


```sql
SELECT scope, fu7_target_pct, discharges_12m, booked_12m, current_fu7_pct, additional_followups, readmissions_avoided, hf_err_current, hf_err_scenario, penalty_current, penalty_scenario, penalty_saved FROM cedarbrook_rcc.gold.hrrp_whatif WHERE fu7_target_pct IN (60, 70, 80, 90, 100) ORDER BY scope, fu7_target_pct
```

| scope | fu7_target_pct | discharges_12m | booked_12m | current_fu7_pct | additional_followups | readmissions_avoided | hf_err_current | hf_err_scenario | penalty_current | penalty_scenario | penalty_saved |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 6N weekend HF | 60 | 196 | 108 | 55.1 | 9.6 | 1.28 | 1.19 | 1.1802 | 1620000.0 | 1620000.0 | 0.0 |
| 6N weekend HF | 70 | 196 | 108 | 55.1 | 29.2 | 3.9 | 1.19 | 1.1602 | 1620000.0 | 1501424.54 | 118575.46 |
| 6N weekend HF | 80 | 196 | 108 | 55.1 | 48.8 | 6.52 | 1.19 | 1.1403 | 1620000.0 | 1381561.85 | 238438.15 |
| 6N weekend HF | 90 | 196 | 108 | 55.1 | 68.4 | 9.14 | 1.19 | 1.1203 | 1620000.0 | 1261699.15 | 358300.85 |
| 6N weekend HF | 100 | 196 | 108 | 55.1 | 88.0 | 11.76 | 1.19 | 1.1003 | 1620000.0 | 1141836.46 | 478163.54 |
| CUMC all HF discharges | 60 | 806 | 492 | 61.0 | 0.0 | 0.0 | 1.19 | 1.19 | 1620000.0 | 1620000.0 | 0.0 |
| CUMC all HF discharges | 70 | 806 | 492 | 61.0 | 72.2 | 9.65 | 1.19 | 1.1164 | 1620000.0 | 1238460.47 | 381539.53 |
| CUMC all HF discharges | 80 | 806 | 492 | 61.0 | 152.8 | 20.42 | 1.19 | 1.0343 | 1620000.0 | 745555.72 | 874444.28 |
| CUMC all HF discharges | 90 | 806 | 492 | 61.0 | 233.4 | 31.19 | 1.19 | 0.9521 | 1620000.0 | 540008.51 | 1079991.49 |
| CUMC all HF discharges | 100 | 806 | 492 | 61.0 | 314.0 | 41.96 | 1.19 | 0.87 | 1620000.0 | 540008.51 | 1079991.49 |
| CUMC weekend HF (all units) | 60 | 289 | 154 | 53.3 | 19.4 | 2.59 | 1.19 | 1.1702 | 1620000.0 | 1561355.89 | 58644.11 |
| CUMC weekend HF (all units) | 70 | 289 | 154 | 53.3 | 48.3 | 6.45 | 1.19 | 1.1408 | 1620000.0 | 1384619.57 | 235380.43 |
| CUMC weekend HF (all units) | 80 | 289 | 154 | 53.3 | 77.2 | 10.32 | 1.19 | 1.1113 | 1620000.0 | 1207883.25 | 412116.75 |
| CUMC weekend HF (all units) | 90 | 289 | 154 | 53.3 | 106.1 | 14.18 | 1.19 | 1.0819 | 1620000.0 | 1031146.93 | 588853.07 |
| CUMC weekend HF (all units) | 100 | 289 | 154 | 53.3 | 135.0 | 18.04 | 1.19 | 1.0524 | 1620000.0 | 854410.61 | 765589.39 |

(15 rows)

### Registered model metrics


```sql
SELECT * FROM cedarbrook_rcc.ml.model_metrics
```

| auc | avg_precision | base_rate | brier | champion_algorithm | hist_gbm_auc | logreg_auc | model_name | run_id | top_decile_lift | top_decile_readmit_rate | version |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.7245 | 0.3226 | 0.1411 | 0.11 | logreg_baseline | 0.7137 | 0.7245 | cedarbrook_rcc.ml.readmit_30d_risk | 7c321ae48dc940c9a5142bd0a4e299ee | 2.6034 | 0.3674 | 2 |

(1 rows)

### Risk tier vs observed readmission (complete outcomes)


```sql
SELECT risk_tier, count(*) AS index_admissions, round(avg(risk_score), 3) AS mean_score, round(100 * avg(CAST(readmit_30d AS INT)), 1) AS observed_readmit_pct FROM cedarbrook_rcc.gold.patient_risk_scores WHERE outcome_complete GROUP BY risk_tier ORDER BY mean_score DESC
```

| risk_tier | index_admissions | mean_score | observed_readmit_pct |
|---|---|---|---|
| High | 1119 | 0.393 | 39.9 |
| Medium | 2462 | 0.229 | 22.4 |
| Low | 10135 | 0.089 | 8.9 |

(3 rows)

### Top 6 North worklist rows (served to the app via Lakebase)


```sql
SELECT encounter_id, unit_name, condition, discharge_ts, weekend_discharge, fu7_booked, ai_lives_alone, risk_score, risk_tier, driver_1, driver_2, recommended_actions FROM cedarbrook_rcc.gold.discharge_worklist WHERE unit_id = 'CUMC-6N' ORDER BY risk_score DESC LIMIT 10
```

| encounter_id | unit_name | condition | discharge_ts | weekend_discharge | fu7_booked | ai_lives_alone | risk_score | risk_tier | driver_1 | driver_2 | recommended_actions |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1014381 | 6 North Telemetry | HF | 2026-11-04T12:45:00.000Z | false | false | false | 0.5461 | High | No 7-day follow-up booked | High comorbidity burden | Book 7-day follow-up (HF Bridge Clinic / PCP); Pharmacist med-reconciliation call within 48h |
| E1014087 | 6 North Telemetry | OTHER | 2026-10-24T11:34:00.000Z | true | false | true | 0.4462 | High | No 7-day follow-up booked | Prior admissions in last 12 months | Book 7-day follow-up (HF Bridge Clinic / PCP); Caregiver check + home-health referral |
| E1013819 | 6 North Telemetry | OTHER | 2026-10-14T11:55:00.000Z | false | false | true | 0.3878 | High | No 7-day follow-up booked | High comorbidity burden | Book 7-day follow-up (HF Bridge Clinic / PCP); Caregiver check + home-health referral |
| E1014314 | 6 North Telemetry | HF | 2026-11-02T13:00:00.000Z | false | false | true | 0.3426 | High | No 7-day follow-up booked | Prior admissions in last 12 months | Book 7-day follow-up (HF Bridge Clinic / PCP); Caregiver check + home-health referral; Pharmacist med-reconciliation cal |
| E1014336 | 6 North Telemetry | HF | 2026-11-03T11:07:00.000Z | false | true | false | 0.3329 | High | High comorbidity burden | Long length of stay | Pharmacist med-reconciliation call within 48h |
| E1014318 | 6 North Telemetry | HF | 2026-11-02T13:44:00.000Z | false | false | true | 0.3291 | High | No 7-day follow-up booked | Lives alone / no caregiver (from note) | Book 7-day follow-up (HF Bridge Clinic / PCP); Caregiver check + home-health referral; Pharmacist med-reconciliation cal |
| E1014074 | 6 North Telemetry | HF | 2026-10-23T16:31:00.000Z | true | false | false | 0.3206 | High | No 7-day follow-up booked | High comorbidity burden | Book 7-day follow-up (HF Bridge Clinic / PCP); Pharmacist med-reconciliation call within 48h |
| E1014451 | 6 North Telemetry | AMI | 2026-11-07T14:08:00.000Z | true | false | false | 0.3203 | High | High comorbidity burden | No 7-day follow-up booked | Book 7-day follow-up (HF Bridge Clinic / PCP) |
| E1013820 | 6 North Telemetry | HF | 2026-10-14T12:37:00.000Z | false | true | true | 0.3201 | High | High comorbidity burden | Lives alone / no caregiver (from note) | Caregiver check + home-health referral; Pharmacist med-reconciliation call within 48h |
| E1013960 | 6 North Telemetry | HF | 2026-10-19T15:33:00.000Z | false | false | true | 0.3166 | High | No 7-day follow-up booked | Lives alone / no caregiver (from note) | Book 7-day follow-up (HF Bridge Clinic / PCP); Caregiver check + home-health referral; Pharmacist med-reconciliation cal |

(10 rows)

### App write-back read from the lakehouse (rcc_lakebase UC catalog -> Lakebase Postgres)


```sql
SELECT plan_id, encounter_id, status, model_endpoint, approved_by, approved_ts FROM rcc_lakebase.app_rcc.transition_plans ORDER BY created_ts DESC
```

| plan_id | encounter_id | status | model_endpoint | approved_by | approved_ts |
|---|---|---|---|---|---|
| c66e94d57e36 | E1014082 | approved | databricks-claude-sonnet-4-6 | melissa.pang@databricks.com | 2026-11-09T17:48:47.567Z |

(1 rows)

### Story validation results (notebook 99)


```sql
SELECT * FROM cedarbrook_rcc.gold.story_validation
```

| check | actual | expected | passed |
|---|---|---|---|
| 6N HF readmit rate, prior 20 weeks | 14.8% | 14.8% | true |
| 6N HF readmit rate, last 20 weeks | 23.9% | 23.9% | true |
| 6N HF change (pts) | 9.1 | +9.1 | true |
| Every other unit within ~1.5 pts (all-cause) | 1.1 | <= 1.5 | true |
| 6N weekend HF discharges with 7-day FU since 2026-06-19 | 18% (11/62) | 18% | true |
| 6N weekday HF discharges with 7-day FU since 2026-06-19 | 69% (94/137) | 69% | true |
| Unbooked 6N weekend notes say 'patient to call / schedule' (AI) | 51/51 | majority | true |
| HF 12m readmit, no 7-day FU | 29.8% | 29.8% | true |
| HF 12m readmit, with 7-day FU | 16.4% | 16.4% | true |
| HF 12m readmit, lives alone (AI from free text) | 33.1% | 33.1% (+/-0.5 for AI extraction) | true |
| HF 12m readmit, not living alone (AI) | 20.6% | 20.6% (+/-0.5) | true |
| CUMC estimated HRRP penalty | $1,620,000 (at cap: True) | $1.62M | true |
| Largest penalty line is HF | HF $1,139,987 | HF $1.14M | true |
| CUMC HF ERR | 1.19 | 1.19 | true |
| What-if 80%: readmissions avoided | 6.52 | ~7 | true |
| What-if 80%: HF ERR | 1.14 | 1.14 | true |
| What-if 80%: penalty saved | $238,438 | ~$240K | true |
| UC model registered @champion | cedarbrook_rcc.ml.readmit_30d_risk v2 | exists | true |
| Model test AUC | 0.7245 | > 0.65 | true |
| Lakebase synced table public.discharge_worklist | SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE | ONLINE* | true |
| Lakebase synced table public.hrrp_whatif | SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE | ONLINE* | true |
| Lakebase synced table public.unit_weekly | SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE | ONLINE* | true |
| Lakebase synced table public.hrrp_hospital | SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE | ONLINE* | true |
| App-approved transition plans visible in UC via Lakebase catalog | 1 approved / 1 plans | >= 1 approved | true |
| Genie answered story questions | 5/5 | all COMPLETED | true |
| Column mask hides PHI for non care_transitions | ***MASKED*** | ***MASKED*** | true |
| Row filter limits patient rows to hospital scope | 3424 of 14475 | < total | true |

(27 rows)
