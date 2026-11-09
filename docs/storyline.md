# Storyline: Readmission Command Center for Cedarbrook Health

The narrative spine for the deck (`docs/deck.md`, built from `docs/deck_walkthrough.md`), the live demo and the role-play
(`docs/talk_track.md`). If a slide or a sentence doesn't serve one of the beats below, cut it.

All numbers come from the prototype run on synthetic Cedarbrook data (job run `601827272748584`, 11/11 tasks, 33/33 checks; sources in
`evidence/`). Items marked **[assumption]** must be stated as such. Real-time scoring at discharge is the **production design**; the prototype scores per job run.

---

## 1. The story in one sentence

> **Readmission spikes cost hospitals Medicare penalties, and they are usually discovered months too late, because discharge records,
> readmission predictions and follow-up data live in separate systems. By unifying them on Databricks, Cedarbrook can see when a
> readmission peak starts, see the root cause (patients leaving without a 7-day follow-up, especially on weekends), and act on
> each high-risk patient at discharge, worth about $240K a year on one unit.**

The three-sentence version (the elevator pitch, ~30 seconds):
1. *Problem:* Heart-failure readmissions on one unit jumped from 14.8% to 23.9%, and nobody noticed until the HRRP penalty ($1.62M, with heart failure the biggest line) showed it.
2. *Insight:* With discharge records, readmission predictions and follow-ups unified and trended over time, the peak and its cause are obvious: patients going home without a 7-day follow-up, especially on weekends (18% booked vs 69% on weekdays). Those patients readmit at nearly twice the rate.
3. *Outcome:* Brief nurses on every high-risk discharge and book the follow-up. Getting weekend follow-up to 80% avoids ~7 readmissions, cuts the HF ERR from 1.19 to 1.14 and saves ~$240K a year on one unit, ~$874K across the hospital. And the system learns from every plan a nurse edits.

---

## 2. Executive accountability map: who owns which number

**Cedarbrook leadership (fictional)**

| Name | Role | Owns |
|---|---|---|
| **Jordan Whitfield** | Chief Financial Officer (executive sponsor) | HRRP penalty $, operating margin |
| **Dr. Elena Vasquez, MD** | VP of Quality & Patient Safety | CMS HF excess readmission ratio (ERR), HF 30-day readmission rate |
| **Priya Raman, RN** | Manager of Transitional Care (domain owner) | 7-day follow-up booked %, high-risk contacted within 48h |
| **Kenji Tanaka** | Chief Data & Analytics Officer (technical stakeholder) | Integration cost, PHI risk, time-to-insight |

Every value claim in the deck is tied to a **named role** and **the number that role is measured on**. This is the map to use when
talking under executive pressure: lead with *their* number, not the platform.

| Role (who) | What they are measured on | Today (prototype) | Target / what the fix delivers | What in the solution moves it | Line that lands |
|---|---|---|---|---|---|
| **Jordan Whitfield, CFO** (executive sponsor, funds the decision) | **HRRP penalty $** (a cut to all Medicare base DRG payments), operating margin | CUMC **$1.62M** (at the 3% cap of $54M base payments); system **$2.08M**; HF line **$1.14M** | **–$238K/yr** at 80% weekend follow-up on 6 North; **–$874K/yr** across CUMC HF; ~**4× payback** on ~$60K/yr of weekend follow-up capacity **[assumption]** | HRRP & What-if page; fixed-rule, auditable method | *"This turns a $1.14M penalty line into a $238K decision you can fund this quarter, with the method on one page your team can audit."* |
| **Dr. Elena Vasquez, MD, VP of Quality & Patient Safety** | **CMS HF excess readmission ratio (ERR)** (publicly reported, drives HRRP), **HF 30-day readmission rate** | HF ERR **1.19**; 6 North HF readmission **23.9%** (was 14.8%) | ERR **1.19 → 1.14** (toward the 1.00 benchmark); 6 North back toward **~15%** | Unit trend over time (see the peak when it starts), root cause, weekly KPI tracking | *"You see the peak the week it starts, not when CMS reports it, and you can show the ERR moving."* |
| **Priya Raman, RN, Manager of Transitional Care** (domain owner) | **7-day follow-up booked at discharge %**, **high-risk patients contacted within 48h %**, nurse time per patient | Weekend 7-day follow-up **18%** (vs 69% weekdays); **54** high-risk patients in the window, **41** with no follow-up | Weekend follow-up **≥ 80%**; **≥ 90%** of high-risk patients contacted within 48h | Worklist with a readmission prediction and an **AI nurse briefing** per patient; AI-drafted plan the RN approves; outreach tasks created automatically | *"Your team starts each shift with a short briefing on who to call and why, and the care plan is already drafted for you to approve."* |
| **Kenji Tanaka, Chief Data & Analytics Officer** (technical stakeholder) | Integration cost, PHI risk, time-to-insight, platform sprawl | 5 siloed sources, multiple PHI copies, monthly manual analysis **[scenario]** | One governed copy; incremental refresh in **~2 min**; AI cost scales with *new* notes | Lakeflow + Unity Catalog + Lakebase + Apps in one bundle; role-based masks; LLM-judge quality gates | *"One governed copy of the data from raw extract to app, deployed as code, with quality checks that run every time."* |

