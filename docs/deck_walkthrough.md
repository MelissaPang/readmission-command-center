# Deck walkthrough: Readmission Command Center for Cedarbrook Health

Slide-by-slide build guide for the presentation deck. It follows `docs/storyline.md` beat by beat. The ready-to-submit, text-only
version of the deck is **`docs/deck.md`**: attach it as `.md`, or export your designed deck as a PDF **with selectable text** (not images of text).

Each slide lists its **headline** (the takeaway, as a sentence), **on-slide text**, **role lines** (who the slide is for, and their number),
the **visual**, the **storyline beat**, and the **source** of every number in this repo.

**Cedarbrook leadership (fictional)**

| Name | Role | Owns |
|---|---|---|
| **Jordan Whitfield** | Chief Financial Officer (executive sponsor) | HRRP penalty $, operating margin |
| **Dr. Elena Vasquez, MD** | VP of Quality & Patient Safety | CMS HF excess readmission ratio (ERR), HF 30-day readmission rate |
| **Priya Raman, RN** | Manager of Transitional Care (domain owner) | 7-day follow-up booked %, high-risk contacted within 48h |
| **Kenji Tanaka** | Chief Data & Analytics Officer (technical stakeholder) | Integration cost, PHI risk, time-to-insight |

**Accountable roles in the room (name them on the slides, not "Finance" or "Quality")**

| Role | Measured on | Today → target |
|---|---|---|
| **Jordan Whitfield, CFO** (executive sponsor) | HRRP penalty $ | $1.62M → $1.38M (–$238K) on one unit; –$874K across CUMC HF |
| **Dr. Elena Vasquez, VP of Quality** | CMS HF excess readmission ratio (ERR), HF 30-day readmission rate | ERR 1.19 → 1.14; 6 North 23.9% → ~15% |
| **Priya Raman, RN, Manager of Transitional Care** (domain owner) | 7-day follow-up booked %, high-risk contacted ≤ 48h % | weekend 18% → ≥ 80%; ≥ 90% contacted |
| **Kenji Tanaka, CDAO** (technical) | Integration cost, PHI risk, time-to-insight | 5 silos → 1 governed copy; ~2 min refresh |

**Deck rules applied:**
* lead with the outcome in named executives' numbers
* show who owns which number
* explain why the customer couldn't solve it before
* value before architecture
* one connected journey
* trade-offs
* an ask per role
* **all text live and extractable**

> All figures come from the prototype run on synthetic Cedarbrook data (job run `601827272748584`, 11/11 tasks, 33/33 checks).
> **[assumption]** items must be stated as such. Real-time scoring at discharge is the **production design**.

**Flow (15 main slides + appendix, 20–30 min)**

| # | Slide | Beat |
|---|---|---|
| 1 | Title | n/a |
| 2 | The outcome, by accountable executive | 0 |
| 3 | The customer and the stakes | 1 |
| 4 | Who owns which number | §2 |
| 5 | A peak nobody saw coming | 2 |
| 6 | Why Cedarbrook couldn't solve it before | 2b |
| 7 | Unified data makes the root cause obvious | 3 |
| 8 | What fixing it is worth, by role | 5 |
| 9 | The solution: unify, predict, visualize, brief and act, measure, learn | 4 |
| 10 | One patient, one platform | §4 |
| 11 | How Databricks solves each challenge | §4b |
| 12 | Demo: what you're about to see | §5 tell |
| 13 | What the demo means, by role | §5 tell back |
| 14 | Trust, quality gates and trade-offs | 6, §8 |
| 15 | 90-day pilot and the ask, by role | 7 |
| A–E | Appendix | supporting |

---

## Slide 1 · Title

**Headline:** *See readmission peaks as they start, and stop them at discharge*

* Subtitle: the Readmission Command Center for Cedarbrook Health, on the Databricks Data Intelligence Platform
* Hero number: **~$240K a year** in avoidable HRRP penalty on one unit, with a path to **~$874K** across CUMC
* Footer: "Prototype on synthetic Cedarbrook data. No real patients."

**Source:** `gold.hrrp_whatif`.

---

## Slide 2 · The outcome, by accountable executive (Beat 0)

**Headline:** *Booking a 7-day follow-up for weekend heart-failure discharges is worth ~$240K a year on one unit*

Three tiles, each labelled with its owner:
* **Jordan Whitfield (CFO), HRRP penalty:** $1.62M → $1.38M (**–$238K / year**); –$874K across CUMC HF
* **Dr. Elena Vasquez (VP of Quality), HF excess readmission ratio:** **1.19 → 1.14**; ~7 readmissions avoided / year
* **Priya Raman (Manager of Transitional Care), weekend 7-day follow-up:** **18% → 80%**; every high-risk discharge briefed

