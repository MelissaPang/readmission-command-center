# Readmission Command Center: Cedarbrook Health

An end-to-end Databricks prototype for **30-day readmissions and the CMS Hospital Readmissions Reduction Program (HRRP)**.
It runs on synthetic data from raw files to a business app:
**Lakeflow → Unity Catalog → ML + Gen AI → Lakebase → Genie → Databricks App** (plus an AI/BI dashboard).

> All data is synthetic, produced by a seeded generator (`src/rcc_datagen.py`). No real patients.

## The customer story

Cedarbrook Health runs Cedarbrook University Medical Center (CUMC, 538 beds), Fairhaven Community Hospital and Pine Hollow
Medical Center. Heart-failure 30-day readmissions on CUMC's **6 North Telemetry** unit rose from **14.8% to 23.9%** over the
last 20 weeks (+9.1 pts), while every other unit stayed within about 1.5 points. Heart failure is also the largest line
(**$1.14M**) of CUMC's estimated **$1.62M** HRRP penalty (at the 3% cap), with an HF excess readmission ratio (**ERR**) of **1.19**.

What the data shows (every number below is recomputed from the gold tables and checked in `notebooks/99_validate_story.py`):

* **The rise is on weekend discharges.** On 2026-06-19, 6 North lost its weekend transitions pharmacist, and on
  2026-06-26 the HF Bridge Clinic dropped its Friday afternoon slots. Since then, only **18%** of 6 North Fri–Sun HF discharges
  leave with a booked 7-day follow-up, against **69%** on weekdays. The notes say *"patient to call the HF Bridge Clinic on Monday"*.
* HF patients **without a 7-day follow-up readmit at 29.8%, against 16.4%** for those with one (trailing 12 months, all hospitals).
* **AI Functions read every discharge note.** *Lives alone / no caregiver* appears only in the free text, and HF patients with that
  flag readmit at **33.1% vs 20.6%**.
* **What-if (fixed-rule, no model):** if 6 North had booked a follow-up for 80% of its weekend HF discharges, CUMC would have avoided about
  **7 readmissions** in 12 months. That moves the HF ERR from **1.19 to 1.14** and saves about **$240K** of penalty.

**Personas (fictional Cedarbrook leadership):** **Jordan Whitfield**, CFO (executive sponsor; owns the HRRP penalty); **Dr. Elena Vasquez, MD**, VP of Quality & Patient Safety (owns the HF excess readmission ratio); **Priya Raman, RN**, Manager of Transitional Care, the app's main user, who approves the transition plans (owns the 7-day follow-up rate); **Kenji Tanaka**, Chief Data & Analytics Officer (owns the platform). Transitional-care nurses and CHWs work the outreach queue.
nurses and CHWs, who work the outreach queue; the Revenue Integrity & Quality team, who use the HRRP page, the dashboard and Genie.

## Industry context: why this matters to a health system

* **The CMS Hospital Readmissions Reduction Program (HRRP)** (ACA §3025, penalties since FY2013) cuts a hospital's base operating
  DRG payments for **all** Medicare fee-for-service discharges, by up to **3%**, when its 30-day readmissions exceed expected for
  six cohorts: AMI, heart failure, pneumonia, COPD, CABG and elective hip/knee replacement. CMS compares hospitals within peer groups
  (by dual-eligible share) over a 3-year performance period. A unit-level problem therefore becomes a hospital-wide payment cut.
* **Heart failure** is among the most readmitted cohorts: roughly one in five HF patients is readmitted within 30 days nationally.
  An early outpatient visit is one of the most consistently cited levers.
* **The 7-day follow-up** matches how care transitions are reimbursed. Transitional Care Management (CPT 99496) expects contact
  within 2 business days and a face-to-face visit within 7 days for high-complexity discharges. So the KPI the app drives (7-day follow-up
  booked before discharge) is one care-transitions teams already own.
* **The buyer's KPIs** used throughout: HRRP penalty $, excess readmission ratio (ERR), HF 30-day readmission rate, 7-day follow-up rate,
  % of high-risk patients contacted within 48h.
* The prototype simplifies the CMS method (12 months, all payers, observed/expected; see *Simplifications*), and says so wherever it matters.