**Reading the room:** answer the person who asked with *their* number, then bridge in one sentence to the person who funds it.
* Jordan (CFO) asks about AI risk → "Every AI output is reviewed by an RN and audited; your exposure is the penalty, not the AI."
* Priya (Transitional Care) asks about workload → "It removes drafting time; Jordan (CFO) sees each booked follow-up as dollars."

---

## 3. Narrative arc (Situation → Complication → Insight → Value → Resolution → Proof → Ask)

The arc **opens with the outcome in the CFO's and Quality's numbers**, then earns it. Architecture appears only after the value is established.

### Beat 0: Outcome first (the hook, first 60 seconds)
* **Message:** *"About $240K a year in avoidable penalty on one unit, and the fix is operational, not clinical."*
* Name the owners as you say the numbers:
  * **for Jordan Whitfield, CFO:** ~$240K a year, ~$874K across CUMC
  * **for Dr. Elena Vasquez, VP of Quality:** HF ERR 1.19 → 1.14
  * **for Priya Raman, Manager of Transitional Care:** weekend 7-day follow-up from 18% to 80%
* Frame what's coming: what we found, a live demo of how nurses and finance use it, how it's built, and what it takes to go live.

### Beat 1: Situation (the customer and the stakes)
* Cedarbrook Health: 3 hospitals. Flagship CUMC has 538 beds.
* CMS **HRRP** cuts payments on *all* Medicare discharges, by up to 3%, when readmissions exceed expected. A unit-level problem becomes a hospital-wide payment cut, and a publicly reported quality metric.
* CUMC's estimated penalty is **$1.62M**, already at the 3% cap. Heart failure is the largest line at **$1.14M**, **ERR 1.19**. This is Jordan's (CFO) and Dr. Vasquez's (VP of Quality) shared problem.

### Beat 2: Complication (a peak nobody saw coming, and nobody could explain)
* One unit's HF readmissions went **14.8% → 23.9%** in 20 weeks. **Every other unit stayed within ~1.5 pts.**
* Cedarbrook found out the way most hospitals do: **after the fact**, from quality reports and the penalty estimate.
* Nobody could answer: **when did it start, and why?**

### Beat 2b: Why Cedarbrook couldn't solve it before (the technical complication)
*Scenario: Cedarbrook's current state, typical of a multi-hospital system. Confirm in discovery.*

1. **Siloed data. Discharges, predictions and follow-ups never meet.**
   * Discharge records sit in the EHR reporting database; follow-up appointments in scheduling; key risk details only in notes; the penalty in Finance spreadsheets.
   * **The readmission prediction is disconnected from the discharge.** If a score exists, it's calculated weeks later in a batch report, not in front of the nurse at discharge.
   * There's no trend view of readmissions by unit, so peaks aren't visible as they start.
2. **Complicated infrastructure.** A warehouse, a lake, a BI tool and an app database, each with its own PHI copy and access rules. Every question is an IT project, and Quality's and Finance's numbers don't match.
3. **Limited ML and AI capability.** There's no way to deploy and govern a model in the workflow, no safe way to use AI on clinical notes, no way to learn from what nurses do, and no way to check that AI answers are right.

> Line: *"The answer was in Cedarbrook's data all along, but discharges, predictions and follow-ups lived in different systems, so nobody could see the peak start or explain it."*

