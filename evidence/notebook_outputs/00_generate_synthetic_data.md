# Executed notebook: generate_data

job run `206873801708733` · task run `155085439701699` · result **SUCCESS** · 2026-11-09 17:49:48 UTC

# 00 · Generate synthetic EHR extracts (raw data)

Cedarbrook Health · Readmission Command Center

This notebook generates a **deterministic (seed=42) synthetic EHR extract** and lands it in the Unity Catalog volume
`/Volumes/<catalog>/raw/landing/`, one folder per source feed. Lakeflow (Auto Loader) ingests it from there.

| Feed | Format | Notes |
|---|---|---|
| encounters | JSON lines, one file per discharge month | ADT inpatient encounters, incl. 45 duplicates + 6 bad timestamps on purpose |
| discharge_notes | JSON lines, one file per month | free-text discharge summaries |
| patients | CSV | demographics (PHI) |
| followup_appointments | CSV | scheduling extract with booking timestamps |
| hospitals, units, icd10_hrrp_map, staffing_events, cms_hrrp_reference | CSV | reference data |

The generator plants the customer story into the data (see `src/rcc_datagen.py`). Ground truth for the
free-text flags goes to a separate volume and is only used to score the AI extraction.

```python
dbutils.widgets.text("catalog", "cedarbrook_rcc")
catalog = dbutils.widgets.get("catalog")

import os, sys, json
sys.path.append(os.path.abspath("../src"))
import rcc_datagen as gen

LANDING = f"/Volumes/{catalog}/raw/landing"
TRUTH = f"/Volumes/{catalog}/raw/ground_truth"
print("landing:", LANDING)
```

Output:

```text
landing: /Volumes/cedarbrook_rcc/raw/landing
```

```python
g = gen.generate(seed=gen.SEED)
print(json.dumps({k: v for k, v in g.calibration.items() if not isinstance(v, dict)}, indent=2))
```

Output:

```text
{
  "rows": 16635,
  "index_encounters": 14475,
  "readmissions": 1969,
  "hf12_R": 0.2210283960092095,
  "hf12_nofu_share": 0.4255850448448471,
  "hf12_la_share": 0.12022716807367614,
  "community_hf_rate": 0.2651730382293763,
  "cumc_hf_readmits_12m": 156,
  "sixn_post_change_rate": 0.2692307692307692,
  "sixn_pre_weekend_fu_rate": 0.6853146853146853
}
```

```python
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
```

Output:

```text
| feed                  | files | rows  |
|-----------------------|-------|-------|
| cms_hrrp_reference    | 1     | 16    |
| discharge_notes       | 19    | 16584 |
| encounters            | 19    | 16635 |
| followup_appointments | 1     | 11329 |
| hospitals             | 1     | 3     |
| icd10_hrrp_map        | 1     | 23    |
| patients              | 1     | 14615 |
| staffing_events       | 1     | 4     |
| units                 | 1     | 16    |
(9 rows shown)
```

### Files landed in the volume

```python
for feed in sorted(g.tables):
    files = dbutils.fs.ls(f"{LANDING}/{feed}")
    print(f"{feed:24s} {len(files):3d} file(s), {sum(f.size for f in files)/1e6:7.2f} MB  e.g. {files[0].name}")
```

Output:

```text
cms_hrrp_reference         1 file(s),    0.00 MB  e.g. cms_hrrp_reference.csv
discharge_notes           19 file(s),   10.01 MB  e.g. discharge_notes_2025-05.json
encounters                19 file(s),    7.57 MB  e.g. encounters_2025-05.json
followup_appointments      1 file(s),    1.01 MB  e.g. followup_appointments.csv
hospitals                  1 file(s),    0.00 MB  e.g. hospitals.csv
icd10_hrrp_map             1 file(s),    0.00 MB  e.g. icd10_hrrp_map.csv
patients                   1 file(s),    1.10 MB  e.g. patients.csv
staffing_events            1 file(s),    0.00 MB  e.g. staffing_events.csv
units                      1 file(s),    0.00 MB  e.g. units.csv
```

### Sample discharge note (free text, input to AI Functions)

```python
n = g.tables["discharge_notes"]
e = g.tables["encounters"]
sample = n.merge(e[["encounter_id", "unit_id", "principal_dx_desc"]], on="encounter_id")
sample = sample[(sample.unit_id == "CUMC-6N") & sample.note_text.str.contains("lives alone|by themself|no one at home", regex=True)
                & sample.principal_dx_desc.str.contains("heart failure")]
print(sample.iloc[0].note_text)
```

Output:

```text
DISCHARGE SUMMARY
Hospital course: Admitted with acute decompensated heart failure (EF 25%), volume overload, dyspnea on exertion. Diuresed with IV furosemide, net negative 3.0 L. Discharge weight 88 kg.
Discharge medications: Furosemide 40 mg PO daily, metoprolol succinate 50 mg daily, sacubitril/valsartan 24/26 mg BID, spironolactone 25 mg daily.
Education: Reviewed 2 g sodium diet, 1.5 L fluid restriction, daily weights; call if weight up 2 lb in a day or 5 lb in a week.
Social history: Widowed, lives by themself. No family nearby to help with medications.
Follow-up: Follow-up appointment scheduled with HF Bridge Clinic on 2025-05-22 at 10:00.
Condition at discharge: stable.
```
