# Databricks notebook source
# MAGIC %md
# MAGIC # 06 · Genie space: "Readmission & HRRP Analyst"
# MAGIC
# MAGIC Creates (or updates) a Genie space over the curated gold tables, with business definitions, example SQL and sample
# MAGIC questions. It then **asks the space the story questions through the Genie Conversation API** and records each
# MAGIC question, the generated SQL and the result rows in `gold.genie_eval_transcript`, so we have text evidence that the agent answers correctly.

# COMMAND ----------

# MAGIC %pip install -q "databricks-sdk>=0.60.0"
# MAGIC %restart_python

# COMMAND ----------

dbutils.widgets.text("catalog", "cedarbrook_rcc")
dbutils.widgets.text("warehouse_id", "")
catalog = dbutils.widgets.get("catalog")
warehouse_id = dbutils.widgets.get("warehouse_id")

import json, time, uuid
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
me = w.current_user.me().user_name
TITLE = "Readmission & HRRP Analyst (Cedarbrook Health)"

def oid():
    return uuid.uuid4().hex

TABLES = {
    "gold.unit_period_summary": "Prior-20-week vs last-20-week readmission rate per hospital unit; condition='ALL' is all-cause.",
    "gold.unit_weekly_readmissions": "Weekly 30-day readmission counts and rates per unit and condition.",
    "gold.followup_gap": "7-day follow-up booked at discharge by unit, condition, weekend vs weekday, before vs since 2026-06-19.",
    "gold.readmission_risk_factors": "Trailing-12-month readmission rate by risk factor (follow-up, AI-extracted lives alone / transport barrier, weekend).",
    "gold.hrrp_condition_err": "HRRP excess readmission ratio (ERR) and penalty contribution per hospital and condition.",
    "gold.hrrp_hospital_penalty": "Estimated HRRP penalty per hospital (3% cap).",
    "gold.hrrp_whatif": "Deterministic what-if: raising 7-day follow-up booking to a target %, avoided readmissions, new ERR, penalty saved.",
    "gold.index_admissions": "One row per index admission with 30-day readmission outcome and flags (no names).",
    "gold.patient_risk_scores": "Model risk score and top drivers per index admission (row-filtered by hospital).",
    "silver.staffing_events": "Operational change log: staffing, clinic schedule and program changes with dates.",
}
INSTRUCTIONS = """You answer questions for Cedarbrook Health's care-transitions and finance & quality teams about 30-day readmissions and the CMS Hospital Readmissions Reduction Program (HRRP).
Hospitals: CUMC = Cedarbrook University Medical Center, FCH = Fairhaven Community Hospital, PHMC = Pine Hollow Medical Center. '6 North' / '6N' = unit_id 'CUMC-6N' (6 North Telemetry).
Definitions: readmission rate = readmissions / index admissions, only where outcome_complete = true (full 30-day window observed). Weekend = Friday, Saturday or Sunday discharge (weekend_discharge). 7-day follow-up = fu7_booked (a follow-up within 7 days booked before the patient left).
'Last 20 weeks' and 'prior 20 weeks' use period_20w ('last_20w', 'prior_20w') or gold.unit_period_summary. 'Trailing 12 months' uses trailing_12m = true. HF = heart failure (condition = 'HF').
ERR = observed readmission rate / CMS expected rate; ERR > 1 means excess readmissions and a penalty. Penalty contribution = condition base DRG payments x (ERR - 1); hospital penalty is capped at 3% of total base DRG payments.
Risk-factor questions (follow-up, living alone, transportation, weekend) must use gold.readmission_risk_factors, which is already limited to the trailing 12 months, unless the user asks for another period.
What-if / scenario / 'how much would we save' questions must read gold.hrrp_whatif (precomputed, deterministic) and never recompute the penalty. Scopes: '6N weekend HF', 'CUMC weekend HF (all units)', 'CUMC all HF discharges'; fu7_target_pct from 40 to 100 in steps of 5.
ai_lives_alone and ai_transport_barrier were extracted from discharge-note free text by AI Functions. Always show rates as percentages with one decimal and money in dollars."""
EXAMPLES = [
    ("Which unit's readmission rate rose the most over the last 20 weeks?",
     f"SELECT hospital_id, unit_name, condition, prior_20w_rate_pct, last_20w_rate_pct, delta_pts\nFROM {catalog}.gold.unit_period_summary\nWHERE condition = 'HF' AND prior_20w_index >= 30\nORDER BY delta_pts DESC\nLIMIT 5"),
    ("How does 7-day follow-up booking on 6 North compare on weekends vs weekdays since the staffing change?",
     f"SELECT discharge_day_type, discharges, fu7_booked, fu7_booked_pct\nFROM {catalog}.gold.followup_gap\nWHERE unit_id = 'CUMC-6N' AND condition = 'HF' AND period = 'since_2026-06-19'"),
    ("What is the estimated HRRP penalty for each hospital and which condition drives it?",
     f"SELECT hospital_name, estimated_penalty, uncapped_penalty, at_cap, largest_condition, largest_condition_contribution, largest_condition_err\nFROM {catalog}.gold.hrrp_hospital_penalty\nORDER BY estimated_penalty DESC"),
    ("Do HF patients who live alone readmit more often?",
     f"SELECT factor, value AS lives_alone, index_admissions, readmissions, readmit_rate_pct\nFROM {catalog}.gold.readmission_risk_factors\nWHERE condition = 'HF' AND factor = 'ai_lives_alone'\nORDER BY value DESC"),
    ("If 6 North booked follow-up for 80% of weekend HF discharges, how much penalty would we save?",
     f"SELECT scope, fu7_target_pct, current_fu7_pct, additional_followups, readmissions_avoided, hf_err_current, hf_err_scenario,\n       penalty_current, penalty_scenario, penalty_saved\nFROM {catalog}.gold.hrrp_whatif\nWHERE scope = '6N weekend HF' AND fu7_target_pct = 80"),
]
SAMPLE_QS = [
    "Which unit's HF readmission rate rose the most in the last 20 weeks?",
    "Compare 7-day follow-up booking on 6 North for weekend vs weekday HF discharges since 2026-06-19",
    "What is CUMC's HF ERR and how much of the HRRP penalty comes from heart failure?",
    "Do HF patients who live alone readmit more often?",
    "If 6 North booked follow-up for 80% of weekend HF discharges, how much penalty would we save?",
]