### Beat 3: The insight (unified data makes the root cause obvious)
Once discharge records, readmission predictions and follow-up data are **unified and trended over time**:
* **When:** readmissions over time by unit show exactly when 6 North's peak started, and that it's confined to one unit. *(Dr. Vasquez, VP of Quality)*
* **Why:** weekend HF discharges with a booked 7-day follow-up fell to **18%**, vs **69%** on weekdays. *(Priya, Transitional Care)*
* **So what:** no 7-day follow-up means **29.8%** readmit, vs **16.4%** with one. *(Dr. Vasquez and Jordan)*
* **Who, right now:** every discharge carries its readmission prediction and a plain-English nurse briefing, so high-risk patients are caught *before they go home*.
* *The "aha":* not a clinical mystery, but a **missing follow-up appointment**: a fixable process gap.

*Supporting detail, only if asked:*
* The weekend drop lines up with two late-June operational changes (the weekend transitions-pharmacist role, and Friday clinic slots).
* AI shows patients who live alone readmit at 33.1% vs 20.6%.

### Beat 5: Value, by accountable executive (deliver this *before* the solution walkthrough)
* **Jordan Whitfield (CFO):**
  * 80% weekend follow-up on 6 North → ~6.5 avoided readmissions → **$238K** less penalty ($1.62M → $1.38M)
  * every 10 points of follow-up ≈ $120K
  * all CUMC HF ≈ **$874K**
  * payback ≈ **4×** on ~$60K/yr of weekend follow-up capacity **[assumption]**
* **Dr. Elena Vasquez (VP of Quality):**
  * HF ERR **1.19 → 1.14**
  * 6 North HF readmissions trend back toward ~15%
  * the trend view shows the next peak the week it starts
* **Priya Raman (Manager of Transitional Care):**
  * **54** high-risk patients today, **41** without a follow-up, each with a 2-sentence briefing
  * plans drafted in **~4 s** for RN approval
  * outreach tasks created on approval
  * target weekend follow-up **≥ 80%**, high-risk contact within 48h **≥ 90%**
* **Kenji Tanaka (CDAO):** one governed copy, ~2 min incremental refresh, quality gates (validation plus an LLM judge) on every run.

### Beat 4: Resolution (one connected journey)
1. **Unify** discharge records, follow-ups, notes and penalty data in one governed place.
2. **Predict** a 30-day readmission risk for every discharge, attached to the discharge record.
3. **Visualize** readmissions over time by unit, so peaks are seen when they start.
4. **Brief and act:**
   * an AI nurse briefing per patient
   * an AI-drafted transition plan the RN approves
   * outreach tasks created automatically
5. **Measure:** what each booked follow-up is worth in ERR and penalty dollars, with Genie for any other question.
6. **Learn:** every RN edit or rejection is captured as a weak label for the next model and prompt iteration (the closed loop).

Then: the one-thread story (§4), and challenge → capability (§4b).

### Beat 6: Proof and trust
* **It really ran:** 11/11 job tasks, 33/33 checks.
* **Governance:**
  * PHI masked for analysts
  * hospital-scoped row filters
  * a **role-based mask on AI-extracted note quotes** (care-transitions only)
  * a least-privilege app identity, lineage and audit
* **Model:** AUC 0.72; High-risk patients readmit at 45% vs 9% for Low.
* **AI quality gates:**
  * Genie graded by an **LLM judge against SQL reference answers** on every run (5/5 PASS)
  * briefings grounded only in the patient's own row
  * AI note extraction scored against ground truth
* **Honest limits:**
  * synthetic data, so AI accuracy will be re-validated on real notes
  * the what-if assumes the follow-up effect is causal
  * the HRRP method is simplified
  * the feedback loop has only 3 reviewed plans so far

### Beat 7: The ask (time to value)
* A **90-day pilot on 6 North:**
  * connect Epic feeds and event-triggered scoring (weeks 0–4)
  * validate the AI and the model with RNs and Quality (weeks 4–8)
  * nurses work the briefed worklist daily (weeks 8–12)
* **Success, by owner:**
  * Jordan (CFO): penalty trajectory
  * Dr. Vasquez (VP of Quality): 6 North HF readmissions toward ~15% and the ERR trend
  * Priya (Transitional Care): weekend follow-up 18% → ≥ 80%, ≥ 90% of high-risk patients contacted within 48h
