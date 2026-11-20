"""Clinic list: score a whole list of patients and sort it into three lanes (Priority, Check, Routine)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from clinic import charts, data, fmt, ui
from strokescope.schema import FEATURES, SMOKING_LABELS, validate_rows

LANES = ["Priority", "Check", "Routine"]


def _template() -> bytes:
    sample = data.clinic()[FEATURES].head(5)
    return sample.to_csv(index=False).encode()


def _uploaded() -> pd.DataFrame | None:
    file = st.file_uploader("Patient list (CSV)", type="csv", key="upload")
    st.download_button("Download a template (5 patients)", _template(), "strokescope-template.csv", icon=":material/download:")
    if file is None:
        return None
    rows, errors = validate_rows(pd.read_csv(file))
    for e in errors:
        st.warning(e, icon=":material/rule:")
    if rows.empty:
        return None
    m = data.model()
    rows = rows.reset_index(drop=True)
    rows.insert(0, "patient_id", range(1, len(rows) + 1))
    rows["proba"] = m.predict_proba(rows)
    rows["tier"] = m.tiers(rows["proba"].to_numpy())
    return rows


def render() -> None:
    m = data.model()
    ui.page("Clinic list", "Sort a clinic list into three lanes",
            "Score every patient on a list at once. <b>Priority</b> patients are checked first, <b>Check</b> patients in the "
            "next round, <b>Routine</b> patients stay in normal care. The held-out list is 1,022 patients the model never "
            "saw, with their real outcome; you can also upload your own CSV.")
    src = st.segmented_control("Source", ["Held-out patients", "Upload a CSV"], default="Held-out patients",
                               required=True, key="list_src", label_visibility="collapsed")
    held_out = src == "Held-out patients"
    if held_out:
        df = data.clinic()
    else:
        with st.container(border=True):
            ui.panel_head("A", "Upload", "one row per patient, the 10 model columns; BMI may be blank")
            df = _uploaded()
        if df is None:
            ui.footer()
            return

    counts = df["tier"].value_counts().reindex(LANES, fill_value=0)
    items = [("Patients scored", f"{len(df):,}", "on this list")]
    items += [(lane, f"{counts[lane]:,}", f"{counts[lane] / len(df):.0%} of the list") for lane in LANES]
    if held_out:
        found = int(df.loc[df["tier"] != "Routine", "stroke"].sum())
        items.append(("Stroke patients flagged", f"{found} of {int(df['stroke'].sum())}", "Priority or Check"))
    ui.stats(items)

    letter = iter("BCDE" if not held_out else "ABCD")
    with ui.panel(next(letter), "Triage board", "the six highest risks in each lane; for Routine, the patients nearest the screening line"):
        cols = st.columns(3, gap="small")
        for col, lane in zip(cols, LANES):
            with col:
                d = df[df["tier"] == lane].sort_values("proba", ascending=False)
                show = d.head(6)
                ui.lane(lane, len(d), int(d["stroke"].sum()) if held_out else None,
                        [{"id": int(r["patient_id"]), "who": fmt.who(r), "p": r["proba"], "tags": fmt.tags(r),
                          "stroke": held_out and bool(r["stroke"])} for _, r in show.iterrows()], len(d) - len(show))

    if held_out:
        with ui.panel(next(letter), "What each lane holds", "held-out patients by real outcome"):
            a, b = st.columns([1.4, 1], gap="large")
            with a:
                charts.show(charts.tier_mix(df), "mix")
            with b:
                prio, chk, rout = (df[df["tier"] == x] for x in LANES)
                ui.note(f"<b>Priority:</b> {int(prio['stroke'].sum())} of {len(prio)} had a stroke "
                        f"({prio['stroke'].mean():.0%}), {prio['stroke'].mean() / df['stroke'].mean():.1f} times the list average.",
                        f"<b>Check:</b> {int(chk['stroke'].sum())} of {len(chk)} ({chk['stroke'].mean():.0%}), close to the average. This "
                        f"lane exists to catch those {int(chk['stroke'].sum())} patients, at the cost of "
                        f"{int((chk['stroke'] == 0).sum())} checks that find no stroke.",
                        f"<b>Routine:</b> {int(rout['stroke'].sum())} of {len(rout)} ({rout['stroke'].mean():.1%}). "
                        "These are the missed patients; the Misses and false alarms page shows who they are.")

    with ui.panel(next(letter), "Full list", "select a row to open the patient" if held_out else "ranked by risk"):
        table = df.sort_values("proba", ascending=False).reset_index(drop=True)
        view = pd.DataFrame({
            "Patient": table["patient_id"].map(lambda v: f"#{int(v)}"), "Tier": table["tier"],
            "Risk": table["proba"] * 100, "Sex": table["gender"], "Age": table["age"],
            "Hypertension": table["hypertension"].map({1: "Yes", 0: "No"}),
            "Heart disease": table["heart_disease"].map({1: "Yes", 0: "No"}), "Glucose": table["avg_glucose_level"],
            "BMI": table["bmi"], "Smoking": table["smoking_status"].map(SMOKING_LABELS),
        })
        if held_out:
            view["Had a stroke"] = table["stroke"].map({1: "Yes", 0: "No"})
        config = {"Risk": st.column_config.ProgressColumn("Risk", format="%.1f%%", min_value=0, max_value=40),
                  "Age": st.column_config.NumberColumn(format="%.0f"), "Glucose": st.column_config.NumberColumn(format="%.0f"),
                  "BMI": st.column_config.NumberColumn(format="%.1f")}
        if held_out:
            event = st.dataframe(view, hide_index=True, width="stretch", height=380, column_config=config,
                                 on_select="rerun", selection_mode="single-row", key="list_table")
            if event.selection.rows:
                from nav import SCREEN
                st.session_state["patient_id"] = int(table.loc[event.selection.rows[0], "patient_id"])
                st.session_state["screen_mode"] = "From the clinic list"
                st.switch_page(SCREEN)
        else:
            st.dataframe(view, hide_index=True, width="stretch", height=380, column_config=config)
        out = table.drop(columns=[c for c in ["stroke"] if c in table.columns]).rename(columns={"proba": "risk"})
        st.download_button("Download the ranked list", out.to_csv(index=False).encode(), "strokescope-ranked.csv",
                           icon=":material/download:", key="dl_list")
        ui.note(f"The lines: <b>Check</b> from {ui.pct(m.threshold)} (set to find 85% of stroke patients in cross-validation), "
                f"<b>Priority</b> from {ui.pct(m.high)} (the best balance of precision and recall, F1).")
    ui.footer()
