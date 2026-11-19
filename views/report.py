"""Model report: what was wrong in the first version, the comparison on the same patients, ranking, calibration, the
model search, data and limits."""

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
    s, first = m.meta["test"], ref["first"]
    ui.page("Model report", "How StrokeScope was built and checked",
            "Every figure on this page comes from the 1,022 held-out patients (50 of them stroke patients), scored once after "
            "every choice had been made in cross-validation.")
    ui.stats([("Stroke patients found", f"{s['Found']} of {s['Found'] + s['Missed']}", f"recall {s['Recall']:.0%} (first version 18%)"),
              ("Flags that are right", f"{s['Precision']:.0%}", f"precision; {m.meta['stroke_rate']:.1%} by chance"),
              ("Ranking quality", f"{s['AUC-ROC']:.3f}", "AUC-ROC (0.5 = random)"),
              ("Calibration", f"{s['Brier']:.3f}", "Brier score (first version 0.055)")])

    with ui.panel("A", "What was wrong in the first version", "and what changed"):
        a, b = st.columns(2, gap="large")
        with a:
            ui.note("<b>1. 40 stroke patients were thrown away.</b> Rows with no BMI were dropped, but 20% of those patients had "
                    "had a stroke (4% of the others): 16% of all stroke cases. Now kept; BMI is estimated from similar patients "
                    "inside the pipeline.",
                    f"<b>2. SMOTE ran before cross-validation.</b> Synthetic copies leaked into the scored folds, so the model "
                    f"looked {first['Leaky CV accuracy']:.0%} accurate with {first['Leaky CV recall']:.0%} recall. Scored on "
                    f"real patients only, the same model found {first['Honest CV recall']:.0%} of stroke patients.",
                    "<b>3. Label encoding, then SMOTE,</b> invented categories that do not exist (a work type of 2.96, a "
                    "smoking status of 0.32). Now one-hot encoded, and resampling was tested only inside folds.")
        with b:
            ui.note("<b>4. Accuracy was the metric.</b> Saying \"no stroke\" to everyone is 95% accurate. Models are now compared "
                    "on ranking (AUC-ROC, PR-AUC) and on precision at 85% recall.",
                    "<b>5. The tuned settings were not used, and the line stayed at 0.5,</b> which almost no real patient "
                    "reaches. The line is now chosen out of fold to find 85% of stroke patients.",
                    "<b>6. The row order.</b> All 249 stroke patients are the first rows of the file. An unshuffled split puts "
                    "none of them in the test set. The first version's split did shuffle, so this was not its problem, but "
                    "every split here is shuffled and stratified.")

    with ui.panel("B", "Against the first version", "same 1,022 held-out patients"):
        st.dataframe(pd.DataFrame({
            "First version (SMOTE + XGBoost, line 0.5)": [f"{first['Found']} of 50", f"{first['Recall']:.0%}", f"{first['Precision']:.0%}",
                                                          f"{first['Flagged']}", f"{first['AUC-ROC']:.3f}", f"{first['Accuracy']:.1%}",
                                                          f"{first['Mean prediction']:.1%}", f"{first['Brier']:.3f}"],
            f"StrokeScope (logistic regression, line {m.threshold:.1%})": [
                f"{s['Found']} of 50", f"{s['Recall']:.0%}", f"{s['Precision']:.0%}", f"{s['Flagged']}", f"{s['AUC-ROC']:.3f}",
                f"{s['Accuracy']:.1%}", f"{df['proba'].mean():.1%}", f"{s['Brier']:.3f}"],
        }, index=["Stroke patients found", "Recall", "Precision", "Patients flagged", "AUC-ROC", "Accuracy",
                  "Average predicted risk (actual 4.9%)", "Brier score (lower is better)"]), width="stretch")
        ui.note("StrokeScope finds 33 more stroke patients. Its accuracy is lower on purpose: accuracy rewards ignoring stroke "
                "patients, and the first version's 93% was below the 95% of answering \"no stroke\" for everyone.")

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
        st.markdown(f"- [Notebook]({NOTEBOOK_URL}): data checks, EDA, the first version's mistakes reproduced, model "
                    "search, thresholds, test results\n"
                    f"- [Project folder]({PROJECT_URL}) in the portfolio repository\n"
                    f"- [App code]({CODE_URL}): Streamlit app, `strokescope/` inference package, `train.py`, tests")
    ui.footer()
