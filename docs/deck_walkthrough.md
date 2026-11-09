# Deck walkthrough: Readmission Command Center for Cedarbrook Health

Slide-by-slide content for building the presentation deck. Each slide lists its **headline** (the takeaway, written as a
sentence), **on-slide content**, a **visual** suggestion, and the **source** of every number in this repo, so each figure can
be defended in the role-play.

**Audience in the room**
* **Executive sponsor / budget owner:** CFO or Chief Quality Officer at Cedarbrook Health. KPIs: HRRP penalty $, excess readmission ratio (ERR), HF 30-day readmission rate, cost per readmission, payback.
* **Domain owner:** Priya Raman, RN, Manager of Transitional Care. KPIs: 7-day follow-up rate, % of high-risk patients contacted within 48h, nurse time per patient, readmissions on her units.
* **Technical stakeholder:** data architect / data platform lead. Concerns: integration with the EHR, data quality, security/PHI, operability, cost.

**Deck rules applied:** lead with the outcome, quantify in the buyer's KPIs, show one integrated data journey (not separate demos), put architecture after value, and document trade-offs.

> All figures come from the synthetic Cedarbrook dataset that the prototype ran on (`evidence/`). Present them as
> "what the prototype shows on Cedarbrook-like data". Figures marked **[assumption]** are not from the build and should be validated with the customer.

Target length: **12 main slides + 4 appendix slides**, for a 20–30 minute session.

---

## Slide 1 · Title

**Headline:** *Cutting heart-failure readmission penalties at Cedarbrook Health: $240K in year one from one unit, with a path to $874K*

* Subtitle: Readmission Command Center, built on the Databricks Data Intelligence Platform
* Presenter name, date
* Small footer: "Prototype on synthetic Cedarbrook data. No real patients."

**Visual:** clean title. One hero number: **$240K**.
**Source:** `gold.hrrp_whatif` (80% target → $238,438; all CUMC HF at 80% → $874,444).

---

## Slide 2 · The outcome (executive summary)

**Headline:** *Booking a follow-up for weekend heart-failure discharges is worth ~$240K a year on one unit*

Three outcome tiles:
* **~7 readmissions avoided / year** on 6 North (6.5 modeled)
* **HF ERR 1.19 → 1.14**: closer to the CMS benchmark of 1.00
* **~$240K HRRP penalty avoided** ($1.62M → $1.38M)

Below the tiles, one line per audience:
* *For the CFO / CQO:* the cause, the fix and the dollars are in one place, so the decision is fundable.
* *For Transitional Care:* a ranked daily worklist with the "why" for each patient and an AI-drafted plan that a nurse approves.

**Visual:** three large KPI tiles; a small "before → after" arrow on the ERR.
**Source:** `evidence/query_results.md` (what-if), `notebooks/executed/05_hrrp_whatif.ipynb`.

---

## Slide 3 · The customer and the problem

**Headline:** *One unit's heart-failure readmissions jumped 9 points, and it is driving most of a $1.62M penalty*

* Cedarbrook Health: 3 hospitals, flagship CUMC with 538 beds
* 6 North Telemetry HF 30-day readmissions: **14.8% → 23.9%** in 20 weeks (+9.1 pts)
* Every other unit: stable, **within ±1.5 pts** (largest change 1.1 pts)
* CUMC estimated HRRP penalty **$1.62M** (at the 3% cap). Heart failure is the largest line at **$1.14M**, **ERR 1.19**
* System-wide penalty across the 3 hospitals: **~$2.08M**

**Visual:** a line chart of 6 North vs all other units (weekly HF readmission rate), with the jump after June 2026 highlighted.
**Source:** `gold.unit_period_summary`, `gold.hrrp_hospital_penalty`; chart = dashboard widget "Weekly HF 30-day readmission rate".

---

## Slide 4 · Why nobody could see it

**Headline:** *The cause was operational, buried in notes, and spread across three teams*

