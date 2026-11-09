# Submission answers: Readmission Command Center (Cedarbrook Health)

*All figures come from the prototype run on synthetic Cedarbrook data (job run `601827272748584`: 11/11 tasks, 33/33 validation checks). Items marked (assumption) are illustrative.*

---

## 1. What is the business challenge you are solving?

Cedarbrook Health, a three-hospital system, is paying Medicare penalties for heart-failure readmissions it discovered months too late.
On 6 North Telemetry at the flagship Cedarbrook University Medical Center (CUMC, 538 beds), heart-failure 30-day readmissions rose from **14.8% to 23.9%** in 20 weeks. Every other unit stayed within 1.5 points.
Under CMS's Hospital Readmissions Reduction Program (HRRP), that drives a payment cut on *all* Medicare discharges. CUMC's estimated penalty is **$1.62M**, already at the 3% cap. Heart failure is the largest line at **$1.14M**, with an excess readmission ratio (ERR) of **1.19**.

Each number has an accountable owner (fictional leadership):
* **Jordan Whitfield, CFO** owns the HRRP penalty.
* **Dr. Elena Vasquez, VP of Quality & Patient Safety** owns the publicly reported HF ERR.
* **Priya Raman, RN, Manager of Transitional Care** owns the 7-day follow-up rate.
* **Kenji Tanaka, Chief Data & Analytics Officer** owns the platform.

Nobody could answer *when the peak started or why*, because the answer was locked in silos:
* **Siloed data:**
  * discharge records, follow-up appointments, clinical notes and penalty data live in separate systems
  * the **readmission prediction is disconnected from the discharge**: it's calculated weeks later, if at all, never in front of the nurse when a follow-up can still be booked
  * there's no view of readmissions over time by unit
* **Complicated infrastructure:** a warehouse, a lake, BI and an app database, each with its own copy of patient data. Every question is an IT project, and Quality's and Finance's numbers don't match.
* **Limited ML and AI capability:**
  * no governed way to put a model into the nurse's workflow
  * no safe way to use AI on clinical notes
  * no way to learn from what nurses do, or check that AI answers are right

## 2. How does your Databricks solution address this challenge?

The Readmission Command Center unifies discharges, predictions and follow-ups on one governed platform. Once unified and trended over time, the root cause becomes obvious: **patients leaving without a 7-day follow-up, especially on weekends**. Only **18%** of weekend heart-failure discharges had one booked, vs **69%** on weekdays, and patients without one readmit at **29.8% vs 16.4%**.

It is one connected data journey:
* **Lakeflow** ingests 9 raw feeds incrementally, with data-quality rules (planted bad records caught), into gold tables that join every discharge to its follow-up status, outcome and unit trend.
* **Unity Catalog** governs one copy:
  * PHI column masks (analysts see `***MASKED***`)
  * a **role-based mask on AI-extracted note quotes** (care-transitions only)
  * hospital row filters, tags, lineage, and the model registry
* **AI Functions** read all **16,584** discharge notes inside the pipeline (0 errors), turning free text into structured risk flags. They also write a **2-sentence nurse briefing** for every worklist patient, grounded in the model's drivers.
* **ML (MLflow plus the UC registry):** a 30-day readmission model scores every discharge (AUC 0.72; High-risk patients readmit at 45% vs 9% for Low), with per-patient drivers.
* **Lakebase** serves the briefed worklist to the app in milliseconds, and stores what nurses do (approved plans, edits, outreach tasks). That write-back can be read in Unity Catalog.
* **A closed loop:** every nurse edit or rejection of an AI plan is captured as a weak label (`gold.plan_feedback`, `ml.retraining_signals`) and logged by the next training run.
* **Genie** answers plain-English questions on the same governed tables. An **LLM judge** grades its answers against SQL reference answers on every run (5/5 PASS).
* **The Databricks App** gives each leader their view:
  * Dr. Vasquez gets the unit trends
  * Priya gets the briefed worklist and Claude-drafted transition plans to edit and approve
  * Jordan gets the HRRP what-if
  * everyone can ask Genie

  An AI/BI dashboard covers executives.

