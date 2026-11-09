---
marp: true
paginate: true
title: Readmission Command Center, Cedarbrook Health
---

<!-- Deck text for submission. Attach this .md file directly, or render it with Marp (`marp docs/deck.md --pdf`) to get a PDF with selectable text. -->

# See readmission peaks as they start, and stop them at discharge

**Readmission Command Center for Cedarbrook Health**, on the Databricks Data Intelligence Platform

**~$240K a year** in avoidable HRRP penalty on one unit · path to **~$874K** across CUMC

*Prototype on synthetic Cedarbrook data. No real patients.*

---

# Booking a 7-day follow-up for weekend heart-failure discharges is worth ~$240K a year on one unit

| Owner | Their number | Today → with the fix |
|---|---|---|
| **CFO** | HRRP penalty | **$1.62M → $1.38M (–$238K/yr)**; –$874K across CUMC HF |
| **VP of Quality** | HF excess readmission ratio (ERR) | **1.19 → 1.14**; ~7 readmissions avoided/yr |
| **Manager of Transitional Care** | Weekend 7-day follow-up booked | **18% → 80%**; every high-risk discharge briefed |

**For the CFO:** a $1.14M penalty line becomes a $238K decision you can fund this quarter.
**For the Transitional Care Manager:** every discharge comes with a risk score and a 2-sentence briefing: who to call today, and why.

---

# Under HRRP, one unit's readmissions can cut a hospital's Medicare payments

- Cedarbrook Health: 3 hospitals. Flagship **CUMC, 538 beds**
- CMS HRRP cuts payments on **all** Medicare discharges, by up to **3%**, when 30-day readmissions exceed expected. The ERR is publicly reported.
- CUMC estimated penalty **$1.62M**, already **at the 3% cap** of $54M base payments. System total **~$2.08M**
- **Heart failure is the largest line: $1.14M, ERR 1.19**

**For the CFO and the VP of Quality:** one penalty, one publicly reported ratio, one shared problem.

---

# Four leaders, four numbers, one root cause

| Role | Measured on | Today | Target |
|---|---|---|---|
| **CFO** | HRRP penalty $ | $1.62M (HF $1.14M) | –$238K on 6 North; –$874K CUMC HF |
| **VP of Quality** | HF ERR; HF 30-day readmission rate | ERR 1.19; 6 North 23.9% | ERR 1.14; ~15% |
| **Manager of Transitional Care** | 7-day follow-up booked; high-risk contacted ≤ 48h | Weekend 18% (weekday 69%); 41 of 54 high-risk with no follow-up | ≥ 80%; ≥ 90% |
| **CIO / CDAO** | Integration cost, PHI risk, time-to-insight | 5 silos, multiple PHI copies | 1 governed copy; ~2 min refresh |

**All four numbers move with one action: a 7-day follow-up booked before a high-risk patient goes home.**

---

# One unit's heart-failure readmissions jumped 9 points, and it was found out months too late

- 6 North HF 30-day readmissions: **14.8% → 23.9%** in 20 weeks (+9.1 pts)
- Every other unit stayed within **±1.5 pts**
- Found **after the fact**, in quality reports and the penalty estimate
- Unanswered: **When did it start? Why?**

**For the VP of Quality:** the ratio CMS reports moved before anyone could explain it.

---

# The answer was in the data, but discharges, predictions and follow-ups never met

**1. Siloed data**
- Discharges, follow-ups, notes and penalty data each live in a separate system
- **The readmission prediction is disconnected from the discharge**: calculated weeks later, not in front of the nurse
- No trend view of readmissions by unit

**2. Complicated infrastructure**
- A warehouse, a lake, BI and an app database, each with its own PHI copy
- Every question is an IT project; Quality's and Finance's numbers don't match

**3. Limited ML and AI**
- No governed way to put a model in the workflow, use AI on notes, learn from nurses, or check that AI answers are right

**For the CIO:** every new question meant another copy of PHI and another integration.

---

# Unify discharges, predictions and follow-ups, and the root cause appears: no 7-day follow-up, especially on weekends

1. **When:** readmissions over time by unit pinpoint when 6 North's peak started *(VP of Quality)*
2. **Why:** weekend HF discharges with a booked 7-day follow-up fell to **18%**, vs **69%** on weekdays *(Transitional Care)*
3. **So what:** no 7-day follow-up → **29.8%** readmit, vs **16.4%** with one *(VP of Quality, CFO)*
4. **Who, right now:** every discharge carries its prediction and an AI nurse briefing, so high-risk patients are caught before they go home

