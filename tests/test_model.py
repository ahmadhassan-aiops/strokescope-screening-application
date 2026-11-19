"""The shipped model, metadata, explanations, what-ifs and validation agree. Run: pytest -q"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import recall_score, roc_auc_score

from clinic.data import DATA
from strokescope.model import StrokeModel, to_prob
from strokescope.schema import FEATURES, Patient, validate_rows

YOUNG = dict(gender="Female", age=28, hypertension=0, heart_disease=0, ever_married="No", work_type="Private",
             Residence_type="Urban", avg_glucose_level=85, bmi=23, smoking_status="never smoked")
OLDER = dict(gender="Male", age=78, hypertension=1, heart_disease=1, ever_married="Yes", work_type="Self-employed",
             Residence_type="Rural", avg_glucose_level=210, bmi=31, smoking_status="formerly smoked")


@pytest.fixture(scope="module")
def model() -> StrokeModel:
    return StrokeModel()


@pytest.fixture(scope="module")
def clinic() -> pd.DataFrame:
    return pd.read_parquet(DATA / "clinic.parquet")


def test_screening_line_finds_most_stroke_patients(model):
    assert model.meta["test"]["Recall"] >= 0.8
    assert model.meta["test"]["AUC-ROC"] > 0.8
    assert model.threshold < model.high


def test_shipped_scores_reproduce(model, clinic):
    assert np.allclose(model.predict_proba(clinic), clinic["proba"], atol=1e-9)
    assert recall_score(clinic["stroke"], clinic["proba"] >= model.threshold) == pytest.approx(model.meta["test"]["Recall"], abs=1e-4)
    assert roc_auc_score(clinic["stroke"], clinic["proba"]) == pytest.approx(model.meta["test"]["AUC-ROC"], abs=1e-4)


def test_explanation_adds_up(model, clinic):
    rows = clinic.head(50)
    contrib = model.explain(rows)
    assert np.allclose([to_prob(model.base_logit + v) for v in contrib.sum(axis=1)], model.predict_proba(rows), atol=1e-9)


def test_profiles_and_tiers(model):
    low = model.predict_proba(Patient(**YOUNG).to_frame())[0]
    high = model.predict_proba(Patient(**OLDER).to_frame())[0]
    assert low < model.threshold < model.high < high
    assert model.tier(low) == "Routine" and model.tier(high) == "Priority"


def test_missing_bmi_is_accepted(model):
    p = model.predict_proba(Patient(**{**OLDER, "bmi": None}).to_frame())[0]
    assert 0 < p < 1


def test_what_if_lowers_the_risk(model):
    rows = model.what_if(Patient(**OLDER).to_frame())
    assert {r["feature"] for r in rows} == {"hypertension", "avg_glucose_level", "all"}
    assert all(r["after"] < r["before"] for r in rows)
    assert model.what_if(Patient(**YOUNG).to_frame()) == []


def test_child_work_type_needs_a_child():
    with pytest.raises(ValueError):
        Patient(**{**OLDER, "work_type": "children"})


def test_validate_rows_reports_bad_rows():
    raw = pd.DataFrame([YOUNG, {**OLDER, "age": 300}, {**YOUNG, "smoking_status": "sometimes"}])
    rows, errors = validate_rows(raw)
    assert len(rows) == 1 and len(errors) == 2
    assert list(rows.columns) == FEATURES
    assert validate_rows(raw.drop(columns="age"))[1][0].startswith("Missing column")
    assert len(validate_rows(raw.drop(columns="bmi"))[0]) == 1
