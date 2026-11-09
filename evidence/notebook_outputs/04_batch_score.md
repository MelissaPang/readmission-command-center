# Executed notebook: batch_score

job run `206873801708733` · task run `1000268409447631` · result **SUCCESS** · 2026-11-09 17:54:51 UTC

# 04 · Batch scoring + discharge worklist

* Loads `<catalog>.ml.readmit_30d_risk@champion` from Unity Catalog.
* Scores every index admission, writing `gold.patient_risk_scores` (row filter `gold.hospital_scope`).
* Explains each score with **counterfactual drivers**: how much the predicted risk drops if a modifiable
  factor is set to its reference value (e.g. follow-up booked, not living alone).
* Builds `gold.discharge_worklist`: patients still inside their 30-day window, with contact details, risk,
  drivers and a recommended action. This is the operational table synced to Lakebase for the app.

```python
dbutils.widgets.text("catalog", "cedarbrook_rcc")
catalog = dbutils.widgets.get("catalog")

import mlflow
import numpy as np
import pandas as pd

mlflow.set_registry_uri("databricks-uc")
MODEL_NAME = f"{catalog}.ml.readmit_30d_risk"
model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@champion")
mv = mlflow.MlflowClient().get_model_version_by_alias(MODEL_NAME, "champion")
print("scoring with", MODEL_NAME, "version", mv.version)

NUM = ["age_at_discharge", "los_days", "prior_admissions_12m", "comorbidity_count"]
BOOL = ["weekend_discharge", "fu7_booked", "ai_lives_alone", "ai_transport_barrier"]
CAT = ["condition", "discharge_disposition", "admission_source", "payer", "service_line"]
FEATURES = NUM + BOOL + CAT
```

Output:

```text
scoring with cedarbrook_rcc.ml.readmit_30d_risk version 2
```

```python
pdf = spark.table(f"{catalog}.gold.index_admissions").toPandas()
X = pdf[FEATURES].copy()
for c in BOOL:
    X[c] = X[c].astype(int)
pdf["risk_score"] = model.predict_proba(X)[:, 1]

# counterfactual drivers (modifiable + key clinical factors)
DRIVERS = {
    "No 7-day follow-up booked": ("fu7_booked", 1),
    "Lives alone / no caregiver (from note)": ("ai_lives_alone", 0),
    "Transportation barrier (from note)": ("ai_transport_barrier", 0),
    "Weekend discharge": ("weekend_discharge", 0),
    "Prior admissions in last 12 months": ("prior_admissions_12m", 0),
    "High comorbidity burden": ("comorbidity_count", 2),
    "Long length of stay": ("los_days", 4),
}
deltas = {}
for label, (col, ref) in DRIVERS.items():
    Xc = X.copy()
    Xc[col] = np.minimum(Xc[col], ref) if col in ("prior_admissions_12m", "comorbidity_count", "los_days") else ref
    deltas[label] = pdf["risk_score"].to_numpy() - model.predict_proba(Xc)[:, 1]
D = pd.DataFrame(deltas)
top = np.argsort(-D.to_numpy(), axis=1)[:, :3]
labels = np.array(list(DRIVERS))
for i in range(3):
    pdf[f"driver_{i+1}"] = [labels[t[i]] if D.iat[r, t[i]] > 0.01 else None for r, t in enumerate(top)]
    pdf[f"driver_{i+1}_impact"] = [round(float(D.iat[r, t[i]]), 4) if D.iat[r, t[i]] > 0.01 else None for r, t in enumerate(top)]
pdf["risk_tier"] = np.select([pdf.risk_score >= 0.30, pdf.risk_score >= 0.18], ["High", "Medium"], "Low")
pdf["model_version"] = int(mv.version)

cols = ["encounter_id", "patient_id", "hospital_id", "unit_id", "unit_name", "condition", "discharge_ts", "discharge_date",
        "weekend_discharge", "fu7_booked", "ai_lives_alone", "ai_transport_barrier", "readmit_30d", "outcome_complete",
        "risk_score", "risk_tier", "driver_1", "driver_1_impact", "driver_2", "driver_2_impact", "driver_3", "driver_3_impact",
        "model_version"]
scores = spark.createDataFrame(pdf[cols])
tbl = f"{catalog}.gold.patient_risk_scores"
if spark.catalog.tableExists(tbl):
    spark.sql(f"ALTER TABLE {tbl} DROP ROW FILTER")
scores.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(tbl)
spark.sql(f"ALTER TABLE {tbl} SET ROW FILTER {catalog}.gold.hospital_scope ON (hospital_id)")
spark.sql(f"COMMENT ON TABLE {tbl} IS '30-day readmission risk score per index admission (model {MODEL_NAME} v{mv.version}) with counterfactual top drivers. Row filter: gold.hospital_scope.'")
print("scored rows:", scores.count())
```

