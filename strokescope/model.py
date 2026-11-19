"""Load the trained pipeline, score patients, explain each score and run what-if changes. No Streamlit here."""

from __future__ import annotations

import json
from functools import cached_property
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from strokescope.schema import CATEGORICAL, FEATURES

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"
MODEL_FILE = "stroke_risk_logreg.joblib"

TIERS = ["Routine", "Check", "Priority"]

# Treatable factors and what "treated" means for the model. (feature, label, applies, change)
WHAT_IF = [
    ("hypertension", "Hypertension controlled", lambda p: p["hypertension"] == 1, lambda p: 0),
    ("avg_glucose_level", "Glucose brought to 100 mg/dl", lambda p: p["avg_glucose_level"] > 125, lambda p: 100.0),
]


class StrokeModel:
    """The saved scikit-learn pipeline (BMI estimation, scaling, one-hot encoding, logistic regression) and its
    metadata. Two lines split patients into tiers: the screening line (finds 85% of stroke patients in
    cross-validation) and the high-risk line (best F1)."""

    def __init__(self, model_dir: Path = MODEL_DIR):
        self.pipeline = joblib.load(model_dir / MODEL_FILE)
        self.meta = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
        self.threshold: float = self.meta["threshold"]
        self.high: float = self.meta["high_threshold"]

    def predict_proba(self, rows: pd.DataFrame) -> np.ndarray:
        """Probability that a patient with this profile has had a stroke."""
        return self.pipeline.predict_proba(rows[FEATURES])[:, 1]

    def tier(self, p: float) -> str:
        """Priority (at or above the high-risk line), Check (at or above the screening line) or Routine."""
        if p >= self.high:
            return "Priority"
        return "Check" if p >= self.threshold else "Routine"

    def tiers(self, p: np.ndarray) -> np.ndarray:
        return np.where(p >= self.high, "Priority", np.where(p >= self.threshold, "Check", "Routine"))

    @cached_property
    def _source(self) -> np.ndarray:
        names = self.pipeline.named_steps["prep"].get_feature_names_out()
        return np.array([next((c for c in CATEGORICAL if n.startswith(c + "_")), n) for n in names])

    @cached_property
    def _reference(self) -> np.ndarray:
        """Mean encoded value of each model column over the training patients (the 'average patient')."""
        names = self.pipeline.named_steps["prep"].get_feature_names_out()
        return np.array([self.meta["reference"][n] for n in names])

    @property
    def base_logit(self) -> float:
        lr = self.pipeline.named_steps["model"]
        return float(lr.intercept_[0] + self._reference @ lr.coef_[0])

    def explain(self, rows: pd.DataFrame) -> pd.DataFrame:
        """Contribution of each original factor to the log-odds, relative to the average training patient.
        base_logit + the row's sum = the patient's log-odds, exactly; exp(contribution) multiplies the odds."""
        z = self.pipeline.named_steps["prep"].transform(rows[FEATURES])
        contrib = (z - self._reference) * self.pipeline.named_steps["model"].coef_[0]
        grouped = pd.DataFrame(contrib, index=rows.index).T.groupby(self._source).sum().T
        return grouped[FEATURES]

    def odds_ratios(self) -> pd.DataFrame:
        """Model coefficients as odds ratios (numbers: per standard deviation; categories: against the reference)."""
        prep = self.pipeline.named_steps["prep"]
        names = prep.get_feature_names_out()
        coef = self.pipeline.named_steps["model"].coef_[0]
        scale = prep.named_transformers_["num"].named_steps["scale"].scale_
        sd = dict(zip(prep.transformers_[0][2], scale))
        return pd.DataFrame({"column": names, "source": self._source, "coef": coef, "odds_ratio": np.exp(coef),
                             "sd": [sd.get(n) for n in names]})

    def what_if(self, row: pd.DataFrame) -> list[dict]:
        """For one patient: each treatable factor that applies, the risk after treating it, and both together."""
        before = float(self.predict_proba(row)[0])
        patient = row.iloc[0]
        out, changed_all = [], row.copy()
        for feature, label, applies, change in WHAT_IF:
            if not applies(patient):
                continue
            changed = row.copy()
            changed[feature] = change(patient)
            changed_all[feature] = change(patient)
            after = float(self.predict_proba(changed)[0])
            out.append({"feature": feature, "label": label, "before": before, "after": after})
        if len(out) > 1:
            out.append({"feature": "all", "label": "Both", "before": before,
                        "after": float(self.predict_proba(changed_all)[0])})
        return out


def to_prob(logit: float) -> float:
    return float(1 / (1 + np.exp(-logit)))