space = {
    "version": 2,
    "config": {"sample_questions": [{"id": oid(), "question": [q]} for q in SAMPLE_QS]},
    "data_sources": {"tables": sorted(
        [{"identifier": f"{catalog}.{t}", "description": [d]} for t, d in TABLES.items()], key=lambda x: x["identifier"])},
    "instructions": {
        "text_instructions": [{"id": oid(), "content": [INSTRUCTIONS]}],
        "example_question_sqls": [{"id": oid(), "question": [q], "sql": [l + "\n" for l in s.split("\n")]} for q, s in EXAMPLES],
    },
}
for k in ("text_instructions", "example_question_sqls"):
    space["instructions"][k] = sorted(space["instructions"][k], key=lambda x: x["id"])
space["config"]["sample_questions"] = sorted(space["config"]["sample_questions"], key=lambda x: x["id"])

existing = [s for s in w.api_client.do("GET", "/api/2.0/genie/spaces").get("spaces", []) if s.get("title") == TITLE]
body = {"title": TITLE, "description": "Natural-language analytics over Cedarbrook readmissions, follow-up gaps and HRRP penalty.",
        "warehouse_id": warehouse_id, "serialized_space": json.dumps(space)}
if existing:
    space_id = existing[0]["space_id"]
    w.api_client.do("PATCH", f"/api/2.0/genie/spaces/{space_id}", body=body)
    print("updated Genie space", space_id)
else:
    body["parent_path"] = f"/Workspace/Users/{me}"
    space_id = w.api_client.do("POST", "/api/2.0/genie/spaces", body=body)["space_id"]
    print("created Genie space", space_id)
host = w.config.host.rstrip("/")
print(f"{host}/genie/rooms/{space_id}")
spark.sql(f"CREATE TABLE IF NOT EXISTS {catalog}.gold.app_config (key STRING, value STRING)")
spark.sql(f"MERGE INTO {catalog}.gold.app_config t USING (SELECT 'genie_space_id' AS key, '{space_id}' AS value) s ON t.key = s.key "
          "WHEN MATCHED THEN UPDATE SET value = s.value WHEN NOT MATCHED THEN INSERT *")

# COMMAND ----------

# MAGIC %md ### Ask the story questions through the Genie Conversation API

# COMMAND ----------

def ask(question, timeout=240):
    r = w.api_client.do("POST", f"/api/2.0/genie/spaces/{space_id}/start-conversation", body={"content": question})
    cid, mid = r["conversation_id"], r["message_id"]
    t0 = time.time()
    while True:
        m = w.api_client.do("GET", f"/api/2.0/genie/spaces/{space_id}/conversations/{cid}/messages/{mid}")
        if m.get("status") in ("COMPLETED", "FAILED", "CANCELLED") or time.time() - t0 > timeout:
            break
        time.sleep(4)
    out = {"question": question, "status": m.get("status"), "conversation_id": cid, "message_id": mid, "sql": None,
           "text": None, "columns": None, "rows": None}
    for a in m.get("attachments", []) or []:
        if a.get("text"):
            out["text"] = a["text"].get("content")
        if a.get("query"):
            out["sql"] = a["query"].get("query")
            out["text"] = out["text"] or a["query"].get("description")
            res = w.api_client.do("GET", f"/api/2.0/genie/spaces/{space_id}/conversations/{cid}/messages/{mid}/attachments/{a['attachment_id']}/query-result")
            sr = res.get("statement_response", {})
            out["columns"] = [c["name"] for c in sr.get("manifest", {}).get("schema", {}).get("columns", [])]
            out["rows"] = (sr.get("result", {}) or {}).get("data_array", [])[:20]
    return out

