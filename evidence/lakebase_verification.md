# Lakebase verification (2026-11-09 18:10 UTC)

* instance `rcc-lakebase`: state **AVAILABLE**, capacity CU_1, PG PG_VERSION_16, host `ep-ancient-haze-d1nu8mwg.database.us-west-2.cloud.databricks.com`

## 1. Synced tables vs Unity Catalog source

| Lakebase table | sync state | UC rows | PG rows | key hash UC | key hash PG | sum UC | sum PG | match |
|---|---|---|---|---|---|---|---|---|
| public.discharge_worklist | SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE | 705 | 705 | b792784f6fbb6465 | b792784f6fbb6465 | 92.65 | 92.65 | ✅ |
| public.hrrp_whatif | SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE | 39 | 39 | 35d533a83a1052e0 | 35d533a83a1052e0 | 12195310.2 | 12195310.2 | ✅ |
| public.unit_weekly | SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE | 2825 | 2825 | ff581ed06c206a46 | ff581ed06c206a46 | 1903.0 | 1903.0 | ✅ |
| public.unit_period_summary | SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE | 56 | 56 | fef0a67c88b46231 | fef0a67c88b46231 | 1024.0 | 1024.0 | ✅ |
| public.followup_gap | SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE | 160 | 160 | f7821d9c90512091 | f7821d9c90512091 | 8765.0 | 8765.0 | ✅ |
| public.risk_factors | SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE | 56 | 56 | 9ac6de8c8e30d1c9 | 9ac6de8c8e30d1c9 | 5324.0 | 5324.0 | ✅ |
| public.hrrp_condition | SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE | 16 | 16 | 52b09e90e83a9af3 | 52b09e90e83a9af3 | 2134999.46 | 2134999.46 | ✅ |
| public.hrrp_hospital | SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE | 3 | 3 | 06dbaa8c3804e648 | 06dbaa8c3804e648 | 2075003.97 | 2075003.97 | ✅ |
| public.staffing_events | SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE | 4 | 4 | 282c8a226ad4c258 | 282c8a226ad4c258 |  |  | ✅ |

## 2. Field-by-field spot check (top-risk 6 North worklist row)

| column | UC | Lakebase |
|---|---|---|
| encounter_id | E1014381 | E1014381 |
| last_name | Perez | Perez |
| mrn | MRN32739700 | MRN32739700 |
| unit_id | CUMC-6N | CUMC-6N |
| condition | HF | HF |
| fu7_booked | false | False |
| ai_lives_alone | false | False |
| risk_score | 0.5461 | 0.5461 |
| risk_tier | High | High |
| driver_1 | No 7-day follow-up booked | No 7-day follow-up booked |

match: ✅

## 3. App-owned write tables and app SP privileges

* schema `app_rcc` owner: `dd97e436-f2e2-4d19-9910-5e845a1a42f7` (app service principal `dd97e436-f2e2-4d19-9910-5e845a1a42f7`)
* row counts: {'transition_plans': 2, 'outreach_tasks': 4, 'plan_audit_log': 6}
* audit log actions: [('draft_generated', 2), ('plan_approved', 2), ('task_completed', 2)]
* SP SELECT on synced `public.discharge_worklist`: **True** · SP INSERT on it: **False** (read-only, as intended)

## 4. App connection and lakehouse read-back

* `GET /api/health` → `{"status": "ok", "lakebase": "ok", "worklist_rows": 705, "assistant_endpoint": "databricks-claude-sonnet-4-6", "genie_space_id": "01f1dc641b0f1595b5867a02cfe2abd8", "pg_user": "dd97e436-f2e2-4d19-9910-5e845a1a42f7"}`
* `SELECT ... FROM rcc_lakebase.app_rcc.transition_plans` via SQL warehouse (UC) → 2 plans, 2 approved; PG says 2

**Overall: PASS ✅**
