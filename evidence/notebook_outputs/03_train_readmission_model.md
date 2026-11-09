# Executed notebook: train_model

job run `601827272748584` · task run `543652077699556` · result **SUCCESS** · 2026-11-09 22:09:21 UTC

# 03 · Train the 30-day readmission risk model (MLflow + UC registry)

* **Data:** `gold.index_admissions` with complete 30-day outcomes, all hospitals and conditions.
* **Features:** structured EHR fields, the follow-up booking status, and the **AI-extracted free-text flags** (lives alone, transportation barrier).
* **Split:** time-based. Train on discharges before the last 20 weeks; test on the last 20 weeks.
* **Models:** scikit-learn HistGradientBoosting and logistic regression; the one with the higher test AUC becomes `@champion`.
* **Registered as** `<catalog>.ml.readmit_30d_risk`, alias `@champion`.

```python
dbutils.widgets.text("catalog", "cedarbrook_rcc")
catalog = dbutils.widgets.get("catalog")

import json
import mlflow
import numpy as np
import pandas as pd
import sklearn
from mlflow.models import infer_signature
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

mlflow.set_registry_uri("databricks-uc")
me = spark.sql("SELECT current_user()").first()[0]
mlflow.set_experiment(f"/Users/{me}/rcc_readmission_risk")
print("mlflow", mlflow.__version__, "| sklearn", sklearn.__version__)
```

Output:

```text
{"ts": "2026-11-09 22:09:37.780", "level": "WARNING", "logger": "pyspark.sql.connect.logging", "msg": "Effective usage policy for this session is cct.Cilqb2JzLzU4MjYyODExNjMyNTQxMy9ydW5zLzYwMTgyNzI3Mjc0ODU4NBABIAEqJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOTIkMDFhMWMyNWItZGNiNS03ZjdmLTg4ZjYtYjQ5YmE2YzJmODM5OiQ2Y2EzMmIwMy01MzlmLTMwZjMtYjNmOS1hMmVlYTgwYTFlNjJCJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOUoMCJKJydcGEMDGpqQCUAJYAWABaLXIt++EwsgCiAEA.", "context": {}}
{"ts": "2026-11-09 22:09:37.780", "level": "WARNING", "logger": "pyspark.sql.connect.logging", "msg": "Effective usage policy for this session is cct.Cilqb2JzLzU4MjYyODExNjMyNTQxMy9ydW5zLzYwMTgyNzI3Mjc0ODU4NBABIAEqJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOTIkMDFhMWMyNWItZGNiNS03ZjdmLTg4ZjYtYjQ5YmE2YzJmODM5OiQ2Y2EzMmIwMy01MzlmLTMwZjMtYjNmOS1hMmVlYTgwYTFlNjJCJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOUoMCJKJydcGEMDGpqQCUAJYAWABaLXIt++EwsgCiAEA.", "context": {}}
{"ts": "2026-11-09 22:09:37.780", "level": "WARNING", "logger": "pyspark.sql.connect.logging", "msg": "Effective usage policy for this session is cct.Cilqb2JzLzU4MjYyODExNjMyNTQxMy9ydW5zLzYwMTgyNzI3Mjc0ODU4NBABIAEqJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOTIkMDFhMWMyNWItZGNiNS03ZjdmLTg4ZjYtYjQ5YmE2YzJmODM5OiQ2Y2EzMmIwMy01MzlmLTMwZjMtYjNmOS1hMmVlYTgwYTFlNjJCJDViNjJmYTAyLTg2NzEtNDZkMy05NmFjLTY0YzE3MjVkYzlkOUoMCJKJydcGEMDGpqQCUAJYAWABaLXIt++EwsgCiAEA.", "context": {}}
mlflow 3.12.0 | sklearn 1.7.2
```

```python
NUM = ["age_at_discharge", "los_days", "prior_admissions_12m", "comorbidity_count"]
BOOL = ["weekend_discharge", "fu7_booked", "ai_lives_alone", "ai_transport_barrier"]
CAT = ["condition", "discharge_disposition", "admission_source", "payer", "service_line"]
FEATURES = NUM + BOOL + CAT

pdf = (spark.table(f"{catalog}.gold.index_admissions").where("outcome_complete")
       .select("encounter_id", "discharge_date", "period_20w", "readmit_30d", *FEATURES).toPandas())
for c in BOOL:
    pdf[c] = pdf[c].astype(int)
pdf["readmit_30d"] = pdf["readmit_30d"].astype(int)
test_mask = pdf.period_20w == "last_20w"
train, test = pdf[~test_mask], pdf[test_mask]
print(f"train {len(train):,} rows ({train.readmit_30d.mean():.3f} readmit) | test {len(test):,} rows ({test.readmit_30d.mean():.3f} readmit)")
```

Output:

```text
train 10,088 rows (0.138 readmit) | test 3,628 rows (0.141 readmit)
```

