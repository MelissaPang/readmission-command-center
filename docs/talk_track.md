# Talk Track: Readmission Command Center for Cedarbrook Health

**How to use this script.** It follows the 14-page deck in order. Each page has what to say, then a **transition line** (→) that carries you into the next page, so the talk flows without pauses. Lines in quotes are meant to be spoken roughly as written; *italics* are stage directions. The live demo sits between page 11 and page 12.

**Who is in the room.** The role-play has two personas. The **business stakeholder** speaks for Jordan Whitfield (CFO) and Dr. Elena Vasquez (VP of Quality). The **technical stakeholder** speaks for Kenji Tanaka (Chief Data & Analytics Officer). Priya Raman, RN (Manager of Transitional Care) is the app's main user. If the personas introduce themselves with other names, use their names and keep the same roles.

**Timing:** about 22 minutes of presenting, then Q&A.

**Before you start (5 minutes before):**

- Open the app and wait for **Unit Trends** to load. This also wakes up the SQL warehouse.
- In **Discharge Worklist**, filter to CUMC · 6 North · High · No 7-day follow-up, and pick a weekend heart-failure patient with **no plan** yet.
- Open **Ask Genie** in a second browser tab, with the question ready to paste.
- Have the deck on page 1.

---

## Page 1: Title, "See readmission peaks early, stop them at discharge" (about 1 minute)

*Smile, pause, and start slowly. This page is about making the room comfortable.*

"Thank you both for making the time today. I know your calendars are full, so I'll keep this practical."

"I want to talk about something every hospital leader recognizes: a readmission problem that shows up in the numbers long before anyone can explain it. At Cedarbrook, it's on one unit, it's in heart failure, and it's costing real money."

"Here's my plan for our time. First, what we found in Cedarbrook's data and what it's worth. Then I'll show you, live, how your care-transitions nurses and your finance team would use it day to day. After that, a short look at how it's built and what it takes to go live. I'll keep plenty of time for your questions, so please jump in at any point."

"And if you remember one number from today, it's this one: **about $240,000 a year** in avoidable penalty, on one unit, with a path to about **$874,000** across the hospital."

→ *Transition:* "Let me show you exactly where that number comes from, and who it matters to."

---

## Page 2: One action, three numbers (about 1.5 minutes)

"The headline is simple: **booking a 7-day follow-up for weekend heart-failure discharges is worth about $240,000 a year on one unit.** And the fix is operational, not clinical."

*Point at each card as you name its owner.*

"Jordan, this first one is yours. The HRRP penalty goes from $1.62 million to **$1.38 million**. That's $238,000 a year on 6 North, and about $874,000 if we apply it to all heart failure at CUMC. A $1.14 million penalty line becomes a decision you can fund this quarter."

"Dr. Vasquez, the heart-failure excess readmission ratio goes from 1.19 to **1.14**. That's about seven readmissions avoided a year, and those are patients who don't come back."

"And for Priya's team, weekend 7-day follow-up goes from 18% to **80%**. Every high-risk discharge comes with a two-sentence briefing: who to call today, and why."

"Three leaders, three numbers, and they all move with one action."

→ *Transition:* "To see why these numbers matter so much, let me take one minute on the stakes."

---

## Page 3: The stakes, "Under HRRP, one unit's readmissions can cut a hospital's Medicare payments" (about 1.5 minutes)

"Cedarbrook runs three hospitals, and the flagship, CUMC, has 538 beds."

"Under CMS's Hospital Readmissions Reduction Program, when readmissions run above expected, CMS cuts payments on **all** Medicare discharges, by up to 3%. So a problem on one unit becomes a payment cut for the whole hospital. And the ratio behind it is publicly reported."

*Point at the bar chart.*

"CUMC's estimated penalty is **$1.62 million**, and that's already at the 3% cap. Heart failure is the largest line by far, at **$1.14 million**, with a ratio of 1.19. Across the system, it's about $2.08 million."

"Jordan, Dr. Vasquez, this is one penalty and one publicly reported ratio, and that makes it a shared problem."

→ *Transition:* "And since it's shared, it helps to be precise about who owns which part of it."

---

## Page 4: Who owns the number, "Four leaders, four numbers, one root cause" (about 1 minute)

"Here's how the accountability lines up."

