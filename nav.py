"""Page registry (top navigation), shared by app.py and pages that link to other pages."""

import streamlit as st

from views import clinic_list, report, risk_factors, screen, tradeoff

SCREEN = st.Page(screen.render, title="Screen a patient", icon=":material/stethoscope:", url_path="screen", default=True)
LIST = st.Page(clinic_list.render, title="Clinic list", icon=":material/view_kanban:", url_path="clinic-list")
TRADEOFF = st.Page(tradeoff.render, title="Misses and false alarms", icon=":material/balance:", url_path="misses")
FACTORS = st.Page(risk_factors.render, title="Risk factors", icon=":material/monitor_heart:", url_path="risk-factors")
REPORT = st.Page(report.render, title="Model report", icon=":material/lab_profile:", url_path="report")

PAGES = [SCREEN, LIST, TRADEOFF, FACTORS, REPORT]
