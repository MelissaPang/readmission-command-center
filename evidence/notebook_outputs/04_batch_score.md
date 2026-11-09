# Executed notebook: batch_score

job run `601827272748584` · task run `636095575461048` · result **SUCCESS** · 2026-11-09 22:10:16 UTC

# 04 · Batch scoring + discharge worklist

* Loads `<catalog>.ml.readmit_30d_risk@champion` from Unity Catalog.
* Scores every index admission, writing `gold.patient_risk_scores` (row filter `gold.hospital_scope`).
* Explains each score with **counterfactual drivers**: how much the predicted risk drops if a modifiable
  factor is set to its reference value (e.g. follow-up booked, not living alone), then turns them into a short **nurse briefing** with AI Functions.
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
scoring with cedarbrook_rcc.ml.readmit_30d_risk version 5
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
# AI-extracted evidence quote (verbatim note text) joins the scores, behind a role-based column mask
sig = spark.table(f"{catalog}.silver.discharge_note_signals").select("encounter_id", "ai_evidence")
scores = scores.join(sig, "encounter_id", "left")
tbl = f"{catalog}.gold.patient_risk_scores"
if spark.catalog.tableExists(tbl):
    spark.sql(f"ALTER TABLE {tbl} DROP ROW FILTER")
    if "ai_evidence" in spark.table(tbl).columns:
        spark.sql(f"ALTER TABLE {tbl} ALTER COLUMN ai_evidence DROP MASK")
scores.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(tbl)
spark.sql(f"ALTER TABLE {tbl} SET ROW FILTER {catalog}.gold.hospital_scope ON (hospital_id)")
spark.sql(f"ALTER TABLE {tbl} ALTER COLUMN ai_evidence SET MASK {catalog}.gold.mask_clinical_text")
spark.sql(f"COMMENT ON TABLE {tbl} IS '30-day readmission risk score per index admission (model {MODEL_NAME} v{mv.version}) with counterfactual top drivers. "
          "Row filter: gold.hospital_scope. Column mask on ai_evidence (verbatim note quote): gold.mask_clinical_text, care_transitions only.'")
