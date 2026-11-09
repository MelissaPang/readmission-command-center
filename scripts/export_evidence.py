"""Export execution evidence for a run of the rcc_end_to_end job as TEXT.

For every notebook task, the executed notebook (with its real cell outputs) is pulled with `jobs export-run`,
decoded from the Databricks HTML export, and written as:
  * notebooks/executed/<task>.ipynb : Jupyter notebook with text outputs (tables rendered as text)
  * evidence/notebook_outputs/<task>.md : the same, as readable markdown
Also writes evidence/job_run_<run_id>.json (task states) and evidence/job_run_summary.md.

Usage: python scripts/export_evidence.py [run_id]   (default: latest run)
"""
import base64
import json
import os
import re
import subprocess
import sys
import urllib.parse

P = ["-p", "e2-demo-field-eng"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def cli(*a):
    out = subprocess.run(["databricks", *a, *P, "-o", "json"], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def text_table(cols, rows, limit=50):
    rows = [["" if v is None else str(v) for v in r] for r in rows[:limit]]
    widths = [min(60, max([len(c)] + [len(r[i]) for r in rows])) for i, c in enumerate(cols)]
    fmt = lambda vals: "| " + " | ".join(v[:60].ljust(widths[i]) for i, v in enumerate(vals)) + " |"
    lines = [fmt(cols), "|" + "|".join("-" * (w + 2) for w in widths) + "|"] + [fmt(r) for r in rows]
    return "\n".join(lines)


def render_result(r):
    """Return list of text blocks for a command result."""
    if not r:
        return []
    t = r.get("type")
    if t == "listResults":
        out = []
        for item in r.get("data", []):
            out += render_result(item)
        return out
    if t in ("ansi", "text"):
        d = r.get("data")
        return [ANSI.sub("", d)] if isinstance(d, str) and d.strip() else []
    if t == "table":
        cols = [c.get("name") for c in r.get("schema", [])]
        rows = r.get("data", [])
        trunc = f"\n({len(rows)} rows shown{' (truncated)' if r.get('truncated') else ''})"
        return [text_table(cols, rows) + trunc]
    if t == "html":
        d = re.sub(r"<[^>]+>", " ", r.get("data", ""))
        d = re.sub(r"\s+", " ", d).strip()
        return [d[:4000]] if d else []
    if t == "error":
        return ["ERROR: " + ANSI.sub("", str(r.get("summary") or r.get("data")))[:3000]]
    d = r.get("data")
    return [ANSI.sub("", d)] if isinstance(d, str) and d.strip() else []


def notebook_from_export(task_run_id):
    d = cli("jobs", "export-run", str(task_run_id), "--views-to-export", "CODE")
    html = d["views"][0]["content"]
    m = re.search(r"__DATABRICKS_NOTEBOOK_MODEL = '([^']+)'", html)
    return json.loads(urllib.parse.unquote(base64.b64decode(m.group(1)).decode("utf-8")))


def main():
    s = json.loads(subprocess.run(["databricks", "bundle", "summary", "-o", "json", *P], capture_output=True, text=True,
                                  check=True, cwd=ROOT).stdout)
    job_id = s["resources"]["jobs"]["rcc_end_to_end"]["id"]
    run_id = sys.argv[1] if len(sys.argv) > 1 else cli("jobs", "list-runs", "--job-id", str(job_id), "--limit", "1")[0]["run_id"]
    run = cli("jobs", "get-run", str(run_id))
    os.makedirs(f"{ROOT}/notebooks/executed", exist_ok=True)
    os.makedirs(f"{ROOT}/evidence/notebook_outputs", exist_ok=True)

    tasks = sorted(run.get("tasks", []), key=lambda t: t.get("start_time", 0))
    slim = {"job_id": job_id, "run_id": run["run_id"], "run_page_url": run.get("run_page_url"),
            "state": run["state"], "start_time": run.get("start_time"), "end_time": run.get("end_time"),
            "tasks": [{"task_key": t["task_key"], "run_id": t["run_id"], "state": t["state"],
                       "start_time": t.get("start_time"), "end_time": t.get("end_time"),
                       "duration_s": round((t.get("end_time", 0) - t.get("start_time", 0)) / 1000, 1),
                       "notebook": (t.get("notebook_task") or {}).get("notebook_path"),
                       "pipeline_id": (t.get("pipeline_task") or {}).get("pipeline_id")} for t in tasks]}
    json.dump(slim, open(f"{ROOT}/evidence/job_run_{run['run_id']}.json", "w"), indent=2)

    import datetime as dt
    ts = lambda ms: dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") if ms else ""
    md = [f"# Job run evidence: rcc_end_to_end\n", f"* job_id: `{job_id}`", f"* run_id: `{run['run_id']}`",
          f"* result: **{run['state'].get('result_state')}**", f"* started: {ts(run.get('start_time'))}", f"* ended: {ts(run.get('end_time'))}",
          f"* run page: {run.get('run_page_url')}\n", "| task | result | duration (s) | started |", "|---|---|---|---|"]
    md += [f"| {t['task_key']} | {t['state'].get('result_state')} | {t['duration_s']} | {ts(t['start_time'])} |" for t in slim["tasks"]]
    open(f"{ROOT}/evidence/job_run_summary.md", "w").write("\n".join(md) + "\n")

    for t in tasks:
        if not t.get("notebook_task") or t["state"].get("result_state") not in ("SUCCESS", "FAILED"):
            continue
        nb = notebook_from_export(t["run_id"])
        cells, mdl = [], [f"# Executed notebook: {t['task_key']}\n", f"job run `{run['run_id']}` · task run `{t['run_id']}` · "
                                                                      f"result **{t['state'].get('result_state')}** · {ts(t.get('start_time'))}\n"]
        for c in sorted(nb["commands"], key=lambda c: c.get("position", 0)):
            src = c.get("command", "")
            if src.lstrip().startswith("%md"):
                body = re.sub(r"^\s*%md\s?", "", src)
                cells.append({"cell_type": "markdown", "metadata": {}, "source": body.splitlines(True)})
                mdl.append(body + "\n")
                continue
            outs = render_result(c.get("results"))
            if c.get("error"):
                outs.append("ERROR: " + ANSI.sub("", str(c.get("errorSummary") or c.get("error")))[:3000])
            cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "source": src.splitlines(True),
                          "outputs": [{"output_type": "stream", "name": "stdout", "text": o if o.endswith("\n") else o + "\n"} for o in outs]})
            mdl.append("```python\n" + src.strip() + "\n```\n")
            if outs:
                mdl.append("Output:\n\n```text\n" + "\n".join(o.rstrip() for o in outs) + "\n```\n")
        ipynb = {"nbformat": 4, "nbformat_minor": 5, "cells": cells,
                 "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"},
                              "databricks_job_run": {"job_id": job_id, "run_id": run["run_id"], "task_run_id": t["run_id"],
                                                     "task_key": t["task_key"], "result_state": t["state"].get("result_state")}}}
        name = os.path.basename(t["notebook_task"]["notebook_path"]).replace(".py", "")
        json.dump(ipynb, open(f"{ROOT}/notebooks/executed/{name}.ipynb", "w"), indent=1)
        open(f"{ROOT}/evidence/notebook_outputs/{name}.md", "w").write("\n".join(mdl))
        print(f"exported {t['task_key']:22s} -> notebooks/executed/{name}.ipynb ({sum(1 for c in cells if c.get('outputs'))} cells with output)")
    print("wrote evidence/job_run_summary.md")


if __name__ == "__main__":
    main()