* **It's operational, not clinical.** 6 North lost its weekend transitions pharmacist (2026-06-19) and the HF Bridge Clinic dropped its Friday afternoon slots (2026-06-26).
* **Part of the evidence is in free text.** Discharge notes say *"patient to call the HF Bridge Clinic on Monday"*, and *"lives alone"* appears only in the note.
* **The data is split across teams.** Quality sees rates, Finance sees the penalty, nurses see a flat discharge list. Nobody could connect a missed follow-up to penalty dollars.

**Visual:** three silo icons (Quality / Finance / Care Transitions) with a broken link between them.

---

## Slide 5 · What the data shows (the root cause, quantified)

**Headline:** *Weekend discharges leave without a follow-up, and those patients come back*

Four evidence points (one chart each, or a 2×2 grid):
1. Since 2026-06-19, 6 North weekend HF discharges with a booked 7-day follow-up: **18%** (11/62) vs **69%** on weekdays (94/137). Before the change, weekends were ~69% too.
2. HF patients **without** a 7-day follow-up readmit at **29.8%** vs **16.4%** with one (trailing 12 months, all hospitals).
3. **AI read all 16,584 discharge notes.** HF patients who *live alone*, a fact found only in free text, readmit at **33.1% vs 20.6%**.
4. 51 of 51 unbooked 6 North weekend notes tell the patient to call or schedule follow-up themselves.

**Visual:** grouped bar chart (weekday vs weekend, before vs since 2026-06-19) plus two rate-comparison bars.
**Source:** `gold.followup_gap`, `gold.readmission_risk_factors`, `notebooks/executed/99_validate_story.ipynb`.

---

## Slide 6 · The value case (in the buyer's KPIs)

**Headline:** *Every 10 points of weekend follow-up on 6 North is worth roughly $120K in avoided penalty*

What-if (fixed-rule, trailing 12 months, CUMC):

* 70% booked → 3.9 readmissions avoided, ERR 1.16, **$119K** saved
* **80% booked → 6.5 avoided, ERR 1.14, $238K saved** ← recommended target
* 90% booked → 9.1 avoided, ERR 1.12, $358K saved
* 100% booked → 11.8 avoided, ERR 1.10, $478K saved

Scaling the same fix:
* All CUMC weekend HF discharges at 80% → **~$412K**
* All CUMC HF discharges at 80% → **~$874K**

Payback framing **[assumption, validate with Cedarbrook finance]:** restoring weekend transitions-pharmacist coverage (~0.4 FTE, ~$60K/yr loaded) against **$238K** of avoided penalty is about a **4× return**, before counting the hospital's cost of the readmissions themselves.

**Visual:** what-if slider screenshot from the app (HRRP & What-if page), plus a simple bar of the three scopes.
**Note for Q&A:** savings rise unevenly because CUMC's uncapped penalty ($1.68M) is above the 3% cap ($1.62M), so the first ~$60K of improvement is absorbed by the cap.
**Source:** `gold.hrrp_whatif`, `evidence/app_api_responses/08_whatif_6n_weekend.json`.

---

## Slide 7 · The solution: one platform, one data journey

**Headline:** *From raw EHR extracts to a nurse's worklist on one governed platform*

Left-to-right flow (this is the key "integrated, not siloed" slide):

**Raw EHR extracts → Lakeflow → Unity Catalog → AI + ML → Lakebase → App · Genie · Dashboard**

* **Lakeflow:** incremental ingest of encounters, notes, appointments and CMS reference files; data-quality rules; HRRP gold tables
* **Unity Catalog:** one governed copy, with PHI masking, hospital-level row filters, lineage and the model registry
* **AI Functions + ML:** Claude reads every note into structured risk flags, which feed a 30-day risk model with per-patient drivers
* **Lakebase:** low-latency serving for the app, plus the app's own writes (approved plans, outreach tasks, audit trail)
* **Genie / App / Dashboard:** plain-English analytics, the nurse worklist, the executive view