- "**Jordan** owns the HRRP penalty: $1.62 million today, with heart failure at $1.14 million."
- "**Dr. Vasquez** owns the heart-failure ratio and the 30-day rate: 1.19 today, and 6 North at 23.9%."
- "**Priya** owns the 7-day follow-up rate. Today it's 18% on weekends against 69% on weekdays, and 41 of 54 high-risk patients have no follow-up booked."
- "**Kenji** owns the platform: today that's five siloed systems and multiple copies of patient data."

*Point at the dark banner at the bottom.*

"And the reason I put all four on one page is the line at the bottom: **all four numbers move with one action**, a 7-day follow-up booked before a high-risk patient goes home."

→ *Transition:* "So how did Cedarbrook end up here? It started with a peak that nobody saw coming."

---

## Page 5: The peak nobody saw coming, "One unit's heart-failure readmissions jumped 9 points" (about 1 minute)

*Trace the red line with your hand.*

"On 6 North Telemetry, heart-failure readmissions climbed from **14.8% to 23.9%** in twenty weeks. That's nine points. Every other unit, the grey line, stayed flat, within about a point and a half."

"Cedarbrook found out the way most hospitals do: after the fact, from the quality report and the penalty estimate. By then, months of patients had already come back."

"Dr. Vasquez, this ratio is yours to answer for, and the first question anyone asks is the one nobody could answer: **when did it start, and why?**"

→ *Transition:* "That's not because people weren't looking. It's because the data made the answer impossible to see."

---

## Page 6: Why it stayed unsolved, "Discharges, predictions and follow-ups never met" (about 1.5 minutes)

"There are three reasons, and they'll sound familiar."

"**First, siloed data.** Discharges, follow-up appointments, notes and penalty data each sit in a different system. And the most important gap: the readmission prediction is calculated weeks later, if at all. It's never in front of the nurse at the moment a follow-up can still be booked. There's also no view of readmissions over time by unit."

"**Second, complicated infrastructure.** A warehouse, a lake, BI and an app database, each with its own copy of patient data. Every new question becomes an IT project, and Quality's numbers and Finance's numbers don't match."

"**Third, limited ML and AI.** There's no governed way to put a model into the workflow, no safe way to use AI on clinical notes or learn from what nurses do, and no way to check whether an AI answer is right."

*Look at the technical stakeholder.*

"Kenji, I suspect you've lived this: every new question meant another copy of PHI and another integration. This is a scenario typical of multi-hospital systems, so we'd confirm the specifics together."

→ *Transition:* "Now here's what happens when you finally put those pieces together."

---

## Page 7: The root cause, "No 7-day follow-up, especially on weekends" (about 1.5 minutes)

"Once discharges, predictions and follow-ups live in one place and are trended over time, the answer appears in four steps."

- "**When:** the unit trend pinpoints exactly where 6 North's peak starts. That's Dr. Vasquez's question answered."
- "**Why:** weekend heart-failure discharges with a booked follow-up fell to **18%**, against **69%** on weekdays. That's Priya's lever."
- "**So what:** patients without a 7-day follow-up readmit at **29.8%**, compared with **16.4%** with one. Nearly double. That's what drives Jordan's penalty."
- "**Who, right now:** every discharge now carries a prediction and a nurse briefing, so the care team can act before the patient goes home."

*Point at the dark box.*

"So this isn't a clinical mystery. It's a missing follow-up appointment, and that's a process gap the team can fix."

→ *Transition:* "And because it's fixable, we can put a precise number on what fixing it is worth."

---

## Page 8: What fixing it is worth, "Every 10 points of weekend follow-up is worth ~$120K" (about 1.5 minutes)

"This is a fixed-rule calculation. No black box: Jordan, your team can reproduce every line."

*Walk down the table.*

"At 70% weekend follow-up, we avoid about four readmissions and save $119,000. At our target of **80%**, it's six and a half readmissions, the ratio drops to **1.14**, and the penalty falls by **$238,000**. At 90% it's $358,000, and at 100% it's $478,000."

"And it scales: about $412,000 if we apply it to weekend heart failure across CUMC, and about **$874,000** for all heart-failure discharges."

"Jordan, if restoring weekend follow-up capacity costs around $60,000 a year (that's my assumption, and we'd validate it with your team), that's roughly a four-times return. Dr. Vasquez, that's your ratio moving toward 1.00. And Priya, today there are 54 high-risk discharges, and 41 have no follow-up booked. Closing those is how we get from 18% to 80%."

→ *Transition:* "So that's the value. Let me show you the solution that delivers it."

---

## Page 9: The solution, "One platform that sees the peak, explains it, acts on every discharge, and learns from every nurse" (about 1.5 minutes)

