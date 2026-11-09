"""Grant the Databricks App's service principal least-privilege access (run once after the app is created).

Lakebase : CAN_USE on the instance, a Postgres role for the SP, SELECT on synced public.* tables, CREATE on database rcc
           (the app creates and owns schema app_rcc for its write tables).
UC       : USE CATALOG/SCHEMA + SELECT on gold (used by Genie, which runs as the app SP), SELECT on silver.staffing_events only
           (no access to raw note text), and an entitlement row role='analyst' (PHI masked by gold.mask_phi, AI evidence quotes
           masked by gold.mask_clinical_text; row filter scope '*').

Usage: uv run --with databricks-sdk --with "psycopg[binary]" python scripts/grant_app_access.py
"""
import json
import subprocess
import uuid

import psycopg
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.database import DatabaseInstanceRole, DatabaseInstanceRoleIdentityType

PROFILE, APP, INSTANCE, DB, CATALOG, WH = "e2-demo-field-eng", "readmission-command-center", "rcc-lakebase", "rcc", "cedarbrook_rcc", "12444b712298f9ac"
w = WorkspaceClient(profile=PROFILE)
sp = w.apps.get(APP).service_principal_client_id
print("app service principal:", sp)

# 1. instance permission
w.api_client.do("PATCH", f"/api/2.0/permissions/database-instances/{INSTANCE}",
                body={"access_control_list": [{"service_principal_name": sp, "permission_level": "CAN_USE"}]})
print("granted CAN_USE on instance", INSTANCE)

# 2. Postgres role for the SP
existing = {r.name for r in w.database.list_database_instance_roles(INSTANCE)}
if sp not in existing:
    w.database.create_database_instance_role(INSTANCE, DatabaseInstanceRole(
        name=sp, identity_type=DatabaseInstanceRoleIdentityType.SERVICE_PRINCIPAL))
    print("created Postgres role", sp)
else:
    print("Postgres role exists", sp)

# 3. Postgres grants
inst = w.database.get_database_instance(INSTANCE)
cred = w.database.generate_database_credential(request_id=str(uuid.uuid4()), instance_names=[INSTANCE])
with psycopg.connect(host=inst.read_write_dns, dbname=DB, user=w.current_user.me().user_name, password=cred.token,
                     sslmode="require", autocommit=True) as c:
    for stmt in [f'GRANT CONNECT, CREATE ON DATABASE {DB} TO "{sp}"',
                 f'GRANT USAGE ON SCHEMA public TO "{sp}"',
                 f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{sp}"',
                 f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO "{sp}"']:
        c.execute(stmt)
        print("pg:", stmt)
    rows = c.execute("SELECT table_name, privilege_type FROM information_schema.role_table_grants WHERE grantee = %s ORDER BY 1", (sp,)).fetchall()
    print("pg grants for SP:", rows)


# 4. Unity Catalog grants + entitlement
def sql(stmt):
    body = {"warehouse_id": WH, "wait_timeout": "50s", "statement": stmt}
    r = json.loads(subprocess.run(["databricks", "api", "post", "/api/2.0/sql/statements", "-p", PROFILE, "--json", json.dumps(body)],
                                  capture_output=True, text=True).stdout)
    print("uc:", r["status"]["state"], stmt[:110])
    return r


for stmt in [f"GRANT USE CATALOG ON CATALOG {CATALOG} TO `{sp}`",
             f"GRANT USE SCHEMA, SELECT, EXECUTE ON SCHEMA {CATALOG}.gold TO `{sp}`",
             # least privilege: no schema-wide silver access (raw note text, verbatim evidence); only the table Genie needs
             f"REVOKE SELECT ON SCHEMA {CATALOG}.silver FROM `{sp}`",
             f"GRANT USE SCHEMA ON SCHEMA {CATALOG}.silver TO `{sp}`",
             f"GRANT SELECT ON TABLE {CATALOG}.silver.staffing_events TO `{sp}`",
             f"MERGE INTO {CATALOG}.gold.rcc_user_entitlements t USING (SELECT '{sp}' AS principal, 'analyst' AS role, '*' AS hospital_scope) s "
             f"ON t.principal = s.principal WHEN NOT MATCHED THEN INSERT *"]:
    sql(stmt)
