"""Readmission Command Center: Databricks App backend (FastAPI).

Reads   : Lakebase Postgres synced tables (public.*): unit trends, worklist, HRRP, what-if.
Writes  : Lakebase app-owned tables (app_rcc.*): transition plans, outreach tasks, audit log.
Gen AI  : Foundation Model API (Claude) drafts transition plans for human approval.
Genie   : Genie Conversation API for natural-language questions.
"""
from __future__ import annotations

import datetime as dt
import decimal
import difflib
import hashlib
import json
import logging
import os
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Any

import psycopg
from databricks.sdk import WorkspaceClient
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rcc")

w = WorkspaceClient()
INSTANCE = os.getenv("LAKEBASE_INSTANCE", "rcc-lakebase")
ASSISTANT_ENDPOINT = os.getenv("ASSISTANT_ENDPOINT", "databricks-claude-sonnet-4-6")
GENIE_SPACE_ID = os.getenv("GENIE_SPACE_ID", "")
APP_SCHEMA = "app_rcc"

# ------------------------------------------------------------------ Lakebase
_tok: dict[str, Any] = {"token": None, "exp": 0.0}
_lock = threading.Lock()


def _password() -> str:
    with _lock:
        if not _tok["token"] or time.time() > _tok["exp"]:
            cred = w.database.generate_database_credential(request_id=str(uuid.uuid4()), instance_names=[INSTANCE])
            _tok.update(token=cred.token, exp=time.time() + 40 * 60)
        return _tok["token"]


def _pg_user() -> str:
    return os.getenv("PGUSER") or w.config.client_id or w.current_user.me().user_name


def _pg_host() -> str:
    return os.getenv("PGHOST") or w.database.get_database_instance(INSTANCE).read_write_dns


@contextmanager
def pg():
    conn = psycopg.connect(host=_pg_host(), port=int(os.getenv("PGPORT", "5432")), dbname=os.getenv("PGDATABASE", "rcc"),
                           user=_pg_user(), password=_password(), sslmode=os.getenv("PGSSLMODE", "require"),
                           row_factory=dict_row, connect_timeout=15)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def q(sql: str, params: tuple | dict | None = None) -> list[dict]:
    with pg() as c, c.cursor() as cur:
        cur.execute(sql, params)
        return [_clean(r) for r in cur.fetchall()] if cur.description else []


def _clean(r: dict) -> dict:
    out = {}
    for k, v in r.items():
        if isinstance(v, decimal.Decimal):
            v = float(v)
        elif isinstance(v, (dt.datetime, dt.date)):
            v = v.isoformat()
        out[k] = v
    return out


DDL = f"""
CREATE SCHEMA IF NOT EXISTS {APP_SCHEMA};
CREATE TABLE IF NOT EXISTS {APP_SCHEMA}.transition_plans (
  plan_id TEXT PRIMARY KEY, encounter_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
  draft_text TEXT NOT NULL, final_text TEXT, model_endpoint TEXT, prompt_sha256 TEXT,
  risk_score DOUBLE PRECISION, created_by TEXT, created_ts TIMESTAMPTZ DEFAULT now(),
  approved_by TEXT, approved_ts TIMESTAMPTZ);
ALTER TABLE {APP_SCHEMA}.transition_plans ADD COLUMN IF NOT EXISTS edited BOOLEAN;
ALTER TABLE {APP_SCHEMA}.transition_plans ADD COLUMN IF NOT EXISTS edit_similarity DOUBLE PRECISION;
ALTER TABLE {APP_SCHEMA}.transition_plans ADD COLUMN IF NOT EXISTS chars_added INTEGER;
ALTER TABLE {APP_SCHEMA}.transition_plans ADD COLUMN IF NOT EXISTS chars_removed INTEGER;
ALTER TABLE {APP_SCHEMA}.transition_plans ADD COLUMN IF NOT EXISTS sections_changed TEXT;
ALTER TABLE {APP_SCHEMA}.transition_plans ADD COLUMN IF NOT EXISTS reject_reason TEXT;
CREATE TABLE IF NOT EXISTS {APP_SCHEMA}.outreach_tasks (
  task_id TEXT PRIMARY KEY, encounter_id TEXT NOT NULL, plan_id TEXT, task_type TEXT NOT NULL,
  description TEXT, assignee TEXT, due_ts TIMESTAMPTZ, status TEXT NOT NULL DEFAULT 'open',
  created_ts TIMESTAMPTZ DEFAULT now(), completed_by TEXT, completed_ts TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS {APP_SCHEMA}.plan_audit_log (
  event_id TEXT PRIMARY KEY, plan_id TEXT, encounter_id TEXT, action TEXT NOT NULL, actor TEXT,
  detail JSONB, event_ts TIMESTAMPTZ DEFAULT now());
"""

