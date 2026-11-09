"""Print task states and errors for the latest (or given) run of the bundle's rcc_end_to_end job.
Usage: python scripts/run_status.py [run_id]"""
import json, subprocess, sys
P = ["-p", "e2-demo-field-eng"]
def cli(*a):
    return json.loads(subprocess.run(["databricks", *a, *P, "-o", "json"], capture_output=True, text=True, check=True).stdout)
s = json.loads(subprocess.run(["databricks", "bundle", "summary", "-o", "json", *P], capture_output=True, text=True, check=True).stdout)
job_id = s["resources"]["jobs"]["rcc_end_to_end"]["id"]
run_id = sys.argv[1] if len(sys.argv) > 1 else cli("jobs", "list-runs", "--job-id", job_id, "--limit", "1")[0]["run_id"]
run = cli("jobs", "get-run", str(run_id))
print("job", job_id, "run", run_id, run["state"].get("life_cycle_state"), run["state"].get("result_state"), run.get("run_page_url"))
for t in sorted(run.get("tasks", []), key=lambda t: t.get("start_time", 0)):
    st = t["state"]
    print(f"  {t['task_key']:22s} {st.get('life_cycle_state'):12s} {st.get('result_state') or ''}")
    if st.get("result_state") == "FAILED":
        try:
            out = cli("jobs", "get-run-output", str(t["run_id"]))
            print("    ERROR:", out.get("error"))
            print("    " + (out.get("error_trace") or "")[-2500:].replace("\n", "\n    "))
        except Exception as e:
            print("    (no output)", e)