## Presentation materials

* [`docs/deck.md`](docs/deck.md): **the presentation deck as extractable text** (Marp-compatible; render to a PDF with selectable text with `marp docs/deck.md --pdf`)
* [`docs/storyline.md`](docs/storyline.md): the narrative spine (outcome-first arc, executive accountability map by role, one-patient thread through every layer, proof points, requirements check)
* [`docs/deck_walkthrough.md`](docs/deck_walkthrough.md): slide-by-slide deck content (outcome first, buyer KPIs, sources for every number)
* [`docs/talk_track.md`](docs/talk_track.md): role-play script with tell-show-tell demo, objection handling for business and technical stakeholders
* [`docs/ai_workflow.md`](docs/ai_workflow.md): AI tools, the actual prompts, and the build workflow with Claude Code
* [`docs/fe_bar_readiness.md`](docs/fe_bar_readiness.md): self-assessment against the four FE Bar domains

## Architecture

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full design. Here is the integrated data journey:

```
src/rcc_datagen.py ──► UC volume raw.landing (JSON/CSV)
   │
   ▼  Lakeflow Declarative Pipeline `rcc_pipeline` (serverless, SQL)
bronze.*  (Auto Loader / read_files, streaming)
   ▼
silver.*  (typed, de-duplicated, expectations, PHI column masks)
   ├─► silver.discharge_note_signals   ← AI Functions: ai_query(Claude Haiku, structured output) on every note
   ▼
gold.*    (index admissions + 30-day outcome, unit trends, follow-up gap, risk factors, HRRP ERR & penalty)
   ├─► ML: MLflow, champion registered in UC `ml.readmit_30d_risk@champion` → gold.patient_risk_scores, gold.discharge_worklist
   ├─► gold.hrrp_whatif (fixed-rule scenarios)
   ├─► Genie space "Readmission & HRRP Analyst" + AI/BI dashboard
   └─► Lakebase synced tables (rcc_lakebase.public.*) ──► Databricks App ──► app writes rcc_lakebase.app_rcc.* ──► readable in UC
                                                            └─► Foundation Model API (Claude) drafts plans; Genie API answers questions
```

| Requirement | Where it is built | Where it is proven (text evidence) |
|---|---|---|
| **Lakeflow** ingest | `pipelines/01_bronze.sql`, `02_silver.sql`, `03_gold.sql`, `resources/rcc.yml` | `evidence/pipeline_events.md` (updates, rows per flow, expectation pass/fail), `evidence/job_run_summary.md` |
| **Unity Catalog** governance | `notebooks/01_uc_governance.py`, `MASK` clauses in `02_silver.sql`, row filter in `04_batch_score.py` | `notebooks/executed/01_uc_governance.ipynb`, `notebooks/executed/99_validate_story.ipynb` (masks/row filter in action, grants, tags, lineage) |
| **Lakebase** operational serving | `notebooks/07_lakebase_setup_and_sync.py`, `scripts/grant_app_access.py`, `app/app.py` | `notebooks/executed/07_lakebase_setup_and_sync.ipynb` (synced tables, psql queries), `evidence/app_api_responses/*`, `evidence/query_results.md` (write-back), `evidence/lakebase_verification.md` (synced vs source, SP privileges) |
| **ML** | `notebooks/03_train_readmission_model.py`, `04_batch_score.py` | `notebooks/executed/03_train_readmission_model.ipynb` (AUC, calibration, importance, UC registration), `04_batch_score.ipynb` |
| **Gen AI** | AI Functions in `02_silver.sql`; nurse briefings in `04_batch_score.py`; plan drafting and edit capture in `app/app.py`; closed loop in `08_feedback_loop.py` | `notebooks/executed/02_ai_note_signals_eval.ipynb` (extraction accuracy vs ground truth), `04_batch_score.ipynb` (briefings), `evidence/app_api_responses/11_draft_plan.json`, `12_approve_plan.json` (RN edit stats), `notebooks/executed/08_feedback_loop.ipynb` (weak labels) |
| **Genie agent** | `notebooks/06_genie_space.py` | `notebooks/executed/06_genie_space.ipynb` (question → SQL → rows, plus LLM-judge verdicts vs SQL reference answers), `evidence/app_api_responses/16_genie_ask.json` |
| **Databricks App** | `app/` (FastAPI + JS), `resources/app.yml` | `evidence/app_deploy.log`, `evidence/app_api_responses/00_app_status.json` … `16_*.json`, `evidence/app_logs.txt` |
| **Dashboard** | `dashboards/readmissions_hrrp_executive.lvdash.json` (built by `scripts/build_dashboard.py`) | `evidence/dashboard_verification.md` (deployed definition: 9 dataset queries executed, 15 widgets resolved) |
| **Story numbers** | `notebooks/99_validate_story.py` | `notebooks/executed/99_validate_story.ipynb`, `evidence/query_results.md` (validation table) |

