"""Risk factors: what goes with stroke in the 5,109 patients, and what the model weighs once age is accounted for."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from clinic import charts, data, ui
from strokescope.schema import SMOKING_LABELS, WORK_LABELS


def _bars(df: pd.DataFrame, by: pd.Series, labels: dict | None = None, order: list | None = None, flag: float = 0.07):
    g = df.groupby(by, observed=True)["stroke"].agg(["mean", "size"])
    if order is not None:
        g = g.reindex([o for o in order if o in g.index])
    names = [str(labels.get(i, i)) if labels else str(i) for i in g.index]
    return charts.rate_bars(names, g["mean"].tolist(), g["size"].tolist(), float(df["stroke"].mean()),
                            [r >= flag for r in g["mean"]])


def render() -> None:
    df = data.patients()
    ref = data.reference()
    overall = df["stroke"].mean()
    ui.page("Risk factors", "What goes with stroke in this data",
            f"All 5,109 patients, {int(df['stroke'].sum())} of whom ({overall:.1%}) had a stroke. Red bars are at least "
            "7%, well above the average. The last panel shows what still matters <b>once age is taken into account</b>.")

    with ui.panel("A", "Age above all", "share of patients who had a stroke, by age"):
        split = st.segmented_control("Split by", ["Hypertension", "Heart disease", "Glucose above 140"],
                                     default="Hypertension", required=True, key="rf_split")
        band = data.age_band(df["age"])
        col = {"Hypertension": df["hypertension"], "Heart disease": df["heart_disease"],
               "Glucose above 140": (df["avg_glucose_level"] > 140).astype(int)}[split]
        table = df.groupby([band, col], observed=True)["stroke"].mean().unstack()
        charts.show(charts.age_lines(table, {0: f"No {split.lower()}" if split != "Glucose above 140" else "Glucose 140 or less",
                                             1: split if split != "Glucose above 140" else "Glucose above 140"}), "age")
        ui.note("The stroke rate climbs from almost zero under 30 to <b>17.7% from age 70</b>; 92% of stroke patients are 50 or "
                "older. Within each age band the red line stays above the grey one for most bands: the condition adds risk "
                "on top of age (small bands under 40 are noisy).")

    with ui.panel("B", "Conditions and measurements", "share who had a stroke in each group"):
        a, b = st.columns(2, gap="large")
        with a:
            st.html('<p class="fgroup-t">Hypertension</p>')
            charts.show(_bars(df, df["hypertension"].map({0: "No hypertension", 1: "Hypertension"})), "hyp")
            st.html('<p class="fgroup-t">Average glucose (mg/dl)</p>')
            charts.show(_bars(df, pd.cut(df["avg_glucose_level"], [0, 100, 140, 200, 400],
                                         labels=["Under 100", "100-140", "140-200", "Over 200"])), "glu")
        with b:
            st.html('<p class="fgroup-t">Heart disease</p>')
            charts.show(_bars(df, df["heart_disease"].map({0: "No heart disease", 1: "Heart disease"})), "heart")
            st.html('<p class="fgroup-t">BMI (patients with a recorded BMI)</p>')
            charts.show(_bars(df.dropna(subset=["bmi"]), pd.cut(df["bmi"].dropna(), [0, 18.5, 25, 30, 35, 100],
                                                                labels=["Under 18.5", "18.5-25", "25-30", "30-35", "Over 35"])),
                        "bmi")
        ui.note("Heart disease (17.0%) and hypertension (13.3%) carry 3 to 4 times the average rate; glucose above 140 "
                "doubles it. BMI is flat above 25: the low rate under 18.5 comes from children, not from weight.")

    with ui.panel("C", "Lifestyle and background", "mostly a reflection of age"):
        a, b = st.columns(2, gap="large")
        with a:
            st.html('<p class="fgroup-t">Smoking</p>')
            charts.show(_bars(df, df["smoking_status"], SMOKING_LABELS), "smoke")
            st.html('<p class="fgroup-t">Sex</p>')
            charts.show(_bars(df, df["gender"]), "sex")
        with b:
            st.html('<p class="fgroup-t">Work type</p>')
            charts.show(_bars(df, df["work_type"], WORK_LABELS), "work")
            st.html('<p class="fgroup-t">Marital status and residence</p>')
            both = pd.concat([df.assign(g=df["ever_married"].map({"Yes": "Ever married", "No": "Never married"})),
                              df.assign(g=df["Residence_type"] + " residence")])
            charts.show(_bars(both, both["g"]), "bg")
        ui.note("Married and self-employed patients look riskier, and children and \"not recorded\" smokers safer, because of "
                "their ages: among patients aged 40 and over, never-married patients have a <b>higher</b> rate (10.1%) than "
                "married ones (8.0%). Sex and residence make little difference.")

    with ui.panel("D", "What the model weighs, all else equal", "odds ratios with 95% bootstrap intervals"):
        a, b = st.columns([1.5, 1], gap="large")
        with a:
            charts.show(charts.forest(pd.DataFrame(ref["odds"])), "forest")
        with b:
            o = {r["label"]: r for r in ref["odds"]}
            ui.note(f"<b>Every 10 years of age multiplies the odds by {o['Age (+10 years)']['odds_ratio']:.2f}.</b>",
                    f"Hypertension multiplies them by {o['Hypertension']['odds_ratio']:.2f} and each 50 mg/dl of glucose by "
                    f"{o['Glucose (+50 mg/dl)']['odds_ratio']:.2f}; both intervals stay above 1.",
                    f"Heart disease ({o['Heart disease']['odds_ratio']:.2f}) and smoking (about 1.2) point the same way, with "
                    "intervals that reach 1: with 199 stroke patients to learn from, the model cannot be sure of them.",
                    "BMI, sex, marital status, work type and residence sit at about 1: once age is known they add nothing, "
                    "and the model's regularisation keeps them small.")
            ui.caution("Odds ratios describe patients in this dataset, not the effect of a treatment. A ratio near 1 for BMI "
                       "does not mean weight is irrelevant to stroke; it means this data cannot show it.")
    ui.footer()