**Role lines (on the slide):**
* **For Jordan (CFO):** "A $1.14M penalty line becomes a $238K decision you can fund this quarter."
* **For Priya (Transitional Care Manager):** "Every discharge comes with a risk score and a 2-sentence briefing: who to call today, and why."

**Visual:** three KPI tiles with the person's name and role in the tile header.
**Source:** `gold.hrrp_whatif`, `gold.hrrp_hospital_penalty`, `gold.followup_gap`.

---

## Slide 3 · The customer and the stakes (Beat 1)

**Headline:** *Under HRRP, one unit's readmissions can cut a hospital's Medicare payments*

* Cedarbrook Health: 3 hospitals. Flagship CUMC has 538 beds.
* CMS HRRP cuts payments on **all** Medicare discharges, by up to **3%**, when 30-day readmissions exceed expected. ERR is publicly reported.
* CUMC penalty **$1.62M**, already **at the 3% cap** ($54M base DRG payments). **Heart failure is the largest line: $1.14M, ERR 1.19.** Across the system: **~$2.08M**.

**Role line:** *For Jordan (CFO) and Dr. Vasquez (VP of Quality):* one penalty, one publicly reported ratio, one shared problem.
**Visual:** penalty bar by condition, with heart failure highlighted.
**Source:** `gold.hrrp_hospital_penalty`, `gold.hrrp_condition_err`.

---

## Slide 4 · Who owns which number (new; executive accountability)

**Headline:** *Four leaders, four numbers, one root cause*

*(Jordan Whitfield, Dr. Elena Vasquez, Priya Raman, Kenji Tanaka)*

| Role | Measured on | Today | Target |
|---|---|---|---|
| **Jordan Whitfield, CFO** | HRRP penalty $ | $1.62M (HF $1.14M) | –$238K on 6 North; –$874K CUMC HF |
| **Dr. Elena Vasquez, VP of Quality** | HF excess readmission ratio; HF 30-day readmission rate | ERR 1.19; 6 North 23.9% | ERR 1.14; ~15% |
| **Priya Raman, Manager of Transitional Care** | 7-day follow-up booked at discharge; high-risk contacted ≤ 48h | weekend 18% (weekday 69%); 41 of 54 high-risk with no follow-up | ≥ 80%; ≥ 90% |
| **Kenji Tanaka, CDAO** | Integration cost, PHI risk, time-to-insight | 5 silos, multiple PHI copies | 1 governed copy; ~2 min refresh |

Bottom line: *"All four numbers move with one action: a 7-day follow-up booked before a high-risk patient goes home."*

**Visual:** a 4-row table or four person cards (name, role, number) connected to one central "7-day follow-up" node.
**Source:** `docs/storyline.md` §2.

---

## Slide 5 · A peak nobody saw coming (Beat 2)

**Headline:** *One unit's heart-failure readmissions jumped 9 points, and it was found out months too late*

* 6 North HF 30-day readmissions: **14.8% → 23.9%** in 20 weeks (+9.1 pts). Every other unit stayed within **±1.5 pts**.
* Found **after the fact**, in quality reports and the penalty estimate.
* Unanswered: **When did it start? Why?**

**Role line:** *For Dr. Vasquez (VP of Quality):* the ratio CMS reports moved before anyone could explain it.
**Visual:** a weekly line chart, 6 North vs all other units, with the peak circled.
**Source:** `gold.unit_period_summary`, dashboard "Weekly HF 30-day readmission rate".

---

## Slide 6 · Why Cedarbrook couldn't solve it before (Beat 2b)

**Headline:** *The answer was in the data, but discharges, predictions and follow-ups never met*

*(Customer scenario: "typical of a multi-hospital system". Confirm in discovery.)*
1. **Siloed data**
   * Discharges, follow-ups, notes and penalty data each live in a separate system.
   * **The readmission prediction is disconnected from the discharge**: calculated weeks later, not in front of the nurse.
   * There's no trend view by unit.
2. **Complicated infrastructure**
   * A warehouse, a lake, BI and an app database, each with its own PHI copy and access rules.
   * Every question is an IT project, and Quality's and Finance's numbers don't match.
3. **Limited ML and AI capability**
   * There's no governed way to put a model in the workflow, use AI on notes, learn from what nurses do, or check that AI answers are right.

**Role line:** *For Kenji (CDAO):* "Every new question meant another copy of PHI and another integration."
**Visual:** three silo icons with broken connectors; a clock on "prediction: weeks later".

---