* **Ask:**
  * from **Jordan (CFO)**, funding for weekend follow-up capacity
  * from **Dr. Vasquez (VP of Quality)**, executive sponsorship and the pilot KPI review
  * from **Priya (Transitional Care)**, a 6 North nurse champion
* Close: *"What would you need to see to move forward?"*

---

## 4. The one-thread story: proving the layers are connected

Follow **one weekend heart-failure patient** through the platform (addresses the "layers present but not connected" failure mode):

1. **Raw data:** Friday 4 pm discharge from 6 North. The discharge record, the appointment extract (no follow-up) and the note (*"patient to call the clinic on Monday… lives alone"*) land as files.
2. **Lakeflow** unifies them: incremental ingest, de-duplication, data-quality rules, then gold tables that join each discharge to its follow-up status, its outcome and the unit trend.
3. **Unity Catalog** governs one copy:
   * name and MRN masked for analysts
   * the verbatim note quote visible to care-transitions only
   * hospital-scoped access, and lineage back to the raw file
4. **AI Functions** read the note and add *lives alone* and *patient to call*, with an evidence quote.
5. **Readmission prediction** (MLflow; champion in UC) scores the discharge **High**. Drivers: *"No 7-day follow-up booked (+16.8 pts)"*, *"Lives alone (+13.5 pts)"*.
6. **AI nurse briefing** turns those drivers into two sentences: *"…45% readmission risk driven by no 7-day follow-up (16.8 pts)… Immediately book the 7-day follow-up and initiate home health referral."*
7. **Lakebase** serves the briefed worklist to the app in milliseconds.
8. **The Databricks App:**
   * Claude drafts the plan
   * the **RN edits and approves it**: the app records 95% similarity, +107 characters, "Within 48 hours" changed
   * outreach tasks are written back
9. **The closed loop:** the edit becomes a `nurse_edited` weak label in `gold.plan_feedback`, and the next training run logs it (3 reviewed, 33% edit rate).
10. **HRRP page:** follow-ups like this one move the ERR 1.19 → 1.14 and the penalty down ~$240K.
11. **Dashboard and Genie:** the trend shows the peak. Genie answers "weekend vs weekday follow-up?" with 17.7% vs 68.6%, and an LLM judge confirms the answer against SQL every run.

> Closing line: *"The discharge, its prediction and its follow-up finally live together, and every nurse decision teaches the system: one platform, one copy of the data."*

---

## 4b. How Databricks solves each challenge (challenge → capability → proof)

| Challenge | Databricks capability | Proof in this build |
|---|---|---|
| **Siloed data; predictions disconnected from discharge** | **Lakeflow** unifies every feed; **one gold layer** joins each discharge to its follow-up, prediction and outcome; the **AI/BI dashboard** trends by unit. *Production:* event-triggered runs for near real-time scoring | 9 feeds → one pipeline; bad records caught (6 invalid, 45 duplicates) |
| **Complicated infrastructure** | **One platform:** Lakeflow + SQL + AI/BI + **Lakebase** + **Databricks Apps**, deployed as code (Asset Bundles), serverless | One bundle; Lakebase tables 9/9 identical to their source |
| **PHI governance across copies** | **Unity Catalog:** PHI masks, **role-based mask on AI evidence quotes**, row filters, tags, lineage, audit on one copy | Analysts see `***MASKED***` and `[restricted: care-transitions only]`; scoped user sees 3,424 of 14,475 rows |
| **Limited ML** | **MLflow + UC model registry**, champion alias, batch scoring into the worklist, **retraining signals from RN feedback** | Champion AUC 0.72; training logs 3 reviewed plans / 33% edit rate |
| **Unstructured notes, AI on PHI** | **AI Functions** inside the governed pipeline (note extraction, **nurse briefings**); **Foundation Model API** with RN approval | 16,584 notes, 0 errors; 705/705 briefings; plan drafted in 4.4 s |
| **No way to learn from frontline decisions** | **Lakebase write-back readable in UC** → weak labels → `ml.retraining_signals` | RN edit → `nurse_edited` label → MLflow metrics |
| **Analysts depend on IT; can't trust AI answers** | **Genie** on governed gold tables, plus an **LLM judge** against SQL reference answers every run | 5/5 PASS, appended to `gold.genie_eval_judgements` |

> Line: *"Separate systems became one governed platform, many copies of PHI became one, the prediction now meets the patient at discharge, and every nurse decision makes it better."*

---