```python
pre = ColumnTransformer([
    ("num", "passthrough", NUM + BOOL),
    ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT),
])
models = {
    "hist_gbm": Pipeline([("pre", pre), ("clf", HistGradientBoostingClassifier(
        max_depth=3, learning_rate=0.05, max_iter=250, l2_regularization=1.0, random_state=42))]),
    "logreg_baseline": Pipeline([("pre", ColumnTransformer([
        ("num", StandardScaler(), NUM + BOOL),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT)])),
        ("clf", LogisticRegression(max_iter=2000))]),
}

def evaluate(model, X, y):
    p = model.predict_proba(X)[:, 1]
    top = np.argsort(-p)[: max(1, len(p) // 10)]
    return {"auc": roc_auc_score(y, p), "avg_precision": average_precision_score(y, p), "brier": brier_score_loss(y, p),
            "top_decile_readmit_rate": float(y.iloc[top].mean()), "base_rate": float(y.mean()),
            "top_decile_lift": float(y.iloc[top].mean() / y.mean())}

results = {}
for name, m in models.items():
    with mlflow.start_run(run_name=name) as run:
        m.fit(train[FEATURES], train.readmit_30d)
        met = evaluate(m, test[FEATURES], test.readmit_30d)
        mlflow.log_params({"model": name, "features": ",".join(FEATURES), "train_rows": len(train), "test_rows": len(test),
                           "split": "time-based: test = last 20 complete weeks"})
        mlflow.log_metrics({f"test_{k}": v for k, v in met.items()})
        results[name] = {"run_id": run.info.run_id, **met}
display(pd.DataFrame(results).T.reset_index().rename(columns={"index": "model"}))
```

Output:

```text
| model           | run_id                           | auc                | avg_precision      | brier               | top_decile_readmit_rate | base_rate           | top_decile_lift    |
|-----------------|----------------------------------|--------------------|--------------------|---------------------|-------------------------|---------------------|--------------------|
| hist_gbm        | 81127455aa3b4494a4f3c4eff048264a | 0.7136612819921373 | 0.3017709243674952 | 0.11146778646540828 | 0.3729281767955801      | 0.14112458654906285 | 2.6425457527624308 |
| logreg_baseline | 30de7decba2d4e0db993340f3adf6928 | 0.7245053253369704 | 0.3225631796489283 | 0.11004263788986973 | 0.3674033149171271      | 0.14112458654906285 | 2.6033969267955803 |
(2 rows shown)
```

### Calibration (test set, deciles of predicted risk) and feature importance

```python
champion = max(results, key=lambda k: results[k]["auc"])
print(f"champion by test AUC: {champion} ({results[champion]['auc']:.4f}) vs "
      + ", ".join(f"{k} {v['auc']:.4f}" for k, v in results.items() if k != champion))
best = models[champion]
p = best.predict_proba(test[FEATURES])[:, 1]
cal = (pd.DataFrame({"p": p, "y": test.readmit_30d.to_numpy()})
       .assign(decile=lambda d: pd.qcut(d.p, 10, labels=False, duplicates="drop") + 1)
       .groupby("decile").agg(n=("y", "size"), mean_predicted=("p", "mean"), observed_rate=("y", "mean")).round(3).reset_index())
display(cal)

from sklearn.inspection import permutation_importance
imp = permutation_importance(best, test[FEATURES], test.readmit_30d, scoring="roc_auc", n_repeats=5, random_state=0)
fi = pd.DataFrame({"feature": FEATURES, "auc_drop": imp.importances_mean}).sort_values("auc_drop", ascending=False).round(4)
display(fi)
```

Output:

```text
champion by test AUC: logreg_baseline (0.7245) vs hist_gbm 0.7137
| decile | n   | mean_predicted | observed_rate |
|--------|-----|----------------|---------------|
| 1      | 363 | 0.026          | 0.033         |
| 2      | 363 | 0.046          | 0.041         |
| 3      | 363 | 0.064          | 0.058         |
| 4      | 362 | 0.081          | 0.091         |
| 5      | 363 | 0.101          | 0.11          |
| 6      | 363 | 0.124          | 0.124         |
| 7      | 362 | 0.152          | 0.16          |
| 8      | 363 | 0.19           | 0.157         |
| 9      | 363 | 0.247          | 0.27          |
| 10     | 363 | 0.383          | 0.366         |
(10 rows shown)
| feature               | auc_drop |
|-----------------------|----------|
| comorbidity_count     | 0.0423   |
| age_at_discharge      | 0.0402   |
| fu7_booked            | 0.0378   |
| prior_admissions_12m  | 0.0243   |
| service_line          | 0.0135   |
| ai_transport_barrier  | 0.0077   |
| ai_lives_alone        | 0.0062   |
| los_days              | 0.0061   |
| condition             | 0.0038   |
| payer                 | 0.002    |
| admission_source      | 0.0008   |
| discharge_disposition | 0.0001   |
| weekend_discharge     | -0.0     |
(13 rows shown)
```

### Register the champion model in Unity Catalog