print("scored rows:", scores.count())
```

Output:

```text
{"ts": "2026-11-09 22:10:27.694", "level": "WARNING", "logger": "pyspark.sql.connect.logging", "msg": "Effective usage policy for this session is cct.Cilqb2JzLzU4MjYyODExNjMyNTQxMy9ydW5zLzYwMTgyNzI3Mjc0ODU4NBABIAEqJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOTIkMDFhMWMyNWItZGNiNS03ZjdmLTg4ZjYtYjQ5YmE2YzJmODM5OiQ2Y2EzMmIwMy01MzlmLTMwZjMtYjNmOS1hMmVlYTgwYTFlNjJCJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOUoMCJKJydcGEMDGpqQCUAJYAWABaLXIt++EwsgCiAEA.", "context": {}}
{"ts": "2026-11-09 22:10:27.694", "level": "WARNING", "logger": "pyspark.sql.connect.logging", "msg": "Effective usage policy for this session is cct.Cilqb2JzLzU4MjYyODExNjMyNTQxMy9ydW5zLzYwMTgyNzI3Mjc0ODU4NBABIAEqJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOTIkMDFhMWMyNWItZGNiNS03ZjdmLTg4ZjYtYjQ5YmE2YzJmODM5OiQ2Y2EzMmIwMy01MzlmLTMwZjMtYjNmOS1hMmVlYTgwYTFlNjJCJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOUoMCJKJydcGEMDGpqQCUAJYAWABaLXIt++EwsgCiAEA.", "context": {}}
{"ts": "2026-11-09 22:10:27.694", "level": "WARNING", "logger": "pyspark.sql.connect.logging", "msg": "Effective usage policy for this session is cct.Cilqb2JzLzU4MjYyODExNjMyNTQxMy9ydW5zLzYwMTgyNzI3Mjc0ODU4NBABIAEqJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOTIkMDFhMWMyNWItZGNiNS03ZjdmLTg4ZjYtYjQ5YmE2YzJmODM5OiQ2Y2EzMmIwMy01MzlmLTMwZjMtYjNmOS1hMmVlYTgwYTFlNjJCJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOUoMCJKJydcGEMDGpqQCUAJYAWABaLXIt++EwsgCiAEA.", "context": {}}
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
CREATE OR REPLACE TEMP VIEW worklist_base AS
SELECT s.encounter_id, s.patient_id, p.first_name, p.last_name, p.mrn, p.home_phone, p.primary_language,
       i.age_at_discharge AS age, i.hospital_id, i.hospital_name, i.unit_id, i.unit_name, i.condition, i.principal_dx_desc,
       i.discharge_ts, i.discharge_dow, i.weekend_discharge, datediff(i.as_of_date, i.discharge_date) AS days_since_discharge,
       i.discharge_disposition, i.fu7_booked, i.first_followup_ts, i.ai_lives_alone, i.ai_transport_barrier,
       i.ai_followup_status, sig.ai_evidence, i.readmit_30d AS readmitted_so_far,
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
LEFT JOIN {catalog}.silver.discharge_note_signals sig ON s.encounter_id = sig.encounter_id
WHERE datediff(i.as_of_date, i.discharge_date) BETWEEN 0 AND 30 AND NOT i.readmit_30d
""")
print("worklist patients:", spark.table("worklist_base").count())
```

Output:

```text
worklist patients: 705
```

### Nurse briefing: the counterfactual drivers as a short, grounded narrative (AI Functions)
Each worklist row gets a 2-sentence briefing generated by `ai_query` from **only** the fields in this row (risk, the model's
counterfactual drivers with their impact in points, follow-up status, AI note flags, recommended actions). It replaces the
driver labels in the app, so the worklist reads like a nurse briefing.

```python
dbutils.widgets.text("briefing_endpoint", "databricks-claude-haiku-4-5")
briefing_endpoint = dbutils.widgets.get("briefing_endpoint")
BRIEF_PROMPT = ("You write briefings for care-transitions nurses. Using ONLY the facts in this JSON, write at most 2 sentences (max 55 words): "
                "first why this patient is at readmission risk (cite the top drivers and their impact in percentage points), then the "
                "single most important action to take next. Do not invent diagnoses, medications, dates or names. Plain text, no markdown. FACTS: ")
spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.gold.discharge_worklist
COMMENT 'Operational worklist for care-transitions staff: discharges in the last 30 days, risk score, drivers, AI nurse briefing, AI note flags, contact details (PHI). Synced to Lakebase.'
AS SELECT w.*,
  ai_query('{briefing_endpoint}',
    concat('{BRIEF_PROMPT}', to_json(named_struct(
      'age', w.age, 'condition', w.condition, 'unit', w.unit_name, 'discharged', w.discharge_dow,
      'weekend_discharge', w.weekend_discharge, 'days_since_discharge', w.days_since_discharge,
      'disposition', w.discharge_disposition, 'risk_pct', round(100 * w.risk_score), 'risk_tier', w.risk_tier,
      'driver_1', w.driver_1, 'driver_1_impact_pts', round(100 * w.driver_1_impact, 1),
      'driver_2', w.driver_2, 'driver_2_impact_pts', round(100 * w.driver_2_impact, 1),
      'driver_3', w.driver_3, 'driver_3_impact_pts', round(100 * w.driver_3_impact, 1),
      '7_day_followup_booked', w.fu7_booked, 'lives_alone', w.ai_lives_alone,
      'transportation_barrier', w.ai_transport_barrier, 'note_followup_instruction', w.ai_followup_status,
      'recommended_actions', w.recommended_actions))),
    failOnError => false).result AS nurse_briefing,
  '{briefing_endpoint}' AS briefing_model
FROM worklist_base w
""")
display(spark.sql(f"""
SELECT hospital_id, unit_name, risk_tier, count(*) AS patients, count_if(NOT fu7_booked) AS without_fu7,
       count_if(nurse_briefing IS NOT NULL) AS with_briefing
FROM {catalog}.gold.discharge_worklist GROUP BY ALL ORDER BY hospital_id, unit_name, risk_tier"""))
```

Output:

```text
| hospital_id | unit_name                | risk_tier | patients | without_fu7 | with_briefing |
|-------------|--------------------------|-----------|----------|-------------|---------------|
| CUMC        | 2 West Step-Down         | High      | 8        | 7           | 8             |
| CUMC        | 2 West Step-Down         | Low       | 22       | 6           | 22            |
| CUMC        | 2 West Step-Down         | Medium    | 6        | 4           | 6             |
| CUMC        | 3 North Orthopedics      | Low       | 45       | 17          | 45            |
| CUMC        | 3 North Orthopedics      | Medium    | 2        | 2           | 2             |
| CUMC        | 4 South Pulmonary        | High      | 2        | 2           | 2             |
| CUMC        | 4 South Pulmonary        | Low       | 20       | 3           | 20            |
| CUMC        | 4 South Pulmonary        | Medium    | 11       | 7           | 11            |
| CUMC        | 5 East Cardiology        | High      | 6        | 3           | 6             |
| CUMC        | 5 East Cardiology        | Low       | 39       | 13          | 39            |
| CUMC        | 5 East Cardiology        | Medium    | 10       | 7           | 10            |
| CUMC        | 6 North Telemetry        | High      | 10       | 8           | 10            |
| CUMC        | 6 North Telemetry        | Low       | 44       | 10          | 44            |
| CUMC        | 6 North Telemetry        | Medium    | 16       | 8           | 16            |
| CUMC        | 7 West Medicine          | High      | 2        | 1           | 2             |
| CUMC        | 7 West Medicine          | Low       | 44       | 14          | 44            |
| CUMC        | 7 West Medicine          | Medium    | 10       | 6           | 10            |
| CUMC        | 8 East CV Surgery        | Low       | 19       | 9           | 19            |
| CUMC        | 8 East CV Surgery        | Medium    | 1        | 1           | 1             |
| CUMC        | 9 North General Medicine | High      | 5        | 4           | 5             |
| CUMC        | 9 North General Medicine | Low       | 45       | 13          | 45            |
| CUMC        | 9 North General Medicine | Medium    | 10       | 6           | 10            |
| FCH         | 2A Medical               | High      | 5        | 3           | 5             |
| FCH         | 2A Medical               | Low       | 48       | 9           | 48            |
| FCH         | 2A Medical               | Medium    | 13       | 9           | 13            |
| FCH         | 2B Surgical              | High      | 1        | 1           | 1             |
| FCH         | 2B Surgical              | Low       | 39       | 16          | 39            |
| FCH         | 2B Surgical              | Medium    | 3        | 3           | 3             |
| FCH         | 3A Telemetry             | High      | 6        | 6           | 6             |
| FCH         | 3A Telemetry             | Low       | 25       | 11          | 25            |
| FCH         | 3A Telemetry             | Medium    | 11       | 6           | 11            |
| FCH         | 3B Orthopedics           | Low       | 33       | 14          | 33            |
| PHMC        | ICU / Step-Down          | Low       | 18       | 6           | 18            |
| PHMC        | ICU / Step-Down          | Medium    | 4        | 3           | 4             |
| PHMC        | Med-Surg 1               | High      | 6        | 4           | 6             |
| PHMC        | Med-Surg 1               | Low       | 38       | 9           | 38            |
| PHMC        | Med-Surg 1               | Medium    | 16       | 12          | 16            |
| PHMC        | Med-Surg 2               | Low       | 35       | 10          | 35            |
| PHMC        | Telemetry                | High      | 3        | 2           | 3             |
| PHMC        | Telemetry                | Low       | 18       | 4           | 18            |
| PHMC        | Telemetry                | Medium    | 6        | 4           | 6             |
(41 rows shown)
```

```python
for r in spark.sql(f"""
SELECT encounter_id, unit_name, condition, risk_score, risk_tier, driver_1, driver_1_impact, driver_2, driver_2_impact, fu7_booked,
       ai_lives_alone, nurse_briefing
FROM {catalog}.gold.discharge_worklist WHERE unit_id = 'CUMC-6N' ORDER BY risk_score DESC LIMIT 6""").collect():
    print(f"[{r.encounter_id}] {r.condition} risk={r.risk_score:.2f} ({r.risk_tier}) drivers: {r.driver_1} (+{100*(r.driver_1_impact or 0):.1f} pts), "
          f"{r.driver_2} (+{100*(r.driver_2_impact or 0):.1f} pts) | fu7={r.fu7_booked} lives_alone={r.ai_lives_alone}\n   BRIEFING: {r.nurse_briefing}\n")
