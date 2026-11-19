"""Every page renders without an exception, including the main interactions."""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

PAGES = ["views/screen.py", "views/clinic_list.py", "views/tradeoff.py", "views/risk_factors.py", "views/report.py"]


def run(module: str, setup=None) -> AppTest:
    script = f"""
import streamlit as st
from clinic.ui import inject_css
import importlib
inject_css()
importlib.import_module("{module.replace('/', '.').removesuffix('.py')}").render()
"""
    at = AppTest.from_string(script, default_timeout=60)
    if setup:
        setup(at)
    return at.run()


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    at = run(page)
    assert not at.exception, at.exception


def test_screen_from_list_and_without_bmi():
    at = run("views/screen.py")
    at.segmented_control(key="screen_mode").set_value("From the clinic list").run()
    assert not at.exception
    at.segmented_control(key="screen_mode").set_value("New patient").run()
    at.toggle(key="in_bmi_known").set_value(False).run()
    assert not at.exception


def test_child_work_type_error_is_shown():
    at = run("views/screen.py")
    at.selectbox(key="in_work").set_value("children").run()
    assert at.error and "under 18" in at.error[0].value


def test_tradeoff_slider_moves():
    at = run("views/tradeoff.py")
    at.select_slider(key="line_pct").set_value(0.2).run()
    assert not at.exception
