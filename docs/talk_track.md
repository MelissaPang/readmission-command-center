# Talk track: Readmission Command Center (presentation and role-play script)

The spoken script for the 20–30 minute session. Slide numbers match `docs/deck_walkthrough.md` / `docs/deck.md` (16 slides).
Lines in quotes are meant to be said roughly as written; *italics* are stage directions. Every demo stop is **tell → show → tell**.

**Who is in the room.** The role-play has two AI personas. Map them to the Cedarbrook leaders:

| Persona in the room | Speaks for | Their numbers |
|---|---|---|
| **Business stakeholder** (the executive who funds it) | **Jordan Whitfield, CFO** and **Dr. Naomi Brooks, CEO** (plus **Dr. Elena Vasquez, VP of Quality** on quality questions) | HRRP penalty $1.62M → $1.38M; star rating 3★ → 4★; HF referrals 420 → 470; payer withhold $300K → $100K forfeited; HF ERR 1.19 → 1.14 |
| **Technical stakeholder** (lives with the build) | **Kenji Tanaka, Chief Data & Analytics Officer** | 5 silos → 1 governed copy; ~2 min refresh; quality gates on every run |
| *(referenced, the app's main user)* | **Priya Raman, RN, Manager of Transitional Care** | weekend 7-day follow-up 18% → ≥ 80%; ≥ 90% of high-risk patients contacted within 48h |

If the personas introduce themselves with other names, use **their** names and keep the same role mapping.

> All numbers are from the prototype on synthetic Cedarbrook data (job run 601827272748584: 11/11 tasks, 33/33 checks). Say "on Cedarbrook-like
> data". The strategic scorecard values (Care Compare category, stars, referrals, contract) and the ~$60K follow-up capacity cost are **synthetic or
> illustrative**: say so if asked. Real-time scoring at discharge is the **production design**: say "in production".

---

## Timing plan (~24 min presenting + Q&A)

| Segment | Slides | Time |
|---|---|---|
| Opening and outcome | 1–2 | 1.5 min |
| Stakes, accountability, strategic scorecard | 3–5 | 3 min |
| Problem and why it couldn't be solved | 6–7 | 2.5 min |
| Root cause | 8 | 1.5 min |
| Value by role | 9 | 1.5 min |
| Solution and one-patient journey | 10–12 | 3 min |
| Live demo (5 stops) | 13–14 | 8–9 min |
| Trust, quality gates, trade-offs | 15 | 1.5 min |
| Pilot and the ask | 16 | 1 min |
| Q&A / objections | n/a | remaining |

---

## Before you start (5 minutes before the session)

* [ ] **Start the Lakebase instance and the app** if they were stopped (`rcc-lakebase`, app `readmission-command-center`). Open the app URL and wait for the **Unit Trends** tab to load. That warms the SQL warehouse too.
* [ ] **Pre-pick the demo patient.**
  * In **Discharge Worklist**, set Hospital = CUMC, Unit = 6 North Telemetry, Tier = High, and tick **No 7-day follow-up**.
  * Pick a **weekend heart-failure** discharge with **no plan** in the Plan column. Note the name.
* [ ] Have the **Ask Genie** tab open in a second browser tab, with the question ready to paste.
* [ ] Deck on slide 1. Repo link ready: https://github.com/MelissaPang/readmission-command-center

---

## 1. Opening and outcome (slides 1–2, ~1.5 min)

**Slide 1**
> "Thank you for the time. In the next twenty minutes I'll show you what we found in Cedarbrook's data, what it's worth, and a live demo of
> how your care-transitions team and your finance team would use it. Then I'll cover how it's built, and what it takes to go live. I'll leave
> plenty of time for questions."

**Slide 2**
> "Here's the headline: **booking a 7-day follow-up for weekend heart-failure discharges on one unit is worth about $240,000 a year.** And the fix is operational, not clinical."

*Point at each tile as you name its owner:*
> "**Jordan**, for you: the HRRP penalty goes from $1.62 million to $1.38 million. That's $238,000 a year on one unit, and about $874,000 if we apply it to all heart failure at CUMC.
> **Dr. Vasquez**: the heart-failure excess readmission ratio goes from 1.19 to 1.14.
> And for **Priya's** team: weekend follow-up goes from 18% to 80%, and every high-risk discharge comes with a two-sentence briefing on who to call and why."

> "And it isn't only financial. **Dr. Brooks**, the same fix moves Cedarbrook out of Care Compare's 'worse than national' category, and it's worth a star and about fifty heart-failure referrals a year. I'll show you those numbers in a moment."

---

## 2. Stakes, accountability, strategic scorecard (slides 3–5, ~3 min)

**Slide 3: the stakes**
> "Quick context. Under CMS's Hospital Readmissions Reduction Program, if readmissions run above expected, CMS cuts payments on *all* Medicare
> discharges, by up to 3%. CUMC's estimated penalty is $1.62 million, and that's already at the cap. Heart failure is the biggest line, $1.14 million, with an excess readmission ratio of 1.19.
> And it's public: the same performance is on Care Compare, where CUMC heart failure shows as *worse than the national rate*, and it feeds a 3-star rating."

**Slide 4: who owns which number**
> "What I want to be precise about is who owns which number, because they all move together:
> * Jordan owns the penalty.
> * Dr. Vasquez owns the readmission ratio and the public rating.
> * Priya owns the 7-day follow-up rate.
> * Kenji owns the platform.
> * Dr. Brooks owns the star rating and referral volume.
>
> All five numbers move with **one action**: a follow-up booked before a high-risk patient goes home."

**Slide 5: beyond the penalty (the strategic scorecard)**
> "This is the slide I'd want in the boardroom. The penalty is only the floor."

*Walk the table row by row, naming the owner:*
> * "**Care Compare**, Dr. Vasquez: heart-failure readmissions go from 19.4% to 18.6%. That takes CUMC from *worse than national* to *no different than national*.
> * **Star rating**, Dr. Brooks: readmission is one of the five star-rating groups. With it back at national, we project 3 stars to 4.
> * **Referrals**, Dr. Brooks: heart-failure referrals from ACO and cardiology partners have been sliding, now 420 a year and down 6%. We project 470. That's 50 admissions, about $372,000 of revenue.
> * **Payer contracts**, Jordan: on a $20 million Medicare Advantage contract with a 2% readmission withhold, we're projected to forfeit $300,000 of $400,000. With the fix, it's $100,000, so you keep $200,000."

> "So: **financial**, $238,000 less penalty. **Strategic**, out of 'worse than national', plus a star, plus 50 referrals, plus $200,000 of contract withhold retained."

*If asked:* "The rate change comes from the model. The category, stars, referral and contract figures are illustrative for Cedarbrook. We'd confirm them with your strategy and managed-care teams."

---

## 3. Problem and why it couldn't be solved (slides 6–7, ~2.5 min)

**Slide 6: the peak**
> "Here's what happened. On 6 North Telemetry, heart-failure readmissions went from **14.8% to 23.9%** in twenty weeks. Every other unit stayed within a point and a half.
> And Cedarbrook found out the way most hospitals do: after the fact, from the quality report and the penalty estimate. Nobody could answer the two questions that matter: when did it start, and why?"

**Slide 7: why it couldn't be solved before**
> "That isn't anyone's fault. It's the data. Three reasons.
> * **First, silos.** Discharges, follow-up appointments, notes and penalty data live in different systems. And critically, the **readmission prediction is disconnected from the discharge**: if there's a score, it's calculated weeks later, not in front of the nurse while a follow-up can still be booked. There's also no view of readmissions over time by unit.
> * **Second, infrastructure.** A warehouse, a lake, BI and an app database, each with its own copy of patient data. Every question becomes an IT project, and Quality's and Finance's numbers don't match.
> * **Third, ML and AI.** There's no governed way to put a model in the nurse's workflow, use AI on notes, learn from what nurses do, or check that an AI answer is right."

*To the technical persona (Kenji):* "Every new question meant another copy of PHI and another integration."

---

## 4. Root cause (slide 8, ~1.5 min)

> "Once you unify discharges, predictions and follow-ups, and trend them over time, the answer is obvious.
> * **When:** the trend shows exactly when 6 North's peak started, and that it's only 6 North.
> * **Why:** weekend heart-failure discharges with a booked 7-day follow-up fell to **18%**, against **69%** on weekdays.
> * **So what:** patients without that follow-up readmit at **29.8%**, compared with **16.4%** with one.
> * **Who, right now:** every discharge now carries its prediction and a nurse briefing, so we catch the high-risk patient *before* they go home.
>
> This isn't a clinical mystery. It's a missing appointment, and that's a process gap the team can fix."

*Hold in reserve (Appendix E), only if asked "why weekends?":* "It lines up with two late-June changes, a vacated weekend transitions-pharmacist role and fewer Friday clinic slots."

---

## 5. Value by role (slide 9, ~1.5 min)

> "Here's what fixing it is worth, using a fixed-rule calculation. Jordan, your team can reproduce every line.
> At **80%** weekend follow-up: about six and a half avoided readmissions, the ratio goes to 1.14, and **$238,000** less penalty. Every ten points of follow-up is worth about $120,000. At hospital scale, about $874,000."

> * "**Jordan:** if restoring weekend follow-up capacity costs around $60,000 a year (that's my assumption, we'd validate it), it's roughly a four-times return on the penalty alone. Add the $200,000 of withhold and the referral revenue on top.
> * **Dr. Vasquez:** 1.19 to 1.14, heading toward the 1.00 benchmark.
> * **Priya:** right now there are 54 high-risk patients in the window, and 41 have no follow-up. Booking those is how we get from 18% to 80%."

---

## 6. Solution and one-patient journey (slides 10–12, ~3 min)

**Slide 10: the solution**
> "Here's the solution in six steps:
> 1. **unify** the data
> 2. **predict** risk for every discharge
> 3. **visualize** readmissions over time
> 4. **brief and act:** a nurse briefing, an AI-drafted plan the nurse approves, outreach tasks created automatically
> 5. **measure** the dollars
> 6. **learn**: every nurse edit becomes a training signal."

**Slide 11: one patient, one platform** *(the integration slide: slow down here)*
> "Let me follow one Friday discharge through it, because this is what makes it one platform and not five tools.
> * The discharge record, the appointment (none booked) and the note, *'patient to call the clinic on Monday… lives alone'*, land as raw files.
> * **Lakeflow** ingests them with data-quality rules. **Unity Catalog** governs one copy, with the name masked for analysts and the note quote visible only to care transitions.
> * **AI Functions** read the note: 'lives alone', 'patient to call'.
> * The **model** scores the patient High: no follow-up is 16.8 points, living alone is 13.5.
> * AI turns that into a **briefing**: 'book the 7-day follow-up and start a home-health referral.'
> * **Lakebase** serves it to the app. Claude drafts the plan, and the nurse **edits** and approves it.
> * That edit becomes a **training signal** for the next model run.
> * The follow-up moves the **ERR**, and **Genie** can answer questions on all of it.
>
> The discharge, its prediction and its follow-up finally live together, and every nurse decision teaches the system."

**Slide 12: challenge → capability** *(look at the technical persona)*
> "Kenji, to close the loop on the three challenges:
> * The silos go into **Lakeflow** and one gold layer. In production, discharge events trigger the scoring.
> * The infrastructure becomes **one platform**: Lakeflow, SQL, Lakebase and Apps, deployed as code, serverless.
> * Governance is **Unity Catalog**: PHI masks, a role-based mask on the AI note quotes, hospital row filters and lineage.
> * ML is **MLflow** and the model registry.
> * AI on notes is **AI Functions**, inside the governed pipeline.
> * Learning comes from the **Lakebase write-back**, which we read back through Unity Catalog.
> * Trusting AI answers is **Genie** plus an **LLM judge** that grades its answers on every run."

---

## 7. Live demo (slides 13–14, ~8–9 min)

**Tell (slide 13):**
> "Let me show you. Five stops: the peak, a briefed patient list, a plan the nurse edits and approves, the dollars, and a plain-English question."

*Switch to the app.*

### Stop 1: Unit Trends (~1.5 min), for Dr. Vasquez
* **Tell:** "First, when did it start and why? This is what Dr. Vasquez's team sees."
* **Show:**
  * The KPI tiles: 6 North 23.9%, up from 14.8%; every other unit within about a point and a half; weekend follow-up 18% vs 69%.
  * The **weekly line chart**: the rolling rate climbs after the dashed lines for late June.
  * The **follow-up bar chart**: the red weekend bar collapses after June 19.
  * The unit table at the bottom: 6 North at the top, every other unit flat.
* **Tell:** "The peak and its cause on one screen, with no query written. You'd see the next one the week it starts, not when CMS reports it."

### Stop 2: Discharge Worklist (~1.5 min), for Priya
* **Tell:** "Now, who do we act on today?"
* **Show:**
  * The **Discharge Worklist** tab, with filters Hospital CUMC, Unit 6 North, Tier High, No 7-day follow-up.
  * The **Nurse briefing** column: read one aloud.
* **Tell:** "Each discharge has its prediction attached and a two-sentence briefing written from the model's drivers. It reads like a handoff, not a scored table. Priya's team knows who to call and why before the follow-up window closes."

### Stop 3: Patient → AI plan → nurse edit → approve (~2.5 min), for Priya and Kenji
* **Tell:** "Let's go from insight to action, and see the system learn."
* **Show:**
  1. Click your pre-picked patient. Point at the **Nurse briefing**, the model drivers with their points, and the **note evidence quote**: "that quote is visible to care transitions only; an analyst sees it masked."
  2. Click **✨ Draft transition plan with AI**. Claude drafts in a few seconds. Point at the sections (48 hours, 7 days, social needs, teach-back) and the closing "requires RN review".
  3. **Edit the draft** in the text box. For example, under *Within 48 hours*, add: "Call patient today to book the HF Bridge Clinic slot before end of shift."
  4. Click **Approve plan & create outreach tasks**. Point at the plan header: **"RN edited (xx% similar; +N/−0 chars; Within 48 hours)"**.
  5. Open the **Outreach Queue** tab: the new tasks, such as booking the follow-up and the pharmacist call.
* **Tell:** "The AI drafts and the nurse decides. Drafting time goes away. And that edit isn't lost: it's recorded and becomes a training signal. Our last model run picked up three reviewed plans and a 33% edit rate. Every decision Priya's nurses make teaches the next version."

### Stop 4: HRRP & What-if (~1.5 min), for Jordan and Dr. Vasquez
* **Tell:** "Now the same action in Jordan's language."
* **Show:**
  * The tiles: $1.62M at the cap, heart failure $1.14M, ERR 1.19.
  * Move the slider from today's ~55% to **80%**: about 6.5 avoided readmissions, ERR **1.14**, **$238K** saved.
  * Switch the scope to **CUMC all HF discharges**: about **$874K**.
* **Tell:** "Every follow-up Priya's team books shows up here. And slide 5 showed you what the same number means for stars, referrals and your payer contract."

### Stop 5: Ask Genie (~1.5 min), for Kenji and Jordan's analysts
* **Tell:** "Finally, the questions nobody built a dashboard for."
* **Show:**
  * Ask: *"Compare 7-day follow-up booking on 6 North for weekend vs weekday HF discharges since 2026-06-19."*
  * Genie answers 17.7% vs 68.6%. Expand **SQL**.
* **Tell:** "It answers in plain English and shows its SQL, on the same governed tables, with patient identifiers masked. And on every run an LLM judge grades Genie's answers against SQL-computed correct answers. It passed five out of five last run, so you know when it's right."

**Tell back (slide 14):**
> "So: from the peak, to the cause, to a briefed patient, to a plan the nurse improved, to the dollars.
> * Jordan, every booked follow-up is visible as dollars, and your team can audit the method.
> * Dr. Vasquez, you see the next peak the week it starts.
> * Priya, your nurses get a briefed list and a drafted plan, and their edits make it better.
> * Kenji, it's one governed copy, with quality gated on every run."

---

## 8. Trust, quality gates, trade-offs (slide 15, ~1.5 min)

> "Two things I'd want to know in your seat: can I trust it, and what did you compromise?
>
> **On trust:**
> * patient identifiers are masked by policy, the AI note quotes are masked by role, and access is scoped by hospital
> * the model separates risk: High-risk patients readmit at 45% against 9% for Low
> * Genie is checked by a judge on every run
> * briefings are grounded in the patient's own record, and the nurse always decides
> * it ran end to end, 11 of 11 tasks, with all 33 validation checks passing.
>
> **On trade-offs, three choices:**
> * I used **synthetic data shaped like Cedarbrook's**, so there's no PHI risk and every number reproduces. Real notes are messier, so re-validating the AI is the first thing in the pilot.
> * I let the data choose the model, and the **simpler logistic regression won**. It's easier for clinicians to trust.
> * The what-if is **fixed-rule and auditable**, on a simplified version of CMS's method, so Jordan's team can reproduce it. It assumes the follow-up effect is causal, which is what the pilot tests.
>
> And to be clear on the limits: the feedback loop only has three reviewed plans so far, and real-time scoring at discharge is the production design."

---

## 9. Pilot and the ask (slide 16, ~1 min)

> "Here's my proposal: a **90-day pilot on 6 North**.
> * Weeks one to four: connect your Epic feeds and turn on scoring at discharge.
> * Weeks four to eight: Priya's nurses and Dr. Vasquez's team validate the AI and the model on real data.
> * Weeks eight to twelve: 6 North works the briefed list every day, with a weekly scorecard."

> "Success, by owner:
> * Jordan: the penalty trajectory toward minus $238,000.
> * Dr. Vasquez: 6 North back toward 15%.
> * Priya: weekend follow-up at 80% or better, and 90% of high-risk patients contacted within 48 hours.
> * Dr. Brooks: the Care Compare rate, the star rating's readmission group, and partner referrals, all on the same scorecard.
>
> What I'm asking for:
> * Jordan, funding for weekend follow-up capacity.
> * Dr. Vasquez, sponsorship and chairing the weekly review.
> * Priya, a nurse champion on 6 North.
> * Kenji, data access and an Epic contact."

> "**What would you need to see to move forward?**"

---

## 10. Objection handling (by role)

Pattern: **acknowledge → answer with their number or a fact → bridge to the other stakeholder in one sentence.**

### Business stakeholder: Jordan (CFO), Dr. Brooks (CEO), Dr. Vasquez (Quality)

**Jordan: "What does this cost?"**
> "Two parts. The platform is serverless and pay-per-use. The heaviest step, AI reading all 16,600 notes, ran once, and after that only new notes are processed: a few hundred a week. We'd size it exactly in the pilot. The bigger decision is operational: weekend follow-up capacity, around $60,000 a year by my assumption, against $238,000 of penalty plus $200,000 of contract withhold."
*Bridge:* "And Kenji, it's one platform, so there's no integration bill for five tools."

**Jordan: "How do I know the $238K is real?"**
> "It's fixed-rule: additional follow-ups times the readmission gap we measured, then CMS's formula. Your team can reproduce it line by line. The one assumption I'll name is causality, and the pilot is designed to test it: 6 North against the other units, before and after."

**Jordan: "Why does savings jump from $119K at 70% to $238K at 80%?"**
> "CUMC is above the 3% cap: uncapped, the penalty would be $1.68 million. So the first $60,000 of improvement is absorbed by the cap, and after that every dollar is real."

**Dr. Brooks: "Is one star really on the table? That sounds optimistic."**
> "Fair challenge. The rate improvement is from our model. The star projection is illustrative. Readmission is one of five groups, at 22% of the weighting, and the scenario assumes CUMC is close to the 4-star cutoff with readmissions holding it back. The pilot scorecard tracks the readmission group directly, so we'll know."

**Dr. Brooks: "Where do the 50 extra referrals come from?"**
> "It's an illustrative scenario: partners who've been moving heart-failure patients away as the published rate worsened (it's down 6% this year) coming back once you're out of 'worse than national'. At $7,444 per heart-failure admission, that's about $372,000. We'd validate it with your strategy team's referral data."

**Dr. Vasquez: "Will this move our public ratio, and when?"**
> "The ratio is calculated on a rolling performance period, so avoided readmissions roll into it over time. That's why the pilot tracks 6 North's rate weekly: that's the leading indicator, and the ratio follows."

**Dr. Vasquez / Jordan: "What's the risk of AI giving bad clinical advice?"**
> "The AI never acts on its own. It drafts and briefs, and a nurse reviews, edits and approves. It's restricted to the patient's own facts, labeled as an AI draft, and every approval and edit is audited. The risk model is a transparent logistic regression with per-patient reasons."

**Dr. Brooks: "Our EHR vendor already has a readmission score."**
> "A score alone doesn't tell you *why* readmissions rose on one unit, or what it's costing you in penalty, stars and contracts. What's new is joining the cause, the free-text risk, the nurse's action and the dollars. We can bring the vendor score in as a feature and compare the two."

**Anyone: "How fast is time to value?"**
> "Operational value starts in the first week nurses work the list. The 90-day pilot proves it, and the longest part is connecting the data, about four weeks."

### Technical stakeholder: Kenji (CDAO)

**"How does this integrate with Epic?"**
> "The pipeline starts from extracts in a governed landing zone. In production that's Epic Clarity or Caboodle through Lakeflow Connect or JDBC, or HL7/FHIR ADT messages for discharge events. Bronze is schema-on-read with Auto Loader, so we map your feeds to the same silver schema, and everything downstream stays the same."
*Bridge:* "So, Jordan, the first four weeks are mapping, not rebuilding."

**"How do you handle data quality?"**
> "Lakeflow expectations on every silver table: valid IDs, discharge after admit, valid reference rates. Bad rows are dropped and counted; bad reference data fails the update. We planted defects to prove it: six bad timestamps and 45 duplicates, all caught and logged. Then 33 validation checks run on every job run."

**"How is PHI secured?"**
> "Unity Catalog column masks on the patient table, declared in the pipeline. A **role-based mask** on the AI-extracted note quotes, so only care transitions sees them. A row filter by hospital. The app runs as its own service principal with least privilege: read-only on served tables, no access to raw notes. Lineage runs end to end."

**"Why Lakebase instead of querying the warehouse?"**
> "The app is operational: many small reads and writes from concurrent nurses, sub-second. That's an OLTP pattern. Lakebase gives Postgres latency and transactions for approvals and edits, and it stays in Unity Catalog. The nurses' writes are readable in UC, which is exactly what feeds the learning loop, with no ETL."

**"How fresh is the app's data?"**
> "Today the synced tables refresh at the end of each pipeline run. In production I'd enable Change Data Feed and triggered sync, and run the pipeline on discharge events, so a weekend discharge reaches the worklist within minutes."

**"How do you know the AI is right?"**
> "Three gates.
> * Note extraction is scored against ground truth. It was 100% on synthetic notes, which I won't oversell, so it's re-validated on real notes.
> * Briefings are generated only from the patient's own row.
> * Genie is graded by an LLM judge against SQL-computed correct answers, every run, with the history stored."

**"Is the feedback loop real, or a slide?"**
> "It's real and running. The app records similarity, characters changed and sections changed on every approval. A pipeline step turns that into weak labels, and training logs them. Today that's three reviewed plans and a 33% edit rate, so it's small. The plumbing is done, and the signal grows with use."

**"Model drift and monitoring?"**
> "A time-based split, testing on the latest 20 weeks. The champion is re-selected by test AUC each run and registered with an alias, so scoring always uses the champion. Calibration is logged in MLflow. In production I'd add Lakehouse Monitoring on the score table."

**"How is it deployed and operated?"**
> "One Databricks Asset Bundle: schemas, pipeline, an 11-task job, the dashboard and the app. `bundle deploy` and `bundle run` rebuild it anywhere, from Git."

**"What would you change for production?"**
> * "Account groups instead of the entitlements table.
> * Change Data Feed plus triggered sync.
> * Real EHR connectors.
> * The full CMS method: 3-year, risk-adjusted, Medicare fee-for-service only.
> * Using the retraining signals as labels once there's volume."

### Switching altitude mid-answer (practice line)
> *"…technically, it's a column mask that checks the user's role before returning the note quote. **What that means for you, Dr. Brooks**, is that
> a finance analyst can use Genie on the same data without ever seeing a patient's clinical note."*

---

## 11. Closing (30 seconds)

> "To summarize: one unit's weekend follow-up gap is costing about $240,000 a year in penalty, plus a star, referrals and contract withhold, with a
> path to nearly $900,000 across CUMC. The platform shows when it started and why, who to call today, and what each call is worth, and it learns from every nurse.
> I'd like to propose the 90-day pilot on 6 North. What would you need to see to move forward?"

---

## Rehearsal checklist

* [ ] The headline number **and its owner's name** in the first 60 seconds
* [ ] Slide 5: say "financial *and* strategic" out loud
* [ ] Every demo stop: tell → show → tell, and name whose number it moves
* [ ] Demo stop 3: **edit** the plan before approving, and point at the edit stats
* [ ] Use their words (ERR, HRRP penalty, Care Compare, star rating, 7-day follow-up), not product names first
* [ ] Name the assumptions yourself (causality, the ~$60K capacity, the synthetic strategic figures, synthetic notes) before they're raised
* [ ] When Kenji asks, go deep, then bridge to Jordan or Dr. Brooks in one sentence
* [ ] End with the ask by role and a question