## Execution evidence (text only)

Everything under `evidence/` and `notebooks/executed/` is **real output from a run in workspace `e2-demo-field-eng`**, committed as text:

* `notebooks/executed/*.ipynb`: every job notebook exported from the job run **with its cell outputs** (tables rendered as text), plus the same content as markdown in `evidence/notebook_outputs/*.md`.
* `evidence/job_run_summary.md`, `evidence/job_run_<run_id>.json`: job and task run IDs, result states and durations.
* `evidence/pipeline_events.md`: Lakeflow event log (rows written per flow, data-quality expectations, dropped records).
* `evidence/query_results.md`: SQL results for every story number, model metrics, worklist and the app write-back.
* `evidence/app_api_responses/*.json`: responses from the deployed app (health, trends, worklist, HRRP, what-if, a Claude-drafted plan,
  its approval and the outreach tasks it created, a Genie answer), plus `evidence/app_deploy.log` and `evidence/app_logs.txt`.

To regenerate the evidence: `python scripts/export_evidence.py` (notebooks plus job run), `python scripts/export_pipeline_evidence.py`, `scripts/capture_app_evidence.sh`.

## Repository layout

```
databricks.yml, resources/        Asset Bundle: schemas, volumes, pipeline, job, app, dashboard
src/rcc_datagen.py                seeded synthetic EHR generator (story built into the data)
pipelines/                        Lakeflow SQL: bronze / silver (+ AI Functions) / gold
notebooks/                        job notebooks (source)      notebooks/executed/  same, with run outputs
app/                              Databricks App: app.py (FastAPI), static/ (UI), app.yaml
dashboards/                       AI/BI dashboard definition
scripts/                          local story check, evidence exporters, verifiers, app grants, run status
docs/                             deck walkthrough, talk track, AI workflow, FE Bar readiness
evidence/                         text execution evidence
```

## Run it yourself

```bash
databricks auth login -p e2-demo-field-eng
databricks catalogs create cedarbrook_rcc -p e2-demo-field-eng
databricks database create-database-instance rcc-lakebase --capacity CU_1 -p e2-demo-field-eng
databricks bundle deploy -p e2-demo-field-eng               # schemas, volumes, pipeline, job, dashboard, app
databricks bundle run rcc_end_to_end -p e2-demo-field-eng   # generate → govern → Lakeflow → ML → what-if → Genie → Lakebase → validate
uv run --with databricks-sdk --with "psycopg[binary]" python scripts/grant_app_access.py
databricks bundle run rcc_app -p e2-demo-field-eng
```

The first pipeline run sends about 16.6k notes to Claude Haiku (roughly 20 minutes). Later runs are incremental, about 2 minutes.

## Simplifications (prototype)

* **ERR** = observed rate / CMS expected rate over a 12-month window. CMS uses risk-adjusted predicted/expected over 3 years
  and Medicare FFS only; here the cohort is all-payer, and the neutrality modifier is 1.0.
* **Entitlements** are a UC table (`gold.rcc_user_entitlements`) instead of account groups, because the shared demo workspace doesn't
  allow creating groups. Masks and row filters work the same way.
* **AI extraction accuracy is 100%** against the generator's ground truth (`02_ai_note_signals_eval`). That is real model output,
  but the synthetic notes use a limited set of phrasings. Expect lower accuracy on real clinical notes and validate against them.
* **The app's Lakebase access** is granted explicitly (`scripts/grant_app_access.py`), because this workspace rejects the Lakebase
  app-resource binding.