## 3. What AI tools did you use, and what was your workflow?

**To build it:** Claude Code (an AI coding agent) as a teammate, driving the Databricks CLI and Asset Bundles from the terminal.

**Inside the product:**
* Claude Haiku via AI Functions (note extraction with structured output; nurse briefings)
* Claude Sonnet via the Foundation Model API (grounded transition plans for RN approval; the LLM judge for Genie)
* Genie for plain-English analytics
* MLflow and the Unity Catalog model registry

**Workflow:**
1. **Story as a contract:** the customer story was written with exact target numbers, and code checks every one.
2. **Verify before deploying:** a seeded synthetic data generator was validated locally against the same rules as the gold layer before anything touched the platform.
3. **Everything as code:** the pipeline, 10 notebooks, an 11-task job, the app and the dashboard are one bundle.
4. **Run → read the error → fix → rerun:** the agent diagnosed real issues from job output, including workspace tag policies, a shifted reporting window, NULL readmission flags, and an app permission block on Lakebase. It asked before anything destructive.
5. **Quality gates:** a validation notebook (33 checks) and the Genie LLM judge run on every job run.
6. **Evidence as text,** committed at every milestone: executed notebooks, event logs, query results, live app responses.
7. **Review feedback** (the closed loop, the LLM judge, briefings, the role mask) was implemented and re-verified in a fresh end-to-end run.

The exact prompts and patterns are in `docs/ai_workflow.md`.

## 4. What decisions and trade-offs did you have to make for your build?

* **Synthetic data shaped like Cedarbrook's, instead of a public dataset.** Zero PHI risk, and every story number reproduces exactly. The trade-off is that real clinical notes are messier: AI extraction was 100% accurate on the uniform synthetic notes, so the pilot re-validates it with RN-reviewed real notes.
* **Let the data choose the model, and the simpler one won.** Logistic regression (AUC 0.7245) beat gradient boosting (0.7137) and is easier for clinicians to trust. The trade-off is less headroom on richer data, so the champion is re-selected on every run and RN feedback is accumulated for retraining.
* **A fixed-rule, auditable HRRP what-if on a simplified penalty method.** Jordan's finance team can reproduce every dollar. The trade-off is that it treats the follow-up effect as causal, and it simplifies CMS's 3-year, risk-adjusted, Medicare-only calculation. The pilot is designed to test the causal assumption.

## 5. What are the business outcomes and impact?

Each outcome is stated in the number its owner is measured on:
* **Jordan Whitfield (CFO), HRRP penalty:**
  * getting 6 North's weekend 7-day follow-up to 80% avoids **~7 readmissions a year** and cuts the penalty from **$1.62M to $1.38M (–$238K a year)**
  * every 10 points of follow-up is worth ~$120K
  * the same fix is worth **~$412K** across all CUMC weekend heart-failure discharges and **~$874K** across all CUMC heart-failure discharges
  * against ~$60K a year of weekend follow-up capacity (assumption), that's roughly a **4× return**
* **Dr. Elena Vasquez (VP of Quality), HF excess readmission ratio:** **1.19 → 1.14**, toward the CMS benchmark of 1.00. The trend view shows the next peak the week it starts, not when CMS reports it.
* **Priya Raman (Manager of Transitional Care), 7-day follow-up and 48-hour contact:**
  * a briefed worklist, starting with 54 high-risk patients in the current window, 41 of them without a follow-up
  * plans drafted in **4.4 seconds** for RN review, with outreach tasks created on approval
  * nurse edits that improve the next draft
  * targets: weekend follow-up from **18% to ≥ 80%**, and **≥ 90%** of high-risk patients contacted within 48 hours
* **Kenji Tanaka (CDAO), platform:** five silos become one governed copy with ~2-minute incremental refresh, PHI and note quotes masked by role, and AI quality checked on every run.

**Next step:** a 90-day pilot on 6 North to prove the $238K, then scale to all CUMC heart failure (~$874K), COPD and pneumonia, and the other two hospitals.
