"""A patient record: field names, labels, valid values and upload validation."""

from __future__ import annotations

from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

NUMERICAL = ["age", "avg_glucose_level", "bmi"]
BINARY = ["hypertension", "heart_disease"]
CATEGORICAL = ["gender", "ever_married", "work_type", "Residence_type", "smoking_status"]
FEATURES = NUMERICAL + BINARY + CATEGORICAL

GENDERS = ["Female", "Male"]
WORK_TYPES = ["Private", "Self-employed", "Govt_job", "children", "Never_worked"]
RESIDENCES = ["Urban", "Rural"]
SMOKING = ["never smoked", "formerly smoked", "smokes", "Unknown"]

LABELS = {
    "age": "Age", "avg_glucose_level": "Average glucose (mg/dl)", "bmi": "BMI", "hypertension": "Hypertension",
    "heart_disease": "Heart disease", "gender": "Sex", "ever_married": "Ever married", "work_type": "Work type",
    "Residence_type": "Residence", "smoking_status": "Smoking",
}
SHORT = {
    "age": "Age", "avg_glucose_level": "Glucose", "bmi": "BMI", "hypertension": "Hypertension",
    "heart_disease": "Heart disease", "gender": "Sex", "ever_married": "Marital status", "work_type": "Work type",
    "Residence_type": "Residence", "smoking_status": "Smoking",
}
WORK_LABELS = {"Private": "Private sector", "Self-employed": "Self-employed", "Govt_job": "Government job",
               "children": "Child (not working)", "Never_worked": "Never worked"}
SMOKING_LABELS = {"never smoked": "Never smoked", "formerly smoked": "Former smoker", "smokes": "Smokes",
                  "Unknown": "Not recorded"}

# How each factor is grouped on the patient report
MODIFIABLE = ["hypertension", "avg_glucose_level", "heart_disease", "smoking_status", "bmi"]
FIXED = ["age", "gender"]
BACKGROUND = ["ever_married", "work_type", "Residence_type"]


class Patient(BaseModel):
    """One patient as the model sees them. BMI may be unknown (the pipeline estimates it from age and glucose)."""

    model_config = ConfigDict(extra="ignore")

    age: float = Field(ge=0.08, le=100)
    avg_glucose_level: float = Field(ge=40, le=400)
    bmi: float | None = Field(default=None, ge=10, le=100)
    hypertension: int = Field(ge=0, le=1)
    heart_disease: int = Field(ge=0, le=1)
    gender: Literal["Female", "Male"]
    ever_married: Literal["Yes", "No"]
    work_type: Literal["Private", "Self-employed", "Govt_job", "children", "Never_worked"]
    Residence_type: Literal["Urban", "Rural"]
    smoking_status: Literal["never smoked", "formerly smoked", "smokes", "Unknown"]

    @model_validator(mode="after")
    def _child_work_type(self) -> "Patient":
        if self.work_type == "children" and self.age >= 18:
            raise ValueError("work type 'children' is only for patients under 18")
        return self

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([self.model_dump()])[FEATURES].astype({"bmi": float})


def validate_rows(raw: pd.DataFrame, max_errors: int = 10) -> tuple[pd.DataFrame, list[str]]:
    """Check every row of an uploaded file. Returns the valid rows (model columns) and readable errors."""
    missing = [c for c in FEATURES if c not in raw.columns and not (c == "bmi")]
    if missing:
        return pd.DataFrame(columns=FEATURES), ["Missing column(s): " + ", ".join(missing)]
    raw = raw.copy()
    if "bmi" not in raw.columns:
        raw["bmi"] = None
    rows, keep, errors = [], [], []
    for i, record in enumerate(raw[FEATURES].to_dict("records")):
        try:
            rows.append(Patient(**{k: (None if pd.isna(v) else v) for k, v in record.items()}).model_dump())
            keep.append(raw.index[i])
        except ValidationError as exc:
            if len(errors) < max_errors:
                errors.append(f"Row {i + 1}: " + "; ".join(
                    (f"{LABELS.get(e['loc'][0], e['loc'][0])}: " if e["loc"] else "")
                    + ("missing" if e["type"] == "missing" else e["msg"].removeprefix("Value error, "))
                    for e in exc.errors()))
    return pd.DataFrame(rows, columns=FEATURES, index=keep).astype({"bmi": float}), errors
