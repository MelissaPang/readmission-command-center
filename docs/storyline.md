# Storyline: Readmission Command Center for Cedarbrook Health

The narrative spine for the deck, the live demo and the role-play. Build the deck (`docs/deck_walkthrough.md`) and rehearse
(`docs/talk_track.md`) *from this document*. If a slide or a sentence doesn't serve one of the beats below, cut it.

All numbers come from the prototype run on synthetic Cedarbrook data (sources in `evidence/`). Items marked **[assumption]** must be stated as such.

---

## 1. The story in one sentence

> **Cedarbrook is losing about $240K a year in Medicare penalties on one unit because weekend heart-failure patients go home
> without a follow-up appointment. The Readmission Command Center finds those patients, tells nurses who to call and why,
> and shows the CFO what every call is worth, on one governed platform.**

The three-sentence version (the elevator pitch, ~30 seconds):
1. *Problem:* Heart-failure readmissions on 6 North jumped from 14.8% to 23.9% after a weekend staffing change, and heart failure is the biggest line of a $1.62M HRRP penalty.
2. *Insight:* Only 18% of weekend discharges leave with a 7-day follow-up (vs 69% on weekdays), and those patients readmit at nearly twice the rate.
3. *Outcome:* Getting weekend follow-up to 80% avoids ~7 readmissions, cuts the HF ERR from 1.19 to 1.14 and saves ~$240K a year on one unit. The same playbook is worth ~$874K across CUMC.

---

## 2. Who we are talking to and what each needs to hear

| | Executive sponsor (funds the decision) | Domain owner (lives with the workflow) | Technical stakeholder (lives with the build) |
|---|---|---|---|
| **Who** | CFO / Chief Quality Officer, Cedarbrook Health | Priya Raman, RN, Manager of Transitional Care | Data architect / platform lead |
| **Their KPIs** | HRRP penalty $, HF excess readmission ratio (ERR), payback, risk | 7-day follow-up rate, high-risk patients contacted within 48h, nurse time per patient, unit readmission rate | Integration effort, data quality, PHI security, operability, cost to run |
| **Their fear** | Spending money on a dashboard that doesn't move the penalty; AI risk | Another tool that adds clicks; AI telling nurses what to do | Another silo to integrate and secure |
| **The line that lands** | "This turns a penalty line into a decision you can fund, with a number attached." | "Your team gets a short, ranked list of who to call today and why, and the care plan is drafted for you to approve." | "One governed copy of the data, from raw extract to app, deployed as code." |
| **Proof they need** | The what-if ($238K at 80%), the method being auditable, a 90-day pilot | The worklist, the AI plan with RN approval, the outreach tasks | Lineage, masks, row filters, data-quality results, Lakebase sync verification, the bundle |

**Reading the room:** answer the person who asked at their altitude, then bridge to the other in one sentence.

---

## 3. Narrative arc (Situation → Complication → Resolution → Value → Proof → Ask)

The arc deliberately **opens with the outcome**, then earns it. Architecture appears only after the value is established.

### Beat 0: Outcome first (the hook, first 60 seconds)
* **Message:** *"About $240K a year in avoidable penalty on one unit, and the fix is operational, not clinical."*
* Three numbers only: **~7 readmissions avoided · ERR 1.19 → 1.14 · ~$240K saved**. The scale-up: **~$874K** across CUMC.
* Frame what's coming: what we found, a live demo of how nurses and finance use it, how it's built, and what it takes to go live.

### Beat 1: Situation (the customer and the stakes)
* Cedarbrook Health: 3 hospitals. Flagship CUMC has 538 beds.
* The CMS **HRRP** cuts payments on *all* Medicare discharges, by up to 3%, when readmissions exceed expected. A unit-level problem becomes a hospital-wide payment cut.
* CUMC's estimated penalty is **$1.62M** (at the cap). Heart failure is the largest line at **$1.14M**, **ERR 1.19**.

### Beat 2: Complication (something changed, and nobody could see why)
* 6 North HF readmissions went **14.8% → 23.9%** in 20 weeks. **Every other unit stayed within ~1.5 pts.**
* Why it stayed hidden: the cause is **operational** (a staffing and clinic schedule change), the evidence is **in free text**, and the data is **split** between Quality, Finance and Care Transitions.

