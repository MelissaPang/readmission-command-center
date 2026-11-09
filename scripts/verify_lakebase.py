"""Verify the Lakebase layer behind the app: synced tables match their UC sources, the app's SP can read and write,
and app writes are readable back in Unity Catalog. Writes evidence/lakebase_verification.md.

Usage: uv run --with databricks-sdk --with "psycopg[binary]" python scripts/verify_lakebase.py
"""
import datetime as dt
import hashlib
import json
import os
import subprocess
import uuid

import psycopg
from databricks.sdk import WorkspaceClient

PROFILE, INSTANCE, DB, WH, C = "e2-demo-field-eng", "rcc-lakebase", "rcc", "12444b712298f9ac", "cedarbrook_rcc"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
w = WorkspaceClient(profile=PROFILE)

# table -> (UC source, key columns, numeric column to sum)
TABLES = {
    "discharge_worklist": (f"{C}.gold.discharge_worklist", ["encounter_id"], "risk_score"),
    "hrrp_whatif": (f"{C}.gold.hrrp_whatif", ["scope", "fu7_target_pct"], "penalty_saved"),
    "unit_weekly": (f"{C}.gold.app_unit_weekly", ["unit_id", "condition", "discharge_week"], "readmissions"),
    "unit_period_summary": (f"{C}.gold.app_unit_period_summary", ["unit_id", "condition"], "last_20w_readmits"),
    "followup_gap": (f"{C}.gold.app_followup_gap", ["unit_id", "condition", "discharge_day_type", "period"], "fu7_booked"),
    "risk_factors": (f"{C}.gold.app_risk_factors", ["condition", "factor", "value"], "readmissions"),
    "hrrp_condition": (f"{C}.gold.app_hrrp_condition", ["hospital_id", "hrrp_condition"], "penalty_contribution"),
    "hrrp_hospital": (f"{C}.gold.app_hrrp_hospital", ["hospital_id"], "estimated_penalty"),
    "staffing_events": (f"{C}.gold.app_staffing_events", ["event_id"], None),
}


def uc(q):
    body = {"warehouse_id": WH, "wait_timeout": "50s", "statement": q}
    r = json.loads(subprocess.run(["databricks", "api", "post", "/api/2.0/sql/statements", "-p", PROFILE, "--json", json.dumps(body)],
                                  capture_output=True, text=True, check=True).stdout)
    assert r["status"]["state"] == "SUCCEEDED", r["status"]
    return r["result"]["data_array"]


def key_hash(keys):
    return hashlib.sha256("\n".join(sorted("|".join("" if v is None else str(v) for v in k) for k in keys)).encode()).hexdigest()[:16]


def norm(v):
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()[:10]
    return v


inst = w.database.get_database_instance(INSTANCE)
token = w.database.generate_database_credential(request_id=str(uuid.uuid4()), instance_names=[INSTANCE]).token
me = w.current_user.me().user_name
lines = [f"# Lakebase verification ({dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M UTC})\n",
         f"* instance `{INSTANCE}`: state **{inst.state.value}**, capacity {inst.effective_capacity}, PG {inst.pg_version}, host `{inst.read_write_dns}`\n",
         "## 1. Synced tables vs Unity Catalog source\n",
         "| Lakebase table | sync state | UC rows | PG rows | key hash UC | key hash PG | sum UC | sum PG | match |", "|---|---|---|---|---|---|---|---|---|"]
