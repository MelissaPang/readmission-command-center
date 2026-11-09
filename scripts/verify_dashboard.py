"""Verify the deployed AI/BI dashboard: run every dataset query from the *deployed* definition on the SQL warehouse,
and check every widget's fields resolve to columns of its dataset. Writes evidence/dashboard_verification.md.

Usage: python scripts/verify_dashboard.py
"""
import datetime as dt
import json
import os
import re
import subprocess

P = ["-p", "e2-demo-field-eng"]
WH = "12444b712298f9ac"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cli(*a):
    return json.loads(subprocess.run(["databricks", *a, *P, "-o", "json"], capture_output=True, text=True, check=True, cwd=ROOT).stdout)


def sql(q):
    body = {"warehouse_id": WH, "wait_timeout": "50s", "statement": q}
    r = json.loads(subprocess.run(["databricks", "api", "post", "/api/2.0/sql/statements", *P, "--json", json.dumps(body)],
                                  capture_output=True, text=True, check=True).stdout)
    if r["status"]["state"] != "SUCCEEDED":
        return None, [], r["status"].get("error", {}).get("message")
    return [c["name"] for c in r["manifest"]["schema"]["columns"]], (r.get("result") or {}).get("data_array") or [], None


did = json.loads(subprocess.run(["databricks", "bundle", "summary", "-o", "json", *P], capture_output=True, text=True, check=True,
                                cwd=ROOT).stdout)["resources"]["dashboards"]["readmissions_hrrp_executive"]["id"]
dash = cli("lakeview", "get", did)
pub = cli("lakeview", "get-published", did)
spec = json.loads(dash["serialized_dashboard"])
md = [f"# Dashboard verification ({dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M UTC})\n",
      f"* dashboard `{dash['display_name']}` id `{did}`, lifecycle **{dash.get('lifecycle_state')}**, published revision {pub.get('revision_create_time')}, warehouse `{dash['warehouse_id']}`",
      f"* {len(spec['datasets'])} datasets, {sum(len(p['layout']) for p in spec['pages'])} widgets (definition read back from the workspace, not from the repo)\n"]
cols_by_ds, ok_all = {}, True
md.append("## Dataset queries (executed on the SQL warehouse)\n")
for d in spec["datasets"]:
    q = "".join(d["queryLines"])
    cols, rows, err = sql(q)
    ok_all &= err is None and len(rows) > 0
    cols_by_ds[d["name"]] = set(cols or [])
    md.append(f"### `{d['name']}`: {'✅' if err is None and rows else '❌'} {len(rows)} rows\n\n```sql\n{q}\n```\n")
    if err:
        md.append(f"ERROR: {err}\n")
    else:
        md.append("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols))
        md += ["| " + " | ".join("" if v is None else str(v) for v in r) + " |" for r in rows[:8]]
        md.append(f"\n({len(rows)} rows{', first 8 shown' if len(rows) > 8 else ''})\n")

md.append("## Widget → dataset field check\n\n| widget | type | title | dataset | fields | resolved |\n|---|---|---|---|---|---|")
for page in spec["pages"]:
    for item in page["layout"]:
        wdg = item["widget"]
        if "queries" not in wdg:
            md.append(f"| {wdg['name']} | text | (header) | | | ✅ |")
            continue
        q = wdg["queries"][0]["query"]
        refs = set()
        for f in q["fields"]:
            refs |= set(re.findall(r"`([^`]+)`", f["expression"]))
        ok = refs <= cols_by_ds.get(q["datasetName"], set())
        ok_all &= ok
        title = wdg["spec"].get("frame", {}).get("title", "")
        md.append(f"| {wdg['name']} | {wdg['spec']['widgetType']} | {title} | {q['datasetName']} | {', '.join(sorted(refs))} | {'✅' if ok else '❌'} |")
md.append(f"\n**Overall: {'PASS ✅' if ok_all else 'FAIL ❌'}**\n")
open(f"{ROOT}/evidence/dashboard_verification.md", "w").write("\n".join(md))
print("\n".join(md[-20:]))
