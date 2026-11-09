# AI as a force multiplier: tools, prompts and patterns

How AI was used to **build** this solution, and how AI works **inside** it. Prompts are quoted from the committed code.

## 1. Tools

| Where | Tool | Role |
|---|---|---|
| Building | **Claude Code** (Anthropic's coding agent, in the terminal) | Wrote the story, architecture, generator, pipeline SQL, notebooks, app, dashboard and evidence exporters. Drove the Databricks CLI / Asset Bundles, read job and pipeline errors, and fixed them. |
| In-product: data | **AI Functions**: `ai_query()` with `databricks-claude-haiku-4-5` and structured output | Reads all 16,584 discharge notes inside the Lakeflow pipeline and extracts social-risk flags and the follow-up instruction type; also writes a grounded nurse briefing for each worklist patient. |
| In-product: workflow | **Foundation Model API**: `databricks-claude-sonnet-4-6` | Drafts a patient-specific transition plan in the app for RN review. |
| In-product: analytics | **Genie** (AI/BI) + an LLM judge | Plain-English Q&A over the governed gold tables for Finance & Quality; every run is graded by Claude against SQL reference answers. |
| In-product: ML | **MLflow + UC model registry** | Experiment tracking, champion selection, governed model serving to batch scoring. |

## 2. Build workflow with Claude Code

The human set the direction and made the decisions. The agent did the typing, running and debugging. The loop:

1. **A story contract first.** The customer story was written with exact target numbers (14.8% → 23.9%, 18% vs 69%, ERR 1.19 → 1.14, ~$240K).
   Those numbers became a *contract* that the code has to satisfy.
2. **Architecture mapped to requirements.** `ARCHITECTURE.md` maps every required layer (Lakeflow, UC, Lakebase, ML/GenAI, Genie, App)
   to a component and to the text evidence that would prove it ran. It was committed before any code.
3. **Verify locally before touching the platform.** The seeded generator (`src/rcc_datagen.py`) builds the story into the data using exact
   counts and a small proportional-fitting solve. `scripts/local_story_check.py` recomputes the story from the raw files with the *same rules as the gold
   layer*. This caught two generator bugs (a readmission timing edge case, and percentages that weren't representable as whole numbers) in seconds instead of pipeline runs.
4. **Everything as code.** One Asset Bundle holds the schemas, volumes, pipeline, a 11-task job, the dashboard and the app.
5. **Run → read the error → fix → rerun.** Real issues the agent diagnosed from job and pipeline output:
   * The bundle's development mode prefixed schema names, so the notebooks couldn't find `cedarbrook_rcc.raw`.
     It was fixed after asking the human before recreating the empty schemas.
   * Workspace **tag policies** rejected `data_classification=synthetic_phi` and `project=…`. It switched to the allowed `RESTRICTED` and `rcc_*` keys.
   * Gold showed **100% readmission rates**: `readmit_30d` was NULL rather than false, so `avg()` skipped those rows. It added `coalesce`.
   * Every reporting window had **shifted by a week**: simulated readmissions were discharged after the extract date. The generator fix was re-verified locally.
   * `full_refresh_selection` refreshed *only* the selected tables, so silver and gold went stale. Diagnosed from the as-of date not changing.
   * The **app couldn't bind Lakebase** (PERMISSION_DENIED even for the owner). Isolated with direct API calls, then replaced with explicit least-privilege grants (`scripts/grant_app_access.py`).
6. **Validation as a gate.** `notebooks/99_validate_story.py` recomputes all 33 story, platform and governance checks from the gold tables, and the job fails if any check fails.
7. **Evidence as text, committed at every milestone.** The exporters turn job runs into `.ipynb` files with outputs, plus event-log, query, app and Lakebase verification files.

**Human decisions the agent surfaced rather than made on its own:**
* which workspace to use
* approval before deleting and recreating resources
* keeping incremental vs full-refresh AI processing (a cost vs clean-rebuild trade-off)
* accepting the simpler model as champion

## 3. In-product prompts and patterns

### 3.1 Note extraction (AI Functions, `pipelines/02_silver.sql`)

```sql
ai_query('databricks-claude-haiku-4-5',
  concat('You read hospital discharge notes and extract social risk factors. ',
         'Set lives_alone_no_caregiver=true only if the note says the patient lives alone or has no caregiver / no one at home to help. ',
         'Set transportation_barrier=true only if the note says the patient lacks reliable transportation or does not drive. ',
         'followup_status must be one of: booked_appointment (a specific follow-up appointment date is scheduled), ',
         'patient_to_call (patient is told to call or schedule follow-up themselves), none (anything else). ',
         'evidence: the shortest verbatim quote supporting the social risk factors (empty if none). NOTE:\n', note_text),
  responseFormat => 'STRUCT<signals:STRUCT<lives_alone_no_caregiver:BOOLEAN, transportation_barrier:BOOLEAN, followup_status:STRING, evidence:STRING>>',
  failOnError => false)
```

Patterns:
* **Structured output** (`responseFormat`): typed columns, no fragile parsing.
* **"Only if the note says…"** wording reduces false positives.
* A **closed label set** for `followup_status`.
* A **verbatim evidence quote**, so every flag can be explained in the app.
* **`failOnError => false`** with an `ai_error` column, so one bad call never fails the pipeline (0 errors in 16,584 notes).
* An **incremental streaming table**, so each note is sent to the model once: ~24 min for the first pass, ~2 min for reruns.
* **Scored against ground truth** (`02_ai_note_signals_eval`): accuracy, precision and recall per flag.

### 3.2 Transition-plan drafting (Foundation Model API, `app/app.py`)

```text
You are a heart-failure and care-transitions nurse planner at Cedarbrook Health. Write a concise post-discharge transition plan for the
care-transitions team. Use ONLY the facts in the patient context; do not invent appointments, medications or diagnoses. Format as markdown
with these sections: **Why this patient is at risk** (1-2 sentences citing the model drivers and note evidence), **Within 48 hours**,
**Within 7 days**, **Social needs**, **Teach-back topics**. Use bullet points and at most 170 words in total. End with: 'Draft generated by AI.
Requires RN review and approval.'
```

Patterns:
* **Grounding:** the user message is a JSON patient context (risk score, drivers, AI note flags, follow-up status, disposition), and the prompt says "use ONLY these facts".
* **A fixed section layout** matching the nurse's workflow, and **temperature 0.2**.
* **Human in the loop:** the output is saved as a `draft`, and only an RN approval makes it final and creates outreach tasks.
* **Auditability:** each draft records the model endpoint, a SHA-256 of the prompt, the latency and the approver (`app_rcc.plan_audit_log`).
* Real output is in `evidence/app_api_responses/11_draft_plan.json`.

### 3.3 Nurse briefing (AI Functions over the worklist, `notebooks/04_batch_score.py`)

```text
You write briefings for care-transitions nurses. Using ONLY the facts in this JSON, write at most 2 sentences (max 55 words): first why this
patient is at readmission risk (cite the top drivers and their impact in percentage points), then the single most important action to take
next. Do not invent diagnoses, medications, dates or names. Plain text, no markdown. FACTS: {to_json(named_struct(age, condition, unit, risk_pct,
driver_1, driver_1_impact_pts, …, 7_day_followup_booked, lives_alone, transportation_barrier, recommended_actions))}
```

Patterns:
* The model's **counterfactual drivers** (risk points each factor adds) are turned into a 2-sentence briefing by `ai_query` in batch. All 705 worklist rows are covered.
* **Grounded in the same gold row:** the facts are built with `to_json(named_struct(...))`, so the narrative can't drift from the score.
* It replaces the driver labels in the app, so the worklist reads like a nurse briefing.
* Real output, in `evidence/app_api_responses/09_*.json`: *"This 83-year-old discharged Saturday to home alone carries 45% readmission risk driven by no 7-day
  follow-up scheduled (16.8 pts), prior admissions in last 12 months (13.6 pts), and living alone without caregiver (13.5 pts). Immediately book the
  7-day follow-up appointment and initiate home health referral."*

### 3.4 Closed loop: nurse edits as weak labels (`app/app.py`, `notebooks/08_feedback_loop.py`)

* On approval, the app compares the AI draft with the nurse's final text (`difflib`) and records:
  * `edited`, `edit_similarity`, `chars_added` and `chars_removed`
  * `sections_changed`: which of the five plan sections changed
  * the reject reason, if the plan was rejected

  These are written to `app_rcc.transition_plans`, with `plan_edited` / `plan_accepted_as_is` events in `app_rcc.plan_audit_log`.
* `08_feedback_loop` reads that write-back **through Unity Catalog** (`rcc_lakebase.app_rcc.*`, no ETL) and assigns a weak label: `accepted_as_is` (≥ 97% similar), `nurse_edited` or `plan_rejected`.
  * The labels go into `gold.plan_feedback`.
  * `ml.retraining_signals` joins them to the model's features, score, drivers and the eventual 30-day outcome.
* `03_train_readmission_model` logs the available feedback (plans reviewed, nurse-edit rate, RN-confirmed high-risk cases) as MLflow metrics on the champion run.
  That makes the RN review a tracked retraining signal. Which sections nurses rewrite is the input to prompt iteration.
* Honest scope: the prototype has only a handful of reviewed plans. The loop is built and running end to end, and its value grows with use.

### 3.5 LLM judge for Genie (`notebooks/06_genie_space.py`)

```text
You are a strict evaluator of an analytics assistant. Compare the ASSISTANT ANSWER (its text and result rows) with the EXPECTED ANSWER computed
from the source tables. PASS only if the key numbers and entities in the assistant answer match the expected answer (allow rounding to 1 decimal
place and equivalent formatting). Return ONLY JSON: {"verdict": "PASS" or "FAIL", "score": integer 1-5, "rationale": "one sentence"}
```

* **Reference answers are deterministic SQL** on the gold tables, not LLM output. The judge (`databricks-claude-sonnet-4-6`, temperature 0) only compares.
* Results are **appended** to `gold.genie_eval_judgements` with a run timestamp, so this is a repeatable regression check on every job run, not a one-time demo.
  `99_validate_story` fails the run if the latest judgement isn't all PASS.

### 3.6 Genie space (`notebooks/06_genie_space.py`)

* **Business definitions as instructions:** what an index admission, a weekend discharge, the 7-day follow-up and ERR mean; hospital and unit aliases ("6N").
* **Routing rules learned from evaluation:** the first evaluation got 2 of 5 answers wrong.
  * For "lives alone", Genie used all-time data instead of the trailing 12 months.
  * For the what-if, it recomputed the penalty instead of reading the precomputed table.

  The fix was an instruction to "use `gold.readmission_risk_factors` for risk-factor questions and `gold.hrrp_whatif` for scenarios, never recompute", plus example SQL for each. After that: **5/5**.
* **Evaluated through the Conversation API** on every run (`gold.genie_eval_transcript`), with question → SQL → rows recorded as evidence.

### 3.7 ML

* **Champion by evidence, not by preference:** both models are trained on a time-based split; the higher test AUC is registered as `@champion`. Logistic regression won.
* **Counterfactual explanations:** for each patient, how much the risk drops if a factor is set to its reference value. These read as actions ("No 7-day follow-up booked +X pts").

## 4. What we would add next (level-up)

* Built since the first review: the closed-loop weak labels (§3.4), the Genie LLM judge (§3.5), the nurse briefings (§3.3), and a role-based mask on the AI evidence quotes.
* Next:
  * use `ml.retraining_signals` as sample weights or extra labels once volume allows
  * MLflow Tracing and an LLM-as-judge on plan faithfulness
  * Lakehouse Monitoring on `gold.patient_risk_scores` for drift
  * re-validate note extraction on real notes, with RN-labelled samples
