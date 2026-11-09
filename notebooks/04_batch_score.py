# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Batch scoring + discharge worklist
# MAGIC
# MAGIC * Loads `<catalog>.ml.readmit_30d_risk@champion` from Unity Catalog.
# MAGIC * Scores every index admission, writing `gold.patient_risk_scores` (row filter `gold.hospital_scope`).
# MAGIC * Explains each score with **counterfactual drivers**: how much the predicted risk drops if a modifiable
# MAGIC   factor is set to its reference value (e.g. follow-up booked, not living alone).
# MAGIC * Builds `gold.discharge_worklist`: patients still inside their 30-day window, with contact details, risk,
# MAGIC   drivers and a recommended action. This is the operational table synced to Lakebase for the app.

# COMMAND ----------

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

# COMMAND ----------

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

# COMMAND ----------

# MAGIC %md ### Does the score separate risk? (complete outcomes, by tier)

# COMMAND ----------

display(spark.sql(f"""
SELECT risk_tier, count(*) AS index_admissions, round(avg(risk_score), 3) AS mean_score,
       round(100 * avg(CAST(readmit_30d AS INT)), 1) AS observed_readmit_pct
FROM {tbl} WHERE outcome_complete GROUP BY risk_tier ORDER BY mean_score DESC"""))

# COMMAND ----------

# MAGIC %md ### Discharge worklist: patients inside their 30-day window

# COMMAND ----------

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

# COMMAND ----------

display(spark.sql(f"""
SELECT encounter_id, unit_name, condition, discharge_ts, risk_score, risk_tier, driver_1, driver_2, recommended_actions
FROM {catalog}.gold.discharge_worklist WHERE unit_id = 'CUMC-6N' ORDER BY risk_score DESC LIMIT 15"""))