## Slide 7 · Unified data makes the root cause obvious (Beat 3)

**Headline:** *Unify discharges, predictions and follow-ups, and the root cause appears: no 7-day follow-up, especially on weekends*

1. **When:** readmissions over time by unit pinpoint when 6 North's peak started. *(Dr. Vasquez, VP of Quality)*
2. **Why:** weekend HF discharges with a booked 7-day follow-up fell to **18%**, vs **69%** on weekdays. *(Priya, Transitional Care)*
3. **So what:** no 7-day follow-up → **29.8%** readmit, vs **16.4%** with one. *(Dr. Vasquez and Jordan)*
4. **Who, right now:** every discharge carries its prediction and an AI nurse briefing, so high-risk patients are caught *before they go home*.

Callout: *"Not a clinical mystery: a missing follow-up appointment, a process gap the team can fix."*
**Visual:** left, the trend with the peak marked; right, a weekday vs weekend bar, before vs during the peak.
**Source:** `gold.unit_weekly_readmissions`, `gold.followup_gap`, `gold.readmission_risk_factors`.
**Speaker note:** the operational "why behind the why" and the "lives alone" finding (33.1% vs 20.6%) are in Appendix E.

---

## Slide 8 · What fixing it is worth, by role (Beat 5, before the solution)

**Headline:** *Every 10 points of weekend follow-up on 6 North is worth ~$120K in avoided penalty*

