"""Export Lakeflow pipeline evidence (event log, rows written, data-quality expectations) and table-level
query results as text: evidence/pipeline_events.md and evidence/query_results.md.

Usage: python scripts/export_pipeline_evidence.py
"""
import json
import os
import subprocess

P = ["-p", "e2-demo-field-eng"]
WH = "12444b712298f9ac"
C = "cedarbrook_rcc"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sql(q):
    body = {"warehouse_id": WH, "wait_timeout": "50s", "statement": q}
    r = json.loads(subprocess.run(["databricks", "api", "post", "/api/2.0/sql/statements", *P, "--json", json.dumps(body)],
                                  capture_output=True, text=True, check=True).stdout)
    while r["status"]["state"] in ("PENDING", "RUNNING"):  # warehouse may be cold-starting
        __import__("time").sleep(5)
        r = json.loads(subprocess.run(["databricks", "api", "get", f"/api/2.0/sql/statements/{r['statement_id']}", *P],
                                      capture_output=True, text=True, check=True).stdout)
    if r["status"]["state"] != "SUCCEEDED":
        raise RuntimeError(f"{r['status']} :: {q[:200]}")
    cols = [c["name"] for c in r["manifest"]["schema"]["columns"]]
    return cols, (r.get("result") or {}).get("data_array") or []


def md_table(cols, rows):
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join("" if v is None else str(v).replace("|", "/").replace("\n", " ")[:120] for v in r) + " |" for r in rows]
    return "\n".join(out)


def section(title, q, note=""):
    cols, rows = sql(q)
    return f"### {title}\n\n{note}\n```sql\n{q.strip()}\n```\n\n{md_table(cols, rows)}\n\n({len(rows)} rows)\n"


summary = json.loads(subprocess.run(["databricks", "bundle", "summary", "-o", "json", *P], capture_output=True, text=True,
                                    check=True, cwd=ROOT).stdout)
pid = summary["resources"]["pipelines"]["rcc_pipeline"]["id"]
updates = json.loads(subprocess.run(["databricks", "pipelines", "list-updates", pid, "--max-results", "10", *P, "-o", "json"],
                                    capture_output=True, text=True, check=True).stdout).get("updates", [])

md = [f"# Lakeflow pipeline evidence: rcc_pipeline\n", f"* pipeline_id: `{pid}` (serverless, Lakeflow Declarative Pipelines, SQL)",
      f"* source: `pipelines/01_bronze.sql`, `02_silver.sql`, `03_gold.sql`\n", "## Recent updates\n",
      md_table(["update_id", "state", "full_refresh", "full_refresh_selection", "cause"],
               [[u["update_id"], u["state"], u.get("full_refresh"), ",".join(u.get("full_refresh_selection", []))[:80], u.get("cause")] for u in updates]), ""]

md.append(section("Rows written per flow (latest successful update of each table)", f"""
WITH ev AS (
  SELECT origin.update_id, origin.flow_name, timestamp,
         details:flow_progress.metrics.num_output_rows::bigint AS rows_out,
         details:flow_progress.status::string AS status
  FROM event_log('{pid}') WHERE event_type = 'flow_progress')
SELECT flow_name, max_by(rows_out, timestamp) AS last_num_output_rows, max(timestamp) AS last_completed
FROM ev WHERE status = 'COMPLETED' AND rows_out IS NOT NULL
GROUP BY flow_name ORDER BY flow_name"""))

md.append(section("Data-quality expectations (all updates)", f"""
SELECT origin.flow_name AS flow, e.name AS expectation, sum(e.passed_records) AS passed, sum(e.failed_records) AS failed
FROM event_log('{pid}')
LATERAL VIEW explode(from_json(details:flow_progress.data_quality.expectations,
  'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) x AS e
WHERE event_type = 'flow_progress' AND details:flow_progress.data_quality.expectations IS NOT NULL
GROUP BY ALL ORDER BY flow, expectation""",
    "Summed over all pipeline updates (3 recomputes of silver, so each planted defect is counted 3 times). Planted defects: 6 encounters with discharge before admit are dropped (18 = 6 x 3); 45 duplicate encounter rows are removed by the QUALIFY de-dup."))

md.append(section("Dropped rows per dataset (data_quality.dropped_records)", f"""
SELECT origin.flow_name AS flow, sum(details:flow_progress.data_quality.dropped_records::bigint) AS dropped_records
FROM event_log('{pid}') WHERE event_type = 'flow_progress' AND details:flow_progress.data_quality.dropped_records IS NOT NULL
GROUP BY ALL ORDER BY flow"""))

