# Executed notebook: validate_story

job run `601827272748584` · task run `31547648132122` · result **SUCCESS** · 2026-11-09 22:14:24 UTC

# 99 · Validate the story end to end + governance evidence

Recomputes every number in the customer story from the **gold tables** (not from the generator) and checks each one.
Then it gathers governance evidence: column masks in action, the row filter, grants, tags and lineage. Results go to `gold.story_validation`.

```python
%pip install -q "databricks-sdk>=0.60.0"
%restart_python
```

Output:

```text
Note: you may need to restart the kernel using %restart_python or dbutils.library.restartPython() to use updated packages.
```

```python
dbutils.widgets.text("catalog", "cedarbrook_rcc")
catalog = dbutils.widgets.get("catalog")
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
me = w.current_user.me().user_name
checks = []

def check(name, actual, expected, ok):
    checks.append((name, str(actual), str(expected), bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {name}: actual={actual} expected={expected}")

def one(sql):
    return spark.sql(sql).first()
```

### Story numbers

```python
r = one(f"SELECT * FROM {catalog}.gold.unit_period_summary WHERE unit_id='CUMC-6N' AND condition='HF'")
check("6N HF readmit rate, prior 20 weeks", f"{r.prior_20w_rate_pct}%", "14.8%", r.prior_20w_rate_pct == 14.8)
check("6N HF readmit rate, last 20 weeks", f"{r.last_20w_rate_pct}%", "23.9%", r.last_20w_rate_pct == 23.9)
check("6N HF change (pts)", r.delta_pts, "+9.1", r.delta_pts == 9.1)
o = one(f"SELECT max(abs(delta_pts)) AS m FROM {catalog}.gold.unit_period_summary WHERE condition='ALL' AND unit_id <> 'CUMC-6N'")
check("Every other unit within ~1.5 pts (all-cause)", o.m, "<= 1.5", o.m <= 1.5)

fu = {x.discharge_day_type: x for x in spark.sql(
    f"SELECT * FROM {catalog}.gold.followup_gap WHERE unit_id='CUMC-6N' AND condition='HF' AND period='since_2026-06-19'").collect()}
wk, wd = fu["Weekend (Fri-Sun)"], fu["Weekday (Mon-Thu)"]
check("6N weekend HF discharges with 7-day FU since 2026-06-19", f"{round(wk.fu7_booked_pct)}% ({wk.fu7_booked}/{wk.discharges})", "18%", round(wk.fu7_booked_pct) == 18)
check("6N weekday HF discharges with 7-day FU since 2026-06-19", f"{round(wd.fu7_booked_pct)}% ({wd.fu7_booked}/{wd.discharges})", "69%", round(wd.fu7_booked_pct) == 69)
note = one(f"""SELECT count(*) AS n, count_if(ai_followup_status='patient_to_call') AS to_call FROM {catalog}.gold.index_admissions
               WHERE unit_id='CUMC-6N' AND condition='HF' AND weekend_discharge AND after_6n_staffing_change AND NOT fu7_booked""")
check("Unbooked 6N weekend notes say 'patient to call / schedule' (AI)", f"{note.to_call}/{note.n}", "majority", note.to_call / note.n > 0.8)

rf = {(x.factor, x.value): x.readmit_rate_pct for x in spark.sql(
    f"SELECT * FROM {catalog}.gold.readmission_risk_factors WHERE condition='HF'").collect()}
check("HF 12m readmit, no 7-day FU", f"{rf[('fu7_booked','false')]}%", "29.8%", rf[("fu7_booked", "false")] == 29.8)
check("HF 12m readmit, with 7-day FU", f"{rf[('fu7_booked','true')]}%", "16.4%", rf[("fu7_booked", "true")] == 16.4)
check("HF 12m readmit, lives alone (AI from free text)", f"{rf[('ai_lives_alone','true')]}%", "33.1% (+/-0.5 for AI extraction)", abs(rf[("ai_lives_alone", "true")] - 33.1) <= 0.5)
check("HF 12m readmit, not living alone (AI)", f"{rf[('ai_lives_alone','false')]}%", "20.6% (+/-0.5)", abs(rf[("ai_lives_alone", "false")] - 20.6) <= 0.5)

p = one(f"SELECT * FROM {catalog}.gold.hrrp_hospital_penalty WHERE hospital_id='CUMC'")
check("CUMC estimated HRRP penalty", f"${p.estimated_penalty:,.0f} (at cap: {p.at_cap})", "$1.62M", round(p.estimated_penalty / 1e4) == 162)
check("Largest penalty line is HF", f"{p.largest_condition} ${p.largest_condition_contribution:,.0f}", "HF $1.14M", p.largest_condition == "HF" and round(p.largest_condition_contribution / 1e4) == 114)
check("CUMC HF ERR", round(p.largest_condition_err, 2), "1.19", round(p.largest_condition_err, 2) == 1.19)
s = one(f"SELECT * FROM {catalog}.gold.hrrp_whatif WHERE scope='6N weekend HF' AND fu7_target_pct=80")
check("What-if 80%: readmissions avoided", s.readmissions_avoided, "~7", round(s.readmissions_avoided) == 7)
check("What-if 80%: HF ERR", round(s.hf_err_scenario, 2), "1.14", round(s.hf_err_scenario, 2) == 1.14)
check("What-if 80%: penalty saved", f"${s.penalty_saved:,.0f}", "~$240K", abs(s.penalty_saved - 240000) <= 10000)
```

