# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Train the 30-day readmission risk model (MLflow + UC registry)
# MAGIC
# MAGIC * **Data:** `gold.index_admissions` with complete 30-day outcomes, all hospitals and conditions.
# MAGIC * **Features:** structured EHR fields, the follow-up booking status, and the **AI-extracted free-text flags** (lives alone, transportation barrier).
# MAGIC * **Split:** time-based. Train on discharges before the last 20 weeks; test on the last 20 weeks.
# MAGIC * **Model:** scikit-learn HistGradientBoosting, with a logistic-regression baseline for comparison.
# MAGIC * **Registered as** `<catalog>.ml.readmit_30d_risk`, alias `@champion`.

# COMMAND ----------

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

# COMMAND ----------

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

# COMMAND ----------

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

# COMMAND ----------

# MAGIC %md ### Calibration (test set, deciles of predicted risk) and feature importance

# COMMAND ----------

best = models["hist_gbm"]
p = best.predict_proba(test[FEATURES])[:, 1]
cal = (pd.DataFrame({"p": p, "y": test.readmit_30d.to_numpy()})
       .assign(decile=lambda d: pd.qcut(d.p, 10, labels=False, duplicates="drop") + 1)
       .groupby("decile").agg(n=("y", "size"), mean_predicted=("p", "mean"), observed_rate=("y", "mean")).round(3).reset_index())
display(cal)

from sklearn.inspection import permutation_importance
imp = permutation_importance(best, test[FEATURES], test.readmit_30d, scoring="roc_auc", n_repeats=5, random_state=0)
fi = pd.DataFrame({"feature": FEATURES, "auc_drop": imp.importances_mean}).sort_values("auc_drop", ascending=False).round(4)
display(fi)

# COMMAND ----------

# MAGIC %md ### Register the champion model in Unity Catalog

# COMMAND ----------

from mlflow import MlflowClient

MODEL_NAME = f"{catalog}.ml.readmit_30d_risk"
X_ex = train[FEATURES].head(5)
with mlflow.start_run(run_id=results["hist_gbm"]["run_id"]):
    mlflow.log_table(cal, "calibration_deciles.json")
    mlflow.log_table(fi, "permutation_importance.json")
    info = mlflow.sklearn.log_model(best, artifact_path="model", signature=infer_signature(X_ex, best.predict_proba(X_ex)[:, 1]),
                                    input_example=X_ex, registered_model_name=MODEL_NAME)
client = MlflowClient()
version = max(int(v.version) for v in client.search_model_versions(f"name='{MODEL_NAME}'"))
client.set_registered_model_alias(MODEL_NAME, "champion", version)
client.update_registered_model(MODEL_NAME, description="30-day all-cause readmission risk for HRRP index admissions (Cedarbrook Health, synthetic). "
                               "HistGradientBoosting on EHR + AI-extracted discharge-note features.")
print(f"registered {MODEL_NAME} version {version} as @champion")

summary = {"model_name": MODEL_NAME, "version": version, "run_id": results["hist_gbm"]["run_id"],
           **{k: round(v, 4) for k, v in results["hist_gbm"].items() if k != "run_id"},
           "baseline_logreg_auc": round(results["logreg_baseline"]["auc"], 4)}
spark.createDataFrame([summary]).write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{catalog}.ml.model_metrics")
print(json.dumps(summary, indent=2))