## 5. Demo storyline (tell → show → tell)

| Stop | Tell | Show | Tell back (and whose number it moves) |
|---|---|---|---|
| 1. Unit Trends | "When did the peak start, and why?" | Readmissions over time by unit; the 6 North peak; the weekend follow-up drop | "Peak and root cause on one screen." *Dr. Vasquez: see the next peak the week it starts* |
| 2. Worklist | "Who to act on today" | Filter 6 North · High · no follow-up; the **AI nurse briefing** per patient | "A briefing, not a scored table." *Priya: 41 high-risk patients without follow-up, each with the reason* |
| 3. Patient → plan → **edit** → approve | "From insight to action, and the system learns" | The evidence quote → Claude drafts → the RN **edits** and approves → tasks are created, edit stats recorded | "AI drafts, the nurse decides, and every edit becomes a learning signal." *Priya: drafting time removed* |
| 4. HRRP & What-if | "The same action in Jordan's (CFO) language" | Slider 55% → 80%: ~6.5 avoided, ERR 1.14, $238K; scope → $874K | *Jordan: $238K; Dr. Vasquez: ERR 1.14* |
| 5. Ask Genie | "Questions nobody built a dashboard for" | Weekend vs weekday follow-up → 17.7% vs 68.6% + SQL; mention the LLM judge (5/5 every run) | *Kenji: self-service on governed data, quality-gated* |

~8–9 minutes. Close with: *"Insight → action → dollars, and it learns from every nurse."*

---

## 6. Proof points (have these ready, all verifiable in the repo)

| Claim | Number | Owner | Evidence |
|---|---|---|---|
| Unit peak, others stable | 14.8% → 23.9%; others ≤ 1.1 pts | Dr. Vasquez | `evidence/query_results.md`, dashboard trend |
| Weekend follow-up gap | 18% (11/62) vs 69% (94/137) | Priya | `gold.followup_gap` |
| Follow-up effect | 29.8% vs 16.4% | Dr. Vasquez | `gold.readmission_risk_factors` |
| Penalty | $1.62M (cap), HF $1.14M, ERR 1.19 | Jordan | `gold.hrrp_hospital_penalty` |
| What-if | 80% → 6.52 avoided, ERR 1.14, $238,438; CUMC HF ≈ $874K | Jordan | `gold.hrrp_whatif` |
| Worklist + briefings | 54 High-risk, 41 without follow-up; 705/705 briefings | Priya | `gold.discharge_worklist`, `04_batch_score.ipynb` |
| AI plan + RN edit | 4.4 s draft; edit 95% similar, +107 chars | Priya | `evidence/app_api_responses/11_*.json`, `12_*.json` |
| Closed loop | 3 reviewed, 1 nurse_edited, 33% edit rate logged in training | Kenji / Dr. Vasquez | `08_feedback_loop.ipynb`, `ml.model_metrics` |
| Genie quality | 5/5 PASS by the LLM judge, every run | Kenji | `06_genie_space.ipynb`, `gold.genie_eval_judgements` |
| Model | AUC 0.7245; High 45% / Low 9% observed | Dr. Vasquez | `03_*.ipynb`, `04_*.ipynb` |
| Governance | PHI masked; evidence quotes role-masked; row filter 3,424 / 14,475 | Kenji | `99_validate_story.ipynb` |
| It really ran | 11/11 tasks; 33/33 checks; Lakebase 9/9 | Kenji | `evidence/job_run_summary.md`, `evidence/lakebase_verification.md` |

---

## 7. Anticipated pushback, built into the story

* **Jordan (CFO): "Is the $240K real?"** (Beat 5) Fixed-rule and reproducible by Finance; state the causal assumption; the pilot proves it.
* **Jordan (CFO): "Why the jump between 70% and 80%?"** CUMC is above the 3% cap, so the first ~$60K of improvement is absorbed by the cap.
* **Dr. Vasquez (VP of Quality): "Will this move our public ERR, and when?"** ERR is calculated on a rolling performance period, so avoided readmissions roll in. Track 6 North's rate and the ERR trend weekly in the pilot.
* **Priya (Transitional Care): "Is AI telling my nurses what to do?"** (Beat 6) No. AI drafts and briefs, the RN decides; edits are captured to improve it; every step is audited.
* **Kenji (CDAO): "What about PHI?"** (§4b) Masks, role-based masking of note quotes, row filters, a least-privilege app identity, lineage.
* **Kenji (CDAO): "Will it integrate with Epic? Another platform?"** (Beat 7, §4b) The same pipeline maps the feeds. It *replaces* copies rather than adding one.
* **Kenji (CDAO): "How do you know the AI is right?"** An LLM judge against SQL reference answers every run, extraction scored against ground truth, briefings grounded in the row.
* **"What caused the weekend gap?"** (Q&A) Two late-June operational changes. The fix is restoring weekend follow-up capacity.