Output:

```text
PASS  6N HF readmit rate, prior 20 weeks: actual=14.8% expected=14.8%
PASS  6N HF readmit rate, last 20 weeks: actual=23.9% expected=23.9%
PASS  6N HF change (pts): actual=9.1 expected=+9.1
PASS  Every other unit within ~1.5 pts (all-cause): actual=1.1 expected=<= 1.5
PASS  6N weekend HF discharges with 7-day FU since 2026-06-19: actual=18% (11/62) expected=18%
PASS  6N weekday HF discharges with 7-day FU since 2026-06-19: actual=69% (94/137) expected=69%
PASS  Unbooked 6N weekend notes say 'patient to call / schedule' (AI): actual=51/51 expected=majority
PASS  HF 12m readmit, no 7-day FU: actual=29.8% expected=29.8%
PASS  HF 12m readmit, with 7-day FU: actual=16.4% expected=16.4%
PASS  HF 12m readmit, lives alone (AI from free text): actual=33.1% expected=33.1% (+/-0.5 for AI extraction)
PASS  HF 12m readmit, not living alone (AI): actual=20.6% expected=20.6% (+/-0.5)
PASS  CUMC estimated HRRP penalty: actual=$1,620,000 (at cap: True) expected=$1.62M
PASS  Largest penalty line is HF: actual=HF $1,139,987 expected=HF $1.14M
PASS  CUMC HF ERR: actual=1.19 expected=1.19
PASS  What-if 80%: readmissions avoided: actual=6.52 expected=~7
PASS  What-if 80%: HF ERR: actual=1.14 expected=1.14
PASS  What-if 80%: penalty saved: actual=$238,438 expected=~$240K
```

### Platform objects exist (ML, Lakebase, Genie)

```python
m = one(f"SELECT * FROM {catalog}.ml.model_metrics")
check("UC model registered @champion", f"{m.model_name} v{m.version}", "exists", m.version >= 1)
check("Model test AUC", m.auc, "> 0.65", m.auc > 0.65)
for t in ["discharge_worklist", "hrrp_whatif", "unit_weekly", "hrrp_hospital"]:
    st = w.database.get_synced_database_table(f"rcc_lakebase.public.{t}")
    state = str(st.data_synchronization_status.detailed_state)
    check(f"Lakebase synced table public.{t}", state, "ONLINE*", "ONLINE" in state)
wb = spark.sql("""SELECT count(*) AS plans, count_if(status = 'approved') AS approved, max(approved_ts) AS last_approved
                   FROM rcc_lakebase.app_rcc.transition_plans""").first()
print("App write-back read from the lakehouse (UC -> Lakebase):", wb)
display(spark.sql("""SELECT p.plan_id, p.encounter_id, p.status, p.model_endpoint, p.approved_by, p.approved_ts, count(t.task_id) AS outreach_tasks
                     FROM rcc_lakebase.app_rcc.transition_plans p LEFT JOIN rcc_lakebase.app_rcc.outreach_tasks t USING (plan_id)
                     GROUP BY ALL ORDER BY p.approved_ts DESC NULLS LAST LIMIT 10"""))
check("App-approved transition plans visible in UC via Lakebase catalog", f"{wb.approved} approved / {wb.plans} plans", ">= 1 approved", wb.approved >= 1)
fb = spark.sql(f"""SELECT count(*) AS n, count_if(weak_label='nurse_edited') AS edited, count_if(weak_label='accepted_as_is') AS as_is
                   FROM {catalog}.gold.plan_feedback""").first()
check("Closed loop: RN plan edits captured as weak labels (gold.plan_feedback)", f"{fb.n} plans ({fb.edited} nurse_edited, {fb.as_is} accepted_as_is)", ">= 1 nurse_edited", fb.edited >= 1)
rs = spark.sql(f"SELECT count(*) AS n FROM {catalog}.ml.retraining_signals").first().n
check("Closed loop: retraining signals joined to features/score/outcome", rs, "= plans", rs == fb.n)
br = spark.sql(f"SELECT count(*) AS n, count_if(nurse_briefing IS NOT NULL AND length(nurse_briefing) > 40) AS ok FROM {catalog}.gold.discharge_worklist").first()
check("Nurse briefing generated for every worklist patient (AI Functions)", f"{br.ok}/{br.n}", "all", br.ok == br.n)
jd = spark.sql(f"""WITH last AS (SELECT max(run_ts) AS t FROM {catalog}.gold.genie_eval_judgements)
                   SELECT count(*) AS n, count_if(verdict='PASS') AS passed, round(avg(score), 2) AS avg_score
                   FROM {catalog}.gold.genie_eval_judgements, last WHERE run_ts = last.t""").first()
check("Genie answers pass the LLM judge (latest run)", f"{jd.passed}/{jd.n} PASS, avg score {jd.avg_score}", "all PASS", jd.passed == jd.n and jd.n > 0)
g = spark.sql(f"SELECT status FROM {catalog}.gold.genie_eval_transcript").toPandas()
check("Genie answered story questions", f"{(g.status == 'COMPLETED').sum()}/{len(g)}", "all COMPLETED", (g.status == "COMPLETED").all())
```

