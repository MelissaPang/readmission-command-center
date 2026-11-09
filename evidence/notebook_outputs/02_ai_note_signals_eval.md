# Executed notebook: ai_note_signals_eval

job run `601827272748584` · task run `944292661098822` · result **SUCCESS** · 2026-11-09 21:57:37 UTC

# 02 · AI Functions on discharge notes: what the free text adds

The Lakeflow pipeline runs `ai_query()` with a structured-output schema over every discharge note
(`silver.discharge_note_signals`). This notebook:

1. shows sample extractions (note excerpt, extracted flags and evidence quote),
2. scores the extraction against the generator's ground truth (accuracy, precision, recall),
3. quantifies the story finding: **HF patients who live alone, a fact found only in free text, readmit at a much higher rate**.

```python
dbutils.widgets.text("catalog", "cedarbrook_rcc")
catalog = dbutils.widgets.get("catalog")
```

```python
sig = spark.table(f"{catalog}.silver.discharge_note_signals")
print("notes processed:", sig.count(), "| model errors:", sig.filter("ai_error IS NOT NULL").count())
display(spark.sql(f"""
SELECT ai_model, count(*) AS notes, count_if(ai_lives_alone) AS lives_alone, count_if(ai_transport_barrier) AS transport_barrier,
       count_if(ai_followup_status='booked_appointment') AS fu_booked, count_if(ai_followup_status='patient_to_call') AS fu_patient_to_call,
       count_if(ai_followup_status='none') AS fu_none
FROM {catalog}.silver.discharge_note_signals GROUP BY ai_model"""))
```

Output:

```text
notes processed: 16584 | model errors: 0
| ai_model                    | notes | lives_alone | transport_barrier | fu_booked | fu_patient_to_call | fu_none |
|-----------------------------|-------|-------------|-------------------|-----------|--------------------|---------|
| databricks-claude-haiku-4-5 | 16584 | 2051        | 1322              | 8765      | 6358               | 1461    |
(1 rows shown)
```

### Sample extractions

```python
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
```

Output:

```text
[E1000625] social: Widowed, lives by themself. No family nearby to help with medications. Relies on a neighbor for rides; transportation is uncertain.
   follow-up: Patient to call clinic to arrange follow-up.
   -> lives_alone=True transport=True followup=patient_to_call | evidence: "Widowed, lives by themself. No family nearby to help with medications. Relies on a neighbor for rides; transportation is uncertain."

[E1002175] social: Social: lives alone, son visits on weekends only. Relies on a neighbor for rides; transportation is uncertain.
   follow-up: Follow-up appointment scheduled with HF Bridge Clinic on 2025-08-03 at 09:00.
   -> lives_alone=True transport=True followup=booked_appointment | evidence: "lives alone, son visits on weekends only. Relies on a neighbor for rides; transportation is uncertain."

[E1004941] social: Lives alone in a second-floor apartment. No caregiver at home. No car; bus route requires two transfers.
   follow-up: Follow-up appointment scheduled with HF Bridge Clinic on 2025-11-15 at 10:00.
   -> lives_alone=True transport=True followup=booked_appointment | evidence: "Lives alone in a second-floor apartment. No caregiver at home. No car; bus route requires two transfers. Follow-up appointment scheduled with HF Bridge Clinic on 2025-11-15 at 10:00."

[E1009180] social: Patient reports no one at home to help with daily weights or pill box. Relies on a neighbor for rides; transportation is uncertain.
   follow-up: Follow-up appointment scheduled with HF Bridge Clinic on 2026-04-21 at 10:00.
   -> lives_alone=True transport=True followup=booked_appointment | evidence: "Patient reports no one at home to help with daily weights or pill box. Relies on a neighbor for rides; transportation is uncertain."

[E1010948] social: Widowed, lives by themself. No family nearby to help with medications. No car; bus route requires two transfers.
   follow-up: Follow-up appointment scheduled with HF Bridge Clinic on 2026-07-01 at 15:00.
   -> lives_alone=True transport=True followup=booked_appointment | evidence: "Widowed, lives by themself. No family nearby to help with medications. No car; bus route requires two transfers. Follow-up appointment scheduled with HF Bridge Clinic on 2026-07-01 at 15:00."

[E1012915] social: Widowed, lives by themself. No family nearby to help with medications. Does not drive, no reliable ride to appointments.
   follow-up: Follow-up appointment scheduled with HF Bridge Clinic on 2026-09-11 at 14:00.
   -> lives_alone=True transport=True followup=booked_appointment | evidence: "Widowed, lives by themself. No family nearby to help with medications. Does not drive, no reliable ride to appointments. Follow-up appointment scheduled with HF Bridge Clinic on 2026-09-11 at 14:00."

[E1000268] social: Widowed, lives by themself. No family nearby to help with medications.
   follow-up: Follow-up appointment scheduled with HF Bridge Clinic on 2025-05-22 at 10:00.
   -> lives_alone=True transport=False followup=booked_appointment | evidence: "Widowed, lives by themself. No family nearby to help with medications."

[E1000470] social: Social: lives alone, son visits on weekends only.
   follow-up: Follow-up appointment scheduled with HF Bridge Clinic on 2025-05-27 at 14:00.
   -> lives_alone=True transport=False followup=booked_appointment | evidence: "lives alone, son visits on weekends only"

[E1001132] social: Widowed, lives by themself. No family nearby to help with medications.
   follow-up: Patient to call clinic to arrange follow-up.
   -> lives_alone=True transport=False followup=patient_to_call | evidence: "Widowed, lives by themself. No family nearby to help with medications."

[E1001163] social: Widowed, lives by themself. No family nearby to help with medications.
   follow-up: Follow-up appointment scheduled with HF Bridge Clinic on 2025-06-22 at 15:00.
   -> lives_alone=True transport=False followup=booked_appointment | evidence: "Widowed, lives by themself. No family nearby to help with medications."

[E1001232] social: Lives alone in a second-floor apartment. No caregiver at home.
   follow-up: Follow-up appointment scheduled with HF Bridge Clinic on 2025-06-26 at 10:00.
   -> lives_alone=True transport=False followup=booked_appointment | evidence: "Lives alone in a second-floor apartment. No caregiver at home."

[E1001426] social: Social: lives alone, son visits on weekends only.
   follow-up: Follow-up appointment scheduled with HF Bridge Clinic on 2025-07-05 at 14:00.
   -> lives_alone=True transport=False followup=booked_appointment | evidence: "lives alone, son visits on weekends only"
```

### Extraction accuracy vs generator ground truth

```python
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
```

Output:

```text
| flag              | notes | accuracy | precision | recall |
|-------------------|-------|----------|-----------|--------|
| lives_alone       | 14475 | 1.0      | 1.0       | 1.0    |
| transport_barrier | 14475 | 1.0      | 1.0       | 1.0    |
| followup_booked   | 14475 | 1.0      | 1.0       | 1.0    |
(3 rows shown)
```

### Story finding: HF readmissions by AI-extracted flags (trailing 12 months, all hospitals)

```python
display(spark.sql(f"""
SELECT factor, value, index_admissions, readmissions, readmit_rate_pct
FROM {catalog}.gold.readmission_risk_factors
WHERE condition = 'HF' ORDER BY factor, value DESC"""))
```

Output:

```text
| factor               | value | index_admissions | readmissions | readmit_rate_pct |
|----------------------|-------|------------------|--------------|------------------|
| ai_lives_alone       | true  | 157              | 52           | 33.1             |
| ai_lives_alone       | false | 1146             | 236          | 20.6             |
| ai_transport_barrier | true  | 115              | 38           | 33.0             |
| ai_transport_barrier | false | 1188             | 250          | 21.0             |
| fu7_booked           | true  | 749              | 123          | 16.4             |
| fu7_booked           | false | 554              | 165          | 29.8             |
| weekend_discharge    | true  | 448              | 109          | 24.3             |
| weekend_discharge    | false | 855              | 179          | 20.9             |
(8 rows shown)
```