One sentence under the flow: *"The flag the AI pulls from a note becomes a model feature, which becomes a worklist priority, which becomes a dollar figure on the HRRP page, all on the same governed data."*

**Visual:** horizontal pipeline diagram with the six product logos; one highlighted thread (a single patient) moving through it.

---

## Slide 8 · Demo: what you are about to see (tell)

**Headline:** *Follow one weekend discharge from the data to an approved care plan*

Demo agenda (5 stops, ~10 minutes):
1. **Unit Trends:** spot the 6 North spike and the weekend follow-up gap
2. **Discharge Worklist:** today's high-risk patients, ranked, with the reason
3. **Patient detail:** AI note evidence, then Claude drafts a transition plan, then the RN approves it and outreach tasks are created
4. **HRRP & What-if:** move the slider and watch the ERR and penalty dollars change
5. **Ask Genie:** a finance question in plain English, answered with SQL and data

**Visual:** five numbered screenshot thumbnails (one per stop).

---

## Slide 9 · What the demo means (tell back)

**Headline:** *Insight to action to dollars, in one workflow*

* **For the domain owner:** 54 high-risk patients in the current 30-day window, 41 of them without a 7-day follow-up. Priya's team knows exactly who to call today, and why.
* **For the executive:** every booked follow-up shows up in ERR and penalty dollars on the same screen.
* **For both:** AI drafts and a nurse decides. Every plan and task is audited.

Proof points:
* Claude drafted a grounded plan in **4.4 s**
* Approving it auto-created 2 outreach tasks (book follow-up, pharmacist call)
* Genie answered 5/5 story questions correctly

**Source:** `gold.discharge_worklist`, `evidence/app_api_responses/11_draft_plan.json`, `12_approve_plan.json`, `16_genie_ask.json`.

---

## Slide 10 · Trust: governance, accuracy, and safety

**Headline:** *Built to clinical and HIPAA-grade expectations from day one*

* **PHI protection:** Unity Catalog column masks. Analysts see `***MASKED***` instead of names, MRNs and phone numbers, and dates of birth are shifted to Jan 1.
* **Least privilege:** hospital-scoped row filters (an FCH-only user sees 3,424 of 14,475 rows). The app's identity has read-only access to served data.
* **Data quality:** pipeline rules caught and dropped all planted bad records (6 invalid timestamps, 45 duplicates).
* **Model:** test AUC **0.72**. The top-risk decile readmits at **2.6×** the average. Observed rates: High 45%, Medium 24%, Low 9%.
* **AI extraction:** 16,584 notes, 0 errors, validated against ground truth. *Caveat: synthetic notes are uniform, so validate on real notes in the pilot.*
* **Human in the loop:** AI drafts, the RN approves, everything is audited. Lineage from raw file to app is in Unity Catalog.

**Source:** `notebooks/executed/99_validate_story.ipynb` (27/27 checks), `evidence/pipeline_events.md`, `evidence/lakebase_verification.md`.

---

## Slide 11 · Decisions and trade-offs

**Headline:** *Three deliberate choices that kept this credible and fast*

* **Synthetic data with the story built in**, instead of a public dataset: no PHI risk, and every number reproduces. Trade-off: real notes are messier, so extraction accuracy must be re-validated on Cedarbrook data.
* **The simpler model won.** Logistic regression (AUC 0.7245) beat gradient boosting (0.7137) and is easier for clinicians to trust. Trade-off: less headroom on richer data, so the champion is re-selected automatically each run.
* **A fixed-rule, auditable what-if** on a simplified HRRP method, so Finance can reproduce every dollar. Trade-off: it assumes the follow-up effect is causal, and it simplifies CMS's 3-year, risk-adjusted, Medicare-only calculation.

---

## Slide 12 · Path to production and the ask