Output:

```text
PASS  UC model registered @champion: actual=cedarbrook_rcc.ml.readmit_30d_risk v5 expected=exists
PASS  Model test AUC: actual=0.7245 expected=> 0.65
PASS  Lakebase synced table public.discharge_worklist: actual=SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE expected=ONLINE*
PASS  Lakebase synced table public.hrrp_whatif: actual=SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE expected=ONLINE*
PASS  Lakebase synced table public.unit_weekly: actual=SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE expected=ONLINE*
PASS  Lakebase synced table public.hrrp_hospital: actual=SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE expected=ONLINE*
App write-back read from the lakehouse (UC -> Lakebase): Row(plans=3, approved=3, last_approved=datetime.datetime(2026, 11, 9, 21, 53, 42, 170191))
| plan_id      | encounter_id | status   | model_endpoint               | approved_by                 | approved_ts              | outreach_tasks |
|--------------|--------------|----------|------------------------------|-----------------------------|--------------------------|----------------|
| 477eeb3bc178 | E1014381     | approved | databricks-claude-sonnet-4-6 | melissa.pang@databricks.com | 2026-11-09T21:53:42.170Z | 2              |
| a070ebfd8570 | E1014074     | approved | databricks-claude-sonnet-4-6 | melissa.pang@databricks.com | 2026-11-09T18:06:45.839Z | 2              |
| c66e94d57e36 | E1014082     | approved | databricks-claude-sonnet-4-6 | melissa.pang@databricks.com | 2026-11-09T17:48:47.567Z | 2              |
(3 rows shown)
PASS  App-approved transition plans visible in UC via Lakebase catalog: actual=3 approved / 3 plans expected=>= 1 approved
PASS  Closed loop: RN plan edits captured as weak labels (gold.plan_feedback): actual=3 plans (1 nurse_edited, 2 accepted_as_is) expected=>= 1 nurse_edited
PASS  Closed loop: retraining signals joined to features/score/outcome: actual=3 expected== plans
PASS  Nurse briefing generated for every worklist patient (AI Functions): actual=705/705 expected=all
PASS  Genie answers pass the LLM judge (latest run): actual=5/5 PASS, avg score 5.0 expected=all PASS
PASS  Genie answered story questions: actual=5/5 expected=all COMPLETED
```

### Governance evidence: column masks + row filter in action
Temporarily remove the current user's entitlement, query, then restore it. The same query, run by the same user, returns masked or filtered rows.