### Beat 3: The insight (root cause, quantified)
* Weekend pharmacist gone (2026-06-19) and Friday clinic slots dropped (2026-06-26). Since then, **18%** of weekend HF discharges have a booked 7-day follow-up vs **69%** on weekdays.
* No follow-up → **29.8%** readmit vs **16.4%** with one.
* AI read **16,584 notes**: patients who **live alone** (only in the text) readmit at **33.1% vs 20.6%**.
* *The "aha":* the problem is a missing appointment on Fridays to Sundays, a fixable process gap.

### Beat 4: Resolution (what the solution does, one connected journey)
* The **one-thread story** below is the centrepiece. It shows the layers are connected, not stitched.
* In business terms: **see the cause → find the patients → act → measure the dollars → ask anything.**

### Beat 5: Value (in the buyer's KPIs)
* For the **executive:**
  * 80% weekend follow-up → ~6.5 avoided readmissions, ERR 1.14, **$238K** saved
  * every 10 points of follow-up ≈ $120K
  * scale to all CUMC HF ≈ **$874K**
  * payback vs ~0.4 FTE of weekend pharmacist coverage (~$60K/yr **[assumption]**) ≈ **4×**
* For the **domain owner:**
  * **54** high-risk patients in the current 30-day window, **41** with no follow-up, ranked with the reason for each
  * the AI-drafted plan in ~4 s, approved by an RN, with outreach tasks created automatically
* For **both:** the nurse's action and the CFO's KPI are on the same data, on the same screen.

### Beat 6: Proof and trust (why they can believe it)
* **Live demo** (tell → show → tell), then the evidence that it really ran: 10/10 job tasks, 27/27 checks.
* **Governance:** PHI masked for analysts, hospital-scoped row filters, lineage, an audit trail of every AI draft and approval.
* **Model:** AUC 0.72; High-risk patients readmit at 45% vs 9% for Low.
* **Honesty up front:**
  * the data is synthetic, so AI accuracy will be re-validated on real notes
  * the what-if assumes the follow-up effect is causal
  * the HRRP method is simplified

### Beat 7: The ask (time to value)
* A **90-day pilot on 6 North:**
  * connect Epic feeds (weeks 0–4)
  * validate the AI and the model with RNs and Quality (weeks 4–8)
  * nurses work the list daily (weeks 8–12)
* **Success** = weekend follow-up 18% → ≥ 80%, ≥ 90% of high-risk patients contacted within 48h, HF readmissions trending back toward ~15%.
* **Ask:** an executive sponsor plus a decision on weekend follow-up coverage. *"What would you need to see to move forward?"*

---

## 4. The one-thread story: proving the layers are connected

Tell the platform story by following **one weekend heart-failure patient** through it. This is the slide, and the demo path, that
addresses the "layers present but not connected" failure mode.

1. **Raw data.** Friday 4 pm discharge from 6 North. The ADT record, the appointment extract (no follow-up booked) and the discharge note
   *"Lives alone… Patient to call the HF Bridge Clinic on Monday"* land as raw files.
2. **Lakeflow** ingests them incrementally, de-duplicates them and enforces data-quality rules, then builds the HRRP gold tables (index admission, 30-day outcome, follow-up gap).
3. **Unity Catalog** governs one copy. The patient's name and MRN are masked for analysts, and access is scoped by hospital. Lineage traces every column back to the raw file.
4. **AI Functions** read the note and add `lives_alone = true` and `followup_status = patient_to_call`, with the evidence quote.
5. **ML:** those AI flags plus the EHR fields feed the 30-day risk model (the champion is registered in UC). This patient scores **High**, with drivers *"No 7-day follow-up booked"* and *"Lives alone"*.
6. **Lakebase** serves the worklist to the app in milliseconds. The patient appears at the top of Priya's list.
7. **The app:**
   * Claude drafts a transition plan from this patient's facts only, and an RN approves it
   * outreach tasks (book the follow-up, pharmacist call, caregiver check) are written back to Lakebase
   * the approval is readable in UC
