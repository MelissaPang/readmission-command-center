# FE Bar readiness: self-assessment against the four domains

Each domain is rated **below / meets / exceeds**; passing needs every domain at *meets* or above, plus the hard gates. The detailed
per-domain must-haves aren't published in the material we have, so this maps the **stated requirements and common failure modes**
to concrete evidence in this repo. An evaluator can verify every line from text.

Common failure modes, and how the build avoids them:
* *"Solves an internal problem."* It's a named customer problem: Cedarbrook Health's 6 North HF readmissions and HRRP penalty.
* *"Layers present but not connected."* One data thread runs end to end. An AI-extracted note flag → a model feature → a worklist priority →
  a Lakebase-served app → an RN-approved plan written back → readable in UC. HRRP dollars come from the same gold tables (README architecture diagram, `ARCHITECTURE.md` §1).
* *"Narrative skips business value."* The README, the deck and the talk track all open with the outcome (~$240K, ERR 1.19 → 1.14) before any architecture.

---

## 1. Industry

**Must-haves (from the requirements):** a real customer scenario in a specific industry, the buyer's KPIs, and a credible problem and value story.

| Evidence | Where |
|---|---|
| A specific provider scenario (3-hospital system, a named unit, named personas) with an operational root cause | `README.md` story, `docs/deck_walkthrough.md` slides 3–5 |
| Correct HRRP mechanics: 6 cohorts, ERR, condition payment × (ERR − 1), 3% cap, peer grouping and 3-year period stated as simplifications | `pipelines/03_gold.sql` (`hrrp_condition_err`, `hrrp_hospital_penalty`), README *Industry context* and *Simplifications* |
| Buyer KPIs: HRRP $, ERR, HF readmission %, 7-day follow-up % (matches TCM CPT 99496), 48h contact | README *Industry context*, deck slide 2/6/12 |
| A quantified, sized value case with scenarios (70–100%, 3 scopes) and an explicit causal assumption | `gold.hrrp_whatif`, `evidence/query_results.md` |
| Clinically appropriate AI use: draft → RN approval, PHI masking | `app/app.py`, `docs/ai_workflow.md` §3.2 |

**Self-rating: meets.** **To lift to exceeds:**
* Benchmark against **real public data**: load the CMS HRRP supplemental file / Hospital Compare for real hospitals and show where a Cedarbrook-like hospital's HF ERR would sit.
* Implement the **full CMS method**: 3-year period, Medicare FFS only, dual-eligible peer groups, neutrality modifier.
* Add the hospital's own **cost of a readmission** next to the penalty, and a TCM revenue view (99495/99496) for the follow-ups booked.

## 2. Product

**Must-haves:** an integrated journey across Lakeflow → Unity Catalog → Lakebase → ML or Gen AI → Genie → Databricks App, used appropriately.

| Product | How it is used (beyond a checkbox) | Evidence |
|---|---|---|
| **Lakeflow** | Serverless declarative pipeline; Auto Loader streaming bronze; expectations (drop / fail); MVs; incremental AI streaming table | `evidence/pipeline_events.md` |
| **Unity Catalog** | PHI column masks declared in the pipeline; **role-based mask on AI evidence quotes** (care-transitions only); row-filter function; tag policies honoured; lineage; UC model registry with alias; Lakebase registered as a UC catalog | `notebooks/executed/99_validate_story.ipynb` (mask/filter demo, lineage), `01_uc_governance.ipynb` |
| **Lakebase** | Synced tables for serving; app-owned OLTP schema; least-privilege SP role; write-back readable in UC | `evidence/lakebase_verification.md` (9/9 tables match source) |
| **ML** | MLflow experiments, two models, champion by test AUC, calibration, permutation importance, UC registry → batch scoring | `notebooks/executed/03_*.ipynb`, `04_*.ipynb` |
| **Gen AI** | AI Functions with structured output in the pipeline; **AI nurse briefing** per worklist patient; Foundation Model API for grounded plan drafting; **closed loop**: RN edits become weak labels for retraining | `02_ai_note_signals_eval.ipynb`, `evidence/app_api_responses/11_draft_plan.json` |
| **Genie** | Space with instructions, example SQL, sample questions; evaluated through the Conversation API **and an LLM judge against SQL reference answers, appended every run**; embedded in the app | `06_genie_space.ipynb` (5/5), `16_genie_ask.json` |
| **Databricks App** | Bundle-deployed FastAPI app with bound resources; SP auth; reads Lakebase, writes plans, calls FM API and Genie | `evidence/app_deploy.log`, `evidence/app_api_responses/*` |
| **AI/BI dashboard** | 15-widget executive dashboard, deployed and published | `evidence/dashboard_verification.md` |
| **Asset Bundles** | Everything is code; `bundle deploy && bundle run` | `databricks.yml`, `resources/` |