all_ok = True
with psycopg.connect(host=inst.read_write_dns, dbname=DB, user=me, password=token, sslmode="require") as pg:
    for t, (src, keys, num) in TABLES.items():
        state = w.database.get_synced_database_table(f"rcc_lakebase.public.{t}").data_synchronization_status.detailed_state.value
        kc = ", ".join(keys)
        uc_keys = uc(f"SELECT {kc} FROM {src}")
        pg_keys = pg.execute(f'SELECT {kc} FROM public."{t}"').fetchall()
        uc_sum = float(uc(f"SELECT coalesce(sum({num}), 0) FROM {src}")[0][0]) if num else None
        pg_sum = float(pg.execute(f'SELECT coalesce(sum({num}), 0) FROM public."{t}"').fetchone()[0]) if num else None
        hu = key_hash(uc_keys)
        hp = key_hash([[norm(v) for v in r] for r in pg_keys])
        ok = len(uc_keys) == len(pg_keys) and hu == hp and (num is None or abs(uc_sum - pg_sum) < 0.01)
        all_ok &= ok
        lines.append(f"| public.{t} | {state} | {len(uc_keys)} | {len(pg_keys)} | {hu} | {hp} | "
                     f"{'' if uc_sum is None else round(uc_sum, 2)} | {'' if pg_sum is None else round(pg_sum, 2)} | {'✅' if ok else '❌'} |")
        print(f"{t:22s} uc={len(uc_keys):5d} pg={len(pg_keys):5d} keys {'=' if hu == hp else '!='} sum {uc_sum} vs {pg_sum} -> {'OK' if ok else 'MISMATCH'}")

    # spot-check one row field by field
    enc = pg.execute("SELECT encounter_id FROM public.discharge_worklist WHERE unit_id='CUMC-6N' ORDER BY risk_score DESC LIMIT 1").fetchone()[0]
    cols = ["encounter_id", "last_name", "mrn", "unit_id", "condition", "fu7_booked", "ai_lives_alone", "risk_score", "risk_tier", "driver_1"]
    pg_row = pg.execute(f"SELECT {', '.join(cols)} FROM public.discharge_worklist WHERE encounter_id = %s", (enc,)).fetchone()
    uc_row = uc(f"SELECT {', '.join(cols)} FROM {C}.gold.discharge_worklist WHERE encounter_id = '{enc}'")[0]
    same = all(str(a).lower() == str(b).lower() or (isinstance(a, float) and abs(a - float(b)) < 1e-9) for a, b in zip(pg_row, uc_row))
    all_ok &= same
    lines += ["\n## 2. Field-by-field spot check (top-risk 6 North worklist row)\n", "| column | UC | Lakebase |", "|---|---|---|"]
    lines += [f"| {c} | {u} | {p} |" for c, u, p in zip(cols, uc_row, pg_row)]
    lines.append(f"\nmatch: {'✅' if same else '❌'}")

    # app-owned tables + their privileges
    sp = w.apps.get("readmission-command-center").service_principal_client_id
    owner = pg.execute("SELECT nspname, pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname='app_rcc'").fetchone()
    counts = {t: pg.execute(f"SELECT count(*) FROM app_rcc.{t}").fetchone()[0] for t in ("transition_plans", "outreach_tasks", "plan_audit_log")}
    sp_can_read = pg.execute("SELECT has_table_privilege(%s, 'public.discharge_worklist', 'SELECT')", (sp,)).fetchone()[0]
    sp_can_write_public = pg.execute("SELECT has_table_privilege(%s, 'public.discharge_worklist', 'INSERT')", (sp,)).fetchone()[0]
    audit = pg.execute("SELECT action, count(*) FROM app_rcc.plan_audit_log GROUP BY 1 ORDER BY 1").fetchall()
    lines += ["\n## 3. App-owned write tables and app SP privileges\n",
              f"* schema `app_rcc` owner: `{owner[1] if owner else None}` (app service principal `{sp}`)",
              f"* row counts: {counts}", f"* audit log actions: {audit}",
              f"* SP SELECT on synced `public.discharge_worklist`: **{sp_can_read}** · SP INSERT on it: **{sp_can_write_public}** (read-only, as intended)"]
    all_ok &= bool(owner and owner[1] == sp and sp_can_read and not sp_can_write_public)

# app health (runs as the SP) + UC read-back of app writes
T = json.loads(subprocess.run(["databricks", "auth", "token", "-p", PROFILE, "-o", "json"], capture_output=True, text=True, check=True).stdout)["access_token"]
url = w.apps.get("readmission-command-center").url
health = json.loads(subprocess.run(["curl", "-s", "-H", f"Authorization: Bearer {T}", f"{url}/api/health"], capture_output=True, text=True).stdout)
back = uc("SELECT count(*), count_if(status='approved') FROM rcc_lakebase.app_rcc.transition_plans")[0]
lines += ["\n## 4. App connection and lakehouse read-back\n", f"* `GET /api/health` → `{json.dumps(health)}`",
          f"* `SELECT ... FROM rcc_lakebase.app_rcc.transition_plans` via SQL warehouse (UC) → {back[0]} plans, {back[1]} approved; PG says {counts['transition_plans']}"]
all_ok &= health.get("status") == "ok" and int(back[0]) == counts["transition_plans"]
lines.append(f"\n**Overall: {'PASS ✅' if all_ok else 'FAIL ❌'}**\n")
open(f"{ROOT}/evidence/lakebase_verification.md", "w").write("\n".join(lines))
print("\n".join(lines[-12:]))
