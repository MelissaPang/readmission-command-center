# Databricks notebook source
# MAGIC %md
# MAGIC # 05 · HRRP penalty and deterministic what-if
# MAGIC
# MAGIC **Question:** if 6 North had booked a 7-day follow-up for X% of its weekend (Fri–Sun) HF discharges, how many
# MAGIC readmissions would CUMC have avoided over the trailing 12 months, and what would that do to the HF ERR and the
# MAGIC HRRP penalty?
# MAGIC
# MAGIC **Method (deterministic, no model):**
# MAGIC 1. `converted = max(0, X% × weekend discharges − weekend discharges already booked)`
# MAGIC 2. `avoided = converted × (readmit rate without 7-day FU − rate with 7-day FU)`, using HF rates over the trailing 12 months, all hospitals
# MAGIC 3. `ERR' = ((readmissions − avoided) / index admissions) / expected rate`
# MAGIC 4. `penalty' = min(3% cap, Σ condition payments × max(0, ERR' − 1))`, recomputed for the whole hospital
# MAGIC
# MAGIC Scenarios are written for X from 40% to 100% (the app's slider) and for three scopes.

# COMMAND ----------

dbutils.widgets.text("catalog", "cedarbrook_rcc")
catalog = dbutils.widgets.get("catalog")

import pandas as pd

display(spark.sql(f"SELECT * FROM {catalog}.gold.hrrp_hospital_penalty ORDER BY estimated_penalty DESC"))
display(spark.sql(f"""SELECT hospital_id, hrrp_condition, index_admissions, readmissions, observed_rate, expected_readmission_rate, err,
                             base_op_drg_payments_condition, penalty_contribution
                      FROM {catalog}.gold.hrrp_condition_err WHERE hospital_id = 'CUMC' ORDER BY penalty_contribution DESC"""))

# COMMAND ----------

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

# COMMAND ----------

# MAGIC %md ### Story scenario: 6 North weekend HF discharges at 80% booked

# COMMAND ----------

s = whatif[(whatif.scope == "6N weekend HF") & (whatif.fu7_target_pct == 80)].iloc[0]
print(f"""6 North weekend HF discharges (trailing 12m): {s.discharges_12m}, booked {s.booked_12m} ({s.current_fu7_pct}%)
Raise to 80%  -> {s.additional_followups:.1f} more patients leave with a 7-day follow-up
Avoided readmissions: {s.readmissions_avoided:.2f}  (~{round(s.readmissions_avoided)})
CUMC HF ERR: {s.hf_err_current:.2f} -> {s.hf_err_scenario:.2f}
CUMC estimated HRRP penalty: ${s.penalty_current:,.0f} -> ${s.penalty_scenario:,.0f}  (saves ${s.penalty_saved:,.0f})""")
display(spark.sql(f"SELECT * FROM {catalog}.gold.hrrp_whatif WHERE fu7_target_pct IN (60, 70, 80, 90, 100) ORDER BY scope, fu7_target_pct"))