**Self-rating: meets.** **To lift to exceeds:**
* **CDF + triggered or continuous Lakebase sync** for minutes-fresh worklists.
* **Lakehouse Monitoring** on `gold.patient_risk_scores`.
* **Genie benchmarks** stored in the space.
* A **UC metric view** for readmission rate and ERR, so Genie, the dashboard and the app share one definition.
* **MLflow Tracing + `mlflow.evaluate`** on the plan drafts.

## 3. Build and AI Mindset

**Must-haves:** a working end-to-end prototype from raw data, with **execution evidence readable as text** (source code alone fails), and AI used as a force multiplier with tools, prompts and patterns documented.

| Evidence | Where |
|---|---|
| Raw data → app on one platform; the job run `601827272748584` had **11/11 tasks SUCCESS** | `evidence/job_run_summary.md`, `evidence/job_run_601827272748584.json` |
| Executed notebooks with real outputs (not screenshots) | `notebooks/executed/*.ipynb`, `evidence/notebook_outputs/*.md` |
| Logged run output and query results | `evidence/pipeline_events.md`, `evidence/query_results.md` |
| Real model output: Claude plan, Genie answers, AI extraction | `evidence/app_api_responses/11_draft_plan.json`, `16_genie_ask.json`, `02_ai_note_signals_eval.ipynb` |
| Independent verifiers: story 33/33, Lakebase 9/9, dashboard 9 datasets + 15 widgets | `99_validate_story.ipynb`, `evidence/lakebase_verification.md`, `evidence/dashboard_verification.md` |
| Decisions and trade-offs | `ARCHITECTURE.md` §7, README, deck slide 11 |
| AI tools, actual prompts, patterns, build workflow (including the bugs found and how) | `docs/ai_workflow.md` |
| Reproducible: seeded data, bundle, scripts | README *Run it yourself* |

* *Added after the first review:* closed-loop weak labels from RN edits; Genie LLM judge; grounded nurse briefings; role-based evidence mask.

**Self-rating: meets.** **To lift to exceeds:**
* **CI:** a GitHub Action running `bundle validate`, `scripts/local_story_check.py` and unit tests for the generator and gold SQL.
* An **LLM-as-judge evaluation** of plan faithfulness, with scores committed.
* **Re-run the evidence from a clean workspace** (destroy → deploy → run) and commit that run.

## 4. Customer Skills

**Must-haves:** a deck that leads with the business outcome, quantifies impact in the buyer's KPIs and frames value for the executive sponsor and
the domain owner; a role-play with demo setup, tell-show-tell, value communication, reading the room and professionalism.

| Evidence | Where |
|---|---|
| Deck content: outcome first, buyer KPIs, executive and domain-owner framing, integrated-journey slide, trade-offs, pilot plan and ask | `docs/deck_walkthrough.md` |
| Role-play script: setup, 5-stop tell-show-tell demo, value lines per persona, about 18 objection answers (business and technical) with altitude bridges, close | `docs/talk_track.md` |
| A working live demo with a known click path | the app (URL in README), talk track §5 |

**Self-rating: on track for meets, but it depends on delivery.** Still to do (by you):
* Build the deck from `docs/deck_walkthrough.md` and **export it as PDF (or .md / .txt)** for the submission's deck field. This is a required artefact.
* **Rehearse the role-play out loud**: headline in the first 60 seconds, tell-show-tell at each demo stop, and name the assumptions (causality, pharmacist cost, synthetic notes) before you're asked.
* Before the session: app running, Lakebase instance started, a High-risk 6 North patient with no plan ready to open.

**To lift to exceeds:**
* A one-page **business case** with a pilot ROI model, sensitivity on the causal assumption, and the cost to run.
* A **customer-specific** opening: Cedarbrook's strategic goals, star ratings, value-based contracts.
* A **mutual action plan** with named owners and dates.

---

## Hard gates checklist

* [x] Real customer scenario in a specific industry (healthcare provider, HRRP)
* [x] All required layers present **and connected** (Lakeflow, UC, Lakebase, ML + Gen AI, Genie, App)
* [x] Raw data generated synthetically, starting the journey (`src/rcc_datagen.py`)
* [x] Code, notebooks, app and dashboards in the repo
* [x] Execution evidence readable as text, committed
* [x] Decisions and trade-offs documented
* [x] Value quantified ($238K; $412K / $874K scaled)
* [x] AI tools, prompts and patterns documented
* [ ] Deck exported (PDF / .md / .txt) and attached (**you**)
* [ ] Role-play completed (**you**)