Output:

```text
{"ts": "2026-11-09 17:55:02.068", "level": "WARNING", "logger": "pyspark.sql.connect.logging", "msg": "Effective usage policy for this session is cct.Cilqb2JzLzU4MjYyODExNjMyNTQxMy9ydW5zLzIwNjg3MzgwMTcwODczMxABIAEqJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOTIkMDFhMWMxNzEtZGZkZC03ZmJiLWI4NjctNzFlNTUzNzU3NWMyOiQ2Y2EzMmIwMy01MzlmLTMwZjMtYjNmOS1hMmVlYTgwYTFlNjJCJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOUoMCKuRyNcGEMCGtNsDUAJYAWABaLXIt++EwsgCiAEA.", "context": {}}
{"ts": "2026-11-09 17:55:02.068", "level": "WARNING", "logger": "pyspark.sql.connect.logging", "msg": "Effective usage policy for this session is cct.Cilqb2JzLzU4MjYyODExNjMyNTQxMy9ydW5zLzIwNjg3MzgwMTcwODczMxABIAEqJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOTIkMDFhMWMxNzEtZGZkZC03ZmJiLWI4NjctNzFlNTUzNzU3NWMyOiQ2Y2EzMmIwMy01MzlmLTMwZjMtYjNmOS1hMmVlYTgwYTFlNjJCJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOUoMCKuRyNcGEMCGtNsDUAJYAWABaLXIt++EwsgCiAEA.", "context": {}}
{"ts": "2026-11-09 17:55:02.068", "level": "WARNING", "logger": "pyspark.sql.connect.logging", "msg": "Effective usage policy for this session is cct.Cilqb2JzLzU4MjYyODExNjMyNTQxMy9ydW5zLzIwNjg3MzgwMTcwODczMxABIAEqJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOTIkMDFhMWMxNzEtZGZkZC03ZmJiLWI4NjctNzFlNTUzNzU3NWMyOiQ2Y2EzMmIwMy01MzlmLTMwZjMtYjNmOS1hMmVlYTgwYTFlNjJCJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOUoMCKuRyNcGEMCGtNsDUAJYAWABaLXIt++EwsgCiAEA.", "context": {}}
scored rows: 14475
```

### Does the score separate risk? (complete outcomes, by tier)

```python
display(spark.sql(f"""
SELECT risk_tier, count(*) AS index_admissions, round(avg(risk_score), 3) AS mean_score,
       round(100 * avg(CAST(readmit_30d AS INT)), 1) AS observed_readmit_pct
FROM {tbl} WHERE outcome_complete GROUP BY risk_tier ORDER BY mean_score DESC"""))
```

Output:

```text
| risk_tier | index_admissions | mean_score | observed_readmit_pct |
|-----------|------------------|------------|----------------------|
| High      | 1119             | 0.393      | 39.9                 |
| Medium    | 2462             | 0.229      | 22.4                 |
| Low       | 10135            | 0.089      | 8.9                  |
(3 rows shown)
```

### Discharge worklist: patients inside their 30-day window

```python
spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.gold.discharge_worklist
COMMENT 'Operational worklist for care-transitions staff: discharges in the last 30 days, risk score, drivers, AI note flags, contact details (PHI). Synced to Lakebase.'
AS
SELECT s.encounter_id, s.patient_id, p.first_name, p.last_name, p.mrn, p.home_phone, p.primary_language,
       i.age_at_discharge AS age, i.hospital_id, i.hospital_name, i.unit_id, i.unit_name, i.condition, i.principal_dx_desc,
       i.discharge_ts, i.discharge_dow, i.weekend_discharge, datediff(i.as_of_date, i.discharge_date) AS days_since_discharge,
       i.discharge_disposition, i.fu7_booked, i.first_followup_ts, i.ai_lives_alone, i.ai_transport_barrier,
       i.ai_followup_status, i.ai_evidence, i.readmit_30d AS readmitted_so_far,
       round(s.risk_score, 4) AS risk_score, s.risk_tier, s.driver_1, s.driver_1_impact, s.driver_2, s.driver_2_impact,
       s.driver_3, s.driver_3_impact, s.model_version,
       concat_ws('; ',
         CASE WHEN NOT i.fu7_booked THEN 'Book 7-day follow-up (HF Bridge Clinic / PCP)' END,
         CASE WHEN i.ai_lives_alone THEN 'Caregiver check + home-health referral' END,
         CASE WHEN i.ai_transport_barrier THEN 'Arrange transportation for follow-up' END,
         CASE WHEN i.condition = 'HF' THEN 'Pharmacist med-reconciliation call within 48h' END) AS recommended_actions,
       i.as_of_date
FROM {tbl} s
JOIN {catalog}.gold.index_admissions i USING (encounter_id)
JOIN {catalog}.silver.patients p ON i.patient_id = p.patient_id
WHERE datediff(i.as_of_date, i.discharge_date) BETWEEN 0 AND 30 AND NOT i.readmit_30d
""")
display(spark.sql(f"""
SELECT hospital_id, unit_name, risk_tier, count(*) AS patients, count_if(NOT fu7_booked) AS without_fu7
FROM {catalog}.gold.discharge_worklist GROUP BY ALL ORDER BY hospital_id, unit_name, risk_tier"""))
```