"It works in six steps, left to right."

1. "**Unify:** one governed place for discharges, follow-ups, notes and penalty data. That's Kenji's foundation."
2. "**Predict:** a 30-day readmission risk on every discharge record."
3. "**Visualize:** readmissions over time by unit, so Dr. Vasquez sees a peak the week it starts."
4. "**Brief and act:** an AI nurse briefing, an AI-drafted care plan the nurse approves, and outreach tasks created automatically. That's Priya's daily workflow."
5. "**Measure:** the ratio and penalty dollars for every booked follow-up, plus Genie for any question. That's for Jordan and Dr. Vasquez."
6. "**Learn:** every time a nurse edits a plan, that edit becomes a signal for the next version of the model."

"Notice the dotted line at the bottom: **Learn feeds back into Predict.** The system gets better every time a nurse uses it."

→ *Transition:* "Kenji, I know your question will be whether this is really one platform, or five tools stitched together. Here's the proof."

---

## Page 10: Platform proof, "Every reason Cedarbrook couldn't solve this has a direct answer on one platform" (about 1.5 minutes)

*Speak mostly to the technical stakeholder, then bridge back.*

"Each challenge from earlier has a direct answer, and a proof point from the build."

- "**Siloed data:** Lakeflow brings nine feeds into one pipeline with data-quality rules. It caught the six invalid records and 45 duplicates we planted."
- "**Complicated infrastructure:** one platform, with Lakebase serving the app and everything deployed as one bundle. The app's data matches the source 9 out of 9 tables."
- "**PHI governance:** Unity Catalog masks patient identifiers. Clinical note quotes are visible only to care transitions, and access is scoped by hospital."
- "**Limited ML:** MLflow and the model registry. The model separates risk well: high-risk patients readmit at 45% against 9% for low."
- "**AI on notes:** AI read 16,584 notes with zero errors, wrote 705 nurse briefings, and drafts a plan in 4.4 seconds for nurse approval."
- "**Learning from the frontline:** nurse edits flow back as training signals. Three reviewed plans so far, with a 33% edit rate."
- "**Trusting AI answers:** an LLM judge checks Genie's answers on every run. Five out of five passed."

"Kenji, the short version: one governed copy, on one platform, with AI quality checked every time it runs."

→ *Transition:* "But you shouldn't have to take a slide's word for it, so let me show it to you."

---

## Page 11: The demo agenda, "Five stops: from the peak, to a briefed patient, to an approved plan, to the dollars" (about 30 seconds)

"I'll make five quick stops: first the peak, then today's worklist, then one patient from briefing to approved plan, then the dollars, and finally a plain-English question to Genie."

→ *Transition:* "Let's start where Dr. Vasquez's team would start their morning." *Switch to the app.*

---

## Live demo (about 8 minutes)

### Stop 1: Unit Trends (for Dr. Vasquez)

- **Tell:** "First, when did the peak start, and why?"
- **Show:** the KPI tiles (6 North 23.9%, up from 14.8%; weekend follow-up 18% vs 69%), the weekly line climbing after the late-June markers, and the red weekend bar dropping after June 19.
- **Tell:** "The peak and its cause, on one screen, with no query written. You'd see the next one the week it starts."
- → "So we know the cause. The next question is who to act on today."

### Stop 2: Discharge Worklist (for Priya)

- **Tell:** "This is Priya's list for today."
- **Show:** the filters CUMC · 6 North · High · No 7-day follow-up. Read one **Nurse briefing** aloud.
- **Tell:** "Every discharge has its risk attached and a two-sentence briefing, so it reads like a handoff, not a spreadsheet."
- → "Let's open one of these patients."

### Stop 3: Patient → AI plan → nurse edit → approve (for Priya and Kenji)

- **Show:** the briefing, the model's drivers with their points, and the note quote. Say: "That quote is visible to care transitions only. An analyst sees it masked."
- Click **Draft transition plan with AI**. "Claude drafts the plan in a few seconds, using only this patient's facts."
- **Edit** the draft. For example, under *Within 48 hours*, add: "Call patient today to book the HF Bridge Clinic slot before end of shift."
- Click **Approve plan & create outreach tasks**. Point at "RN edited (…% similar…)", then open the **Outreach Queue**.
- **Tell:** "The AI drafts, and the nurse decides. And that edit isn't lost: it becomes a training signal for the next version."
- → "Now let's see what that one booked follow-up means in Jordan's language."