```

Output:

```text
[E1014381] HF risk=0.55 (High) drivers: No 7-day follow-up booked (+18.0 pts), High comorbidity burden (+17.0 pts) | fu7=False lives_alone=False
   BRIEFING: This 87-year-old with heart failure is at 55% readmission risk primarily due to no 7-day follow-up scheduled (18 pts), high comorbidity burden (17 pts), and prolonged hospitalization (10.4 pts). Book a 7-day follow-up appointment immediately with HF Bridge Clinic or PCP and arrange pharmacist medication reconciliation within 48 hours.

[E1014087] OTHER risk=0.45 (High) drivers: No 7-day follow-up booked (+16.8 pts), Prior admissions in last 12 months (+13.6 pts) | fu7=False lives_alone=True
   BRIEFING: This 83-year-old discharged Saturday to home alone carries 45% readmission risk driven by no 7-day follow-up booked (16.8 pts), prior admissions in last 12 months (13.6 pts), and living alone without caregiver support (13.5 pts). Immediately book the 7-day follow-up appointment and initiate home health referral.

[E1013819] OTHER risk=0.39 (High) drivers: No 7-day follow-up booked (+15.5 pts), High comorbidity burden (+14.7 pts) | fu7=False lives_alone=True
   BRIEFING: This 72-year-old has 39% readmission risk driven by no 7-day follow-up booked (15.5 pts), high comorbidity burden (14.7 pts), and living alone without caregiver support (12.6 pts). Immediately book the overdue 7-day follow-up appointment with HF Bridge Clinic or PCP and initiate home health referral given social isolation.