app = FastAPI(title="Readmission Command Center")


@app.on_event("startup")
def _startup():
    try:
        with pg() as c, c.cursor() as cur:
            cur.execute(DDL)
        log.info("Lakebase ready (user=%s, host=%s)", _pg_user(), _pg_host())
    except Exception as e:  # app still serves static pages; /api/health shows the error
        log.exception("Lakebase init failed: %s", e)


def _user(req: Request) -> str:
    return req.headers.get("X-Forwarded-Email") or req.headers.get("X-Forwarded-User") or "local-user"


def _audit(cur, action, actor, plan_id=None, encounter_id=None, detail=None):
    cur.execute(f"INSERT INTO {APP_SCHEMA}.plan_audit_log (event_id, plan_id, encounter_id, action, actor, detail) VALUES (%s,%s,%s,%s,%s,%s)",
                (uuid.uuid4().hex, plan_id, encounter_id, action, actor, json.dumps(detail or {})))


# --------------------------------------------------------------------- API
@app.get("/api/health")
def health():
    try:
        rows = q("SELECT count(*) AS n FROM public.discharge_worklist")
        return {"status": "ok", "lakebase": "ok", "worklist_rows": rows[0]["n"], "assistant_endpoint": ASSISTANT_ENDPOINT,
                "genie_space_id": GENIE_SPACE_ID, "pg_user": _pg_user()}
    except Exception as e:
        return JSONResponse({"status": "degraded", "error": str(e)}, status_code=503)


@app.get("/api/units/summary")
def units_summary(condition: str = "ALL"):
    return q("""SELECT hospital_id, hospital_name, unit_id, unit_name, condition, prior_20w_index, prior_20w_rate_pct,
                       last_20w_index, last_20w_rate_pct, delta_pts
                FROM public.unit_period_summary WHERE condition = %s AND last_20w_index > 0 ORDER BY delta_pts DESC""", (condition,))


@app.get("/api/units/{unit_id}/weekly")
def unit_weekly(unit_id: str, condition: str = "HF"):
    return q("""SELECT discharge_week, index_admissions, readmissions, readmit_rate_pct, weekend_discharges, fu7_booked
                FROM public.unit_weekly WHERE unit_id = %s AND condition = %s ORDER BY discharge_week""", (unit_id, condition))


@app.get("/api/followup-gap")
def followup_gap(unit_id: str = "CUMC-6N", condition: str = "HF"):
    return q("""SELECT discharge_day_type, period, discharges, fu7_booked, fu7_booked_pct FROM public.followup_gap
                WHERE unit_id = %s AND condition = %s ORDER BY period, discharge_day_type""", (unit_id, condition))


@app.get("/api/staffing-events")
def staffing_events():
    return q("SELECT event_id, scope_id, event_date, event_type, description FROM public.staffing_events ORDER BY event_date")


@app.get("/api/risk-factors")
def risk_factors(condition: str = "HF"):
    return q("SELECT factor, value, index_admissions, readmissions, readmit_rate_pct FROM public.risk_factors WHERE condition = %s ORDER BY factor, value",
             (condition,))


