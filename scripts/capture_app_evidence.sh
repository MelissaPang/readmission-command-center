#!/usr/bin/env bash
# Exercise the deployed Databricks App end to end and save every API response as text evidence.
# Usage: scripts/capture_app_evidence.sh
set -euo pipefail
PROFILE=e2-demo-field-eng
APP=readmission-command-center
OUT=evidence/app_api_responses
mkdir -p "$OUT"
URL=$(databricks apps get "$APP" -p "$PROFILE" -o json | python3 -c "import sys,json;print(json.load(sys.stdin)['url'])")
TOKEN=$(databricks auth token -p "$PROFILE" -o json | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
H=(-H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")
pretty() { python3 -m json.tool --no-ensure-ascii; }

databricks apps get "$APP" -p "$PROFILE" -o json | python3 -c "
import sys,json; d=json.load(sys.stdin)
print(json.dumps({k: d.get(k) for k in ['name','url','app_status','compute_status','service_principal_client_id','active_deployment','resources']}, indent=2))" > "$OUT/00_app_status.json"
echo "app: $URL"

get() { echo "GET $2"; curl -sf "${H[@]}" "$URL$2" | pretty > "$OUT/$1.json"; }
get 01_health                /api/health
get 02_units_summary_hf      "/api/units/summary?condition=HF"
get 03_units_summary_all     "/api/units/summary?condition=ALL"
get 04_unit_weekly_6n_hf     "/api/units/CUMC-6N/weekly?condition=HF"
get 05_followup_gap_6n       "/api/followup-gap?unit_id=CUMC-6N&condition=HF"
get 06_risk_factors_hf       "/api/risk-factors?condition=HF"
get 07_hrrp                  /api/hrrp
get 08_whatif_6n_weekend     "/api/hrrp/whatif?scope=6N%20weekend%20HF"
get 09_worklist_6n_high_nofu "/api/worklist?unit_id=CUMC-6N&risk_tier=High&no_followup=true&limit=10"

# pick the highest-risk 6 North HF weekend discharge without a follow-up and no plan yet
ENC=$(python3 -c "
import json; rows=json.load(open('$OUT/09_worklist_6n_high_nofu.json'))
c=[r for r in rows if r['condition']=='HF' and r['weekend_discharge'] and not r['plan_status']] or [r for r in rows if not r['plan_status']] or rows
print(c[0]['encounter_id'])")
echo "patient encounter: $ENC"
get 10_patient_before "/api/patients/$ENC"

echo "POST draft-plan (Foundation Model API)"
curl -sf "${H[@]}" -X POST "$URL/api/patients/$ENC/draft-plan" | pretty > "$OUT/11_draft_plan.json"
PLAN=$(python3 -c "import json;print(json.load(open('$OUT/11_draft_plan.json'))['plan_id'])")
echo "POST approve plan $PLAN with an RN edit (closed loop: edit metrics -> audit log -> weak label)"
EDITED=$(python3 -c "
import json; d=json.load(open('$OUT/11_draft_plan.json'))['draft_text']
edit = 'Within 48 hours**\\n- RN edit: call patient (and caregiver if any) today to book the HF Bridge Clinic slot before end of shift'
d = d.replace('Within 48 hours**', edit, 1) if 'Within 48 hours**' in d else d + '\\n- RN edit: call patient today to book follow-up'
print(json.dumps({'final_text': d}))")
curl -sf "${H[@]}" -X POST "$URL/api/plans/$PLAN/approve" -d "$EDITED" | pretty > "$OUT/12_approve_plan.json"
get 13_patient_after "/api/patients/$ENC"
get 14_outreach_open "/api/outreach-tasks?status=open"
TASK=$(python3 -c "import json;print(json.load(open('$OUT/12_approve_plan.json'))['tasks_created'][0]['task_id'])")
curl -sf "${H[@]}" -X POST "$URL/api/outreach-tasks/$TASK/complete" | pretty > "$OUT/15_task_complete.json"

echo "POST genie ask"
curl -sf "${H[@]}" -X POST "$URL/api/genie/ask" \
  -d '{"question":"Compare 7-day follow-up booking on 6 North for weekend vs weekday HF discharges since 2026-06-19"}' | pretty > "$OUT/16_genie_ask.json"

databricks apps logs "$APP" -p "$PROFILE" --tail-lines 80 > evidence/app_logs.txt 2>&1 || true
echo "saved to $OUT"