```python
q_mask = f"SELECT patient_id, mrn, first_name, last_name, date_of_birth, home_phone FROM {catalog}.silver.patients ORDER BY patient_id LIMIT 3"
q_rows = f"SELECT count(*) AS visible_rows FROM {catalog}.gold.patient_risk_scores"
q_evid = f"SELECT encounter_id, risk_tier, ai_evidence FROM {catalog}.gold.patient_risk_scores WHERE ai_evidence IS NOT NULL AND ai_evidence <> '' ORDER BY encounter_id LIMIT 3"
print("WITH care_transitions entitlement:")
spark.sql(q_mask).show(truncate=False); spark.sql(q_rows).show(); spark.sql(q_evid).show(truncate=80)
spark.sql(f"UPDATE {catalog}.gold.rcc_user_entitlements SET role='analyst', hospital_scope='FCH' WHERE principal='{me}'")
try:
    print("AS analyst scoped to FCH only:")
    masked = spark.sql(q_mask).collect(); spark.sql(q_mask).show(truncate=False)
    rows_fch = spark.sql(q_rows).first().visible_rows; spark.sql(q_rows).show()
    evid_masked = spark.sql(q_evid).collect(); spark.sql(q_evid).show(truncate=80)
finally:
    spark.sql(f"UPDATE {catalog}.gold.rcc_user_entitlements SET role='care_transitions', hospital_scope='*' WHERE principal='{me}'")
total = spark.sql(q_rows).first().visible_rows
check("Column mask hides PHI for non care_transitions", masked[0].mrn, "***MASKED***", masked[0].mrn == "***MASKED***")
check("Row filter limits patient rows to hospital scope", f"{rows_fch} of {total}", "< total", 0 < rows_fch < total)
check("Role-based mask hides AI evidence quotes from non care_transitions", evid_masked[0].ai_evidence if evid_masked else None,
      "[restricted: care-transitions only]", bool(evid_masked) and evid_masked[0].ai_evidence == "[restricted: care-transitions only]")
check("gold.index_admissions (analyst-facing) no longer exposes verbatim evidence", "ai_evidence" in spark.table(f"{catalog}.gold.index_admissions").columns,
      False, "ai_evidence" not in spark.table(f"{catalog}.gold.index_admissions").columns)
```

Output:

```text
WITH care_transitions entitlement:
+----------+-----------+----------+---------+-------------+--------------+
|patient_id|mrn        |first_name|last_name|date_of_birth|home_phone    |
+----------+-----------+----------+---------+-------------+--------------+
|P500000   |MRN85155948|Lisa      |Rodriguez|1964-07-18   |(630) 555-9868|
|P500001   |MRN24397084|Arjun     |Lewis    |1950-01-09   |(630) 555-8805|
|P500002   |MRN28644424|John      |Davis    |1963-04-06   |(630) 555-1801|
+----------+-----------+----------+---------+-------------+--------------+

+------------+
|visible_rows|
+------------+
|       14475|
+------------+

+------------+---------+--------------------------------------------------------------------------------+
|encounter_id|risk_tier|                                                                     ai_evidence|
+------------+---------+--------------------------------------------------------------------------------+
|    E1000000|      Low|Lives with adult daughter who will assist with medications and daily weights....|
|    E1000001|      Low|                                Does not drive, no reliable ride to appointments|
|    E1000002|      Low|    Lives with adult daughter who will assist with medications and daily weights|
+------------+---------+--------------------------------------------------------------------------------+

AS analyst scoped to FCH only:
+----------+------------+------------+------------+-------------+------------+
|patient_id|mrn         |first_name  |last_name   |date_of_birth|home_phone  |
+----------+------------+------------+------------+-------------+------------+
|P500000   |***MASKED***|***MASKED***|***MASKED***|1964-01-01   |***MASKED***|
|P500001   |***MASKED***|***MASKED***|***MASKED***|1950-01-01   |***MASKED***|
|P500002   |***MASKED***|***MASKED***|***MASKED***|1963-01-01   |***MASKED***|
+----------+------------+------------+------------+-------------+------------+

+------------+
|visible_rows|
+------------+
|        3424|
+------------+

+------------+---------+-----------------------------------+
|encounter_id|risk_tier|                        ai_evidence|
+------------+---------+-----------------------------------+
|    E1000000|      Low|[restricted: care-transitions only]|
|    E1000002|      Low|[restricted: care-transitions only]|
|    E1000004|      Low|[restricted: care-transitions only]|
+------------+---------+-----------------------------------+

PASS  Column mask hides PHI for non care_transitions: actual=***MASKED*** expected=***MASKED***
PASS  Row filter limits patient rows to hospital scope: actual=3424 of 14475 expected=< total
PASS  Role-based mask hides AI evidence quotes from non care_transitions: actual=[restricted: care-transitions only] expected=[restricted: care-transitions only]
PASS  gold.index_admissions (analyst-facing) no longer exposes verbatim evidence: actual=False expected=False
```