transcript = []
for q in SAMPLE_QS:
    a = ask(q)
    transcript.append(a)
    print("=" * 100)
    print("Q:", q)
    print("status:", a["status"])
    if a["text"]:
        print("Genie:", a["text"])
    if a["sql"]:
        print("SQL:\n" + a["sql"])
    if a["rows"] is not None:
        print("columns:", a["columns"])
        for row in a["rows"][:10]:
            print("  ", row)

# COMMAND ----------

import pandas as pd
tdf = pd.DataFrame([{**t, "columns": json.dumps(t["columns"]), "rows": json.dumps(t["rows"]), "space_id": space_id} for t in transcript])
spark.createDataFrame(tdf.astype(str)).write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{catalog}.gold.genie_eval_transcript")
print("completed:", sum(t["status"] == "COMPLETED" for t in transcript), "/", len(transcript))

# COMMAND ----------

# MAGIC %md ### LLM judge: a repeatable quality check on Genie's answers
# MAGIC For every question, the **expected answer is computed directly from the gold tables** (deterministic SQL, not by an LLM).
# MAGIC A judge model then compares Genie's answer (text plus result rows) with it and returns PASS/FAIL, a 1–5 score and a rationale.
# MAGIC Results are **appended** to `gold.genie_eval_judgements` with a run timestamp, so Genie quality is tracked run over run.

# COMMAND ----------

dbutils.widgets.text("judge_endpoint", "databricks-claude-sonnet-4-6")
judge_endpoint = dbutils.widgets.get("judge_endpoint")
G = f"{catalog}.gold"
EXPECTED_SQL = {
    SAMPLE_QS[0]: f"SELECT unit_name, prior_20w_rate_pct, last_20w_rate_pct, delta_pts FROM {G}.unit_period_summary WHERE condition='HF' AND prior_20w_index >= 30 ORDER BY delta_pts DESC LIMIT 1",
    SAMPLE_QS[1]: f"SELECT discharge_day_type, discharges, fu7_booked, fu7_booked_pct FROM {G}.followup_gap WHERE unit_id='CUMC-6N' AND condition='HF' AND period='since_2026-06-19'",
    SAMPLE_QS[2]: f"SELECT hrrp_condition, err, penalty_contribution FROM {G}.hrrp_condition_err WHERE hospital_id='CUMC' AND hrrp_condition='HF'",
    SAMPLE_QS[3]: f"SELECT value AS lives_alone, index_admissions, readmit_rate_pct FROM {G}.readmission_risk_factors WHERE condition='HF' AND factor='ai_lives_alone'",
    SAMPLE_QS[4]: f"SELECT fu7_target_pct, readmissions_avoided, hf_err_scenario, penalty_saved FROM {G}.hrrp_whatif WHERE scope='6N weekend HF' AND fu7_target_pct=80",
}
JUDGE_SYSTEM = ("You are a strict evaluator of an analytics assistant. Compare the ASSISTANT ANSWER (its text and result rows) with the EXPECTED "
                "ANSWER computed from the source tables. PASS only if the key numbers and entities in the assistant answer match the expected answer "
                "(allow rounding to 1 decimal place and equivalent formatting). Return ONLY JSON: "
                '{"verdict": "PASS" or "FAIL", "score": integer 1-5, "rationale": "one sentence"}')

def judge(question, expected, answer):
    msg = {"question": question, "expected_answer_rows": expected,
           "assistant_answer": {"text": answer.get("text"), "columns": answer.get("columns"), "rows": (answer.get("rows") or [])[:10]}}
    r = w.api_client.do("POST", f"/serving-endpoints/{judge_endpoint}/invocations",
                        body={"messages": [{"role": "system", "content": JUDGE_SYSTEM},
                                           {"role": "user", "content": json.dumps(msg, default=str)}],
                              "max_tokens": 300, "temperature": 0})
    content = r["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    out = json.loads(content[content.find("{"): content.rfind("}") + 1])
    return out["verdict"].upper(), int(out["score"]), out["rationale"]

run_ts = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
judgements = []
for t in transcript:
    expected = [r.asDict() for r in spark.sql(EXPECTED_SQL[t["question"]]).collect()]
    verdict, score, rationale = judge(t["question"], expected, t)
    judgements.append({"run_ts": run_ts, "space_id": space_id, "question": t["question"], "genie_status": t["status"],
                       "genie_sql": t["sql"], "genie_text": t["text"], "genie_rows": json.dumps(t["rows"], default=str),
                       "expected_rows": json.dumps(expected, default=str), "judge_model": judge_endpoint,
                       "verdict": verdict, "score": score, "rationale": rationale})
    print(f"{verdict} ({score}/5)  {t['question']}\n   expected: {json.dumps(expected, default=str)[:200]}\n   judge: {rationale}\n")

jdf = pd.DataFrame(judgements)
spark.createDataFrame(jdf).write.mode("append").option("mergeSchema", True).saveAsTable(f"{catalog}.gold.genie_eval_judgements")
display(spark.sql(f"""SELECT run_ts, count(*) AS questions, count_if(verdict='PASS') AS passed, round(avg(score), 2) AS avg_score
                      FROM {catalog}.gold.genie_eval_judgements GROUP BY run_ts ORDER BY run_ts DESC LIMIT 10"""))
