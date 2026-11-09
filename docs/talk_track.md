# Talk track: Readmission Command Center (role-play script)

A spoken script for the 20–30 minute role-play with two AI personas in the room:
* **Business stakeholder:** the executive who funds the decision (CFO / Chief Quality Officer at Cedarbrook Health)
* **Technical stakeholder:** the data architect / platform lead who has to live with the build

Slide numbers refer to `docs/deck_walkthrough.md`. Lines in *italics* are stage directions. Everything else is meant to be
said roughly as written. Keep the demo tight. Every demo stop follows **tell → show → tell**.

**Timing plan (~22 min presenting + Q&A)**

| Segment | Slides | Time |
|---|---|---|
| Setup and outcome | 1–2 | 2 min |
| Problem and root cause | 3–5 | 4 min |
| Value case | 6 | 2 min |
| Solution journey | 7 | 2 min |
| Live demo (5 stops) | 8–9 | 9 min |
| Trust and trade-offs | 10–11 | 2 min |
| Path to production and ask | 12 | 1 min |
| Q&A / objections | n/a | remaining |

**Before you start:** have the app open on the Unit Trends tab, the Genie tab pre-loaded, the deck on slide 1, and a 6 North
weekend high-risk patient with no plan yet. To find one, run `scripts/capture_app_evidence.sh` or filter the worklist: Unit = 6 North, Tier = High, No follow-up.

---

## 1. Setup and outcome (slides 1–2, ~2 min)

> "Thank you both for the time. Here's what I'd like to do in the next twenty minutes. I'll start with what we found in
> Cedarbrook's data and what it's worth. Then I'll show you live how a care-transitions nurse and your finance team would use it.
> Then I'll walk through how it's built and what it takes to put it into production. I'll leave plenty of time for your questions."

> "The headline: **heart-failure readmissions on 6 North are costing Cedarbrook University Medical Center about $240,000 a year
> in avoidable HRRP penalty, and the fix is operational, not clinical.** If 6 North books a 7-day follow-up for 80% of its weekend
> heart-failure discharges, we avoid about seven readmissions a year and move the HF excess readmission ratio from 1.19 to 1.14.
> Apply the same fix to all heart-failure discharges at CUMC and the opportunity grows to about $870,000."

*Look at the executive:*
> "For you, this turns a penalty line into a decision you can fund, with a number attached."

*Look at the domain owner role / technical stakeholder:*
> "For the transitional-care team, it's a ranked daily worklist that tells nurses who to call and why. And all of it runs on one
> governed platform, which I know matters to you."

---

## 2. Problem and root cause (slides 3–5, ~4 min)

**Slide 3**
> "Cedarbrook runs three hospitals. At the flagship, CUMC, heart-failure 30-day readmissions on 6 North Telemetry went from
> **14.8% to 23.9%** in twenty weeks. That's nine points. Every other unit in the system stayed within about a point and a half. So this
> isn't a system-wide quality drift. It's one unit, and it started at a specific time."

> "It matters financially because heart failure is the largest line of CUMC's estimated **$1.62 million HRRP penalty**: **$1.14 million**,
> with an excess readmission ratio of **1.19**. CMS penalizes anything above 1.0."

**Slide 4**
> "Why didn't anyone catch this? Three reasons. First, the cause is operational. In June, 6 North lost its weekend transitions pharmacist,
> and a week later the HF Bridge Clinic stopped offering Friday afternoon slots. Second, part of the evidence lives only in free text:
> the discharge note says 'patient to call the clinic on Monday', and whether the patient lives alone is only in the note. Third, the data
> is split: Quality sees rates, Finance sees the penalty, nurses see a flat discharge list."

**Slide 5**
> "When we put it together, the story is very clear. Since June 19th, only **18%** of 6 North's weekend heart-failure discharges leave
> with a booked follow-up, against **69%** on weekdays. Before June, weekends were at about 69% as well."

> "And it matters: across all three hospitals, heart-failure patients without a 7-day follow-up readmit at **29.8%**, compared with **16.4%** with one."

> "One more finding that nobody could see before: we used AI to read every one of the 16,584 discharge notes. Patients who live alone, which is only
> written in the note, readmit at **33% versus 21%**. That's a risk factor your structured data simply doesn't have."

---

## 3. Value case (slide 6, ~2 min)

> "So what is fixing it worth? This is a fixed-rule calculation, no black box. Finance can reproduce every dollar."

> "Take 6 North's weekend heart-failure discharges over the last twelve months: about 196 of them, 55% booked today. Raise that to **80%** and
> that's about 49 more patients leaving with an appointment. At the readmission gap we measured, that's about **six and a half avoided
> readmissions**, the ERR moves from **1.19 to 1.14**, and the penalty drops by about **$238,000**."

