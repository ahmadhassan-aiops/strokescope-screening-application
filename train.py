"""
Reproduce model/ and data/ from the raw dataset (the research is in the notebook; this replays the final choice):

    python train.py "path/to/healthcare-dataset-stroke-data.csv"

Writes model/stroke_risk_logreg.joblib, model/metadata.json, data/clinic.parquet (the 1,022 held-out patients with
outcome and score), data/patients.parquet (all patients, for the risk factor charts) and data/reference.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.impute import KNNImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, average_precision_score, brier_score_loss, confusion_matrix, f1_score, fbeta_score,
    precision_recall_curve, roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from strokescope.model import MODEL_FILE, StrokeModel
from strokescope.schema import BINARY, CATEGORICAL, FEATURES, NUMERICAL

ROOT = Path(__file__).resolve().parent
C = 0.046689498537088946  # the notebook's tuned regularisation (RandomizedSearchCV, 40 values, 5x3-fold AUC-ROC)
TARGET_RECALL = 0.85

# Notebook results that need the full model search (cross-validation on the training set)
TUNED = [
    {"Model": "XGBoost", "AUC-ROC": 0.8407, "Std": 0.018, "Precision at 85% recall": 0.128, "File (KB)": 319},
    {"Model": "Logistic regression (deployed)", "AUC-ROC": 0.8401, "Std": 0.0175, "Precision at 85% recall": 0.125,
     "File (KB)": 116},
    {"Model": "Random forest", "AUC-ROC": 0.8388, "Std": 0.0192, "Precision at 85% recall": 0.126, "File (KB)": 944},
]
BALANCING = [
    {"Approach": "None (threshold moving)", "AUC-ROC": 0.841, "Precision at 85% recall": 0.126, "Brier": 0.043},
    {"Approach": "Class weights", "AUC-ROC": 0.840, "Precision at 85% recall": 0.125, "Brier": 0.173},
    {"Approach": "SMOTE", "AUC-ROC": 0.837, "Precision at 85% recall": 0.124, "Brier": 0.173},
    {"Approach": "Undersampling", "AUC-ROC": 0.834, "Precision at 85% recall": 0.127, "Brier": 0.176},
]


def build() -> Pipeline:
    prep = ColumnTransformer(
        [("num", Pipeline([("impute", KNNImputer(n_neighbors=10)), ("scale", StandardScaler())]), NUMERICAL),
         ("bin", "passthrough", BINARY),
         ("cat", OneHotEncoder(handle_unknown="ignore", drop="if_binary", sparse_output=False), CATEGORICAL)],
        verbose_feature_names_out=False,
    )
    return Pipeline([("prep", prep), ("model", LogisticRegression(max_iter=5000, C=C))])


UNITS = {"age": (10, "Age (+10 years)"), "avg_glucose_level": (50, "Glucose (+50 mg/dl)"), "bmi": (5, "BMI (+5)")}
CONTRASTS = [  # (label, column, reference column or None)
    ("Hypertension", "hypertension", None), ("Heart disease", "heart_disease", None),
    ("Male (vs female)", "gender_Male", None), ("Ever married", "ever_married_Yes", None),
    ("Urban (vs rural)", "Residence_type_Urban", None),
    ("Smokes (vs never)", "smoking_status_smokes", "smoking_status_never smoked"),
    ("Former smoker (vs never)", "smoking_status_formerly smoked", "smoking_status_never smoked"),
    ("Smoking unknown (vs never)", "smoking_status_Unknown", "smoking_status_never smoked"),
    ("Self-employed (vs private)", "work_type_Self-employed", "work_type_Private"),
    ("Government job (vs private)", "work_type_Govt_job", "work_type_Private"),
    ("Child (vs private)", "work_type_children", "work_type_Private"),
    ("Never worked (vs private)", "work_type_Never_worked", "work_type_Private"),
]


def log_odds_ratios(pipe: Pipeline) -> dict[str, float]:
    """Log odds ratios in readable units: numbers per clinical step, categories against a reference category."""
    prep = pipe.named_steps["prep"]
    coef = dict(zip(prep.get_feature_names_out(), pipe.named_steps["model"].coef_[0]))
    sd = dict(zip(NUMERICAL, prep.named_transformers_["num"].named_steps["scale"].scale_))
    out = {label: coef[c] * step / sd[c] for c, (step, label) in UNITS.items()}
    out.update({label: coef[c] - (coef[ref] if ref else 0.0) for label, c, ref in CONTRASTS})
    return out


def screening_threshold(y, p, target=TARGET_RECALL) -> float:
    _, recall, thresholds = precision_recall_curve(y, p)
    return float(np.floor(thresholds[recall[:-1] >= target].max() * 1000) / 1000)


def f1_threshold(y, p) -> float:
    grid = np.round(np.arange(0.005, 0.95, 0.001), 3)
    return float(grid[int(np.argmax([f1_score(y, p >= t) for t in grid]))])


def metrics(y, p, t) -> dict:
    pred = (p >= t).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred).ravel()
    return {"Recall": tp / (tp + fn), "Precision": tp / (tp + fp), "Specificity": tn / (tn + fp),
            "F1": f1_score(y, pred), "F2": fbeta_score(y, pred, beta=2), "Accuracy": accuracy_score(y, pred),
            "AUC-ROC": roc_auc_score(y, p), "PR-AUC": average_precision_score(y, p), "Brier": brier_score_loss(y, p),
            "Found": int(tp), "Missed": int(fn), "Flagged": int(tp + fp), "False alarms": int(fp)}


def main(csv: Path) -> None:
    raw = pd.read_csv(csv)
    df = raw[raw["gender"] != "Other"].reset_index(drop=True)
    X, y = df[FEATURES], df["stroke"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=1)

    pipe = build()
    oof = cross_val_predict(pipe, X_train, y_train, cv=cv, method="predict_proba", n_jobs=5)[:, 1]
    threshold, high = screening_threshold(y_train, oof), f1_threshold(y_train, oof)
    pipe.fit(X_train, y_train)
    proba = pipe.predict_proba(X_test)[:, 1]
    test = {k: (round(float(v), 4) if isinstance(v, float) else v) for k, v in metrics(y_test, proba, threshold).items()}

    names = pipe.named_steps["prep"].get_feature_names_out()
    reference = pipe.named_steps["prep"].transform(X_train).mean(axis=0)
    (ROOT / "model").mkdir(exist_ok=True)
    joblib.dump(pipe, ROOT / "model" / MODEL_FILE)
    meta = {
        "model": "Logistic regression", "threshold": threshold, "high_threshold": high, "target_recall": TARGET_RECALL,
        "features": {"numerical": NUMERICAL, "binary": BINARY, "categorical": CATEGORICAL}, "params": {"C": C},
        "oof_auc_roc": round(float(roc_auc_score(y_train, oof)), 4), "test": test,
        "test_high": {k: (round(float(v), 4) if isinstance(v, float) else v) for k, v in metrics(y_test, proba, high).items()},
        "test_rows": int(len(y_test)), "train_rows": int(len(y_train)), "stroke_rate": round(float(y.mean()), 4),
        "reference": {n: float(v) for n, v in zip(names, reference)},
        "versions": {"scikit-learn": sklearn.__version__, "pandas": pd.__version__, "numpy": np.__version__},
    }
    (ROOT / "model" / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    (ROOT / "data").mkdir(exist_ok=True)
    clinic = df.loc[X_test.index, ["id"] + FEATURES].rename(columns={"id": "patient_id"}).copy()
    clinic["stroke"] = y_test.to_numpy()
    clinic["proba"] = proba
    clinic.reset_index(drop=True).to_parquet(ROOT / "data" / "clinic.parquet", index=False)
    df[FEATURES + ["stroke"]].to_parquet(ROOT / "data" / "patients.parquet", index=False)

    model = StrokeModel(ROOT / "model")
    contrib = model.explain(X_test)
    bins = pd.cut(oof, [0, 0.01, 0.03, 0.06, 0.1, 0.2, 1.0], include_lowest=True)
    calib = (pd.DataFrame({"p": oof, "y": y_train.to_numpy()}).groupby(bins, observed=True)
             .agg(predicted=("p", "mean"), observed=("y", "mean"), patients=("y", "size")))
    rng = np.random.default_rng(1)
    boot = []
    for _ in range(200):  # 95% bootstrap intervals for the odds ratios
        i = rng.integers(0, len(X_train), len(X_train))
        boot.append(log_odds_ratios(build().fit(X_train.iloc[i], y_train.iloc[i])))
    boot = pd.DataFrame(boot)
    point = log_odds_ratios(pipe)
    odds = [{"label": k, "odds_ratio": round(float(np.exp(v)), 4), "lo": round(float(np.exp(boot[k].quantile(0.025))), 4),
             "hi": round(float(np.exp(boot[k].quantile(0.975))), 4)} for k, v in point.items()]
    ref = {
        "test": test,
        "oof": {"Recall": round(float((oof[y_train == 1] >= threshold).mean()), 4),
                "Precision": round(float(y_train[oof >= threshold].mean()), 4)},
        "importance": {k: round(float(v), 4) for k, v in contrib.abs().mean().sort_values(ascending=False).items()},
        "calibration": {k: [round(float(v), 4) for v in calib[k]] for k in calib.columns},
        "odds": odds,
        "tuned": TUNED, "balancing": BALANCING,
    }
    (ROOT / "data" / "reference.json").write_text(json.dumps(ref, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in meta.items() if k != "reference"}, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "healthcare-dataset-stroke-data.csv")