[E1014314] HF risk=0.34 (High) drivers: No 7-day follow-up booked (+14.3 pts), Prior admissions in last 12 months (+11.7 pts) | fu7=False lives_alone=True
   BRIEFING: 76-year-old with heart failure at 34% readmission risk driven by no scheduled 7-day follow-up (14.3 pts), prior admissions in past year (11.7 pts), and living alone (11.7 pts). Immediately book 7-day cardiology or primary care follow-up appointment and arrange pharmacist medication reconciliation call within 48 hours.

[E1014336] HF risk=0.33 (High) drivers: High comorbidity burden (+16.8 pts), Long length of stay (+2.6 pts) | fu7=True lives_alone=False
   BRIEFING: This 91-year-old HF patient faces 33% readmission risk driven primarily by high comorbidity burden (16.8 pts) and long length of stay (2.6 pts). Schedule a pharmacist-led medication reconciliation call within 48 hours to address post-discharge medication safety.

[E1014318] HF risk=0.33 (High) drivers: No 7-day follow-up booked (+13.9 pts), Lives alone / no caregiver (from note) (+11.4 pts) | fu7=False lives_alone=True
   BRIEFING: This 73-year-old with heart failure is at 33% readmission risk driven by no scheduled 7-day follow-up (13.9 pts), living alone without caregiver support (11.4 pts), and high comorbidity burden (9.3 pts). Immediately book the 7-day follow-up appointment with HF Bridge Clinic or PCP and arrange a pharmacist medication reconciliation call within 48 hours.
```
