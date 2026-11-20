"""Screen a patient: intake form (or a held-out patient), the risk and tier, why, what treating the treatable factors
would change, and the next step."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
from pydantic import ValidationError

from clinic import data, fmt, ui
from clinic import theme as t
from strokescope.schema import (
    BACKGROUND, FEATURES, FIXED, LABELS, SHORT, SMOKING, SMOKING_LABELS, WORK_LABELS, WORK_TYPES, Patient,
)

NEW = dict(gender="Male", age=67.0, hypertension=1, heart_disease=0, ever_married="Yes", work_type="Private",
           Residence_type="Urban", avg_glucose_level=180.0, bmi=31.0, smoking_status="formerly smoked")

NEXT = {
    "Priority": ("Check first.",
                 "Book a stroke risk review soon: a clinician would typically confirm blood pressure, glucose (or HbA1c), "
                 "cholesterol and heart rhythm, and review the treatment of any condition already known."),
    "Check": ("Offer a check.",
              "Include this patient in the next round of risk checks (blood pressure, glucose, heart rhythm). Most patients "
              "in this tier have not had a stroke: the check is how the false alarms are sorted out."),
    "Routine": ("Routine care.",
                "No extra check on the model's account. A low score never rules a stroke out: in the test set, 8 of the 50 "
                "stroke patients scored below the screening line, all under 48 with no recorded risk factor."),
}


def _intake() -> pd.DataFrame | None:
    a, b = st.columns(2)
    sex = a.segmented_control("Sex", ["Female", "Male"], default=NEW["gender"], key="in_sex", required=True)
    age = b.number_input("Age (years)", 0.1, 100.0, NEW["age"], step=1.0, format="%.0f", key="in_age")
    st.html('<p class="fgroup-t">Conditions already diagnosed</p>')
    a, b = st.columns(2)
    hyp = a.toggle("Hypertension", bool(NEW["hypertension"]), key="in_hyp")
    heart = b.toggle("Heart disease", bool(NEW["heart_disease"]), key="in_heart")
    st.html('<p class="fgroup-t">Measurements</p>')
    a, b = st.columns(2)
    glucose = a.number_input("Average glucose (mg/dl)", 40.0, 400.0, NEW["avg_glucose_level"], step=5.0, format="%.0f",
                             key="in_glu")
    bmi_known = b.toggle("BMI recorded", True, key="in_bmi_known")
    bmi = b.number_input("BMI", 10.0, 100.0, NEW["bmi"], step=0.5, format="%.1f", key="in_bmi", disabled=not bmi_known,
                         label_visibility="collapsed")
    st.html('<p class="fgroup-t">Lifestyle and background</p>')
    smoking = st.selectbox("Smoking", SMOKING, index=SMOKING.index(NEW["smoking_status"]),
                           format_func=SMOKING_LABELS.get, key="in_smoke")
    a, b = st.columns(2)
    work = a.selectbox("Work type", WORK_TYPES, index=0, format_func=WORK_LABELS.get, key="in_work")
    married = b.selectbox("Ever married", ["Yes", "No"], key="in_married")
    residence = st.segmented_control("Residence", ["Urban", "Rural"], default="Urban", key="in_res", required=True)
    try:
        return Patient(gender=sex, age=age, hypertension=int(hyp), heart_disease=int(heart), avg_glucose_level=glucose,
                       bmi=bmi if bmi_known else None, smoking_status=smoking, work_type=work, ever_married=married,
                       Residence_type=residence).to_frame()
    except ValidationError as exc:
        st.error(exc.errors()[0]["msg"].removeprefix("Value error, "), icon=":material/error:")
        return None


def _from_list() -> tuple[pd.DataFrame, pd.Series]:
    clinic = data.clinic().sort_values("proba", ascending=False).reset_index(drop=True)
    ids = clinic["patient_id"].tolist()
    current = st.session_state.get("patient_id", ids[0])
    choice = st.selectbox("Held-out patient", ids, index=ids.index(current) if current in ids else 0, key="pick_patient",
                          format_func=lambda pid: (lambda r: f"#{pid} · {fmt.summary(r)} · {r['tier']}")(
                              clinic.loc[clinic["patient_id"] == pid].iloc[0]))
    st.session_state["patient_id"] = choice
    record = clinic.loc[clinic["patient_id"] == choice].iloc[0]
    ui.sheet([(LABELS[f], fmt.value(f, record[f])) for f in FEATURES])
    return pd.DataFrame([record[FEATURES].to_dict()]).astype({"age": float, "avg_glucose_level": float, "bmi": float}), record


def _row(f: str, patient: pd.Series, mult: pd.Series) -> dict:
    """One results-table row: the value, a lab-style flag and the reference interval where one exists."""
    v = patient[f]
    flag, ref = "", ""
    if f == "avg_glucose_level":
        ref = "70 to 116 mg/dl"
        flag = "H" if v >= 117 else "L" if v < 70 else ""
    elif f == "bmi":
        ref = "18.5 to 24.9"
        if not pd.isna(v):
            flag = "H" if v >= 25 else "L" if v < 18.5 else ""
    elif f in ("hypertension", "heart_disease"):
        ref = "Negative"
        flag = "+" if int(v) == 1 else ""
    elif f == "smoking_status":
        ref = "Never smoked"
        flag = "+" if v == "smokes" else ""
    result = fmt.value(f, v)
    if f in ("hypertension", "heart_disease"):
        result = "Positive" if int(v) == 1 else "Negative"
    if f == "bmi" and pd.isna(v):
        result = "not recorded (estimated)"
    return {"test": LABELS[f] if f != "avg_glucose_level" else "Average glucose", "result": result, "flag": flag, "ref": ref,
            "mult": float(mult[f])}


def _report(patient: pd.Series, p: float, tier: str, rows: list[dict]) -> str:
    lines = ["StrokeScope screening summary (screening aid, not a diagnosis)", "",
             f"Model risk: {p:.1%}   Tier: {tier}", ""]
    lines += [f"{LABELS[f]}: {fmt.value(f, patient[f])}" for f in FEATURES]
    if rows:
        lines += ["", "If treatable factors were controlled:"] + [f"  {r['label']}: {r['before']:.1%} -> {r['after']:.1%}" for r in rows]
    lines += ["", f"Next step: {NEXT[tier][0]} {NEXT[tier][1]}", "",
              "Stroke warning signs (FAST): Face drooping, Arm weakness, Speech difficulty, Time to call emergency services.",
              "Generated by StrokeScope, a portfolio demonstration. Not medical advice."]
    return "\n".join(lines)


def render() -> None:
    m = data.model()
    ui.page("Screen a patient", "Who should be checked for stroke risk?",
            "Enter a patient's record, or open one of the held-out patients. StrokeScope estimates how closely the profile "
            "matches patients who have had a stroke, places it on the <b>Routine / Check / Priority</b> scale and shows "
            "<b>which factors drive it</b> and <b>which of them can be treated</b>.")
    mode = st.segmented_control("Source", ["New patient", "From the clinic list"], default="New patient", required=True,
                                key="screen_mode", label_visibility="collapsed")

    left, right = st.columns([1, 1.45], gap="medium")
    with left:
        with ui.panel("A", "Patient record", "the 10 fields the model reads"):
            if mode == "New patient":
                row, record = _intake(), None
            else:
                row, record = _from_list()
    if row is None:
        return
    p = float(m.predict_proba(row)[0])
    tier = m.tier(p)
    patient = row.iloc[0]
    rates = data.band_rates()
    band = str(data.age_band(pd.Series([patient["age"]])).iloc[0])
    stroke_rate = m.meta["stroke_rate"]

    with right:
        with ui.panel("B", "Result", "the model's estimate and where it falls"):
            times = p / stroke_rate
            ui.verdict(p, tier, f"Among patients with a profile like this, about <b>{p * 1000:.0f} in 1,000</b> had had a "
                                f"stroke: {times:.1f} times the average patient ({stroke_rate:.1%}). "
                                f"{t.TIER_TEXT[tier]}",
                       f"All patients <b>{stroke_rate:.1%}</b><br>Age {band}: <b>{rates[band]:.1%}</b><br>"
                       f"Check from <b>{m.threshold:.1%}</b> · Priority from <b>{m.high:.1%}</b>")
            ui.ruler(p, m.threshold, m.high, [(stroke_rate, f"All patients {stroke_rate:.1%}"),
                                              (float(rates[band]), f"Age {band}: {rates[band]:.1%}")])
            if record is not None:
                outcome = "had a stroke" if record["stroke"] == 1 else "had not had a stroke"
                ui.caution(f"<b>Held-out outcome:</b> this patient {outcome}. The model never saw them in training.")

    contrib = m.explain(row).iloc[0]
    mult = np.exp(contrib)
    with ui.panel("C", "Results and what they do to the risk",
                  "each finding with its flag and reference interval, and the factor by which the model multiplies the "
                  "odds compared with the average patient"):
        ui.results([("Measurements", [_row(f, patient, mult) for f in ("avg_glucose_level", "bmi")]),
                    ("History", [_row(f, patient, mult) for f in ("hypertension", "heart_disease", "smoking_status")]),
                    ("Demographics", [_row(f, patient, mult) for f in FIXED]),
                    ("Background", [_row(f, patient, mult) for f in BACKGROUND])])
        top = mult.drop(FIXED).sort_values(ascending=False)
        lead = ", ".join(f"{SHORT[f].lower()} (× {v:.2f})" for f, v in top.items() if v >= 1.05) or "none of them"
        ui.note(f"<b>Age</b> multiplies this patient's odds by {mult['age']:.2f}. Among the factors that can be treated or "
                f"changed, the ones raising the risk are: {lead}.",
                "Odds multipliers come straight from the logistic regression: the average patient's odds times every "
                "multiplier give this patient's odds exactly. Rows in grey barely move the score.")

    a, b = st.columns(2, gap="medium")
    rows = m.what_if(row)
    with a:
        with ui.panel("D", "If the treatable factors were controlled", "the model's risk after one change"):
            if rows:
                ui.what_if(rows)
            else:
                ui.note("This patient has no hypertension and a glucose level under 125 mg/dl: no treatable factor the "
                        "model can measure is raised.")
            ui.caution("These are the scores of patients with that profile in the data, not a promise of what treatment "
                       "achieves. Quitting smoking and losing weight matter medically, but this data cannot measure their "
                       "benefit (former smokers are older; BMI adds almost nothing once age is known).")
    with b:
        with ui.panel("E", "Next step", NEXT[tier][0]):
            st.html(f'<div style="margin:-.2rem 0 .7rem">{ui.tier_badge(tier)}</div>'
                    f'<p style="margin:0 0 .8rem;line-height:1.6">{NEXT[tier][1]}</p>')
            ui.fast()
            st.download_button("Download the screening summary", _report(patient, p, tier, rows), "strokescope-summary.txt",
                               icon=":material/download:", key="dl_summary")
    ui.signature(f"Calculated by the StrokeScope logistic regression (trained on {m.meta['train_rows']:,} patients). Glucose "
                 "reference: an average below 117 mg/dl matches an HbA1c below 5.7%. A screening aid; not reviewed by a clinician.")
    ui.footer()
