# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · AI Functions on discharge notes: what the free text adds
# MAGIC
# MAGIC The Lakeflow pipeline runs `ai_query()` with a structured-output schema over every discharge note
# MAGIC (`silver.discharge_note_signals`). This notebook:
# MAGIC
# MAGIC 1. shows sample extractions (note excerpt, extracted flags and evidence quote),
# MAGIC 2. scores the extraction against the generator's ground truth (accuracy, precision, recall),
# MAGIC 3. quantifies the story finding: **HF patients who live alone, a fact found only in free text, readmit at a much higher rate**.

# COMMAND ----------

dbutils.widgets.text("catalog", "cedarbrook_rcc")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------

sig = spark.table(f"{catalog}.silver.discharge_note_signals")
print("notes processed:", sig.count(), "| model errors:", sig.filter("ai_error IS NOT NULL").count())
display(spark.sql(f"""
SELECT ai_model, count(*) AS notes, count_if(ai_lives_alone) AS lives_alone, count_if(ai_transport_barrier) AS transport_barrier,
       count_if(ai_followup_status='booked_appointment') AS fu_booked, count_if(ai_followup_status='patient_to_call') AS fu_patient_to_call,
       count_if(ai_followup_status='none') AS fu_none
FROM {catalog}.silver.discharge_note_signals GROUP BY ai_model"""))

# COMMAND ----------

# MAGIC %md ### Sample extractions

# COMMAND ----------

rows = spark.sql(f"""
SELECT n.encounter_id, regexp_extract(n.note_text, 'Social history: ([^\\n]*)', 1) AS social_history,
       regexp_extract(n.note_text, 'Follow-up: ([^\\n]*)', 1) AS follow_up_line,
       s.ai_lives_alone, s.ai_transport_barrier, s.ai_followup_status, s.ai_evidence
FROM {catalog}.silver.discharge_notes n JOIN {catalog}.silver.discharge_note_signals s USING (encounter_id)
WHERE n.encounter_id IN (SELECT encounter_id FROM {catalog}.gold.index_admissions WHERE unit_id='CUMC-6N' AND condition='HF')
ORDER BY s.ai_lives_alone DESC, s.ai_transport_barrier DESC, n.encounter_id LIMIT 12""").collect()
for r in rows:
    print(f"[{r.encounter_id}] social: {r.social_history}\n   follow-up: {r.follow_up_line}\n"
          f"   -> lives_alone={r.ai_lives_alone} transport={r.ai_transport_barrier} followup={r.ai_followup_status} | evidence: \"{r.ai_evidence}\"\n")

# COMMAND ----------

# MAGIC %md ### Extraction accuracy vs generator ground truth

# COMMAND ----------

truth = (spark.read.option("header", True).csv(f"/Volumes/{catalog}/raw/ground_truth/note_flags_ground_truth.csv")
         .selectExpr("encounter_id", "CAST(lives_alone AS BOOLEAN) AS true_lives_alone",
                     "CAST(transport_barrier AS BOOLEAN) AS true_transport_barrier",
                     "CAST(fu7_booked AS BOOLEAN) AS true_fu7_booked"))
truth.createOrReplaceTempView("truth")
sig.createOrReplaceTempView("sig")
display(spark.sql("""
WITH j AS (SELECT * FROM sig JOIN truth USING (encounter_id))
SELECT 'lives_alone' AS flag, count(*) AS notes,
  round(avg(CAST(ai_lives_alone = true_lives_alone AS INT)), 4) AS accuracy,
  round(count_if(ai_lives_alone AND true_lives_alone) / count_if(ai_lives_alone), 4) AS precision,
  round(count_if(ai_lives_alone AND true_lives_alone) / count_if(true_lives_alone), 4) AS recall
FROM j
UNION ALL
SELECT 'transport_barrier', count(*),
  round(avg(CAST(ai_transport_barrier = true_transport_barrier AS INT)), 4),
  round(count_if(ai_transport_barrier AND true_transport_barrier) / count_if(ai_transport_barrier), 4),
  round(count_if(ai_transport_barrier AND true_transport_barrier) / count_if(true_transport_barrier), 4)
FROM j
UNION ALL
SELECT 'followup_booked', count(*),
  round(avg(CAST((ai_followup_status = 'booked_appointment') = true_fu7_booked AS INT)), 4),
  round(count_if(ai_followup_status = 'booked_appointment' AND true_fu7_booked) / count_if(ai_followup_status = 'booked_appointment'), 4),
  round(count_if(ai_followup_status = 'booked_appointment' AND true_fu7_booked) / count_if(true_fu7_booked), 4)
FROM j
"""))

# COMMAND ----------

# MAGIC %md ### Story finding: HF readmissions by AI-extracted flags (trailing 12 months, all hospitals)

# COMMAND ----------

display(spark.sql(f"""
SELECT factor, value, index_admissions, readmissions, readmit_rate_pct
FROM {catalog}.gold.readmission_risk_factors
WHERE condition = 'HF' ORDER BY factor, value DESC"""))