### Stop 4: HRRP & What-if (for Jordan and Dr. Vasquez)

- **Show:** $1.62M at the cap, heart failure $1.14M, ratio 1.19. Move the slider from about 55% to **80%**: about 6.5 avoided, ratio **1.14**, **$238K** saved. Switch the scope to **CUMC all HF** to show about **$874K**.
- **Tell:** "Every follow-up Priya's team books shows up right here."
- → "Last stop. What about the questions nobody built a dashboard for?"

### Stop 5: Ask Genie (for Kenji)

- **Show:** paste "Compare 7-day follow-up booking on 6 North for weekend vs weekday HF discharges since 2026-06-19." Genie answers 17.7% vs 68.6%. Expand the SQL.
- **Tell:** "Plain English in, a verified answer out, on the same governed data. An LLM judge checks Genie's answers on every run."
- → *Switch back to the deck.* "So let me bring that back to what it means for each of you."

---

## Page 12: What it means for you, "Insight → action → dollars, in one workflow that learns" (about 1 minute)

*Go around the four cards and make eye contact with each owner.*

"Jordan, every booked follow-up is now visible as penalty dollars, using a method your team can audit."

"Dr. Vasquez, you see the next peak the week it starts, and you can track the ratio moving."

"Priya's team gets a briefed worklist (41 high-risk patients without a follow-up today), plans drafted in 4.4 seconds for their approval, and every edit makes the next draft better."

"And Kenji, it's one governed copy, with AI quality checked on every run."

→ *Transition:* "Now, I'd want two things answered in your seat: can I trust it, and what did you compromise? So let me be direct about both."

---

## Page 13: Trust and quality, "Built to be trusted, measured every run, and honest about its limits" (about 1.5 minutes)

"On **trust**:"

- "Patient identifiers are masked, and AI note quotes are masked by role."
- "Access is scoped by hospital, the app runs with least privilege, and everything has lineage and an audit trail."
- "The model separates risk clearly: 45% for high-risk patients against 9% for low."
- "Genie is checked by an LLM judge on every run, and it passed 5 out of 5."
- "Briefings come only from each patient's own record. The AI drafts and the nurse decides."
- "And it ran end to end: 11 of 11 tasks, and all 33 checks passed."

"On **trade-offs**, three honest choices:"

- "We used **synthetic data**, so there's zero PHI risk. Real notes are messier, so re-validating the AI is the first thing we'd do in the pilot."
- "The **simpler model won**, 0.7245 against 0.7137. It's easier for clinicians to trust, though it has less headroom."
- "The **what-if is fixed-rule** so Finance can reproduce it. It assumes the follow-up effect is causal, and it simplifies CMS's three-year method."

"And the stated limits: only three reviewed plans so far, and real-time scoring at discharge is the production design."

→ *Transition:* "Which brings me to how we'd prove all of this on Cedarbrook's real data."

---

## Page 14: The 90-day pilot, "A 90-day pilot on 6 North proves the $240K before scaling hospital-wide" (about 1.5 minutes)

"Here's what I'd propose: a **90-day pilot on 6 North**."

"In weeks one to four, we connect your Epic feeds and turn on scoring at discharge. In weeks four to eight, Priya's nurses validate the AI on real notes, we recalibrate the model, and Dr. Vasquez's team confirms the ratio method. In weeks eight to twelve, 6 North works the briefed worklist every day, with a weekly KPI review. Then we scale: all CUMC heart failure at about $874,000, then COPD and pneumonia, then the other two hospitals."

*Walk the table, one owner at a time.*

- "**Jordan:** success is the penalty heading toward minus $238,000. My ask is funding for weekend follow-up capacity."
- "**Dr. Vasquez:** success is 6 North heading back toward 15%. My ask is that you sponsor the pilot and chair the weekly review."
- "**Priya:** success is weekend follow-up at 80% or better, with 90% of high-risk patients contacted within 48 hours. The ask is a nurse champion on 6 North."
- "**Kenji:** success is feeds connected and quality gates green. The ask is data access and an Epic integration contact."

*Pause. Then ask the question on the slide, and stop talking.*

"**What would you need to see to move forward?**"

---

## Closing (if you need one before Q&A, about 20 seconds)

"To sum up: a weekend follow-up gap on one unit is costing about $240,000 a year, with a path to nearly $900,000 across CUMC. The platform shows when it started and why, who to call today, and what each call is worth, and it learns from every nurse. I'd love to start with 6 North."