What-if (fixed-rule, trailing 12 months, CUMC; reproducible by Jordan's finance team):
* 70% booked → 3.9 avoided · ERR 1.16 · **$119K**
* **80% booked → 6.5 avoided · ERR 1.14 · $238K** ← target
* 90% booked → 9.1 avoided · ERR 1.12 · $358K
* 100% booked → 11.8 avoided · ERR 1.10 · $478K

Scaled: CUMC weekend HF (all units) **~$412K** · all CUMC HF **~$874K**.

**Role lines (on the slide):**
* **For Jordan (CFO):** "–$238K on 6 North; ~4× payback on ~$60K/yr of weekend follow-up capacity **[assumption]**; –$874K at hospital scale."
* **For Dr. Vasquez (VP of Quality):** "HF ERR 1.19 → 1.14, toward the 1.00 benchmark."
* **For Priya (Manager of Transitional Care):** "54 high-risk patients in the window today; 41 have no follow-up. Booking those is how weekend follow-up gets from 18% to 80%."

**Speaker note:** savings rise unevenly because CUMC is above the 3% cap (uncapped $1.68M), so the first ~$60K is absorbed by the cap.
**Visual:** a what-if slider screenshot plus a small bar of the three scopes.
**Source:** `gold.hrrp_whatif`, `gold.discharge_worklist`, `evidence/app_api_responses/08_whatif_6n_weekend.json`.

---

## Slide 9 · The solution (Beat 4)

**Headline:** *One platform that sees the peak, explains it, acts on every discharge, and learns from every nurse*

Six steps:
1. **Unify:** discharges, follow-ups, notes and penalty data in one governed place.
2. **Predict:** a 30-day risk for every discharge, attached to the discharge record.
3. **Visualize:** readmissions over time by unit.
4. **Brief and act:**
   * an AI nurse briefing per patient
   * an AI-drafted plan the RN approves
   * outreach tasks created automatically
5. **Measure:** ERR and penalty dollars per booked follow-up, plus Genie for any question.
6. **Learn:** every RN edit or rejection becomes a weak label for retraining (the closed loop).

**Role lines:**
* *Transitional Care:* steps 4 and 6
* *VP of Quality:* steps 3 and 5
* *CFO:* step 5
* *CIO:* step 1, and the fact that it's one platform

**Visual:** six-step chevron with a loop arrow from "Learn" back to "Predict".

---

## Slide 10 · One patient, one platform (the integrated journey)

**Headline:** *A Friday discharge, from raw record to an RN-approved plan, and back into the model*

1. **Raw:** the discharge record, the appointment (none booked) and the note (*"patient to call the clinic on Monday… lives alone"*) land as files.
2. **Lakeflow:** incremental ingest, data-quality rules, gold tables joining discharge, follow-up, outcome and unit trend.
3. **Unity Catalog:** one governed copy. Name and MRN masked for analysts; the **note quote visible to care-transitions only**; lineage.
4. **AI Functions:** *lives alone*, *patient to call*, plus an evidence quote.
5. **Prediction** (MLflow, UC champion): **High**. Drivers *no 7-day follow-up (+16.8 pts)*, *lives alone (+13.5 pts)*.
6. **AI nurse briefing:** *"…45% readmission risk driven by no 7-day follow-up (16.8 pts)… Immediately book the 7-day follow-up and initiate home health referral."*
7. **Lakebase** serves the worklist; **the App:** Claude drafts, the **RN edits** (95% similar, +107 chars) and approves, and tasks are written back.
8. **Closed loop:** the edit becomes a `nurse_edited` weak label, and the next training run logs it.
9. **HRRP page:** ERR 1.19 → 1.14. **Genie:** "weekend vs weekday follow-up?" → 17.7% vs 68.6%, LLM-judge verified.

Closing line: *"The discharge, its prediction and its follow-up finally live together, and every nurse decision teaches the system."*
**Visual:** a horizontal flow with product logos; one patient card moving through, and a return arrow from the app to the model.

---

## Slide 11 · How Databricks solves each challenge (§4b)

**Headline:** *Every reason Cedarbrook couldn't solve this has a direct answer on one platform*

| Challenge | Databricks capability | Proof |
|---|---|---|
| Siloed data; prediction disconnected | **Lakeflow** + one gold layer; **AI/BI** trend; *production:* event-triggered scoring | 9 feeds → one pipeline; 6 invalid + 45 duplicate records caught |
| Complicated infrastructure | One platform: Lakeflow, SQL, AI/BI, **Lakebase**, **Apps**; Asset Bundles; serverless | One bundle; Lakebase 9/9 identical to source |
| PHI governance | **Unity Catalog:** PHI masks, **role-based mask on note quotes**, row filters, lineage, audit | `***MASKED***`, `[restricted: care-transitions only]`, 3,424 of 14,475 rows |
| Limited ML | **MLflow + UC registry**, champion alias, scoring into the worklist | AUC 0.72; High 45% vs Low 9% observed |
| AI on notes | **AI Functions** (extraction + briefings), **Foundation Model API** with RN approval | 16,584 notes, 0 errors; 705/705 briefings; plan in 4.4 s |
| Can't learn from the frontline | **Lakebase write-back readable in UC** → weak labels → retraining signals | 3 reviewed plans, 33% edit rate logged in MLflow |
| Can't trust AI answers | **Genie** plus an **LLM judge** vs SQL reference answers, every run | 5/5 PASS, history in `gold.genie_eval_judgements` |

**Role line:** *For Kenji (CDAO):* "Separate systems became one governed platform, and the quality gates run on every refresh."
**Source:** `evidence/pipeline_events.md`, `evidence/lakebase_verification.md`, `99_validate_story.ipynb`.

---

## Slide 12 · Demo: what you're about to see (tell)

**Headline:** *Five stops: from the peak, to a briefed patient, to an approved plan, to the dollars*

1. **Unit Trends:** when did the peak start, and why? *(Dr. Vasquez, VP of Quality)*
2. **Worklist:** each discharge with its prediction and an AI nurse briefing *(Priya, Transitional Care)*
3. **Patient:** note evidence → Claude drafts → the RN **edits** and approves → tasks created, edit captured *(Priya, Transitional Care)*
4. **HRRP & What-if:** slider to 80% → ERR 1.14, $238K *(Jordan and Dr. Vasquez)*
5. **Ask Genie:** "weekend vs weekday follow-up on 6 North?", judged correct every run *(Kenji, CDAO)*

**Visual:** five numbered screenshot thumbnails, each tagged with its role.

---

## Slide 13 · What the demo means, by role (tell back)

**Headline:** *Insight → action → dollars, in one workflow that learns*

* **For Jordan (CFO):** each booked follow-up is visible as penalty dollars, using a method your team can audit.
* **For Dr. Vasquez (VP of Quality):** you see the next peak the week it starts, and track the ERR moving.
* **For Priya (Manager of Transitional Care):** a briefed worklist (41 high-risk patients without a follow-up); plans drafted in 4.4 s for your approval; your edits improve the next draft.
* **For Kenji (CDAO):** one governed copy; AI quality is gated on every run.

**Source:** `evidence/app_api_responses/09_*.json`, `11_*.json`, `12_*.json`, `16_*.json`.

---

## Slide 14 · Trust, quality gates and trade-offs (Beat 6, §8)

**Headline:** *Built to be trusted, measured every run, and honest about its limits*

Left, **trust and quality gates:**
* PHI masked; **AI note quotes masked by role**; hospital row filters; least-privilege app identity; lineage and audit.
* The prediction separates risk (High 45% vs Low 9%; AUC 0.72).
* **Genie checked by an LLM judge** against SQL reference answers: 5/5 every run.
* Briefings grounded in each patient's own row; AI drafts, the RN decides.
* It really ran: **11/11 job tasks, 33/33 checks**.

Right, **three trade-offs:**
* **Synthetic data:** zero PHI risk, reproducible. *Trade-off:* real notes are messier, so re-validate in the pilot.
* **The simpler model won** (0.7245 vs 0.7137): clinician-explainable. *Trade-off:* less headroom, so the champion is re-selected each run, with RN feedback accumulating.
* **A fixed-rule what-if** on a simplified HRRP method: Jordan's finance team can reproduce it. *Trade-off:* it assumes causality and simplifies CMS's 3-year, risk-adjusted method.

Limits stated: the feedback loop has only 3 reviewed plans so far; real-time scoring is the production design.

---

## Slide 15 · 90-day pilot and the ask, by role (Beat 7)

**Headline:** *A 90-day pilot on 6 North proves the $240K before scaling hospital-wide*

* **Weeks 0–4:** Epic Clarity / FHIR feeds; event-triggered scoring at discharge.
* **Weeks 4–8:** RN validation of AI on real notes; model recalibration; Quality confirms the ERR method.
* **Weeks 8–12:** 6 North works the briefed worklist daily; weekly KPI review.
* **Then:** all CUMC HF (~$874K) → COPD and pneumonia → the other two hospitals.

**Success and ask, by owner:**

| Role | Pilot success metric | Ask |
|---|---|---|
| **Jordan Whitfield, CFO** | penalty trajectory toward –$238K | Fund weekend follow-up capacity |
| **Dr. Elena Vasquez, VP of Quality** | 6 North HF readmissions toward ~15%; the ERR trend | Executive sponsor; chair the weekly KPI review |
| **Priya Raman, Manager of Transitional Care** | weekend follow-up ≥ 80%; ≥ 90% of high-risk contacted ≤ 48h | A 6 North nurse champion |
| **Kenji Tanaka, CDAO** | feeds connected; quality gates green | Data access and an Epic integration contact |

Close: *"What would you need to see to move forward?"*

---

## Appendix A · Architecture detail

* **Ingest:** Lakeflow Declarative Pipeline (serverless, SQL); Auto Loader → bronze (9 feeds) → silver (expectations, PHI masks) → gold (10 tables)
* **AI:**
  * `ai_query` (Claude Haiku, structured output) in an incremental streaming table: ~24 min for the first pass, ~2 min for reruns
  * nurse briefings via `ai_query` over the worklist
* **ML:** MLflow; champion by test AUC → `ml.readmit_30d_risk@champion`; counterfactual drivers; `ml.retraining_signals` from RN feedback
* **Serving:** Lakebase (Postgres 16) synced tables; the app's own schema `app_rcc`, read back in UC via `rcc_lakebase`
* **App:** Databricks App (FastAPI + JS) as its own service principal; Foundation Model API (Claude Sonnet); Genie Conversation API
* **Quality:** `99_validate_story` (33 checks) and the Genie LLM judge (`gold.genie_eval_judgements`), on every run
* **Deployment:** one Asset Bundle with an 11-task job

## Appendix B · Evidence the build ran
* Job run `601827272748584`: 11/11 SUCCESS; 33/33 checks; Lakebase 9/9 match; dashboard 9 datasets + 15 widgets verified
* Evidence as text: `notebooks/executed/`, `evidence/`. Repo: https://github.com/MelissaPang/readmission-command-center

## Appendix C · AI as a force multiplier
* **Built with Claude Code:** the story as a code-checked contract; local verification first; one bundle; run → fix → rerun; a validation gate; evidence at every milestone; review feedback re-verified in a fresh run.
* **In the product:**
  * Claude Haiku: note extraction, nurse briefings
  * Claude Sonnet: plans for RN approval, judging Genie
  * Genie
  * the RN-edit feedback loop
* Prompts: `docs/ai_workflow.md`.

## Appendix D · Assumptions and simplifications
* ERR = observed / expected, 12 months, all payers, neutrality modifier 1.0. CMS uses 3 years, risk adjustment and Medicare FFS only.
* The what-if assumes the follow-up effect is causal. The ~$60K/yr weekend follow-up capacity is illustrative.
* Real-time scoring at discharge is the production design. The feedback loop has 3 reviewed plans so far.
* All patient data is synthetic.

## Appendix E · Supporting detail (only if asked)
* **The why behind the why:** the weekend follow-up drop lines up with late-June changes: a vacated weekend transitions-pharmacist role (2026-06-19) and fewer Friday clinic slots (2026-06-26).
* **Free-text risk:** HF patients who live alone readmit at **33.1% vs 20.6%**. 51/51 unbooked weekend notes told the patient to call or schedule follow-up themselves.
