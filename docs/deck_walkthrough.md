# Deck walkthrough: Readmission Command Center for Cedarbrook Health

Slide-by-slide content for building the presentation deck. It follows `docs/storyline.md` beat by beat. Each slide lists its
**headline** (the takeaway, written as a sentence), **on-slide content**, a **visual** suggestion, the **storyline beat** it serves, and
the **source** of every number in this repo, so each figure can be defended in the role-play.

**Audience in the room**
* **Executive sponsor / budget owner:** CFO or Chief Quality Officer. KPIs: HRRP penalty $, excess readmission ratio (ERR), HF 30-day readmission rate, payback.
* **Domain owner:** Priya Raman, RN, Manager of Transitional Care. KPIs: 7-day follow-up rate, high-risk patients contacted within 48h, nurse time per patient.
* **Technical stakeholder:** data architect / platform lead. Concerns: integration, data quality, PHI security, operability, cost.

**Deck rules applied:**
* lead with the outcome
* quantify in the buyer's KPIs
* explain why the customer couldn't solve it before
* show one connected data journey
* put value before architecture
* document trade-offs
* close with a concrete ask

> All figures come from the prototype run on synthetic Cedarbrook data (`evidence/`). Present them as "what the prototype shows on
> Cedarbrook-like data". Figures marked **[assumption]** are not from the build and must be stated as such. Real-time discharge
> scoring is the **production design**. In the prototype the pipeline runs per job, so say "in production".

**Flow at a glance (14 main slides + appendix, 20–30 min)**

| # | Slide | Storyline beat |
|---|---|---|
| 1 | Title | n/a |
| 2 | The outcome | Beat 0 |
| 3 | The customer and the stakes | Beat 1 |
| 4 | A peak nobody saw coming | Beat 2 |
| 5 | Why Cedarbrook couldn't solve it before | Beat 2b |
| 6 | Unified data makes the root cause obvious | Beat 3 |
| 7 | What fixing it is worth | Beat 5 |
| 8 | The solution: unify, predict, visualize, act, measure | Beat 4 |
| 9 | One patient, one platform | §4 one-thread story |
| 10 | How Databricks solves each challenge | §4b |
| 11 | Demo: what you're about to see | §5 (tell) |
| 12 | What the demo means | §5 (tell back) |
| 13 | Trust, and the trade-offs we made | Beat 6, §8 |
| 14 | 90-day pilot and the ask | Beat 7 |
| A–E | Appendix | supporting detail |

---

## Slide 1 · Title

**Headline:** *See readmission peaks as they start, and stop them at discharge*

* Subtitle: the Readmission Command Center for Cedarbrook Health, on the Databricks Data Intelligence Platform
* One hero number: **~$240K a year** in avoidable HRRP penalty on one unit, with a path to **~$874K** hospital-wide
* Presenter, date. Footer: "Prototype on synthetic Cedarbrook data. No real patients."

**Visual:** clean title slide with the hero number.
**Source:** `gold.hrrp_whatif` (80% → $238,438; CUMC all HF at 80% → $874,444).

---

## Slide 2 · The outcome (Beat 0)

**Headline:** *Booking a 7-day follow-up for weekend heart-failure discharges is worth ~$240K a year on one unit*

Three outcome tiles:
* **~7 readmissions avoided / year** (6.5 modeled)
* **HF ERR 1.19 → 1.14**, moving toward the CMS benchmark of 1.00
* **~$240K penalty avoided** ($1.62M → $1.38M), and **~$874K** if applied to all CUMC heart-failure discharges

One line per audience:
* *Executive:* a penalty line becomes a fundable decision with a number attached.
* *Transitional Care:* every discharge comes with a readmission prediction, so nurses know who to call today and why.

**Visual:** three large KPI tiles; a "before → after" arrow on the ERR.
**Source:** `evidence/query_results.md` (what-if), `notebooks/executed/05_hrrp_whatif.ipynb`.

---

## Slide 3 · The customer and the stakes (Beat 1)

**Headline:** *Under HRRP, one unit's readmissions can cut a hospital's Medicare payments*