Output:

```text
| hospital_id | unit_name                | risk_tier | patients | without_fu7 |
|-------------|--------------------------|-----------|----------|-------------|
| CUMC        | 2 West Step-Down         | High      | 8        | 7           |
| CUMC        | 2 West Step-Down         | Low       | 22       | 6           |
| CUMC        | 2 West Step-Down         | Medium    | 6        | 4           |
| CUMC        | 3 North Orthopedics      | Low       | 45       | 17          |
| CUMC        | 3 North Orthopedics      | Medium    | 2        | 2           |
| CUMC        | 4 South Pulmonary        | High      | 2        | 2           |
| CUMC        | 4 South Pulmonary        | Low       | 20       | 3           |
| CUMC        | 4 South Pulmonary        | Medium    | 11       | 7           |
| CUMC        | 5 East Cardiology        | High      | 6        | 3           |
| CUMC        | 5 East Cardiology        | Low       | 39       | 13          |
| CUMC        | 5 East Cardiology        | Medium    | 10       | 7           |
| CUMC        | 6 North Telemetry        | High      | 10       | 8           |
| CUMC        | 6 North Telemetry        | Low       | 44       | 10          |
| CUMC        | 6 North Telemetry        | Medium    | 16       | 8           |
| CUMC        | 7 West Medicine          | High      | 2        | 1           |
| CUMC        | 7 West Medicine          | Low       | 44       | 14          |
| CUMC        | 7 West Medicine          | Medium    | 10       | 6           |
| CUMC        | 8 East CV Surgery        | Low       | 19       | 9           |
| CUMC        | 8 East CV Surgery        | Medium    | 1        | 1           |
| CUMC        | 9 North General Medicine | High      | 5        | 4           |
| CUMC        | 9 North General Medicine | Low       | 45       | 13          |
| CUMC        | 9 North General Medicine | Medium    | 10       | 6           |
| FCH         | 2A Medical               | High      | 5        | 3           |
| FCH         | 2A Medical               | Low       | 48       | 9           |
| FCH         | 2A Medical               | Medium    | 13       | 9           |
| FCH         | 2B Surgical              | High      | 1        | 1           |
| FCH         | 2B Surgical              | Low       | 39       | 16          |
| FCH         | 2B Surgical              | Medium    | 3        | 3           |
| FCH         | 3A Telemetry             | High      | 6        | 6           |
| FCH         | 3A Telemetry             | Low       | 25       | 11          |
| FCH         | 3A Telemetry             | Medium    | 11       | 6           |
| FCH         | 3B Orthopedics           | Low       | 33       | 14          |
| PHMC        | ICU / Step-Down          | Low       | 18       | 6           |
| PHMC        | ICU / Step-Down          | Medium    | 4        | 3           |
| PHMC        | Med-Surg 1               | High      | 6        | 4           |
| PHMC        | Med-Surg 1               | Low       | 38       | 9           |
| PHMC        | Med-Surg 1               | Medium    | 16       | 12          |
| PHMC        | Med-Surg 2               | Low       | 35       | 10          |
| PHMC        | Telemetry                | High      | 3        | 2           |
| PHMC        | Telemetry                | Low       | 18       | 4           |
| PHMC        | Telemetry                | Medium    | 6        | 4           |
(41 rows shown)
```

