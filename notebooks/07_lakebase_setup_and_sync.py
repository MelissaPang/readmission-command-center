# Databricks notebook source
# MAGIC %md
# MAGIC # 07 · Lakebase: operational serving for the app
# MAGIC
# MAGIC * Registers the Lakebase Postgres database `rcc` (instance `rcc-lakebase`) in Unity Catalog as the catalog `rcc_lakebase`.
# MAGIC * Publishes app-serving gold tables to Postgres as **synced tables** (UC → Lakebase, snapshot mode), so the app
# MAGIC   reads low-latency Postgres instead of querying the warehouse.
# MAGIC * The app owns its write tables (`app_rcc.transition_plans`, `app_rcc.outreach_tasks`, `app_rcc.plan_audit_log`); it creates them on startup.
# MAGIC   Because the database is registered in UC, approvals written by the app are queryable from the lakehouse (`rcc_lakebase.app_rcc.*`).
# MAGIC * Verifies the result with direct Postgres queries (psycopg + OAuth database credential).

# COMMAND ----------

# MAGIC %pip install -q "databricks-sdk>=0.60.0" "psycopg[binary]>=3.2"
# MAGIC %restart_python

# COMMAND ----------

dbutils.widgets.text("catalog", "cedarbrook_rcc")
dbutils.widgets.text("lakebase_instance", "rcc-lakebase")
dbutils.widgets.text("lakebase_database", "rcc")
catalog = dbutils.widgets.get("catalog")
instance = dbutils.widgets.get("lakebase_instance")
dbname = dbutils.widgets.get("lakebase_database")
DB_CATALOG = "rcc_lakebase"

import time, uuid
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.database import (DatabaseCatalog, SyncedDatabaseTable, SyncedTableSpec,
                                             SyncedTableSchedulingPolicy)

w = WorkspaceClient()
inst = w.database.get_database_instance(instance)
print(instance, inst.state, inst.read_write_dns)

# COMMAND ----------

try:
    w.database.get_database_catalog(DB_CATALOG)
    print("database catalog exists:", DB_CATALOG)
except Exception:
    w.database.create_database_catalog(DatabaseCatalog(name=DB_CATALOG, database_instance_name=instance,
                                                       database_name=dbname, create_database_if_not_exists=True))
    print("created database catalog", DB_CATALOG, "->", instance, "/", dbname)

# COMMAND ----------

# MAGIC %md ### App-serving Delta tables (one snapshot per run) and their primary keys

# COMMAND ----------

SERVE = {
    # lakebase table name: (source SQL or table, primary key)
    "discharge_worklist": (f"{catalog}.gold.discharge_worklist", ["encounter_id"]),
    "hrrp_whatif": (f"{catalog}.gold.hrrp_whatif", ["scope", "fu7_target_pct"]),
    "unit_weekly": (f"SELECT * FROM {catalog}.gold.unit_weekly_readmissions", ["unit_id", "condition", "discharge_week"]),
    "unit_period_summary": (f"SELECT * FROM {catalog}.gold.unit_period_summary", ["unit_id", "condition"]),
    "followup_gap": (f"SELECT * FROM {catalog}.gold.followup_gap", ["unit_id", "condition", "discharge_day_type", "period"]),
    "risk_factors": (f"SELECT * FROM {catalog}.gold.readmission_risk_factors", ["condition", "factor", "value"]),
    "hrrp_condition": (f"SELECT * FROM {catalog}.gold.hrrp_condition_err", ["hospital_id", "hrrp_condition"]),
    "hrrp_hospital": (f"SELECT * FROM {catalog}.gold.hrrp_hospital_penalty", ["hospital_id"]),
    "staffing_events": (f"SELECT * FROM {catalog}.silver.staffing_events", ["event_id"]),
}
sources = {}
for name, (src, pk) in SERVE.items():
    if src.upper().startswith("SELECT"):
        tbl = f"{catalog}.gold.app_{name}"
        spark.sql(f"CREATE OR REPLACE TABLE {tbl} AS {src}")
    else:
        tbl = src
    dupes = spark.sql(f"SELECT count(*) - count(DISTINCT {', '.join(pk)}) AS d FROM {tbl}").first().d
    assert dupes == 0, f"primary key not unique for {tbl}"
    sources[name] = (tbl, pk)
    print(f"{name:22s} <- {tbl:55s} rows={spark.table(tbl).count():>6,d} pk={pk}")

