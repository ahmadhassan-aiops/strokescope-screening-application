"""
StrokeScope: stroke risk screening. Score a patient or a clinic list, see why, and see what the screening line costs in
missed strokes and false alarms. Model in model/ (built by train.py), code in strokescope/.
"""

from pathlib import Path

import streamlit as st

st.set_page_config(page_title="StrokeScope | Stroke risk screening | Ahmad Hassan", page_icon=":material/neurology:",
                   layout="wide", initial_sidebar_state="collapsed")

from clinic.ui import inject_css  # noqa: E402
from nav import PAGES  # noqa: E402

st.logo(str(Path(__file__).parent / "assets" / "logo.svg"), size="large")
inject_css()
st.navigation(PAGES, position="top").run()
