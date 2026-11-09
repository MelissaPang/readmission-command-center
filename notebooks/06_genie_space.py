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
ai_lives_alone and ai_transport_barrier were extracted from discharge-note free text by AI Functions. Always show rates as percentages with one decimal and money in dollars."""
EXAMPLES = [
    ("Which unit's readmission rate rose the most over the last 20 weeks?",
     f"SELECT hospital_id, unit_name, condition, prior_20w_rate_pct, last_20w_rate_pct, delta_pts\nFROM {catalog}.gold.unit_period_summary\nWHERE condition = 'HF' AND prior_20w_index >= 30\nORDER BY delta_pts DESC\nLIMIT 5"),
    ("How does 7-day follow-up booking on 6 North compare on weekends vs weekdays since the staffing change?",
     f"SELECT discharge_day_type, discharges, fu7_booked, fu7_booked_pct\nFROM {catalog}.gold.followup_gap\nWHERE unit_id = 'CUMC-6N' AND condition = 'HF' AND period = 'since_2026-06-19'"),
    ("What is the estimated HRRP penalty for each hospital and which condition drives it?",
     f"SELECT hospital_name, estimated_penalty, uncapped_penalty, at_cap, largest_condition, largest_condition_contribution, largest_condition_err\nFROM {catalog}.gold.hrrp_hospital_penalty\nORDER BY estimated_penalty DESC"),
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