```python
from mlflow import MlflowClient

MODEL_NAME = f"{catalog}.ml.readmit_30d_risk"
X_ex = train[FEATURES].head(5)
# Closed-loop signal from the app (notebook 08): RN plan reviews as weak labels for the next retraining
fb = {"feedback_plans_reviewed": 0, "feedback_nurse_edit_rate": 0.0, "feedback_rn_confirmed_high_risk": 0, "feedback_rn_disputed": 0}
if spark.catalog.tableExists(f"{catalog}.ml.retraining_signals"):
    r = spark.sql(f"""SELECT count(*) AS n, avg(CAST(weak_label = 'nurse_edited' AS INT)) AS edit_rate,
                             count_if(risk_signal = 'rn_confirmed_high_risk') AS confirmed, count_if(risk_signal = 'rn_disputed') AS disputed
                      FROM {catalog}.ml.retraining_signals WHERE weak_label <> 'pending_review'""").first()
    fb = {"feedback_plans_reviewed": int(r.n), "feedback_nurse_edit_rate": float(r.edit_rate or 0),
          "feedback_rn_confirmed_high_risk": int(r.confirmed), "feedback_rn_disputed": int(r.disputed)}
print("weak-label feedback available for retraining:", fb)

with mlflow.start_run(run_id=results[champion]["run_id"]):
    mlflow.log_metrics(fb)
    mlflow.log_table(cal, "calibration_deciles.json")
    mlflow.log_table(fi, "permutation_importance.json")
    info = mlflow.sklearn.log_model(best, artifact_path="model", signature=infer_signature(X_ex, best.predict_proba(X_ex)[:, 1]),
                                    input_example=X_ex, registered_model_name=MODEL_NAME)
client = MlflowClient()
version = max(int(v.version) for v in client.search_model_versions(f"name='{MODEL_NAME}'"))
client.set_registered_model_alias(MODEL_NAME, "champion", version)
client.update_registered_model(MODEL_NAME, description="30-day all-cause readmission risk for HRRP index admissions (Cedarbrook Health, synthetic). "
                               f"Champion = best test AUC of HistGradientBoosting vs logistic regression (current: {champion}); EHR + AI-extracted discharge-note features.")
print(f"registered {MODEL_NAME} version {version} as @champion")

summary = {"model_name": MODEL_NAME, "version": version, "champion_algorithm": champion, "run_id": results[champion]["run_id"],
           **{k: round(v, 4) for k, v in results[champion].items() if k != "run_id"},
           "hist_gbm_auc": round(results["hist_gbm"]["auc"], 4), "logreg_auc": round(results["logreg_baseline"]["auc"], 4), **fb}
spark.createDataFrame([summary]).write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{catalog}.ml.model_metrics")
print(json.dumps(summary, indent=2))
```

Output:

```text
weak-label feedback available for retraining: {'feedback_plans_reviewed': 3, 'feedback_nurse_edit_rate': 0.3333333333333333, 'feedback_rn_confirmed_high_risk': 2, 'feedback_rn_disputed': 0}
/databricks/python/lib/python3.12/site-packages/mlflow/types/utils.py:440: UserWarning: Hint: Inferred schema contains integer column(s). Integer columns in Python cannot represent missing values. If your input data contains missing values at inference time, it will be encoded as floats and will cause a schema enforcement error. The best way to avoid this problem is to infer the model schema based on a realistic data sample (training dataset) that includes missing values. Alternatively, you can declare integer columns as doubles (float64) whenever these columns may have missing values. See `Handling Integers With Missing Values <https://www.mlflow.org/docs/latest/models.html#handling-integers-with-missing-values>`_ for more details.
  warnings.warn(
2026/11/09 22:09:57 WARNING mlflow.models.model: `artifact_path` is deprecated. Please use `name` instead.
🔗 View Logged Model at: https://e2-demo-field-eng.cloud.databricks.com/ml/experiments/3464532796422956/models/m-47cb8e1107494368b6c2b2d4f188e034?o=1444828305810485
Registered model 'cedarbrook_rcc.ml.readmit_30d_risk' already exists. Creating a new version of this model...
🔗 Created version '5' of model 'cedarbrook_rcc.ml.readmit_30d_risk': https://e2-demo-field-eng.cloud.databricks.com/explore/data/models/cedarbrook_rcc/ml/readmit_30d_risk/version/5?o=1444828305810485
registered cedarbrook_rcc.ml.readmit_30d_risk version 5 as @champion
{
  "model_name": "cedarbrook_rcc.ml.readmit_30d_risk",
  "version": 5,
  "champion_algorithm": "logreg_baseline",
  "run_id": "30de7decba2d4e0db993340f3adf6928",
  "auc": 0.7245,
  "avg_precision": 0.3226,
  "brier": 0.11,
  "top_decile_readmit_rate": 0.3674,
  "base_rate": 0.1411,
  "top_decile_lift": 2.6034,
  "hist_gbm_auc": 0.7137,
  "logreg_auc": 0.7245,
  "feedback_plans_reviewed": 3,
  "feedback_nurse_edit_rate": 0.3333333333333333,
  "feedback_rn_confirmed_high_risk": 2,
  "feedback_rn_disputed": 0
}
```
