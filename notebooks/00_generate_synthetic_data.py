# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Generate synthetic EHR extracts (raw data)
# MAGIC
# MAGIC Cedarbrook Health · Readmission Command Center
# MAGIC
# MAGIC This notebook generates a **deterministic (seed=42) synthetic EHR extract** and lands it in the Unity Catalog volume
# MAGIC `/Volumes/<catalog>/raw/landing/`, one folder per source feed. Lakeflow (Auto Loader) ingests it from there.
# MAGIC
# MAGIC | Feed | Format | Notes |
# MAGIC |---|---|---|
# MAGIC | encounters | JSON lines, one file per discharge month | ADT inpatient encounters, incl. 45 duplicates + 6 bad timestamps on purpose |
# MAGIC | discharge_notes | JSON lines, one file per month | free-text discharge summaries |
# MAGIC | patients | CSV | demographics (PHI) |
# MAGIC | followup_appointments | CSV | scheduling extract with booking timestamps |
# MAGIC | hospitals, units, icd10_hrrp_map, staffing_events, cms_hrrp_reference | CSV | reference data |
# MAGIC
# MAGIC The generator plants the customer story into the data (see `src/rcc_datagen.py`). Ground truth for the
# MAGIC free-text flags goes to a separate volume and is only used to score the AI extraction.

# COMMAND ----------

dbutils.widgets.text("catalog", "cedarbrook_rcc")
catalog = dbutils.widgets.get("catalog")

import os, sys, json
sys.path.append(os.path.abspath("../src"))
import rcc_datagen as gen

LANDING = f"/Volumes/{catalog}/raw/landing"
TRUTH = f"/Volumes/{catalog}/raw/ground_truth"
print("landing:", LANDING)

# COMMAND ----------

g = gen.generate(seed=gen.SEED)
print(json.dumps({k: v for k, v in g.calibration.items() if not isinstance(v, dict)}, indent=2))

# COMMAND ----------

import pandas as pd

# Clean previous landing files so a re-run is a true full refresh
for feed in g.tables:
    try:
        dbutils.fs.rm(f"{LANDING}/{feed}", True)
    except Exception:
        pass

written = []
for feed, df in g.tables.items():
    path = f"{LANDING}/{feed}"
    os.makedirs(path, exist_ok=True)
    if feed in ("encounters", "discharge_notes"):
        ts_col = "discharge_ts" if feed == "encounters" else "note_ts"
        month = pd.to_datetime(df[ts_col]).dt.strftime("%Y-%m")
        for m, part in df.groupby(month):
            fn = f"{path}/{feed}_{m}.json"
            part.to_json(fn, orient="records", lines=True, date_format="iso")
            written.append((feed, fn.split("/")[-1], len(part)))
    else:
        fn = f"{path}/{feed}.csv"
        df.to_csv(fn, index=False)
        written.append((feed, fn.split("/")[-1], len(df)))

os.makedirs(TRUTH, exist_ok=True)
g.ground_truth.to_csv(f"{TRUTH}/note_flags_ground_truth.csv", index=False)

summary = (pd.DataFrame(written, columns=["feed", "file", "rows"])
           .groupby("feed").agg(files=("file", "count"), rows=("rows", "sum")).reset_index())
display(summary)

# COMMAND ----------

# MAGIC %md ### Files landed in the volume

# COMMAND ----------

for feed in sorted(g.tables):
    files = dbutils.fs.ls(f"{LANDING}/{feed}")
    print(f"{feed:24s} {len(files):3d} file(s), {sum(f.size for f in files)/1e6:7.2f} MB  e.g. {files[0].name}")

# COMMAND ----------

# MAGIC %md ### Sample discharge note (free text, input to AI Functions)

# COMMAND ----------

n = g.tables["discharge_notes"]
e = g.tables["encounters"]
sample = n.merge(e[["encounter_id", "unit_id", "principal_dx_desc"]], on="encounter_id")
sample = sample[(sample.unit_id == "CUMC-6N") & sample.note_text.str.contains("lives alone|by themself|no one at home", regex=True)
                & sample.principal_dx_desc.str.contains("heart failure")]
print(sample.iloc[0].note_text)