* Cedarbrook Health: 3 hospitals. Flagship CUMC has 538 beds.
* CMS's Hospital Readmissions Reduction Program cuts payments on **all** Medicare discharges, by up to **3%**, when 30-day readmissions exceed expected.
* CUMC's estimated penalty is **$1.62M** (at the cap). **Heart failure is the largest line: $1.14M, ERR 1.19.**
* Across the three hospitals: **~$2.08M**.

**Visual:** a penalty bar by condition, with heart failure highlighted.
**Source:** `gold.hrrp_hospital_penalty`, `gold.hrrp_condition_err`.

---

## Slide 4 · A peak nobody saw coming (Beat 2)

**Headline:** *One unit's heart-failure readmissions jumped 9 points, and it was found out months too late*

* 6 North HF 30-day readmissions: **14.8% → 23.9%** in 20 weeks (+9.1 pts).
* Every other unit stayed stable, within **±1.5 pts** (the largest change was 1.1).
* It was found the way most hospitals find these things: **after the fact**, in quality reports and the penalty estimate.
* Two questions nobody could answer: **When did it start? Why?**

**Visual:** a line chart of 6 North vs all other units (weekly HF readmission rate), with the peak circled and a big "?" next to it.
**Source:** `gold.unit_period_summary`, dashboard widget "Weekly HF 30-day readmission rate".

---

## Slide 5 · Why Cedarbrook couldn't solve it before (Beat 2b)

**Headline:** *The answer was in the data, but discharges, predictions and follow-ups never met*