Full answers: `docs/talk_track.md` §8.

---

## 8. Decisions and trade-offs (the three to tell)

* **Synthetic data shaped like Cedarbrook's**: zero PHI risk, reproducible numbers. *Trade-off:* real notes are messier, so extraction is re-validated in the pilot.
* **The simpler model won** (logistic regression 0.7245 vs gradient boosting 0.7137): easier for clinicians to trust. *Trade-off:* less headroom, so the champion is re-selected each run, and RN feedback is accumulated for retraining.
* **A fixed-rule, auditable what-if** on a simplified HRRP method: Jordan's finance team can reproduce every dollar. *Trade-off:* it assumes causality, and it simplifies CMS's 3-year, risk-adjusted, Medicare-only method.

---

## 9. AI as a force multiplier

* **Built with Claude Code** as a teammate:
  1. story numbers as a contract checked by code
  2. data verified locally before deploying
  3. one bundle
  4. run → read the error → fix → rerun
  5. a validation gate
  6. evidence committed at each milestone
  7. review feedback implemented and re-verified in a fresh run
* **AI inside the product:**
  * Claude Haiku turns notes into structured flags and writes nurse briefings
  * Claude Sonnet drafts grounded care plans for RN approval, and judges Genie's answers
  * Genie for plain-English analytics
  * an RN-edit feedback loop that turns human decisions into training signals
* Details and exact prompts: `docs/ai_workflow.md`.

---

## 10. Requirements coverage check

**Deck**
* [x] Leads with the business outcome (Beat 0), stated in **named executives' numbers**
* [x] Quantifies impact in the buyer's KPIs, **each tied to its accountable role** (§2 accountability map)
* [x] Frames value for the executive sponsor (**Jordan Whitfield, CFO**) *and* the domain owner (**Priya Raman, Manager of Transitional Care**) explicitly, plus **Dr. Elena Vasquez (VP of Quality)** and **Kenji Tanaka (CDAO)**
* [x] The deck's text is extractable: `docs/deck.md` is the deck as plain text, with a "For Jordan (CFO) / For Dr. Vasquez (VP of Quality) / For Priya (Transitional Care Manager)" line on every value slide
* [x] Architecture after value

**Role-play**
* [x] Demo setup (Beat 0) · [x] Tell-show-tell (§5) · [x] Value at executive altitude with named roles (§2, Beat 5)
* [x] Reading the room (§2 bridge rule) · [x] Objections by role (§7)

**Build guidance and failure modes**
* [x] A customer problem, not an internal one · [x] An integrated journey (§4) · [x] Trade-offs (§8) · [x] Value quantified · [x] AI as a force multiplier (§9)
* [x] Why the customer couldn't solve it before, and how Databricks solves each challenge (Beat 2b, §4b)
* [x] Root cause kept simple: unified discharges + predictions + a trend view → missing 7-day follow-up, especially on weekends

**Four domains**
* *Industry:* Beats 1–3, plus **executive-pressure fluency**: each HRRP metric mapped to the role measured on it (§2)
* *Product:* §4, §4b (every layer used for a purpose and connected, plus the closed loop, the LLM judge and role-based masking)
* *Build and AI Mindset:* Beat 6 proof, §9
* *Customer Skills:* §§2, 5, 7 and the deck itself (`docs/deck.md`)

---

## 11. Timing (20–30 minute session)

| Beat | Minutes |
|---|---|
| 0 Outcome hook, by named role | 1 |
| 1–3 Situation, complication (business + technical), insight | 5 |
| 5 Value by accountable executive (before the demo) | 2 |
| 4 Resolution: challenges → capabilities, the one-thread story | 3 |
| Demo, 5 stops | 8–9 |
| 6 Proof and trust, plus trade-offs | 1–2 |
| 7 Ask, by role | 1 |
| Q&A | remaining |