> "Every ten points of weekend follow-up is worth roughly $120,000 here. Scale the fix to all heart-failure discharges at CUMC and it's about **$874,000**."

*To the executive:*
> "To put that against a cost: if restoring weekend pharmacist coverage is around 0.4 of an FTE, call it $60,000 a year (that's my assumption,
> we'd validate it with your finance team), that's roughly a four-times return on the penalty alone. That's before counting what the readmissions
> themselves cost the hospital."

---

## 4. Solution journey (slide 7, ~2 min)

> "Here's how it works end to end. The important point is that this is one connected flow, not five tools stitched together."

> "Raw EHR extracts land in the platform and **Lakeflow** ingests them incrementally, with data-quality rules. It caught every bad record
> we planted. Everything is governed in **Unity Catalog**: one copy of the data, with patient identifiers masked for anyone who isn't on the care team."

> "**AI Functions** read every discharge note and turn sentences like 'lives alone' into structured columns. Those columns feed a **30-day risk model**,
> and the model's scores and reasons feed the nurse worklist. **Lakebase** serves that worklist to the app in milliseconds, and it stores what nurses
> do back: approved plans and outreach tasks. **Genie** lets Finance ask questions in plain English, on the same governed data."

> "So the flag the AI pulls from a note becomes a model feature, which becomes a priority on Priya's worklist, which becomes a dollar figure on the
> HRRP page. Same data, all the way through."

---

## 5. Live demo (slides 8–9, ~9 min)

**Tell (slide 8):**
> "Let me show you this live. I'll follow one weekend discharge from the data to an approved care plan, in five stops: the trend, the worklist, a patient,
> the dollars, and a plain-English question to Genie."

*Switch to the app.*

### Stop 1: Unit Trends (~1.5 min)
* **Tell:** "First, what Priya sees when she opens it in the morning."
* **Show:**
  * The KPI tiles: 6 North at 23.9%, up from 14.8%; every other unit within about a point and a half; weekend follow-up 18% vs 69%.
  * The line chart: point at the dashed lines for June 19 and June 26.
  * The follow-up bar chart: the red weekend bar collapses after June 19.
* **Tell:** "Without anyone writing a query, the system has connected the spike to the date of the staffing change and to the weekend follow-up gap.
  That's the root cause on one screen."

### Stop 2: Discharge Worklist (~1.5 min)
* **Tell:** "Now the question is what to do about it today."
* **Show:**
  * Open Discharge Worklist and filter to Unit = 6 North, Tier = High, No 7-day follow-up.
  * Point at the risk %, the AI note flags (lives alone, transport) and the top drivers.
* **Tell:** "Across the system there are 54 high-risk patients in their 30-day window right now, and 41 of them have no follow-up booked. This is the
  list Priya's nurses work from: ranked by risk, with the reason next to each name, so a nurse knows what to do on the call."

### Stop 3: Patient detail, AI plan, approval (~2.5 min)
* **Tell:** "Let's open one patient and go from insight to action."
* **Show:**
  * Click the top patient.
  * Point at the model drivers (e.g. "No 7-day follow-up booked +X pts") and the **note evidence quote** extracted by AI.
  * Click **Draft transition plan with AI**. Claude drafts in a few seconds.
  * Point at the plan:
    * it uses only this patient's facts
    * it has sections for 48 hours, 7 days, social needs and teach-back
    * it ends with "requires RN review"
  * Click **Approve**.
  * Show that the outreach tasks were created, and open the Outreach Queue tab.
* **Tell:** "The AI drafts and the nurse decides. Writing that plan by hand takes most of the time per patient. Now it's a review. And the approval and
  every task are recorded in an audit trail that's queryable on the platform, so Quality can see what was done for whom."

### Stop 4: HRRP & What-if (~2 min)
* **Tell:** "Now the same action, in the CFO's language."
* **Show:**
  * The HRRP tiles: CUMC $1.62M at the cap, heart failure $1.14M, ERR 1.19.
  * Move the slider from 55% → 80%. Read out: ~6.5 readmissions avoided, ERR 1.14, **$238K saved**.
  * Switch the scope to "CUMC all HF discharges": ~$874K.
* **Tell:** "Every follow-up Priya's team books moves this number. That's the link that didn't exist before: the nurse's action and the CFO's KPI on the same data."

### Stop 5: Ask Genie (~1.5 min)
* **Tell:** "Finally, your finance and quality analysts won't always have a dashboard for the question they have. So they can just ask."
* **Show:**
  * Ask: *"Compare 7-day follow-up booking on 6 North for weekend vs weekday HF discharges since 2026-06-19."*
  * Genie answers 17.7% vs 68.6%. Expand the SQL.