**Not a clinical mystery: a missing follow-up appointment, a process gap the team can fix.**

---

# Every 10 points of weekend follow-up on 6 North is worth ~$120K in avoided penalty

| Weekend 7-day follow-up booked | Readmissions avoided / yr | HF ERR | Penalty saved / yr |
|---|---|---|---|
| 70% | 3.9 | 1.16 | $119K |
| **80% (target)** | **6.5** | **1.14** | **$238K** |
| 90% | 9.1 | 1.12 | $358K |
| 100% | 11.8 | 1.10 | $478K |

Scaled: all CUMC weekend HF **~$412K** · all CUMC HF **~$874K** · fixed-rule, reproducible by Finance

**For the CFO:** –$238K on 6 North; ~4× payback on ~$60K/yr of weekend follow-up capacity *(assumption)*; –$874K at hospital scale.
**For the VP of Quality:** HF ERR 1.19 → 1.14, toward the 1.00 benchmark.
**For the Manager of Transitional Care:** 54 high-risk patients in the window today, 41 with no follow-up. Booking those is how weekend follow-up gets from 18% to 80%.

---

# One platform that sees the peak, explains it, acts on every discharge, and learns from every nurse

1. **Unify:** discharges, follow-ups, notes and penalty data in one governed place
2. **Predict:** a 30-day readmission risk for every discharge, attached to the discharge record
3. **Visualize:** readmissions over time by unit
4. **Brief and act:** an AI nurse briefing; an AI-drafted plan the RN approves; outreach tasks created automatically
5. **Measure:** ERR and penalty dollars per booked follow-up; Genie for any question
6. **Learn:** every RN edit or rejection becomes a weak label for retraining

**Transitional Care:** 4 and 6 · **VP of Quality:** 3 and 5 · **CFO:** 5 · **CIO:** 1, on one platform

---

# A Friday discharge, from raw record to an RN-approved plan, and back into the model

1. **Raw data:** the discharge record, the appointment (none booked) and the note *"patient to call the clinic on Monday… lives alone"*
2. **Lakeflow:** ingest, data-quality rules, gold tables joining discharge, follow-up, outcome and trend
3. **Unity Catalog:** one governed copy; PHI masked for analysts; note quotes for care-transitions only
4. **AI Functions:** *lives alone*, *patient to call*, plus an evidence quote
5. **Prediction** (MLflow, UC champion): **High**. No 7-day follow-up +16.8 pts; lives alone +13.5 pts
6. **AI nurse briefing:** *"45% readmission risk driven by no 7-day follow-up (16.8 pts)… Immediately book the 7-day follow-up and initiate home health referral."*
7. **Lakebase + Databricks App:** Claude drafts the plan; the **RN edits** (95% similar, +107 chars) and approves; tasks are written back
8. **Closed loop:** the edit becomes a weak label, and the next training run logs it
9. **HRRP:** ERR 1.19 → 1.14 · **Genie:** weekend vs weekday follow-up = 17.7% vs 68.6%, LLM-judge verified

**The discharge, its prediction and its follow-up finally live together, and every nurse decision teaches the system.**

---

# Every reason Cedarbrook couldn't solve this has a direct answer on one platform

| Challenge | Databricks capability | Proof |
|---|---|---|
| Siloed data; prediction disconnected | Lakeflow + one gold layer; AI/BI trend; event-triggered scoring in production | 9 feeds, one pipeline; bad records caught |
| Complicated infrastructure | One platform: Lakeflow, SQL, AI/BI, Lakebase, Apps; Asset Bundles; serverless | One bundle; Lakebase 9/9 identical to source |
| PHI governance | Unity Catalog: PHI masks, role-based mask on note quotes, row filters, lineage | Masked for analysts; 3,424 of 14,475 rows for a scoped user |
| Limited ML | MLflow + UC model registry; scores in the worklist | AUC 0.72; High 45% vs Low 9% observed |
| AI on clinical notes | AI Functions (extraction, briefings); Foundation Model API with RN approval | 16,584 notes, 0 errors; 705/705 briefings |
| Can't learn from the frontline | Lakebase write-back read in UC → weak labels → retraining signals | 3 reviewed plans, 33% edit rate in MLflow |
| Can't trust AI answers | Genie plus an LLM judge vs SQL reference answers, every run | 5/5 PASS |

