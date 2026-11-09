# Executed notebook: feedback_loop

job run `601827272748584` · task run `514218579664164` · result **SUCCESS** · 2026-11-09 22:12:24 UTC

# 08 · Closed loop: nurse edits become weak labels for retraining

The app writes every AI-drafted transition plan, the nurse's decision and **how much the nurse edited it** to Lakebase
(`app_rcc.transition_plans`, `app_rcc.plan_audit_log`). That database is registered in Unity Catalog (`rcc_lakebase`), so
the lakehouse reads the write-back directly, with no ETL. This notebook turns it into learning signals:

* `gold.plan_feedback`: one row per plan, with edit similarity, characters added and removed, sections changed, reject reason, and a **weak label**:
  * `accepted_as_is`: the draft was approved with ≥ 97% similarity
  * `nurse_edited`: approved after edits
  * `plan_rejected`: rejected (with a reason)
* `ml.retraining_signals`: the weak labels joined to the patient features, model score and drivers, and (once the 30-day window closes) the
  observed outcome. Two uses:
  1. **Plan-generation quality:** which drivers or sections nurses rewrite, to drive prompt changes and evaluation sets.
  2. **Risk-model signal:** RN-confirmed high-risk cases and outcomes as extra, weakly labelled training rows. `03_train_readmission_model` reports how many are available.

With a prototype there are only a handful of approved plans. The loop is built and running; the signal volume grows with use.

```python
dbutils.widgets.text("catalog", "cedarbrook_rcc")
catalog = dbutils.widgets.get("catalog")
LB = "rcc_lakebase.app_rcc"

display(spark.sql(f"SELECT status, count(*) AS plans, count_if(edited) AS edited FROM {LB}.transition_plans GROUP BY status"))
display(spark.sql(f"SELECT action, count(*) AS events, max(event_ts) AS last_event FROM {LB}.plan_audit_log GROUP BY action ORDER BY action"))
```

Output:

```text
| status   | plans | edited |
|----------|-------|--------|
| approved | 3     | 1      |
(1 rows shown)
| action          | events | last_event               |
|-----------------|--------|--------------------------|
| draft_generated | 3      | 2026-11-09T21:53:41.327Z |
| plan_approved   | 3      | 2026-11-09T21:53:42.170Z |
| plan_edited     | 1      | 2026-11-09T21:53:42.170Z |
| task_completed  | 3      | 2026-11-09T21:53:43.947Z |
(4 rows shown)
```

```python
spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.gold.plan_feedback
COMMENT 'Closed-loop feedback from the app: one row per AI-drafted transition plan with the RN decision, edit metrics and a weak label.'
AS SELECT
  p.plan_id, p.encounter_id, p.status, p.model_endpoint, p.created_by, p.created_ts, p.approved_by, p.approved_ts,
  p.edited, p.edit_similarity, p.chars_added, p.chars_removed,
  CASE WHEN p.sections_changed IS NULL OR p.sections_changed = '' THEN array() ELSE split(p.sections_changed, ',') END AS sections_changed,
  p.reject_reason, p.risk_score AS risk_score_at_draft,
  CASE WHEN p.status = 'rejected' THEN 'plan_rejected'
       WHEN p.status = 'approved' AND coalesce(p.edit_similarity, 1.0) >= 0.97 THEN 'accepted_as_is'
       WHEN p.status = 'approved' THEN 'nurse_edited'
       ELSE 'pending_review' END AS weak_label,
  (SELECT count(*) FROM {LB}.outreach_tasks t WHERE t.plan_id = p.plan_id) AS outreach_tasks,
  (SELECT count(*) FROM {LB}.outreach_tasks t WHERE t.plan_id = p.plan_id AND t.status = 'done') AS outreach_tasks_done,
  current_timestamp() AS refreshed_ts
FROM {LB}.transition_plans p
""")
display(spark.sql(f"""SELECT plan_id, encounter_id, status, weak_label, edited, edit_similarity, chars_added, chars_removed, sections_changed,
                             reject_reason, outreach_tasks, outreach_tasks_done FROM {catalog}.gold.plan_feedback ORDER BY created_ts"""))
```

