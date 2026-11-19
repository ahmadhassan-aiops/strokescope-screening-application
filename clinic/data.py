"""Cached loaders for the model and the app's data (built by train.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from strokescope.model import StrokeModel

DATA = Path(__file__).resolve().parent.parent / "data"


@st.cache_resource(show_spinner="Loading the model...")
def model() -> StrokeModel:
    return StrokeModel()


@st.cache_data
def clinic() -> pd.DataFrame:
    """The 1,022 held-out patients (never seen in training): profile, whether they had a stroke, and the score."""
    df = pd.read_parquet(DATA / "clinic.parquet")
    df["tier"] = model().tiers(df["proba"].to_numpy())
    return df


@st.cache_data
def patients() -> pd.DataFrame:
    """All 5,109 patients and whether they had a stroke (for the risk factor charts)."""
    return pd.read_parquet(DATA / "patients.parquet")


@st.cache_data
def reference() -> dict:
    return json.loads((DATA / "reference.json").read_text(encoding="utf-8"))


AGE_BANDS = [0, 30, 40, 50, 60, 70, 83]
AGE_LABELS = ["Under 30", "30-39", "40-49", "50-59", "60-69", "70+"]


def age_band(age: pd.Series) -> pd.Series:
    return pd.cut(age, AGE_BANDS, labels=AGE_LABELS, right=False)


@st.cache_data
def band_rates() -> pd.Series:
    """Share of patients in each age band who had a stroke (all 5,109 patients)."""
    df = patients()
    return df.groupby(age_band(df["age"]), observed=True)["stroke"].mean()