---

## Q&A: prepared answers

Pattern: **acknowledge → answer with their number → bridge to the other person in one sentence.**

### Business stakeholder (Jordan, CFO / Dr. Vasquez, VP of Quality)

**"What does this cost?"** "The platform is serverless and pay-per-use. The heaviest step, AI reading all the notes, ran once, and after that it only reads new notes. The bigger decision is operational: weekend follow-up capacity, around $60,000 a year by my assumption, against $238,000 of penalty." *Bridge:* "And Kenji, because it's one platform, there's no integration bill for five tools."

**"How do I know the $238K is real?"** "It's fixed-rule: additional follow-ups times the readmission gap we measured, run through CMS's formula, so your team can reproduce it. The one assumption I'll name is causality, and the pilot is designed to test it by comparing 6 North with the other units, before and after."

**"Why does 70% save $119K but 80% save $238K?"** "CUMC is above the 3% cap. Uncapped, the penalty would be $1.68 million. So the first $60,000 of improvement is absorbed by the cap, and after that every dollar is real savings."

**"Will this move our public ratio, and when?"** "The ratio is calculated on a rolling period, so avoided readmissions roll into it over time. That's why the pilot tracks 6 North's rate weekly: it's the leading indicator, and the ratio follows."

**"Is AI telling our nurses what to do?"** "No. The AI drafts and briefs, and a nurse reviews, edits and approves. It only uses the patient's own facts, it's labeled as an AI draft, and every approval and edit is audited."

**"Our EHR vendor already has a readmission score."** "A score alone doesn't tell you why readmissions rose on one unit, or what it costs you. What's new here is joining the cause, the free-text risk, the nurse's action and the dollars. We can bring your vendor score in as a feature and compare."

**"How fast is time to value?"** "Operational value starts the first week nurses use the list. The pilot proves it in 90 days, and connecting the data is the longest part, about four weeks."

### Technical stakeholder (Kenji, CDAO)

**"How does this integrate with Epic?"** "We'd use Epic Clarity or Caboodle extracts through Lakeflow Connect, or HL7/FHIR messages for discharge events. We map your feeds to the same schema, and everything downstream stays the same." *Bridge:* "So, Jordan, the first four weeks are mapping, not rebuilding."

**"How do you handle data quality?"** "Every table has data-quality rules: valid IDs, discharge after admit, valid reference rates. Bad rows are dropped and counted. We planted defects to prove it (six bad timestamps and 45 duplicates), and all were caught. Then 33 validation checks run on every job."

**"How is patient data secured?"** "Unity Catalog masks patient identifiers. A role-based mask hides note quotes from anyone outside care transitions, and a row filter scopes access by hospital. The app runs with least privilege and can't read raw notes, and lineage runs end to end."

**"Why Lakebase instead of the warehouse?"** "The app has many small reads and writes from nurses at the same time, so it needs sub-second response. Lakebase gives Postgres speed and transactions, it stays in Unity Catalog, and the nurses' edits are readable for the learning loop with no extra ETL."

**"How fresh is the data?"** "Today it refreshes with each pipeline run, about two minutes incremental. In production we'd trigger the pipeline on discharge events, so a weekend discharge reaches the worklist within minutes."

**"How do you know the AI is right?"** "There are three checks. Note extraction is scored against known answers, and we'll re-validate on real notes. Briefings are written only from the patient's own record. And an LLM judge grades Genie against SQL-computed answers on every run."

**"Is the feedback loop real?"** "Yes, it's real and running. The app records how much the nurse changed each plan, a pipeline turns that into training signals, and the model training logs them. It's small today, three plans, but the plumbing is done."

**"What would you change for production?"** "Account groups instead of an entitlements table, change-data-feed sync for freshness, real Epic connectors, and the full CMS method: three years, risk-adjusted, Medicare only."

### Practice line for switching altitude

"…technically, it's a column mask that checks the user's role before returning the note. **What that means for you, Jordan**, is that your finance analysts can use Genie on the same data without ever seeing a patient's clinical note."

---

## Rehearsal checklist

- Open warmly, and say the $240K number within the first minute.
- Say every transition line (→) out loud. That's what makes it feel smooth.
- Name the owner every time you say a number.
- In demo stop 3, edit the plan before approving it.
- Name the assumptions yourself (the causal effect, the ~$60K capacity, synthetic data) before anyone asks.
- On page 14, ask the question and then stop talking.