**For the CIO:** separate systems became one governed platform, and the quality gates run on every refresh.

---

# Demo: five stops, from the peak to a briefed patient to an approved plan to the dollars

1. **Unit Trends:** when did the peak start, and why? *(VP of Quality)*
2. **Worklist:** each discharge with its prediction and an AI nurse briefing *(Transitional Care)*
3. **Patient:** note evidence → Claude drafts → the RN **edits** and approves → tasks created *(Transitional Care)*
4. **HRRP & What-if:** slider to 80% → ERR 1.14, $238K *(CFO, VP of Quality)*
5. **Ask Genie:** weekend vs weekday follow-up on 6 North, judged correct every run *(CIO)*

---

# Insight → action → dollars, in one workflow that learns

- **For the CFO:** each booked follow-up is visible as penalty dollars, with a method your team can audit
- **For the VP of Quality:** see the next peak the week it starts; track the ERR moving
- **For the Manager of Transitional Care:** a briefed worklist (41 high-risk without a follow-up); plans drafted in 4.4 s for your approval; your edits improve the next draft
- **For the CIO:** one governed copy; AI quality gated on every run

---

# Built to be trusted, measured every run, and honest about its limits

**Trust and quality gates**
- PHI masked; AI note quotes masked by role; hospital row filters; least-privilege app identity; lineage and audit
- The prediction separates risk: High 45% vs Low 9% (AUC 0.72)
- Genie checked by an LLM judge against SQL reference answers: 5/5 every run
- Briefings grounded in the patient's own record; AI drafts, the RN decides
- It ran end to end: 11/11 job tasks, 33/33 checks

**Trade-offs**
- **Synthetic data:** zero PHI risk, reproducible. *Real notes are messier, so re-validate in the pilot.*
- **The simpler model won** (0.7245 vs 0.7137): clinician-explainable. *Champion re-selected each run.*
- **A fixed-rule what-if** on a simplified HRRP method: auditable. *It assumes causality.*

Limits: the feedback loop has 3 reviewed plans so far; real-time scoring at discharge is the production design.

---

# A 90-day pilot on 6 North proves the $240K before scaling hospital-wide

- **Weeks 0–4:** Epic Clarity / FHIR feeds; event-triggered scoring at discharge
- **Weeks 4–8:** RN validation of AI on real notes; model recalibration; Quality confirms the ERR method
- **Weeks 8–12:** 6 North works the briefed worklist daily; weekly KPI review
- **Then:** all CUMC HF (~$874K) → COPD and pneumonia → the other two hospitals

| Role | Pilot success metric | Ask |
|---|---|---|
| **CFO** | Penalty trajectory toward –$238K | Fund weekend follow-up capacity |
| **VP of Quality** | 6 North HF readmissions toward ~15%; the ERR trend | Executive sponsor; chair the weekly KPI review |
| **Manager of Transitional Care** | Weekend follow-up ≥ 80%; ≥ 90% of high-risk contacted ≤ 48h | A 6 North nurse champion |
| **CIO** | Feeds connected; quality gates green | Data access and an Epic integration contact |

**What would you need to see to move forward?**

---

# Appendix: how it's built and how we know it ran

- **Lakeflow** (serverless SQL): 9 raw feeds → bronze → silver (data-quality rules, PHI masks) → 10 gold tables
- **AI Functions** (Claude Haiku): 16,584 notes → structured flags, processed once (incremental); 705 nurse briefings
- **MLflow + Unity Catalog:** champion `readmit_30d_risk@champion` (logistic regression, AUC 0.7245); retraining signals from RN feedback
- **Lakebase** (Postgres) serves the app; app writes are read back in Unity Catalog
- **Databricks App** (FastAPI): Claude Sonnet drafts plans; Genie API; one Asset Bundle with an 11-task job
- **Evidence:** job run 601827272748584, 11/11 tasks, 33/33 checks, all committed as text: github.com/MelissaPang/readmission-command-center
- **Assumptions:** simplified HRRP method (12 months, all payers); the follow-up effect treated as causal; the ~$60K/yr follow-up capacity is illustrative; synthetic data
