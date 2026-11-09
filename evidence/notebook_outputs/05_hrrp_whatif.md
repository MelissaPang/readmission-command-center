# Executed notebook: hrrp_whatif

job run `206873801708733` · task run `301344254297234` · result **SUCCESS** · 2026-11-09 17:53:47 UTC

# 05 · HRRP penalty and deterministic what-if

**Question:** if 6 North had booked a 7-day follow-up for X% of its weekend (Fri–Sun) HF discharges, how many
readmissions would CUMC have avoided over the trailing 12 months, and what would that do to the HF ERR and the
HRRP penalty?

**Method (deterministic, no model):**
1. `converted = max(0, X% × weekend discharges − weekend discharges already booked)`
2. `avoided = converted × (readmit rate without 7-day FU − rate with 7-day FU)`, using HF rates over the trailing 12 months, all hospitals
3. `ERR' = ((readmissions − avoided) / index admissions) / expected rate`
4. `penalty' = min(3% cap, Σ condition payments × max(0, ERR' − 1))`, recomputed for the whole hospital

Scenarios are written for X from 40% to 100% (the app's slider) and for three scopes.

```python
dbutils.widgets.text("catalog", "cedarbrook_rcc")
catalog = dbutils.widgets.get("catalog")

import pandas as pd

display(spark.sql(f"SELECT * FROM {catalog}.gold.hrrp_hospital_penalty ORDER BY estimated_penalty DESC"))
display(spark.sql(f"""SELECT hospital_id, hrrp_condition, index_admissions, readmissions, observed_rate, expected_readmission_rate, err,
                             base_op_drg_payments_condition, penalty_contribution
                      FROM {catalog}.gold.hrrp_condition_err WHERE hospital_id = 'CUMC' ORDER BY penalty_contribution DESC"""))
```

Output:

```text
| hospital_id | hospital_name                        | uncapped_penalty | total_base_op_drg_payments | penalty_cap_amount | estimated_penalty | at_cap | largest_condition | largest_condition_contribution | largest_condition_err |
|-------------|--------------------------------------|------------------|----------------------------|--------------------|-------------------|--------|-------------------|--------------------------------|-----------------------|
| CUMC        | Cedarbrook University Medical Center | 1679995.49       | 54000000.0                 | 1620000.0          | 1620000.0         | True   | HF                | 1139986.98                     | 1.19                  |
| PHMC        | Pine Hollow Medical Center           | 245005.35        | 16800000.0                 | 504000.0           | 245005.35         | False  | HF                | 171002.73                      | 1.09                  |
| FCH         | Fairhaven Community Hospital         | 209998.62        | 21500000.0                 | 645000.0           | 209998.62         | False  | HF                | 143999.38                      | 1.06                  |
(3 rows shown)
| hospital_id | hrrp_condition | index_admissions | readmissions | observed_rate | expected_readmission_rate | err  | base_op_drg_payments_condition | penalty_contribution |
|-------------|----------------|------------------|--------------|---------------|---------------------------|------|--------------------------------|----------------------|
| CUMC        | HF             | 806              | 156          | 0.1935        | 0.162646                  | 1.19 | 6000000.0                      | 1139986.98           |
| CUMC        | COPD           | 428              | 82           | 0.1916        | 0.177397                  | 1.08 | 3500000.0                      | 280000.49            |
| CUMC        | PN             | 623              | 100          | 0.1605        | 0.15287                   | 1.05 | 4000000.0                      | 200003.76            |
| CUMC        | CABG           | 148              | 18           | 0.1216        | 0.118079                  | 1.03 | 2000000.0                      | 60004.26             |
| CUMC        | THA_TKA        | 373              | 16           | 0.0429        | 0.045633                  | 0.94 | 5100000.0                      | 0.0                  |
| CUMC        | AMI            | 305              | 46           | 0.1508        | 0.155484                  | 0.97 | 3200000.0                      | 0.0                  |
(6 rows shown)
```

```python
rates = {r.value: r.readmit_rate_pct / 100 for r in spark.sql(
    f"SELECT value, readmit_rate_pct FROM {catalog}.gold.readmission_risk_factors WHERE condition='HF' AND factor='fu7_booked'").collect()}
r_nofu, r_fu = rates["false"], rates["true"]
# use unrounded rates for the computation
exact = spark.sql(f"""SELECT avg(CASE WHEN NOT fu7_booked THEN CAST(readmit_30d AS INT) END) AS r_nofu,
                             avg(CASE WHEN fu7_booked THEN CAST(readmit_30d AS INT) END) AS r_fu
                      FROM {catalog}.gold.index_admissions WHERE trailing_12m AND condition='HF'""").first()
r_nofu, r_fu = float(exact.r_nofu), float(exact.r_fu)
print(f"HF trailing-12m readmit rate: no 7-day FU {r_nofu:.4f} | with 7-day FU {r_fu:.4f} | delta {r_nofu - r_fu:.4f}")

scopes = {
    "6N weekend HF": "unit_id = 'CUMC-6N' AND weekend_discharge",
    "CUMC weekend HF (all units)": "hospital_id = 'CUMC' AND weekend_discharge",
    "CUMC all HF discharges": "hospital_id = 'CUMC'",
}
base = {r.scope: r for r in spark.sql(" UNION ALL ".join(
    f"SELECT '{name}' AS scope, count(*) AS discharges, sum(CAST(fu7_booked AS INT)) AS booked FROM {catalog}.gold.index_admissions "
    f"WHERE trailing_12m AND condition='HF' AND {cond}" for name, cond in scopes.items())).collect()}
err = spark.table(f"{catalog}.gold.hrrp_condition_err").where("hospital_id = 'CUMC'").toPandas()
hf = err[err.hrrp_condition == "HF"].iloc[0]
cap = float(err.total_base_op_drg_payments.iloc[0] * err.penalty_cap.iloc[0])
others = float(err[err.hrrp_condition != "HF"].penalty_contribution.sum())
penalty_now = min(cap, others + float(hf.penalty_contribution))

rows = []
for scope, b in base.items():
    for target in range(40, 101, 5):
        converted = max(0.0, target / 100 * b.discharges - b.booked)
        avoided = converted * (r_nofu - r_fu)
        new_err = ((hf.readmissions - avoided) / hf.index_admissions) / hf.expected_readmission_rate
        new_hf_line = hf.base_op_drg_payments_condition * max(0.0, new_err - 1)
        new_penalty = min(cap, others + new_hf_line)
        rows.append(dict(hospital_id="CUMC", scope=scope, fu7_target_pct=target, discharges_12m=int(b.discharges),
                         booked_12m=int(b.booked), current_fu7_pct=round(100 * b.booked / b.discharges, 1),
                         additional_followups=round(converted, 1), readmissions_avoided=round(avoided, 2),
                         hf_err_current=round(float(hf.err), 4), hf_err_scenario=round(new_err, 4),
                         penalty_current=round(penalty_now, 2), penalty_scenario=round(new_penalty, 2),
                         penalty_saved=round(penalty_now - new_penalty, 2),
                         rate_no_fu7=round(r_nofu, 4), rate_with_fu7=round(r_fu, 4)))
whatif = pd.DataFrame(rows)
spark.createDataFrame(whatif).write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{catalog}.gold.hrrp_whatif")
spark.sql(f"COMMENT ON TABLE {catalog}.gold.hrrp_whatif IS 'Deterministic HRRP what-if: raising 7-day follow-up booking for a discharge scope to a target %, with resulting avoided readmissions, HF ERR and penalty (CUMC, trailing 12 months).'")
```

Output:

```text
HF trailing-12m readmit rate: no 7-day FU 0.2978 | with 7-day FU 0.1642 | delta 0.1336
```

### Story scenario: 6 North weekend HF discharges at 80% booked

```python
s = whatif[(whatif.scope == "6N weekend HF") & (whatif.fu7_target_pct == 80)].iloc[0]
print(f"""6 North weekend HF discharges (trailing 12m): {s.discharges_12m}, booked {s.booked_12m} ({s.current_fu7_pct}%)
Raise to 80%  -> {s.additional_followups:.1f} more patients leave with a 7-day follow-up
Avoided readmissions: {s.readmissions_avoided:.2f}  (~{round(s.readmissions_avoided)})
CUMC HF ERR: {s.hf_err_current:.2f} -> {s.hf_err_scenario:.2f}
CUMC estimated HRRP penalty: ${s.penalty_current:,.0f} -> ${s.penalty_scenario:,.0f}  (saves ${s.penalty_saved:,.0f})""")
display(spark.sql(f"SELECT * FROM {catalog}.gold.hrrp_whatif WHERE fu7_target_pct IN (60, 70, 80, 90, 100) ORDER BY scope, fu7_target_pct"))
```

Output:

```text
6 North weekend HF discharges (trailing 12m): 196, booked 108 (55.1%)
Raise to 80%  -> 48.8 more patients leave with a 7-day follow-up
Avoided readmissions: 6.52  (~7)
CUMC HF ERR: 1.19 -> 1.14
CUMC estimated HRRP penalty: $1,620,000 -> $1,381,562  (saves $238,438)
| hospital_id | scope                       | fu7_target_pct | discharges_12m | booked_12m | current_fu7_pct | additional_followups | readmissions_avoided | hf_err_current | hf_err_scenario | penalty_current | penalty_scenario | penalty_saved | rate_no_fu7 | rate_with_fu7 |
|-------------|-----------------------------|----------------|----------------|------------|-----------------|----------------------|----------------------|----------------|-----------------|-----------------|------------------|---------------|-------------|---------------|
| CUMC        | 6N weekend HF               | 60             | 196            | 108        | 55.1            | 9.6                  | 1.28                 | 1.19           | 1.1802          | 1620000.0       | 1620000.0        | 0.0           | 0.2978      | 0.1642        |
| CUMC        | 6N weekend HF               | 70             | 196            | 108        | 55.1            | 29.2                 | 3.9                  | 1.19           | 1.1602          | 1620000.0       | 1501424.54       | 118575.46     | 0.2978      | 0.1642        |
| CUMC        | 6N weekend HF               | 80             | 196            | 108        | 55.1            | 48.8                 | 6.52                 | 1.19           | 1.1403          | 1620000.0       | 1381561.85       | 238438.15     | 0.2978      | 0.1642        |
| CUMC        | 6N weekend HF               | 90             | 196            | 108        | 55.1            | 68.4                 | 9.14                 | 1.19           | 1.1203          | 1620000.0       | 1261699.15       | 358300.85     | 0.2978      | 0.1642        |
| CUMC        | 6N weekend HF               | 100            | 196            | 108        | 55.1            | 88.0                 | 11.76                | 1.19           | 1.1003          | 1620000.0       | 1141836.46       | 478163.54     | 0.2978      | 0.1642        |
| CUMC        | CUMC all HF discharges      | 60             | 806            | 492        | 61.0            | 0.0                  | 0.0                  | 1.19           | 1.19            | 1620000.0       | 1620000.0        | 0.0           | 0.2978      | 0.1642        |
| CUMC        | CUMC all HF discharges      | 70             | 806            | 492        | 61.0            | 72.2                 | 9.65                 | 1.19           | 1.1164          | 1620000.0       | 1238460.47       | 381539.53     | 0.2978      | 0.1642        |
| CUMC        | CUMC all HF discharges      | 80             | 806            | 492        | 61.0            | 152.8                | 20.42                | 1.19           | 1.0343          | 1620000.0       | 745555.72        | 874444.28     | 0.2978      | 0.1642        |
| CUMC        | CUMC all HF discharges      | 90             | 806            | 492        | 61.0            | 233.4                | 31.19                | 1.19           | 0.9521          | 1620000.0       | 540008.51        | 1079991.49    | 0.2978      | 0.1642        |
| CUMC        | CUMC all HF discharges      | 100            | 806            | 492        | 61.0            | 314.0                | 41.96                | 1.19           | 0.87            | 1620000.0       | 540008.51        | 1079991.49    | 0.2978      | 0.1642        |
| CUMC        | CUMC weekend HF (all units) | 60             | 289            | 154        | 53.3            | 19.4                 | 2.59                 | 1.19           | 1.1702          | 1620000.0       | 1561355.89       | 58644.11      | 0.2978      | 0.1642        |
| CUMC        | CUMC weekend HF (all units) | 70             | 289            | 154        | 53.3            | 48.3                 | 6.45                 | 1.19           | 1.1408          | 1620000.0       | 1384619.57       | 235380.43     | 0.2978      | 0.1642        |
| CUMC        | CUMC weekend HF (all units) | 80             | 289            | 154        | 53.3            | 77.2                 | 10.32                | 1.19           | 1.1113          | 1620000.0       | 1207883.25       | 412116.75     | 0.2978      | 0.1642        |
| CUMC        | CUMC weekend HF (all units) | 90             | 289            | 154        | 53.3            | 106.1                | 14.18                | 1.19           | 1.0819          | 1620000.0       | 1031146.93       | 588853.07     | 0.2978      | 0.1642        |
| CUMC        | CUMC weekend HF (all units) | 100            | 289            | 154        | 53.3            | 135.0                | 18.04                | 1.19           | 1.0524          | 1620000.0       | 854410.61        | 765589.39     | 0.2978      | 0.1642        |
(15 rows shown)
```