8. **The HRRP page:** booking follow-ups like this one is what moves the ERR from 1.19 toward 1.14 and the penalty down ~$240K.
9. **Genie:** Finance asks *"weekend vs weekday follow-up on 6 North since June 19?"* and gets 17.7% vs 68.6%, with the SQL, on the same governed tables.

> Closing line for this beat: *"A sentence in a discharge note became a model feature, which became a call on a nurse's list, which became a dollar
> figure on the CFO's page: one platform, one copy of the data."*

---

## 5. Demo storyline (tell → show → tell)

| Stop | Tell (what you'll see) | Show | Tell back (what it means) |
|---|---|---|---|
| 1. Unit Trends | "What Priya sees each morning" | 6 North spike, staffing-change markers, weekend follow-up collapse | "Root cause on one screen, no query written" |
| 2. Worklist | "Who to act on today" | Filter 6 North · High · no follow-up; risk, AI flags, drivers | "A short, ranked list with the reason next to each name" |
| 3. Patient → AI plan → approve | "From insight to action" | Note evidence quote → Claude drafts → RN approves → tasks created | "AI drafts, the nurse decides, everything is audited" |
| 4. HRRP & What-if | "The same action in the CFO's language" | Slider 55% → 80%: ~6.5 avoided, ERR 1.14, $238K; scope → $874K | "Every booked follow-up moves this number" |
| 5. Ask Genie | "Questions nobody built a dashboard for" | Weekend vs weekday follow-up → 17.7% vs 68.6% + SQL | "Self-service on governed data, PHI stays masked" |

Keep the demo to ~9 minutes and close with: *"Insight → action → dollars in one workflow."*

---

## 6. Proof points (have these ready, all verifiable in the repo)

| Claim | Number | Evidence |
|---|---|---|
| Unit spike, others stable | 14.8% → 23.9%; others ≤ 1.1 pts | `evidence/query_results.md` |
| Weekend follow-up gap | 18% (11/62) vs 69% (94/137) | `gold.followup_gap` |
| Follow-up effect | 29.8% vs 16.4% | `gold.readmission_risk_factors` |
| Free-text risk (AI) | lives alone 33.1% vs 20.6%; 16,584 notes, 0 errors | `02_ai_note_signals_eval.ipynb` |
| Penalty | $1.62M (cap), HF $1.14M, ERR 1.19 | `gold.hrrp_hospital_penalty` |
| What-if | 80% → 6.52 avoided, ERR 1.14, $238,438; CUMC HF ≈ $874K | `gold.hrrp_whatif` |
| Model | AUC 0.7245; High 45% / Low 9% observed | `03_*.ipynb`, `04_*.ipynb` |
| Worklist | 54 High-risk, 41 without follow-up | `gold.discharge_worklist` |
| AI plan | 4.4 s, grounded, RN-approved, 2 tasks created | `evidence/app_api_responses/11_*.json`, `12_*.json` |
| Genie | 5/5 story questions correct | `06_genie_space.ipynb` |
| Governance | masked PHI; row filter 3,424 / 14,475 | `99_validate_story.ipynb` |
| It really ran | 10/10 tasks; 27/27 checks; Lakebase 9/9 match | `evidence/job_run_summary.md`, `evidence/lakebase_verification.md` |

---

## 7. Anticipated pushback, built into the story (not left for Q&A)

Address these *inside* the beats so the objections are already answered:
* **"Is the $240K real?"** (Beat 5) The method is fixed-rule and reproducible by Finance. Say the causal assumption out loud. The pilot is designed to prove it.
* **"Is AI safe here?"** (Beat 6) AI drafts and nurses decide; every step is audited; the prompt is grounded in the patient's own facts.
* **"What about PHI?"** (Beat 4, step 3) Masks, row filters, a least-privilege app identity, lineage.
* **"How long until value?"** (Beat 7) A 90-day pilot; value starts the first week nurses use the list.
* **"Will it integrate with Epic?"** (Beat 7 / Q&A) Same pipeline. The connect phase maps feeds, it doesn't rebuild.
* **"Why the jump between 70% and 80%?"** (Q&A) CUMC is above the 3% cap, so the first ~$60K of improvement is absorbed by the cap.

Full objection answers are in `docs/talk_track.md` §8.

---

## 8. Decisions and trade-offs (the three to tell)

* **Synthetic data shaped like Cedarbrook's** → zero PHI risk and every number reproducible. *Trade-off:* real notes are messier, so extraction is re-validated in the pilot.
* **The simpler model won** (logistic regression 0.7245 vs gradient boosting 0.7137) → easier for clinicians to trust. *Trade-off:* less headroom on richer data, so the champion is re-selected each run.
* **A fixed-rule, auditable what-if** on a simplified HRRP method → Finance can reproduce every dollar. *Trade-off:* it assumes causality and simplifies CMS's 3-year, risk-adjusted, Medicare-only method.

---

## 9. AI as a force multiplier (one beat in the "how it's built" segment, and in the written submission)

* **Built with Claude Code** as a teammate. The story's numbers were a contract checked by code, the data was verified locally before deploying, everything was
  deployed as one bundle, and the agent ran it, read the errors and fixed them, with a validation gate and evidence committed at each milestone.
* **AI inside the product:**
  * Claude Haiku turns notes into structured data (with evidence quotes)
  * Claude Sonnet drafts grounded care plans for RN approval
  * Genie gives plain-English analytics, tuned with instructions and example SQL after evaluation (3/5 → 5/5)
* Details and the exact prompts: `docs/ai_workflow.md`.

---

## 10. Requirements coverage check

**Deck requirements**
* [x] Leads with the business outcome: Beat 0 (~$240K, ERR 1.19 → 1.14) before anything else
* [x] Quantifies impact in the buyer's KPIs: HRRP $, ERR, HF readmission %, 7-day follow-up %, 48h contact
* [x] Frames value for the executive sponsor *and* the domain owner: §2, Beat 5
* [x] Architecture after value: Beat 4 comes after Beats 0–3

**Role-play scoring criteria**
* [x] Demo setup: Beat 0 frames the customer, the problem and what's coming before any demo
* [x] Tell-show-tell: §5, every stop
* [x] Value communication at executive altitude: Beats 0, 5 and 7 speak in penalty $, ERR and payback, not features
* [x] Reading the room: §2 persona map and the bridge rule; talk track §8 has answers for each persona
* [x] Professionalism and objection handling: §7 builds the pushback into the story; assumptions are named proactively

**Build guidance and failure modes**
* [x] A real customer scenario in a specific industry (healthcare provider, CMS HRRP), not an internal problem
* [x] An integrated journey with the data flow obvious: §4 one-thread story (raw → Lakeflow → UC → AI/ML → Lakebase → App/Genie)
* [x] Trade-offs documented: §8
* [x] Value quantified: $238K; ~$412K and ~$874K scaled; ~4× payback **[assumption]**
* [x] AI as a force multiplier: §9
* [x] The narrative never skips business value: Beats 0–3 are business-only

**Four domains**
* *Industry:* Beats 1–3 (HRRP mechanics, the clinical-operational root cause, the buyer's KPIs)
* *Product:* Beat 4 / §4 (every layer used for a real purpose and connected)
* *Build and AI Mindset:* Beat 6 proof plus §9 (evidence it ran; AI as a teammate)
* *Customer Skills:* §§2, 5, 7 (persona framing, tell-show-tell, objections, the ask)

---

## 11. Timing (20–30 minute session)

| Beat | Minutes |
|---|---|
| 0 Outcome hook | 1 |
| 1–3 Situation, complication, insight | 4 |
| 5 Value (before the demo, so the demo proves it) | 2 |
| 4 Resolution: the one-thread story | 2 |
| Demo, 5 stops (tell → show → tell) | 9 |
| 6 Proof and trust, plus trade-offs | 2 |
| 7 Ask | 1 |
| Q&A / objections | remaining |

Note: in delivery, **Value (Beat 5) comes before the Resolution walkthrough (Beat 4)**, so the audience knows what the demo is worth before they see it.
