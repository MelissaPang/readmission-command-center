# Executed notebook: lakebase_sync

job run `206873801708733` · task run `1123241612241153` · result **SUCCESS** · 2026-11-09 17:55:27 UTC

# 07 · Lakebase: operational serving for the app

* Registers the Lakebase Postgres database `rcc` (instance `rcc-lakebase`) in Unity Catalog as the catalog `rcc_lakebase`.
* Publishes app-serving gold tables to Postgres as **synced tables** (UC → Lakebase, snapshot mode), so the app
  reads low-latency Postgres instead of querying the warehouse.
* The app owns its write tables (`app_rcc.transition_plans`, `app_rcc.outreach_tasks`, `app_rcc.plan_audit_log`); it creates them on startup.
  Because the database is registered in UC, approvals written by the app are queryable from the lakehouse (`rcc_lakebase.app_rcc.*`).
* Verifies the result with direct Postgres queries (psycopg + OAuth database credential).

```python
%pip install -q "databricks-sdk>=0.60.0" "psycopg[binary]>=3.2"
%restart_python
```

Output:

```text
Note: you may need to restart the kernel using %restart_python or dbutils.library.restartPython() to use updated packages.
```

```python
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
```

Output:

```text
rcc-lakebase DatabaseInstanceState.AVAILABLE ep-ancient-haze-d1nu8mwg.database.us-west-2.cloud.databricks.com
```

```python
try:
    w.database.get_database_catalog(DB_CATALOG)
    print("database catalog exists:", DB_CATALOG)
except Exception:
    w.database.create_database_catalog(DatabaseCatalog(name=DB_CATALOG, database_instance_name=instance,
                                                       database_name=dbname, create_database_if_not_exists=True))
    print("created database catalog", DB_CATALOG, "->", instance, "/", dbname)
```

Output:

```text
database catalog exists: rcc_lakebase
```

### App-serving Delta tables (one snapshot per run) and their primary keys

```python
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
```

Output:

```text
discharge_worklist     <- cedarbrook_rcc.gold.discharge_worklist                  rows=   705 pk=['encounter_id']
hrrp_whatif            <- cedarbrook_rcc.gold.hrrp_whatif                         rows=    39 pk=['scope', 'fu7_target_pct']
unit_weekly            <- cedarbrook_rcc.gold.app_unit_weekly                     rows= 2,825 pk=['unit_id', 'condition', 'discharge_week']
unit_period_summary    <- cedarbrook_rcc.gold.app_unit_period_summary             rows=    56 pk=['unit_id', 'condition']
followup_gap           <- cedarbrook_rcc.gold.app_followup_gap                    rows=   160 pk=['unit_id', 'condition', 'discharge_day_type', 'period']
risk_factors           <- cedarbrook_rcc.gold.app_risk_factors                    rows=    56 pk=['condition', 'factor', 'value']
hrrp_condition         <- cedarbrook_rcc.gold.app_hrrp_condition                  rows=    16 pk=['hospital_id', 'hrrp_condition']
hrrp_hospital          <- cedarbrook_rcc.gold.app_hrrp_hospital                   rows=     3 pk=['hospital_id']
staffing_events        <- cedarbrook_rcc.gold.app_staffing_events                 rows=     4 pk=['event_id']
```

### Create or refresh synced tables

```python
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
```

Output:

```text
refresh rcc_lakebase.public.discharge_worklist pipeline bd84019f-bded-4026-9fef-561a69deec85
refresh rcc_lakebase.public.hrrp_whatif pipeline 1958954b-c389-40d2-9830-1ff308139447
refresh rcc_lakebase.public.unit_weekly pipeline 4ad3f838-d595-4497-a18d-45bb1d2da568
refresh rcc_lakebase.public.unit_period_summary pipeline 354741ce-a588-4a58-aeec-284f980f54e5
refresh rcc_lakebase.public.followup_gap pipeline a7cd9c03-550c-4b72-bc87-a9255f151111
refresh rcc_lakebase.public.risk_factors pipeline 5f0629cc-bf44-4d2b-a0c6-88d70575cbcf
refresh rcc_lakebase.public.hrrp_condition pipeline 6a7b557b-70bc-498e-9263-0676d62b0ac1
refresh rcc_lakebase.public.hrrp_hospital pipeline 55feabae-05a3-4bc1-9dee-de57d1345147
refresh rcc_lakebase.public.staffing_events pipeline d16e19e0-4033-4422-b9ed-bdd6f8422c57
```

```python
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
```

Output:

```text
hrrp_whatif            synced  state=SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE
discharge_worklist     synced  state=SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE
hrrp_hospital          synced  state=SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE
risk_factors           synced  state=SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE
unit_period_summary    synced  state=SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE
unit_weekly            synced  state=SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE
staffing_events        synced  state=SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE
followup_gap           synced  state=SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE
hrrp_condition         synced  state=SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE
```

### Verify in Postgres (direct connection, OAuth credential)

```python
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
```

Output:

```text
PostgreSQL 16.15 (23d2a0d) on aarch64-unknown-linux-gnu, compiled by gcc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0, 64-bit
public.discharge_worklist        705 rows
public.hrrp_whatif                39 rows
public.unit_weekly             2,825 rows
public.unit_period_summary        56 rows
public.followup_gap              160 rows
public.risk_factors               56 rows
public.hrrp_condition             16 rows
public.hrrp_hospital               3 rows
public.staffing_events             4 rows

Top 6 North worklist rows from Postgres:
   ('6 North Telemetry', 'HF', 'High', Decimal('0.546'), False, False, 'Book 7-day follow-up (HF Bridge Clinic / PCP); Pharmacist me')
   ('6 North Telemetry', 'OTHER', 'High', Decimal('0.446'), False, True, 'Book 7-day follow-up (HF Bridge Clinic / PCP); Caregiver che')
   ('6 North Telemetry', 'OTHER', 'High', Decimal('0.388'), False, True, 'Book 7-day follow-up (HF Bridge Clinic / PCP); Caregiver che')
   ('6 North Telemetry', 'HF', 'High', Decimal('0.343'), False, True, 'Book 7-day follow-up (HF Bridge Clinic / PCP); Caregiver che')
   ('6 North Telemetry', 'HF', 'High', Decimal('0.333'), True, False, 'Pharmacist med-reconciliation call within 48h')

What-if rows from Postgres:
   ('6N weekend HF', 60, 1.28, 1.1802, 0.0)
   ('6N weekend HF', 80, 6.52, 1.1403, 238438.15)
   ('6N weekend HF', 100, 11.76, 1.1003, 478163.54)
```