Three columns, one per challenge. *(This is the customer's scenario: say "typical of a multi-hospital system", and confirm in discovery.)*

1. **Siloed data**
   * Discharge records, follow-up appointments, discharge notes and penalty data each live in a separate system.
   * **The readmission prediction is disconnected from the discharge.** If a score exists, it's calculated weeks later in a batch report, not in front of the nurse at discharge.
   * There's no trend view of readmissions by unit, so peaks aren't visible as they start.
2. **Complicated infrastructure**
   * A warehouse, a data lake, a BI tool and an app database, each with its own copy of PHI and its own access rules.
   * Every new question is an IT project, and Quality and Finance numbers don't match.
3. **Limited ML and AI capability**
   * There's no way to deploy and govern a prediction model inside the workflow.
   * Key risk details exist only in free text, and there's no safe way to apply AI to patient data.

**Visual:** three silo icons with broken connectors; a small clock icon on "prediction" showing "weeks later".
**Line to say:** *"Discharges, predictions and follow-ups lived in different systems, so nobody could see the peak start, or explain it."*

---

## Slide 6 · Unified data makes the root cause obvious (Beat 3)

**Headline:** *Unify discharges, predictions and follow-ups, and the root cause appears: no 7-day follow-up, especially on weekends*

Four steps across the slide:
1. **When:** readmissions over time by unit show exactly when 6 North's peak started, and that it's confined to one unit.
2. **Why:** inside the peak, weekend heart-failure discharges with a booked 7-day follow-up fell to **18%**, vs **69%** on weekdays.
3. **So what:** patients without a 7-day follow-up readmit at **29.8%**, vs **16.4%** with one (trailing 12 months, all hospitals).
4. **Who, right now:** every discharge carries its readmission prediction, so high-risk patients without a follow-up are caught *before they go home*.

Callout: *"Not a clinical mystery: a missing follow-up appointment, a process gap the team can fix."*

**Visual:** left, the trend line with the peak marked; right, a grouped bar (weekday vs weekend, before vs during the peak).
**Source:** `gold.unit_weekly_readmissions`, `gold.followup_gap`, `gold.readmission_risk_factors`.
**Speaker note:** the operational "why behind the why" (late-June weekend staffing and clinic schedule changes) and the AI finding that patients who live alone readmit at 33.1% vs 20.6% are in **Appendix E**. Use them only if asked.

---

## Slide 7 · What fixing it is worth (Beat 5, before the solution)

**Headline:** *Every 10 points of weekend follow-up on 6 North is worth ~$120K in avoided penalty*

Fixed-rule what-if (trailing 12 months, CUMC; Finance can reproduce it):
* 70% booked → 3.9 readmissions avoided · ERR 1.16 · **$119K**
* **80% booked → 6.5 avoided · ERR 1.14 · $238K** ← recommended target
* 90% booked → 9.1 avoided · ERR 1.12 · $358K
* 100% booked → 11.8 avoided · ERR 1.10 · $478K

Scaling the same fix:
* CUMC weekend HF discharges (all units) → **~$412K**
* All CUMC HF discharges → **~$874K**

Payback **[assumption]:** if restoring weekend follow-up capacity costs ~$60K/yr (~0.4 FTE of weekend scheduling or pharmacist time), that's **~4×** on the penalty alone.

For the domain owner: today there are **54** high-risk patients in the 30-day window, and **41** of them have no follow-up booked.

**Visual:** a screenshot of the what-if slider in the app, plus a small bar of the three scopes.
**Speaker note:** savings rise unevenly because CUMC's uncapped penalty ($1.68M) is above the 3% cap ($1.62M), so the first ~$60K of improvement is absorbed by the cap.
**Source:** `gold.hrrp_whatif`, `gold.discharge_worklist`, `evidence/app_api_responses/08_whatif_6n_weekend.json`.

---

## Slide 8 · The solution: unify, predict, visualize, act, measure (Beat 4)

**Headline:** *One platform that sees the peak, explains it, and acts on every discharge*

Five steps left to right:
1. **Unify:** discharge records, follow-ups, notes and penalty data in one governed place.
2. **Predict:** a 30-day readmission risk for every discharge, attached to the discharge record.
3. **Visualize:** readmissions over time by unit, so peaks are seen as they start.
4. **Act:** a ranked nurse worklist; an AI-drafted transition plan that the nurse approves; outreach tasks created automatically.
5. **Measure:** what each booked follow-up is worth in ERR and penalty dollars; ask anything in plain English with Genie.

Business framing underneath: **see the peak → understand the cause → act on each patient → measure the dollars.**

**Visual:** a five-step chevron with an icon per step.

---

## Slide 9 · One patient, one platform (the integrated journey)

**Headline:** *A Friday discharge, from raw record to approved care plan, on one governed platform*

Follow one weekend heart-failure patient, left to right, with the product used at each step:

1. **Raw data:** the discharge record, the appointment extract (no follow-up) and the note (*"patient to call the clinic on Monday… lives alone"*) land as files.
2. **Lakeflow** unifies them: incremental ingest, de-duplication and data-quality rules, then gold tables that join each discharge to its follow-up status, its outcome and the unit trend.
3. **Unity Catalog** governs one copy: PHI masked for analysts, hospital-scoped access, lineage back to the raw file.
4. **AI Functions** read the note and add *lives alone* and *patient to call*, with an evidence quote.
5. **Readmission prediction** (MLflow, with the champion registered in UC) scores the discharge as **High**. Drivers: *"No 7-day follow-up booked"*, *"Lives alone"*.
6. **Lakebase** serves the worklist to the app in milliseconds.
7. **The Databricks App:** Claude drafts the plan, the RN approves it, and outreach tasks are written back and readable in UC.
8. **HRRP page:** follow-ups like this one move the ERR 1.19 → 1.14.
9. **Dashboard and Genie:** the trend shows the peak; Genie answers "weekend vs weekday follow-up?" with 17.7% vs 68.6%.

Closing line on the slide: *"The discharge, its prediction and its follow-up finally live together: one platform, one copy of the data."*

**Visual:** a horizontal flow with product logos; a single highlighted patient card moving through the steps.
**Source:** `ARCHITECTURE.md` §1, `evidence/app_api_responses/*`.

---

## Slide 10 · How Databricks solves each challenge (§4b)

**Headline:** *Every reason Cedarbrook couldn't solve this has a direct answer on one platform*

Mirror slide 5. Each challenge → capability → proof:

| Challenge | Databricks capability | Proof in the build |
|---|---|---|
| Siloed data; predictions disconnected from discharge | **Lakeflow** unifies every feed; **one gold layer** joins each discharge to its follow-up, prediction and outcome; **AI/BI dashboard** trends by unit. *Production:* event-triggered runs for near real-time scoring | 9 feeds → one pipeline; bad records caught (6 invalid, 45 duplicates) |
| Complicated infrastructure | **One platform:** Lakeflow + SQL + AI/BI + **Lakebase** + **Databricks Apps**, deployed as code (Asset Bundles), serverless | One bundle; Lakebase tables 9/9 identical to their source |
| PHI governance across copies | **Unity Catalog:** masks, row filters, tags, lineage, audit on one copy | Analysts see `***MASKED***`; scoped user sees 3,424 of 14,475 rows |
| Limited ML | **MLflow + UC model registry**, champion alias, batch scoring into the worklist | Two models compared; champion AUC 0.72 |
| Unstructured notes, AI on PHI | **AI Functions** inside the governed pipeline; **Foundation Model API** with nurse approval | 16,584 notes, 0 errors; plan drafted in 4.4 s |
| Analysts depend on IT | **Genie** on governed gold tables | 5/5 questions answered correctly |

**Line to say:** *"Separate systems became one governed platform, many copies of PHI became one, and the prediction now meets the patient at discharge."*
**Source:** `evidence/pipeline_events.md`, `evidence/lakebase_verification.md`, `99_validate_story.ipynb`.

---

## Slide 11 · Demo: what you're about to see (tell)

**Headline:** *Five stops: from the peak to an approved care plan to the dollars*

1. **Unit Trends:** when did the peak start, and why? (trend over time, then the weekend follow-up drop)
2. **Discharge Worklist:** discharges with their readmission prediction attached (filter: 6 North · High · no follow-up)
3. **Patient detail:** the AI note evidence → Claude drafts a plan → the RN approves → outreach tasks are created
4. **HRRP & What-if:** move the slider to 80% → ERR 1.14, $238K
5. **Ask Genie:** "Weekend vs weekday 7-day follow-up on 6 North?"

**Visual:** five numbered screenshot thumbnails.

---

## Slide 12 · What the demo means (tell back)

**Headline:** *Insight → action → dollars, in one workflow*

* **For the domain owner:** the prediction is on the discharge, so nurses reach high-risk patients while a follow-up can still be booked. There are 54 High-risk patients today, 41 of them without a follow-up.
* **For the executive:** every booked follow-up shows up as ERR and penalty dollars on the same data.
* **For both:** AI drafts and a nurse decides. Every plan and task is audited.

Proof points: plan drafted in **4.4 s** · approval created **2 outreach tasks** · Genie **5/5** correct.
**Source:** `evidence/app_api_responses/11_draft_plan.json`, `12_approve_plan.json`, `16_genie_ask.json`.

---

## Slide 13 · Trust, and the trade-offs we made (Beat 6, §8)

**Headline:** *Built to be trusted, and honest about its limits*

Left, **trust:**
* PHI masked by policy; hospital-scoped row filters; a least-privilege app identity; lineage raw → app.
* Data-quality rules caught every planted bad record.
* The prediction separates risk: the High tier readmits at **45%**, the Low tier at **9%** (test AUC 0.72).
* AI drafts, a nurse approves, everything is audited. It really ran: **10/10 job tasks**, **27/27 checks**.

Right, **three trade-offs:**
* **Synthetic data shaped like Cedarbrook's:** zero PHI risk and reproducible numbers. *Trade-off:* real notes are messier, so AI accuracy is re-validated in the pilot.
* **The simpler model won** (logistic regression 0.7245 vs gradient boosting 0.7137): easier for clinicians to trust. *Trade-off:* less headroom on richer data, so the champion is re-selected each run.
* **A fixed-rule, auditable what-if** on a simplified HRRP method: Finance can reproduce every dollar. *Trade-off:* it assumes the follow-up effect is causal, and it simplifies CMS's 3-year, risk-adjusted, Medicare-only method.

**Source:** `notebooks/executed/99_validate_story.ipynb`, `03_train_readmission_model.ipynb`.

---

## Slide 14 · 90-day pilot and the ask (Beat 7)

**Headline:** *A 90-day pilot on 6 North proves the $240K before scaling hospital-wide*

* **Weeks 0–4, connect:** Epic Clarity / FHIR discharge feeds into the same pipeline; event-triggered runs so predictions reach the worklist at discharge.
* **Weeks 4–8, validate:** RNs review AI note extraction on real notes; recalibrate the model on Cedarbrook outcomes; Quality confirms the ERR method.
* **Weeks 8–12, operate:** 6 North works the worklist daily; weekly KPI review.
* **Then scale:** all CUMC heart failure (~$874K), then COPD and pneumonia, then the other two hospitals.

**Success metrics:**
* Weekend 7-day follow-up from **18% to ≥ 80%**
* **≥ 90%** of high-risk patients contacted within 48h
* HF readmissions trending back toward ~15%

**The ask:**
1. An executive sponsor and data access for the pilot.
2. Funding for weekend follow-up capacity, so weekend discharges leave with an appointment.

Close: *"What would you need to see to move forward?"*

---

## Appendix A · Architecture detail (technical stakeholder)

* **Ingest:** Lakeflow Declarative Pipeline (serverless, SQL); Auto Loader from UC volumes; bronze (9 feeds) → silver (typed, de-duplicated, expectations, PHI masks) → gold (10 tables)
* **AI:** `ai_query(databricks-claude-haiku-4-5, responseFormat => STRUCT<…>)` in an incremental streaming table, so each note is processed once (~24 min for the first pass, ~2 min for reruns)
* **ML:** scikit-learn models in MLflow; champion by test AUC → `ml.readmit_30d_risk@champion`; counterfactual drivers per patient
* **Serving:** Lakebase (Postgres 16) synced tables (snapshot; *production:* Change Data Feed + triggered sync); the app's own schema `app_rcc`, readable in UC via the `rcc_lakebase` catalog
* **App:** Databricks App (FastAPI + JS) running as its own service principal; Foundation Model API (Claude Sonnet); Genie Conversation API
* **Deployment:** one Asset Bundle, a 10-task job; `bundle deploy && bundle run`

**Visual:** the diagram from `ARCHITECTURE.md` §1.

## Appendix B · Evidence the build ran

* Job run `206873801708733`: 10/10 tasks SUCCESS; validation **27/27**
* Lakebase 9/9 synced tables match their source; dashboard: 9 datasets executed, 15 widgets resolved
* All evidence committed as text: `notebooks/executed/`, `evidence/`
* Repo: https://github.com/MelissaPang/readmission-command-center

## Appendix C · AI as a force multiplier

* **Built with Claude Code:**
  1. story numbers as a contract checked by code
  2. data verified locally before deploying
  3. one bundle
  4. run → read the error → fix → rerun
  5. a validation gate
  6. evidence committed at every milestone
* **AI in the product:** Claude Haiku (notes → structured flags with evidence), Claude Sonnet (grounded plans, RN-approved), Genie (tuned from 3/5 to 5/5 with instructions and example SQL)
* Exact prompts: `docs/ai_workflow.md`

## Appendix D · Assumptions and simplifications

* ERR = observed / expected over 12 months, all payers, neutrality modifier 1.0. CMS uses 3 years, risk adjustment and Medicare FFS only.
* The what-if assumes the follow-up effect (29.8% vs 16.4%) is causal.
* The cost of weekend follow-up capacity (~$60K/yr) is illustrative.
* Real-time scoring at discharge is the production design; the prototype scores per job run.
* All patient data is synthetic.

## Appendix E · Supporting detail (use only if asked)

* **The why behind the why:** the weekend follow-up drop lines up with two late-June operational changes, a vacated weekend transitions-pharmacist role (2026-06-19) and fewer Friday clinic slots (2026-06-26) (`silver.staffing_events`).
* **Free-text risk found by AI:** HF patients who live alone, a fact only in the notes, readmit at **33.1% vs 20.6%**. 51/51 unbooked weekend notes told the patient to call or schedule follow-up themselves.