@app.get("/api/worklist")
def worklist(hospital_id: str | None = None, unit_id: str | None = None, risk_tier: str | None = None,
             no_followup: bool = False, limit: int = 200):
    where, params = ["1=1"], []
    for col, val in (("hospital_id", hospital_id), ("unit_id", unit_id), ("risk_tier", risk_tier)):
        if val:
            where.append(f"w.{col} = %s")
            params.append(val)
    if no_followup:
        where.append("NOT w.fu7_booked")
    params.append(min(limit, 1000))
    return q(f"""SELECT w.encounter_id, w.first_name, w.last_name, w.mrn, w.age, w.hospital_id, w.unit_id, w.unit_name, w.condition,
                        w.discharge_ts, w.discharge_dow, w.weekend_discharge, w.days_since_discharge, w.fu7_booked,
                        w.ai_lives_alone, w.ai_transport_barrier, w.risk_score, w.risk_tier, w.driver_1, w.driver_2,
                        w.recommended_actions, w.nurse_briefing, p.status AS plan_status
                 FROM public.discharge_worklist w
                 LEFT JOIN LATERAL (SELECT status FROM {APP_SCHEMA}.transition_plans t WHERE t.encounter_id = w.encounter_id
                                    ORDER BY created_ts DESC LIMIT 1) p ON true
                 WHERE {' AND '.join(where)} ORDER BY w.risk_score DESC LIMIT %s""", tuple(params))


@app.get("/api/patients/{encounter_id}")
def patient(encounter_id: str):
    rows = q("SELECT * FROM public.discharge_worklist WHERE encounter_id = %s", (encounter_id,))
    if not rows:
        raise HTTPException(404, "encounter not in worklist")
    plans = q(f"SELECT * FROM {APP_SCHEMA}.transition_plans WHERE encounter_id = %s ORDER BY created_ts DESC", (encounter_id,))
    tasks = q(f"SELECT * FROM {APP_SCHEMA}.outreach_tasks WHERE encounter_id = %s ORDER BY created_ts", (encounter_id,))
    return {"patient": rows[0], "plans": plans, "tasks": tasks}


PLAN_SYSTEM = (
    "You are a heart-failure and care-transitions nurse planner at Cedarbrook Health. Write a concise post-discharge "
    "transition plan for the care-transitions team. Use ONLY the facts in the patient context; do not invent appointments, "
    "medications or diagnoses. Format as markdown with these sections: **Why this patient is at risk** (1-2 sentences "
    "citing the model drivers and note evidence), **Within 48 hours**, **Within 7 days**, **Social needs**, **Teach-back "
    "topics**. Use bullet points and at most 170 words in total. End with: 'Draft generated by AI. Requires RN review and approval.'")


def _llm(messages: list[dict], max_tokens: int = 600) -> str:
    r = w.api_client.do("POST", f"/serving-endpoints/{ASSISTANT_ENDPOINT}/invocations",
                        body={"messages": messages, "max_tokens": max_tokens, "temperature": 0.2})
    content = r["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return content


@app.post("/api/patients/{encounter_id}/draft-plan")
def draft_plan(encounter_id: str, req: Request):
    p = patient(encounter_id)["patient"]
    ctx = {k: p.get(k) for k in ("age", "condition", "principal_dx_desc", "unit_name", "discharge_ts", "discharge_dow",
                                  "discharge_disposition", "days_since_discharge", "fu7_booked", "first_followup_ts",
                                  "ai_lives_alone", "ai_transport_barrier", "ai_followup_status", "ai_evidence",
                                  "risk_score", "risk_tier", "driver_1", "driver_2", "driver_3", "recommended_actions",
                                  "nurse_briefing", "primary_language")}
    prompt = "Patient context (JSON):\n" + json.dumps(ctx, default=str, indent=1)
    t0 = time.time()
    text = _llm([{"role": "system", "content": PLAN_SYSTEM}, {"role": "user", "content": prompt}])
    plan_id = uuid.uuid4().hex[:12]
    user = _user(req)
    sha = hashlib.sha256(prompt.encode()).hexdigest()
    with pg() as c, c.cursor() as cur:
        cur.execute(f"""INSERT INTO {APP_SCHEMA}.transition_plans (plan_id, encounter_id, status, draft_text, model_endpoint,
                        prompt_sha256, risk_score, created_by) VALUES (%s,%s,'draft',%s,%s,%s,%s,%s)""",
                    (plan_id, encounter_id, text, ASSISTANT_ENDPOINT, sha, p.get("risk_score"), user))
        _audit(cur, "draft_generated", user, plan_id, encounter_id,
               {"model": ASSISTANT_ENDPOINT, "latency_s": round(time.time() - t0, 2), "prompt_sha256": sha})
    log.info("draft plan %s for %s (%.1fs)", plan_id, encounter_id, time.time() - t0)
    return {"plan_id": plan_id, "encounter_id": encounter_id, "status": "draft", "draft_text": text,
            "model_endpoint": ASSISTANT_ENDPOINT, "latency_s": round(time.time() - t0, 2), "context": ctx}


class Approve(BaseModel):
    final_text: str | None = None


SECTIONS = ["Why this patient is at risk", "Within 48 hours", "Within 7 days", "Social needs", "Teach-back topics"]


def _section(text: str, name: str) -> str:
    """Text of one markdown section (from its heading to the next known heading)."""
    i = text.find(name)
    if i < 0:
        return ""
    ends = [text.find(n, i + len(name)) for n in SECTIONS if n != name]
    ends = [e for e in ends if e > i]
    return text[i:min(ends) if ends else len(text)].strip()


def edit_stats(draft: str, final: str) -> dict:
    """How much the nurse changed the AI draft: similarity, characters added/removed, sections changed."""
    sm = difflib.SequenceMatcher(None, draft, final)
    added = removed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "delete"):
            removed += i2 - i1
        if tag in ("replace", "insert"):
            added += j2 - j1
    changed = [n for n in SECTIONS if _section(draft, n) != _section(final, n)]
    return {"edited": draft.strip() != final.strip(), "edit_similarity": round(sm.ratio(), 4),
            "chars_added": added, "chars_removed": removed, "sections_changed": changed}