* **Tell:** "It answers in plain English and shows the SQL, so it's verifiable, on the same governed tables. And patient identifiers stay masked for analysts."

**Tell back (slide 9):**
> "So in five minutes we went from a trend, to the cause, to the patients who need a call today, to an approved plan, to the dollars. Insight, action and
> value in one workflow, on one governed platform."

---

## 6. Trust and trade-offs (slides 10–11, ~2 min)

> "Two things I'd want to know in your seat: can I trust it, and what did you compromise?"

> "On trust:
> * patient identifiers are masked by policy, and access is scoped by hospital
> * the pipeline enforces data-quality rules
> * the model separates risk well: the highest-risk tier readmits at 45% versus 9% for the lowest
> * every AI output is reviewed by a nurse and audited."

> "On trade-offs, three deliberate choices.
> * I built on **synthetic data shaped like Cedarbrook's**, so we'd have zero PHI risk and every number reproduces. The AI extraction was 100% accurate on it, but
>   real notes are messier, so re-validating that is the first thing in the pilot.
> * I let the data choose the model, and the **simpler logistic regression beat gradient boosting**. It's also easier for clinicians to trust.
> * I kept the **what-if fixed-rule and auditable** rather than modeled, on a simplified version of CMS's method, so Finance can reproduce it.
>   It assumes the follow-up effect is causal, which the pilot will test."

---

## 7. Path to production and the ask (slide 12, ~1 min)

> "Here's what I'd propose: a **90-day pilot on 6 North**.
> * The first month: connect your real Epic feeds into the same pipeline.
> * The second month: validate the AI and the model on your data with your nurses and Quality team.
> * The third month: 6 North works from the worklist every day, and we measure weekend follow-up, contact within 48 hours, and readmissions weekly."

> "Success is weekend follow-up going from 18% to 80%, and readmissions trending back toward 15%. If we hit that, we scale to all heart failure at CUMC,
> then COPD and pneumonia, then Fairhaven and Pine Hollow."

*To the executive:*
> "What I need from you is a sponsor for the pilot and a decision on weekend follow-up coverage. Would you be open to that?"

---

## 8. Objection handling

Answer the person who asked, at their altitude, then bridge to the other stakeholder in one sentence.
Pattern: **acknowledge → answer with a number or a fact → connect to the outcome**.

### From the business stakeholder (cost, risk, time to value)

**"What does this cost?"**
> "There are two pieces. The platform runs serverless and pay-per-use. The heaviest step was reading all 16,600 notes with AI once, and after that it only processes
> new notes, a few hundred a week. The serving database is the smallest size. I'd size it precisely with your team in the pilot, but the run cost is small
> next to a $238,000 penalty reduction on one unit. The bigger cost decision is the operational one: weekend follow-up coverage, which we estimate at around
> $60,000 a year against $238,000 in avoided penalty."
*Bridge to tech:* "And because it's one platform, you're not paying to integrate five tools."

**"How quickly do we see value?"**
> "The penalty is calculated on a rolling performance period, so the ERR improves as the readmissions you avoid roll into the window. Operationally, value
> starts the first week nurses work the list. We track weekend follow-up weekly. The pilot is 90 days, and the data connection is the longest part, about four weeks."

**"How do I know the $240K is real?"**
> "Three things. It's fixed-rule: additional follow-ups × the measured readmission gap, then CMS's penalty formula. Your finance team can reproduce it line by line.
> I'm also explicit about the assumption: it treats the follow-up effect as causal. And the pilot is designed to prove it: we measure 6 North against the other
> units before and after."

**"Why does the savings curve jump? 70% gives $119K but 80% gives $238K."**
> "Good catch. CUMC is currently above the 3% cap. Uncapped it would be $1.68M, but the cap holds it at $1.62M. So the first $60,000 of improvement is absorbed by
> the cap, and every dollar after that is real savings."

**"What's the risk of AI giving bad clinical advice?"**
> "The AI never acts on its own. It drafts, and a nurse reviews, edits and approves. The prompt restricts it to this patient's facts, it's labelled as an AI draft,
> and every approval is audited with who approved it and when. The model behind the risk score is a transparent logistic regression with per-patient reasons."

**"Our EHR vendor already has a readmission risk score. Why this?"**
> "A risk score alone doesn't tell you *why* readmissions went up on one unit, or what it costs you. What's new here is connecting the operational cause, the
> free-text risk factors, the nurse's actions and the HRRP dollars. We can also bring your existing vendor score in as a feature and compare."

**"What about PHI and HIPAA?"**
> "Patient identifiers are masked by policy for anyone who isn't on the care team, access is restricted by hospital, and everything is audited and traceable.
> For the prototype we used synthetic data, so no real patient data was touched."