```python
display(spark.sql(f"""
SELECT encounter_id, unit_name, condition, discharge_ts, risk_score, risk_tier, driver_1, driver_2, recommended_actions
FROM {catalog}.gold.discharge_worklist WHERE unit_id = 'CUMC-6N' ORDER BY risk_score DESC LIMIT 15"""))
```

Output:

```text
| encounter_id | unit_name         | condition | discharge_ts             | risk_score | risk_tier | driver_1                           | driver_2                               | recommended_actions                                          |
|--------------|-------------------|-----------|--------------------------|------------|-----------|------------------------------------|----------------------------------------|--------------------------------------------------------------|
| E1014381     | 6 North Telemetry | HF        | 2026-11-04T12:45:00.000Z | 0.5461     | High      | No 7-day follow-up booked          | High comorbidity burden                | Book 7-day follow-up (HF Bridge Clinic / PCP); Pharmacist me |
| E1014087     | 6 North Telemetry | OTHER     | 2026-10-24T11:34:00.000Z | 0.4462     | High      | No 7-day follow-up booked          | Prior admissions in last 12 months     | Book 7-day follow-up (HF Bridge Clinic / PCP); Caregiver che |
| E1013819     | 6 North Telemetry | OTHER     | 2026-10-14T11:55:00.000Z | 0.3878     | High      | No 7-day follow-up booked          | High comorbidity burden                | Book 7-day follow-up (HF Bridge Clinic / PCP); Caregiver che |
| E1014314     | 6 North Telemetry | HF        | 2026-11-02T13:00:00.000Z | 0.3426     | High      | No 7-day follow-up booked          | Prior admissions in last 12 months     | Book 7-day follow-up (HF Bridge Clinic / PCP); Caregiver che |
| E1014336     | 6 North Telemetry | HF        | 2026-11-03T11:07:00.000Z | 0.3329     | High      | High comorbidity burden            | Long length of stay                    | Pharmacist med-reconciliation call within 48h                |
| E1014318     | 6 North Telemetry | HF        | 2026-11-02T13:44:00.000Z | 0.3291     | High      | No 7-day follow-up booked          | Lives alone / no caregiver (from note) | Book 7-day follow-up (HF Bridge Clinic / PCP); Caregiver che |
| E1014074     | 6 North Telemetry | HF        | 2026-10-23T16:31:00.000Z | 0.3206     | High      | No 7-day follow-up booked          | High comorbidity burden                | Book 7-day follow-up (HF Bridge Clinic / PCP); Pharmacist me |
| E1014451     | 6 North Telemetry | AMI       | 2026-11-07T14:08:00.000Z | 0.3203     | High      | High comorbidity burden            | No 7-day follow-up booked              | Book 7-day follow-up (HF Bridge Clinic / PCP)                |
| E1013820     | 6 North Telemetry | HF        | 2026-10-14T12:37:00.000Z | 0.3201     | High      | High comorbidity burden            | Lives alone / no caregiver (from note) | Caregiver check + home-health referral; Pharmacist med-recon |
| E1013960     | 6 North Telemetry | HF        | 2026-10-19T15:33:00.000Z | 0.3166     | High      | No 7-day follow-up booked          | Lives alone / no caregiver (from note) | Book 7-day follow-up (HF Bridge Clinic / PCP); Caregiver che |
| E1014452     | 6 North Telemetry | OTHER     | 2026-11-07T14:24:00.000Z | 0.2722     | Medium    | No 7-day follow-up booked          | High comorbidity burden                | Book 7-day follow-up (HF Bridge Clinic / PCP)                |
| E1014379     | 6 North Telemetry | HF        | 2026-11-04T12:10:00.000Z | 0.269      | Medium    | Long length of stay                | Prior admissions in last 12 months     | Pharmacist med-reconciliation call within 48h                |
| E1014295     | 6 North Telemetry | HF        | 2026-11-01T18:35:00.000Z | 0.2688     | Medium    | High comorbidity burden            | Long length of stay                    | Pharmacist med-reconciliation call within 48h                |
| E1014082     | 6 North Telemetry | HF        | 2026-10-23T18:25:00.000Z | 0.2623     | Medium    | No 7-day follow-up booked          | High comorbidity burden                | Book 7-day follow-up (HF Bridge Clinic / PCP); Pharmacist me |
| E1014410     | 6 North Telemetry | HF        | 2026-11-05T14:34:00.000Z | 0.2557     | Medium    | Prior admissions in last 12 months | No 7-day follow-up booked              | Book 7-day follow-up (HF Bridge Clinic / PCP); Pharmacist me |
(15 rows shown)
```
