"""Readable values for patient fields."""

from __future__ import annotations

import pandas as pd

from strokescope.schema import SMOKING_LABELS, WORK_LABELS


def age(v: float) -> str:
    return f"{v * 12:.0f} months" if v < 2 else f"{v:.0f} years"


def value(feature: str, v) -> str:
    if feature == "age":
        return age(float(v))
    if feature == "avg_glucose_level":
        return f"{float(v):.0f} mg/dl"
    if feature == "bmi":
        return "not recorded" if v is None or pd.isna(v) else f"{float(v):.1f}"
    if feature in ("hypertension", "heart_disease"):
        return "Yes" if int(v) == 1 else "No"
    if feature == "work_type":
        return WORK_LABELS.get(v, str(v))
    if feature == "smoking_status":
        return SMOKING_LABELS.get(v, str(v))
    if feature == "Residence_type":
        return str(v)
    if feature == "ever_married":
        return "Married (now or before)" if v == "Yes" else "Never married"
    return str(v)


def summary(row: pd.Series) -> str:
    """One line: sex, age, and the conditions that matter most."""
    bits = [f"{row['gender']}, {age(float(row['age']))}"]
    if row["hypertension"] == 1:
        bits.append("hypertension")
    if row["heart_disease"] == 1:
        bits.append("heart disease")
    if row["avg_glucose_level"] > 140:
        bits.append(f"glucose {row['avg_glucose_level']:.0f}")
    if row["smoking_status"] == "smokes":
        bits.append("smokes")
    return " · ".join(bits)


def tags(row: pd.Series) -> list[str]:
    """Short tags for the findings that raise stroke risk."""
    out = []
    if row["hypertension"] == 1:
        out.append("Hypertension")
    if row["heart_disease"] == 1:
        out.append("Heart disease")
    if row["avg_glucose_level"] > 140:
        out.append(f"Glucose {row['avg_glucose_level']:.0f}")
    if row["smoking_status"] == "smokes":
        out.append("Smokes")
    return out


def who(row: pd.Series) -> str:
    return f"{row['gender']}, {age(float(row['age']))}"