### From the technical stakeholder (architecture, data quality, security, integration)

**"How does this integrate with Epic?"**
> "The pipeline starts from file or stream extracts in a governed landing zone. In production that's Epic Clarity / Caboodle extracts via Lakeflow Connect or
> JDBC, or HL7/FHIR ADT messages for near-real-time discharges. Bronze is schema-on-read with Auto Loader, so we map your feeds to the same silver
> schema and everything downstream (gold, model, app) is unchanged."
*Bridge to business:* "So the four-week connect phase is mapping, not rebuilding."

**"How do you handle data quality?"**
> "Lakeflow expectations on every silver table: valid IDs, discharge after admit, valid reference rates. Invalid rows are dropped and counted, and bad reference
> data fails the update. We planted defects to prove it: 6 bad timestamps and 45 duplicates, all caught, and it's in the event log. Every story number is
> re-checked by a validation notebook, 27 of 27 checks, on every run."

**"How is PHI secured, technically?"**
> "Unity Catalog column masks on the PHI columns of the patients table, declared in the pipeline. A row-filter function on the patient-level score table scopes
> rows by hospital. Both read an entitlements table that maps to account groups in production. Tags classify the data as RESTRICTED. The app runs as its own
> service principal with least privilege: read-only on the served tables, and owner only of its own write schema in Postgres. Lineage is captured end to end."

**"Why Lakebase? Why not just query the warehouse from the app?"**
> "The app is operational: many small reads and writes with concurrent nurses, sub-second. That's an OLTP pattern. Lakebase gives us Postgres latency and
> transactions for plan approvals and tasks, while staying in Unity Catalog. Gold tables sync in. The app's writes are readable back in UC, so Genie and
> Quality can report on what nurses did, with no separate ETL."

**"How fresh is the data in the app?"**
> "Today the synced tables use snapshot mode, refreshed at the end of each pipeline run. In production I'd enable Change Data Feed on the gold tables and switch to
> triggered or continuous sync, and run the pipeline on discharge-event triggers. Then a weekend discharge reaches the worklist within minutes."

**"How accurate is the AI extraction, really?"**
> "It ran on all 16,584 notes with zero errors and matched ground truth 100%, but I won't oversell that, because the synthetic notes are uniform. The extraction
> uses structured output with an evidence quote, so every flag is explainable. In the pilot, RNs review a stratified sample of real notes and we report
> precision and recall before the flags are trusted in the model."

**"What about model drift and monitoring?"**
> "Training uses a time-based split, testing on the most recent 20 weeks. The champion is re-selected by test AUC and registered in UC with an alias, so
> scoring always pulls `@champion`. Calibration by decile is logged in MLflow. In production I'd add Lakehouse Monitoring on the score table for drift and
> retrain on a schedule."

**"How does the AI cost scale?"**
> "The extraction is an incremental streaming table, so each note goes to the model exactly once. The first full pass took about 24 minutes. Incremental
> reruns take about 2 minutes. Volume scales with new discharges, not with history."

**"How is it deployed and operated?"**
> "One Databricks Asset Bundle defines the schemas, volumes, pipeline, 11-task job, dashboard and app. `bundle deploy` and `bundle run` rebuild it in any
> workspace, and it's in Git with CI-friendly validation."

**"What would you change for production?"**
> "Four things:
> * account groups instead of the entitlements table
> * CDF plus triggered sync for freshness
> * real EHR connectors
> * the full CMS method: 3-year, risk-adjusted, Medicare fee-for-service only."

### Switching altitude mid-answer (practice line)
> *"…technically, that's a column mask declared in the pipeline that checks the user's entitlement. **What that means for you** is that a finance analyst can
> use Genie on the same data without ever seeing a patient's name."*

---

## 9. Closing (30 seconds)

> "To summarize: one unit's weekend follow-up gap is costing about $240,000 a year, with a path to nearly $900,000 across CUMC. The platform shows
> why it's happening, who to call today, and what each call is worth, all governed and audited. I'd like to propose the 90-day pilot on 6 North.
> What would you need to see to move forward?"

---

## Rehearsal checklist

* [ ] Say the headline number in the first 60 seconds
* [ ] Every demo stop: tell → show → tell (say what it means for the business)
* [ ] Use the buyer's words: ERR, HRRP penalty, 7-day follow-up, readmission rate, not product names first
* [ ] When the technical persona asks, go deep, then bridge back to the outcome in one sentence
* [ ] Name the assumptions yourself (causality, the pharmacist cost, synthetic notes) before they're raised as objections
* [ ] End with a concrete ask and a question