Output:

```text
| plan_id      | encounter_id | status   | weak_label     | edited | edit_similarity | chars_added | chars_removed | sections_changed    | reject_reason | outreach_tasks | outreach_tasks_done |
|--------------|--------------|----------|----------------|--------|-----------------|-------------|---------------|---------------------|---------------|----------------|---------------------|
| c66e94d57e36 | E1014082     | approved | accepted_as_is |        |                 |             |               | []                  |               | 2              | 1                   |
| a070ebfd8570 | E1014074     | approved | accepted_as_is |        |                 |             |               | []                  |               | 2              | 1                   |
| 477eeb3bc178 | E1014381     | approved | nurse_edited   | True   | 0.9507          | 107         | 0             | ['Within 48 hours'] |               | 2              | 1                   |
(3 rows shown)
```

### Retraining signals: weak labels joined to features, score, drivers and outcome

```python
spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.ml.retraining_signals
COMMENT 'Weak labels from RN plan review joined to model inputs/outputs and the observed 30-day outcome (when complete). Input for prompt evaluation and model retraining.'
AS SELECT
  f.plan_id, f.encounter_id, f.weak_label, f.edited, f.edit_similarity, f.sections_changed, f.reject_reason,
  s.risk_score, s.risk_tier, s.driver_1, s.driver_2, s.driver_3, s.model_version,
  i.condition, i.unit_id, i.age_at_discharge, i.los_days, i.prior_admissions_12m, i.comorbidity_count,
  i.weekend_discharge, i.fu7_booked, i.ai_lives_alone, i.ai_transport_barrier,
  i.outcome_complete, CASE WHEN i.outcome_complete THEN i.readmit_30d END AS observed_readmit_30d,
  CASE WHEN f.weak_label IN ('accepted_as_is', 'nurse_edited') AND s.risk_tier = 'High' THEN 'rn_confirmed_high_risk'
       WHEN f.weak_label = 'plan_rejected' THEN 'rn_disputed'
       ELSE 'other' END AS risk_signal,
  current_timestamp() AS refreshed_ts
FROM {catalog}.gold.plan_feedback f
JOIN {catalog}.gold.patient_risk_scores s USING (encounter_id)
JOIN {catalog}.gold.index_admissions i USING (encounter_id)
""")
display(spark.sql(f"""SELECT weak_label, risk_signal, count(*) AS plans, round(avg(edit_similarity), 3) AS avg_similarity,
                             count_if(outcome_complete) AS with_outcome
                      FROM {catalog}.ml.retraining_signals GROUP BY ALL"""))
```

Output:

```text
| weak_label     | risk_signal            | plans | avg_similarity | with_outcome |
|----------------|------------------------|-------|----------------|--------------|
| accepted_as_is | rn_confirmed_high_risk | 1     |                | 0            |
| accepted_as_is | other                  | 1     |                | 0            |
| nurse_edited   | rn_confirmed_high_risk | 1     | 0.951          | 0            |
(3 rows shown)
```

### What nurses change (input to prompt iteration)

```python
display(spark.sql(f"""
SELECT section, count(*) AS plans_where_changed
FROM {catalog}.gold.plan_feedback LATERAL VIEW explode(sections_changed) x AS section
GROUP BY section ORDER BY plans_where_changed DESC"""))
m = spark.sql(f"""SELECT count(*) AS n, count_if(weak_label='nurse_edited') AS edited, count_if(weak_label='plan_rejected') AS rejected
                  FROM {catalog}.gold.plan_feedback WHERE status IN ('approved','rejected')""").first()
print(f"reviewed plans: {m.n} | nurse-edited: {m.edited} | rejected: {m.rejected} | edit rate: {(m.edited / m.n if m.n else 0):.0%}")
```

Output:

```text
| section         | plans_where_changed |
|-----------------|---------------------|
| Within 48 hours | 1                   |
(1 rows shown)
reviewed plans: 3 | nurse-edited: 1 | rejected: 0 | edit rate: 33%
```