md.append(section("Row counts bronze -> silver -> gold", f"""
SELECT 'bronze.encounters' AS t, count(*) AS n FROM {C}.bronze.encounters UNION ALL
SELECT 'silver.encounters (dedup + DQ)', count(*) FROM {C}.silver.encounters UNION ALL
SELECT 'gold.index_admissions', count(*) FROM {C}.gold.index_admissions UNION ALL
SELECT 'bronze.discharge_notes', count(*) FROM {C}.bronze.discharge_notes UNION ALL
SELECT 'silver.discharge_note_signals (AI)', count(*) FROM {C}.silver.discharge_note_signals UNION ALL
SELECT 'silver.discharge_note_signals ai_error', count_if(ai_error IS NOT NULL) FROM {C}.silver.discharge_note_signals UNION ALL
SELECT 'gold.patient_risk_scores', count(*) FROM {C}.gold.patient_risk_scores UNION ALL
SELECT 'gold.discharge_worklist', count(*) FROM {C}.gold.discharge_worklist"""))
open(f"{ROOT}/evidence/pipeline_events.md", "w").write("\n".join(md))
print("wrote evidence/pipeline_events.md")

q = ["# Query results (SQL warehouse, gold tables)\n", "Every number in the customer story, queried from the gold layer.\n"]
q.append(section("6 North vs every other unit: prior 20 weeks vs last 20 weeks",
                 f"SELECT hospital_id, unit_name, condition, prior_20w_index, prior_20w_rate_pct, last_20w_index, last_20w_rate_pct, delta_pts FROM {C}.gold.unit_period_summary WHERE condition = 'ALL' OR (unit_id = 'CUMC-6N' AND condition = 'HF') ORDER BY condition DESC, delta_pts DESC"))
q.append(section("7-day follow-up gap on 6 North (HF)", f"SELECT * FROM {C}.gold.followup_gap WHERE unit_id = 'CUMC-6N' AND condition = 'HF' ORDER BY period, discharge_day_type"))
q.append(section("HF readmission by risk factor, trailing 12 months, all hospitals", f"SELECT factor, value, index_admissions, readmissions, readmit_rate_pct FROM {C}.gold.readmission_risk_factors WHERE condition = 'HF' ORDER BY factor, value"))
q.append(section("HRRP ERR and penalty contribution", f"SELECT hospital_id, hrrp_condition, index_admissions, readmissions, observed_rate, expected_readmission_rate, err, base_op_drg_payments_condition, penalty_contribution FROM {C}.gold.hrrp_condition_err ORDER BY hospital_id, penalty_contribution DESC"))
q.append(section("Estimated HRRP penalty per hospital", f"SELECT * FROM {C}.gold.hrrp_hospital_penalty ORDER BY estimated_penalty DESC"))
q.append(section("Deterministic what-if (selected targets)", f"SELECT scope, fu7_target_pct, discharges_12m, booked_12m, current_fu7_pct, additional_followups, readmissions_avoided, hf_err_current, hf_err_scenario, penalty_current, penalty_scenario, penalty_saved FROM {C}.gold.hrrp_whatif WHERE fu7_target_pct IN (60, 70, 80, 90, 100) ORDER BY scope, fu7_target_pct"))
q.append(section("Registered model metrics", f"SELECT * FROM {C}.ml.model_metrics"))
q.append(section("Risk tier vs observed readmission (complete outcomes)", f"SELECT risk_tier, count(*) AS index_admissions, round(avg(risk_score), 3) AS mean_score, round(100 * avg(CAST(readmit_30d AS INT)), 1) AS observed_readmit_pct FROM {C}.gold.patient_risk_scores WHERE outcome_complete GROUP BY risk_tier ORDER BY mean_score DESC"))
q.append(section("Top 6 North worklist rows (served to the app via Lakebase)", f"SELECT encounter_id, unit_name, condition, discharge_ts, weekend_discharge, fu7_booked, ai_lives_alone, risk_score, risk_tier, driver_1, driver_2, recommended_actions FROM {C}.gold.discharge_worklist WHERE unit_id = 'CUMC-6N' ORDER BY risk_score DESC LIMIT 10"))
q.append(section("App write-back read from the lakehouse (rcc_lakebase UC catalog -> Lakebase Postgres)", "SELECT plan_id, encounter_id, status, model_endpoint, approved_by, approved_ts FROM rcc_lakebase.app_rcc.transition_plans ORDER BY created_ts DESC"))
q.append(section("Story validation results (notebook 99)", f"SELECT * FROM {C}.gold.story_validation"))
open(f"{ROOT}/evidence/query_results.md", "w").write("\n".join(q))
print("wrote evidence/query_results.md")