```python
display(spark.sql(f"SELECT table_name, column_name, mask_name FROM {catalog}.information_schema.column_masks"))
display(spark.sql(f"SELECT table_name, filter_name, target_columns FROM {catalog}.information_schema.row_filters"))
display(spark.sql(f"SELECT schema_name, tag_name, tag_value FROM {catalog}.information_schema.schema_tags"))
```

Output:

```text
| table_name          | column_name   | mask_name                              |
|---------------------|---------------|----------------------------------------|
| patient_risk_scores | ai_evidence   | cedarbrook_rcc.gold.mask_clinical_text |
| patients            | home_phone    | cedarbrook_rcc.gold.mask_phi           |
| patients            | last_name     | cedarbrook_rcc.gold.mask_phi           |
| patients            | mrn           | cedarbrook_rcc.gold.mask_phi           |
| patients            | date_of_birth | cedarbrook_rcc.gold.mask_phi_date      |
| patients            | first_name    | cedarbrook_rcc.gold.mask_phi           |
(6 rows shown)
| table_name          | filter_name                        | target_columns |
|---------------------|------------------------------------|----------------|
| patient_risk_scores | cedarbrook_rcc.gold.hospital_scope | hospital_id    |
(1 rows shown)
| schema_name | tag_name           | tag_value |
|-------------|--------------------|-----------|
| silver      | rcc_medallion_tier | silver    |
| gold        | rcc_medallion_tier | gold      |
| ml          | rcc_medallion_tier | ml        |
| bronze      | rcc_medallion_tier | bronze    |
| raw         | rcc_medallion_tier | landing   |
(5 rows shown)
```

### Lineage (Unity Catalog lineage API): raw volume → bronze → silver → gold → app tables

```python
def lineage(table):
    r = w.api_client.do("GET", "/api/2.0/lineage-tracking/table-lineage", query={"table_name": table, "include_entity_lineage": "true"})
    ups = [u.get("tableInfo", {}) for u in r.get("upstreams", [])]
    return sorted({f"{u.get('catalog_name')}.{u.get('schema_name')}.{u.get('name')}" for u in ups if u.get("name")})

for t in ["bronze.encounters", "silver.encounters", "silver.discharge_note_signals", "gold.index_admissions",
          "gold.hrrp_condition_err", "gold.patient_risk_scores", "gold.discharge_worklist", "gold.hrrp_whatif",
          "gold.plan_feedback", "ml.retraining_signals"]:
    print(f"{catalog}.{t:32s} <- {lineage(f'{catalog}.{t}')}")
```

Output:

```text
cedarbrook_rcc.bronze.encounters                <- []
cedarbrook_rcc.silver.encounters                <- ['cedarbrook_rcc.bronze.encounters']
cedarbrook_rcc.silver.discharge_note_signals    <- ['cedarbrook_rcc.silver.discharge_notes']
cedarbrook_rcc.gold.index_admissions            <- ['cedarbrook_rcc.gold.encounters_enriched', 'cedarbrook_rcc.silver.discharge_note_signals', 'cedarbrook_rcc.silver.encounters', 'cedarbrook_rcc.silver.followup_appointments', 'cedarbrook_rcc.silver.staffing_events']
cedarbrook_rcc.gold.hrrp_condition_err          <- ['cedarbrook_rcc.gold.index_admissions', 'cedarbrook_rcc.silver.cms_hrrp_reference']
cedarbrook_rcc.gold.patient_risk_scores         <- ['cedarbrook_rcc.silver.discharge_note_signals']
cedarbrook_rcc.gold.discharge_worklist          <- ['cedarbrook_rcc.gold.index_admissions', 'cedarbrook_rcc.gold.patient_risk_scores', 'cedarbrook_rcc.silver.discharge_note_signals', 'cedarbrook_rcc.silver.patients']
cedarbrook_rcc.gold.hrrp_whatif                 <- []
cedarbrook_rcc.gold.plan_feedback               <- ['rcc_lakebase.app_rcc.outreach_tasks', 'rcc_lakebase.app_rcc.transition_plans']
cedarbrook_rcc.ml.retraining_signals            <- ['cedarbrook_rcc.gold.index_admissions', 'cedarbrook_rcc.gold.patient_risk_scores', 'cedarbrook_rcc.gold.plan_feedback']
```

```python
import pandas as pd
res = pd.DataFrame(checks, columns=["check", "actual", "expected", "passed"])
spark.createDataFrame(res).write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{catalog}.gold.story_validation")
print(f"\n{res.passed.sum()}/{len(res)} checks passed")
assert res.passed.all(), res[~res.passed].to_string()
```

Output:

```text

33/33 checks passed
```