TASKS = [
    ("book_followup", "Book 7-day follow-up", lambda p: not p.get("fu7_booked"), 2),
    ("caregiver_check", "Caregiver check + home-health referral", lambda p: p.get("ai_lives_alone"), 3),
    ("transportation", "Arrange transportation for follow-up", lambda p: p.get("ai_transport_barrier"), 3),
    ("pharmacist_call", "Pharmacist med-reconciliation call", lambda p: p.get("condition") == "HF", 2),
]


@app.post("/api/plans/{plan_id}/approve")
def approve(plan_id: str, body: Approve, req: Request):
    user = _user(req)
    plans = q(f"SELECT * FROM {APP_SCHEMA}.transition_plans WHERE plan_id = %s", (plan_id,))
    if not plans:
        raise HTTPException(404, "plan not found")
    plan = plans[0]
    p = q("SELECT * FROM public.discharge_worklist WHERE encounter_id = %s", (plan["encounter_id"],))[0]
    created = []
    final = body.final_text or plan["draft_text"]
    es = edit_stats(plan["draft_text"], final)
    with pg() as c, c.cursor() as cur:
        cur.execute(f"""UPDATE {APP_SCHEMA}.transition_plans SET status='approved', final_text=%s, approved_by=%s, approved_ts=now(),
                        edited=%s, edit_similarity=%s, chars_added=%s, chars_removed=%s, sections_changed=%s
                        WHERE plan_id=%s""", (final, user, es["edited"], es["edit_similarity"], es["chars_added"],
                                               es["chars_removed"], ",".join(es["sections_changed"]), plan_id))
        for ttype, desc, cond, due_days in TASKS:
            if cond(p):
                tid = uuid.uuid4().hex[:12]
                cur.execute(f"""INSERT INTO {APP_SCHEMA}.outreach_tasks (task_id, encounter_id, plan_id, task_type, description, assignee, due_ts)
                                VALUES (%s,%s,%s,%s,%s,%s, now() + make_interval(days => %s))""",
                            (tid, plan["encounter_id"], plan_id, ttype, desc, "care-transitions-queue", due_days))
                created.append({"task_id": tid, "task_type": ttype, "description": desc})
        _audit(cur, "plan_edited" if es["edited"] else "plan_accepted_as_is", user, plan_id, plan["encounter_id"], es)
        _audit(cur, "plan_approved", user, plan_id, plan["encounter_id"], {"tasks_created": len(created), **es})
    return {"plan_id": plan_id, "status": "approved", "approved_by": user, "edit_stats": es, "tasks_created": created}


