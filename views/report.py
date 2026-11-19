"""Model report: how the model works, held-out results at both lines, ranking, calibration, the model search, data
and limits."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from sklearn.metrics import roc_auc_score, roc_curve

from clinic import charts, data, ui
from clinic.site import CODE_URL, NOTEBOOK_URL, PROJECT_URL


def render() -> None:
    m = data.model()
    ref = data.reference()
    df = data.clinic()
    s, h = m.meta["test"], m.meta["test_high"]
    ui.page("Model report", "How StrokeScope was built and checked",
            "Every figure on this page comes from the 1,022 held-out patients (50 of them stroke patients), scored once after "
            "every choice had been made in cross-validation.")
    ui.stats([("Stroke patients found", f"{s['Found']} of {s['Found'] + s['Missed']}", f"recall {s['Recall']:.0%} at the screening line"),
              ("Flags that are right", f"{s['Precision']:.0%}", f"precision; {m.meta['stroke_rate']:.1%} by chance"),
              ("Ranking quality", f"{s['AUC-ROC']:.3f}", "AUC-ROC (0.5 = random)"),
              ("Calibration", f"{s['Brier']:.3f}", "Brier score (lower is better)")])

    with ui.panel("A", "How the model works", "one pipeline from patient record to risk"):
        a, b = st.columns(2, gap="large")
        with a:
            ui.note("<b>Every patient is used.</b> 201 patients have no BMI, and 20% of them had a stroke (4% of the others), so "
                    "they are kept: the pipeline estimates BMI from the 10 most similar patients.",
                    "<b>Inputs:</b> age, glucose and BMI are scaled; hypertension and heart disease are yes/no; sex, marital "
                    "status, work type, residence and smoking are one-hot encoded.",
                    "<b>Model:</b> a tuned logistic regression trained on the real 4.9% stroke rate, so its risks read as real "
                    "chances. Each score is the average patient's odds times one multiplier per factor.")
        with b:
            ui.note("<b>Measured on what matters.</b> Answering \"no stroke\" for everyone is 95% accurate and finds no one, "
                    "so models are compared on ranking (AUC-ROC, PR-AUC) and on precision at 85% recall, not accuracy.",
                    "<b>Two lines, chosen out of fold.</b> Check finds 85% of stroke patients in cross-validation; Priority "
                    "is the best balance of precision and recall (F1).",
                    "<b>Split:</b> shuffled and stratified, because the source file lists all 249 stroke patients first. The "
                    "held-out patients were scored once, after every choice was made.")

    with ui.panel("B", "Held-out results at each line", "1,022 patients, 50 of them stroke patients"):
        rows = ["Stroke patients found", "Recall", "Precision", "Patients flagged", "False alarms", "F1"]
        def col(r):
            return [f"{r['Found']} of 50", f"{r['Recall']:.0%}", f"{r['Precision']:.0%}", f"{r['Flagged']}",
                    f"{r['False alarms']}", f"{r['F1']:.3f}"]
        st.dataframe(pd.DataFrame({f"Check line ({m.threshold:.1%})": col(s), f"Priority line ({m.high:.1%})": col(h)},
                                  index=rows), width="stretch")
        ui.note(f"Across all patients: AUC-ROC {s['AUC-ROC']:.3f}, PR-AUC {s['PR-AUC']:.3f} (random scores would give "
                f"{m.meta['stroke_rate']:.3f}), average predicted risk {df['proba'].mean():.1%} against an actual 4.9%.")

    a, b = st.columns(2, gap="medium")
    with a:
        with ui.panel("C", "Ranking", "ROC curve, held-out patients"):
            y, p = df["stroke"].to_numpy(), df["proba"].to_numpy()
            fpr, tpr, _ = roc_curve(y, p)
            spec = s["Specificity"]
            charts.show(charts.roc(fpr, tpr, roc_auc_score(y, p), (1 - spec, s["Recall"])), "roc")
            ui.note("A random stroke patient scores higher than a random patient without a stroke 84% of the time "
                    "(95% bootstrap interval 0.78 to 0.90).")
    with b:
        with ui.panel("D", "Can the risks be read as real chances?", "out-of-fold calibration"):
            c = ref["calibration"]
            charts.show(charts.calibration(c["predicted"], c["observed"], c["patients"]), "cal")
            ui.note("Yes, roughly: patients given about 4% had a stroke 4% of the time, those given about 8% had 9%. The model was "
                    "trained on the real 4.9% rate, not on resampled data, so its risks are not inflated.")

    with ui.panel("E", "Model search", "cross-validation on the 4,087 training patients"):
        a, b = st.columns(2, gap="large")
        with a:
            st.caption("Three tuned models (40 settings each, 5-fold cross-validation repeated 3 times)")
            st.dataframe(pd.DataFrame(ref["tuned"]), hide_index=True, width="stretch",
                         column_config={"AUC-ROC": st.column_config.NumberColumn(format="%.4f"),
                                        "Std": st.column_config.NumberColumn("Fold std", format="%.3f"),
                                        "Precision at 85% recall": st.column_config.NumberColumn(format="%.3f")})
        with b:
            st.caption("Handling the 4.9% stroke rate (logistic regression)")
            st.dataframe(pd.DataFrame(ref["balancing"]), hide_index=True, width="stretch",
                         column_config={"AUC-ROC": st.column_config.NumberColumn(format="%.3f"),
                                        "Precision at 85% recall": st.column_config.NumberColumn(format="%.3f"),
                                        "Brier": st.column_config.NumberColumn(format="%.3f")})
        ui.note("The three tuned models tie: their gaps are a tenth of the fold-to-fold variation. Logistic regression was "
                "chosen because its risks are calibrated and each patient's score splits exactly into one multiplier per "
                "factor, which the patient screen shows.",
                "Class weights, SMOTE and undersampling find stroke patients no better than moving the line, and they inflate "
                "the risks (Brier 0.17 against 0.04), so the model is trained on the real data and the line handles the imbalance.")

    with ui.panel("F", "Data and limits"):
        a, b = st.columns(2, gap="large")
        with a:
            ui.note("<b>5,110 patients</b>, 249 (4.9%) with a stroke; the single patient recorded as \"Other\" sex was removed.",
                    "<b>Split:</b> 4,087 to train, 1,022 held out, shuffled and stratified. Every choice used cross-validation "
                    "on the training patients.",
                    f"<b>Lines:</b> Check from {m.threshold:.1%} (finds 85% of stroke patients out of fold), Priority from "
                    f"{m.high:.1%} (best F1).")
        with b:
            ui.caution("<b>Past strokes, not future ones.</b> The data records whether a patient has had a stroke, at one point "
                       "in time. The model recognises stroke-like profiles; it has not been shown to predict who will have one.")
            ui.caution("<b>Unknown origin, not validated.</b> The dataset's source is not documented, and the model has not been "
                       "tested on another hospital's patients. It is a portfolio demonstration, not a medical device.")

    with ui.panel("G", "Code and notebook"):
        st.markdown(f"- [Notebook]({NOTEBOOK_URL}): data checks, EDA, model search, thresholds, test results\n"
                    f"- [Project folder]({PROJECT_URL}) in the portfolio repository\n"
                    f"- [App code]({CODE_URL}): Streamlit app, `strokescope/` inference package, `train.py`, tests")
    ui.footer()