**Headline:** *A 90-day pilot on 6 North proves the $240K before scaling to the system*

* **Weeks 0–4 (connect):** replace the synthetic extracts with Epic Clarity / Caboodle feeds or HL7/FHIR ADT; map to the same bronze schema; enable account groups for the masks.
* **Weeks 4–8 (validate):** re-validate note extraction on real notes (sample review by RNs); recalibrate the model on Cedarbrook outcomes; confirm the ERR method with Quality.
* **Weeks 8–12 (operate):** 6 North nurses use the worklist daily. Track 7-day follow-up %, contact-within-48h % and readmissions weekly.
* **Then scale:** all CUMC HF (~$874K at 80%), then COPD and pneumonia lines, then Fairhaven and Pine Hollow.

**The ask:**
1. An executive sponsor and data access for a 90-day pilot.
2. A decision on weekend follow-up coverage (backfill the pharmacist or restore the Friday clinic slots).

**Success metrics for the pilot:**
* 6 North weekend 7-day follow-up from 18% to ≥ 80%
* HF readmissions trending back toward ~15%
* ≥ 90% of high-risk patients contacted within 48h

---

## Appendix A · Architecture detail (for the technical stakeholder)

* **Ingest:** Lakeflow Declarative Pipeline (serverless, SQL), Auto Loader from UC volumes → bronze (9 feeds) → silver (typed, de-duplicated, expectations, PHI masks) → gold (10 tables)
* **AI:** `ai_query(databricks-claude-haiku-4-5, responseFormat => STRUCT<...>)` in an incremental streaming table, so each note is processed once. First run ~24 min for 16.6k notes; reruns ~2 min.
* **ML:** scikit-learn models tracked in MLflow; champion picked by test AUC and registered as `ml.readmit_30d_risk@champion`; counterfactual drivers per patient
* **Serving:** Lakebase (Postgres 16) synced tables (snapshot); the app writes to its own schema `app_rcc`, which is readable from UC via the `rcc_lakebase` catalog
* **App:** Databricks App (FastAPI + JS) running as its own service principal; Foundation Model API (Claude Sonnet) for plans; Genie Conversation API
* **Deployment:** one Databricks Asset Bundle with a 10-task job; everything is reproducible with `bundle deploy && bundle run`

**Visual:** the architecture diagram from `ARCHITECTURE.md` §1.

## Appendix B · Evidence the build ran

* Job run `206873801708733`: 10/10 tasks SUCCESS; validation **27/27** checks pass
* Lakebase: 9/9 synced tables match their UC source (row count, key hash, numeric sum)
* All evidence committed as text: `notebooks/executed/`, `evidence/`
* Repo: https://github.com/MelissaPang/readmission-command-center

## Appendix C · AI as a force multiplier (how this was built)

* **Built with Claude Code** (an AI coding agent) driving the Databricks CLI and Asset Bundles from the terminal
* **Workflow:**
  1. Story with target numbers
  2. Architecture mapped to requirements
  3. Seeded generator verified locally *before* touching the platform
  4. Bundle deploy
  5. Run → read the error → fix → rerun
  6. A validation notebook as the gate
  7. Commit the evidence at every milestone
* **Patterns that paid off:**
  * a "story contract" (exact target numbers) checked by code
  * structured-output prompts for extraction
  * grounded prompts for plan drafting: "use ONLY the facts in the patient context"
  * incremental AI processing to control cost
* **In-product AI:** Claude Haiku (note extraction), Claude Sonnet (care plans), Genie (plain-English analytics)

## Appendix D · Assumptions and simplifications

* ERR = observed / expected rate over 12 months, all payers, neutrality modifier 1.0. CMS uses 3 years, risk adjustment and Medicare FFS only.
* The what-if assumes the observed follow-up effect (29.8% vs 16.4%) is causal.
* Pharmacist cost (~$60K for ~0.4 FTE) is an illustrative assumption.
* All patient data is synthetic.