class Reject(BaseModel):
    reason: str | None = None


@app.post("/api/plans/{plan_id}/reject")
def reject(plan_id: str, req: Request, body: Reject | None = None):
    user = _user(req)
    reason = (body.reason if body else None) or "not specified"
    with pg() as c, c.cursor() as cur:
        cur.execute(f"UPDATE {APP_SCHEMA}.transition_plans SET status='rejected', reject_reason=%s WHERE plan_id=%s RETURNING encounter_id",
                    (reason, plan_id))
        r = cur.fetchone()
        if not r:
            raise HTTPException(404, "plan not found")
        _audit(cur, "plan_rejected", user, plan_id, r["encounter_id"], {"reason": reason})
    return {"plan_id": plan_id, "status": "rejected"}


@app.get("/api/outreach-tasks")
def outreach_tasks(status: str = "open"):
    return q(f"""SELECT t.*, w.first_name, w.last_name, w.unit_name, w.risk_tier, w.home_phone
                 FROM {APP_SCHEMA}.outreach_tasks t LEFT JOIN public.discharge_worklist w USING (encounter_id)
                 WHERE t.status = %s ORDER BY t.due_ts""", (status,))


@app.post("/api/outreach-tasks/{task_id}/complete")
def complete_task(task_id: str, req: Request):
    user = _user(req)
    with pg() as c, c.cursor() as cur:
        cur.execute(f"UPDATE {APP_SCHEMA}.outreach_tasks SET status='done', completed_by=%s, completed_ts=now() WHERE task_id=%s RETURNING plan_id, encounter_id",
                    (user, task_id))
        r = cur.fetchone()
        if not r:
            raise HTTPException(404, "task not found")
        _audit(cur, "task_completed", user, r["plan_id"], r["encounter_id"], {"task_id": task_id})
    return {"task_id": task_id, "status": "done"}


@app.get("/api/hrrp")
def hrrp():
    return {"hospitals": q("SELECT * FROM public.hrrp_hospital ORDER BY estimated_penalty DESC"),
            "conditions": q("SELECT * FROM public.hrrp_condition ORDER BY hospital_id, penalty_contribution DESC")}


@app.get("/api/hrrp/whatif")
def whatif(scope: str = "6N weekend HF"):
    return q("SELECT * FROM public.hrrp_whatif WHERE scope = %s ORDER BY fu7_target_pct", (scope,))


class Ask(BaseModel):
    question: str
    conversation_id: str | None = None


@app.post("/api/genie/ask")
def genie_ask(body: Ask):
    if not GENIE_SPACE_ID:
        raise HTTPException(503, "Genie space not configured")
    base = f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}"
    if body.conversation_id:
        r = w.api_client.do("POST", f"{base}/conversations/{body.conversation_id}/messages", body={"content": body.question})
        cid, mid = body.conversation_id, r.get("message_id") or r.get("id")
    else:
        r = w.api_client.do("POST", f"{base}/start-conversation", body={"content": body.question})
        cid, mid = r["conversation_id"], r["message_id"]
    t0 = time.time()
    while True:
        m = w.api_client.do("GET", f"{base}/conversations/{cid}/messages/{mid}")
        if m.get("status") in ("COMPLETED", "FAILED", "CANCELLED") or time.time() - t0 > 120:
            break
        time.sleep(2)
    out = {"conversation_id": cid, "status": m.get("status"), "text": None, "sql": None, "columns": [], "rows": []}
    for a in m.get("attachments") or []:
        if a.get("text"):
            out["text"] = a["text"].get("content")
        if a.get("query"):
            out["sql"] = a["query"].get("query")
            out["text"] = out["text"] or a["query"].get("description")
            res = w.api_client.do("GET", f"{base}/conversations/{cid}/messages/{mid}/attachments/{a['attachment_id']}/query-result")
            sr = res.get("statement_response", {})
            out["columns"] = [c["name"] for c in sr.get("manifest", {}).get("schema", {}).get("columns", [])]
            out["rows"] = ((sr.get("result") or {}).get("data_array") or [])[:50]
    return out


# ---------------------------------------------------------------- frontend
STATIC = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))
