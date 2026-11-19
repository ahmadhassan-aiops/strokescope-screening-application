"""Misses and false alarms: move the screening line and see, on the held-out patients, how many stroke patients are
found or missed and how many false alarms it costs."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from clinic import charts, data, fmt, ui
from clinic import theme as t
from strokescope.schema import SMOKING_LABELS

STEPS = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.047, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1, 0.109, 0.12,
         0.14, 0.16, 0.18, 0.2, 0.25, 0.3, 0.4, 0.5]


@st.cache_data
def _curve(y: np.ndarray, p: np.ndarray) -> pd.DataFrame:
    ts = np.unique(np.concatenate([np.geomspace(0.001, 0.6, 400), [0.5]]))
    return pd.DataFrame({"threshold": ts, "flagged": [(p >= x).mean() for x in ts],
                         "missed": [1 - (p[y == 1] >= x).mean() for x in ts]})


def render() -> None:
    m = data.model()
    df = data.clinic()
    y, p = df["stroke"].to_numpy(), df["proba"].to_numpy()
    ui.page("Misses and false alarms", "What the screening line costs, and what it saves",
            "A missed stroke patient (<b>false negative</b>) goes unchecked; a <b>false alarm</b> (false positive) costs a "
            "check. No line avoids both with this data. Move the line and watch both change on the 1,022 held-out patients.")
    if st.session_state.get("line_pct") not in STEPS:
        st.session_state["line_pct"] = m.threshold

    with ui.panel("A", "Move the line", "patients at or above the line are flagged for a check"):
        line = st.select_slider("Screening line (model risk)", STEPS, key="line_pct", format_func=lambda v: f"{v:.1%}")
        flag = p >= line
        found, strokes = int((flag & (y == 1)).sum()), int(y.sum())
        alarms = int((flag & (y == 0)).sum())
        precision = found / flag.sum() if flag.sum() else 0
        ui.stats([("Stroke patients found", f"{found} of {strokes}", f"recall {found / strokes:.0%}"),
                  ("Stroke patients missed", f"{strokes - found}", "false negatives"),
                  ("False alarms", f"{alarms:,}", f"{alarms / (len(y) - strokes):.0%} of patients without a stroke"),
                  ("Flags that are right", f"{precision:.0%}", f"precision; {flag.sum():,} flagged")])
        ui.freq_tree(len(y), strokes, found, alarms)
        name = ("the screening line" if abs(line - m.threshold) < 1e-9 else
                "the high-risk line" if abs(line - m.high) < 1e-9 else f"a line at {line:.1%}")
        ui.note(f"With {name}, every stroke patient found costs about <b>{alarms / max(found, 1):.0f} false alarms</b>. "
                f"The deployed screening line ({m.threshold:.1%}) was chosen before the test set was opened, as the line that "
                "finds 85% of stroke patients in cross-validation.")

    test, high = m.meta["test"], m.meta["test_high"]
    points = [
        {"label": "Screening line (deployed)", "flagged": test["Flagged"] / len(y), "missed": 1 - test["Recall"],
         "colour": t.TIER["Check"], "pos": "top right"},
        {"label": "High-risk line (best F1)", "flagged": high["Flagged"] / len(y), "missed": 1 - high["Recall"],
         "colour": t.TIER["Priority"], "pos": "middle right"},
        {"label": "Default 0.5: finds nobody", "flagged": float((p >= 0.5).mean()), "missed": 1 - float((p[y == 1] >= 0.5).mean()),
         "colour": t.INK, "pos": "bottom right", "symbol": "x"},
    ]
    a, b = st.columns([1.25, 1], gap="medium")
    with a:
        with ui.panel("B", "Every possible line", "fewer misses always means more patients flagged"):
            charts.show(charts.tradeoff(_curve(y, p), points, line), "tradeoff")
            ui.note("Each point on the curve is one possible line. Down means fewer missed strokes, left means fewer patients "
                    f"checked. The deployed screening line flags {test['Flagged']} patients and misses {test['Missed']} of 50 "
                    "stroke patients.")
    with b:
        with ui.panel("C", "Why precision and recall cannot both be high", "the limit is in the data"):
            ui.note("Age carries most of the signal, and many older patients without a stroke look, in these 10 fields, "
                    "exactly like those who had one. Any line that catches most stroke patients must also flag them.",
                    f"The best balance of the two (F1) is {high['F1']:.2f}, at the high-risk line: it finds "
                    f"{high['Found']} of 50 and misses {high['Missed']}. For screening a missed stroke is the worse error, "
                    "so the deployed line accepts more false alarms to miss fewer patients.",
                    "Better data, not a better algorithm, would move the curve: measured blood pressure, cholesterol, atrial "
                    "fibrillation, diabetes, family history and prior mini-strokes. Six model families were tried; all stop "
                    "at the same ranking quality (AUC-ROC about 0.84).")

    with ui.panel("D", "Where the scores fall", "every held-out patient, stroke patients on their own row"):
        charts.show(charts.score_strip(df, m.threshold, m.high), "strip")
        ui.note("Most stroke patients sit to the right of the screening line; most patients without a stroke sit to the left, "
                "but the two groups overlap heavily between about 3% and 20%.")

    with ui.panel("E", "Who the line misses", f"stroke patients below the line at {line:.1%}"):
        missed = df[(df["stroke"] == 1) & (df["proba"] < line)].sort_values("proba")
        if missed.empty:
            ui.note("No stroke patient falls below this line, at the cost of the false alarms above.")
        else:
            st.dataframe(pd.DataFrame({
                "Patient": missed["patient_id"].map(lambda v: f"#{int(v)}"), "Risk": missed["proba"] * 100,
                "Profile": [fmt.summary(r) for _, r in missed.iterrows()],
                "Glucose": missed["avg_glucose_level"], "Smoking": missed["smoking_status"].map(SMOKING_LABELS)}),
                hide_index=True, width="stretch",
                column_config={"Risk": st.column_config.NumberColumn(format="%.1f%%"),
                               "Glucose": st.column_config.NumberColumn(format="%.0f")})
            young = (missed["age"] < 50).mean()
            ui.caution(f"{young:.0%} of these patients are under 50, and "
                       f"{((missed['hypertension'] == 0) & (missed['heart_disease'] == 0)).mean():.0%} have neither hypertension "
                       "nor heart disease. Strokes in young people without risk factors happen, but nothing in this data "
                       "tells them apart from healthy young patients. <b>Symptoms always override a low score.</b>")
    ui.footer()