# COMMAND ----------

# MAGIC %md ### Create or refresh synced tables

# COMMAND ----------

updates = {}
for name, (tbl, pk) in sources.items():
    full = f"{DB_CATALOG}.public.{name}"
    try:
        st = w.database.get_synced_database_table(full)
        pid = st.data_synchronization_status.pipeline_id
        upd = w.pipelines.start_update(pid, full_refresh=True)
        updates[name] = (pid, upd.update_id)
        print("refresh", full, "pipeline", pid)
    except Exception as e:
        if "does not exist" not in str(e) and "NOT_FOUND" not in str(e) and "not found" not in str(e).lower():
            raise
        st = w.database.create_synced_database_table(SyncedDatabaseTable(
            name=full, spec=SyncedTableSpec(source_table_full_name=tbl, primary_key_columns=pk,
                                            scheduling_policy=SyncedTableSchedulingPolicy.SNAPSHOT)))
        print("created synced table", full)
        updates[name] = (None, None)

# COMMAND ----------

deadline = time.time() + 1800
pending = set(updates)
while pending and time.time() < deadline:
    for name in list(pending):
        st = w.database.get_synced_database_table(f"{DB_CATALOG}.public.{name}")
        s = st.data_synchronization_status
        state = str(s.detailed_state) if s else "UNKNOWN"
        pid, uid = updates[name]
        if pid is None and s and s.pipeline_id:
            updates[name] = (s.pipeline_id, None)
        done = "ONLINE" in state
        if uid:
            u = w.pipelines.get_update(pid, uid).update
            done = str(u.state).endswith("COMPLETED")
            if str(u.state).endswith(("FAILED", "CANCELED")):
                raise RuntimeError(f"sync failed for {name}: {u.state}")
        if done:
            pending.discard(name)
            print(f"{name:22s} synced  state={state}")
    if pending:
        time.sleep(20)
assert not pending, f"sync timed out for {pending}"

# COMMAND ----------

# MAGIC %md ### Verify in Postgres (direct connection, OAuth credential)

# COMMAND ----------

import psycopg

cred = w.database.generate_database_credential(request_id=str(uuid.uuid4()), instance_names=[instance])
user = w.current_user.me().user_name
with psycopg.connect(host=inst.read_write_dns, dbname=dbname, user=user, password=cred.token, sslmode="require") as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT version()")
        print(cur.fetchone()[0])
        for name in sources:
            cur.execute(f'SELECT count(*) FROM public."{name}"')
            print(f"public.{name:22s} {cur.fetchone()[0]:>6,d} rows")
        cur.execute("""SELECT unit_name, condition, risk_tier, round(risk_score::numeric, 3), fu7_booked, ai_lives_alone, left(recommended_actions, 60)
                       FROM public.discharge_worklist WHERE unit_id = 'CUMC-6N' ORDER BY risk_score DESC LIMIT 5""")
        print("\nTop 6 North worklist rows from Postgres:")
        for r in cur.fetchall():
            print("  ", r)
        cur.execute("""SELECT scope, fu7_target_pct, readmissions_avoided, hf_err_scenario, penalty_saved
                       FROM public.hrrp_whatif WHERE scope = '6N weekend HF' AND fu7_target_pct IN (60, 80, 100) ORDER BY 2""")
        print("\nWhat-if rows from Postgres:")
        for r in cur.fetchall():
            print("  ", r)
