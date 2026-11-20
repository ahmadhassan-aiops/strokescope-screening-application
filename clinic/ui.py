"""StrokeScope components: a hospital laboratory report. Every page opens with a maroon letterhead; every block is a
report section on a white sheet with a heavy rule under its heading; results are monospaced rows with H/L flags,
reference intervals and the model's effect; comments, critical-value alerts and a worklist complete the report."""

from __future__ import annotations

import html
import math
from contextlib import contextmanager

import pandas as pd
import streamlit as st

from clinic import theme as t
from clinic.site import CODE_URL, DATA_CREDIT, LEARN_URL, NOTEBOOK_URL

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;500;600;700;800&family=Roboto+Mono:wght@400;500;600;700&display=swap');
:root {{ --bg:{t.BG}; --panel:{t.PANEL}; --line:{t.LINE}; --rule:{t.RULE}; --ink:{t.INK}; --muted:{t.MUTED}; --faint:{t.FAINT};
         --shade:{t.SHADE}; --brand:{t.BRAND}; --brand-dark:{t.BRAND_DARK}; --brand-soft:{t.BRAND_SOFT};
         --sans:{t.SANS}; --mono:{t.MONO}; }}
html, body, [data-testid="stAppViewContainer"] {{ font-family: var(--sans); color: var(--ink); }}
[data-testid="stAppViewContainer"], [data-testid="stMain"] {{ background: var(--bg); }}
.block-container {{ padding-top: 4.4rem; max-width: 1180px; }}
header[data-testid="stHeader"] {{ background: #ffffff; border-bottom: 3px solid var(--brand); }}
.msr {{ font-family: 'Material Symbols Rounded'; font-weight: normal; font-style: normal; line-height: 1; display: inline-block;
        -webkit-font-feature-settings: 'liga'; font-feature-settings: 'liga'; -webkit-font-smoothing: antialiased; }}

/* Report sheets: square, a hairline border and a paper shadow */
[data-testid="stVerticalBlock"][data-test-scroll-behavior] {{ border: 1px solid var(--line) !important; border-radius: 0 !important;
    background: var(--panel); box-shadow: 0 1px 2px rgba(29,35,48,.06), 0 6px 18px -12px rgba(29,35,48,.25); }}

/* Letterhead */
.lh {{ background: var(--panel); border: 1px solid var(--line); border-top: 6px solid var(--brand); padding: 1rem 1.3rem .9rem;
       margin: 0 0 1.2rem; display: grid; grid-template-columns: 1fr auto; gap: 1rem 1.5rem; align-items: start;
       box-shadow: 0 6px 18px -12px rgba(29,35,48,.25); }}
@media (max-width: 760px) {{ .lh {{ grid-template-columns: 1fr; }} }}
.lh-org {{ font-family: var(--mono); font-size: .7rem; letter-spacing: .12em; text-transform: uppercase; color: var(--brand); margin: 0 0 .5rem; font-weight: 600; }}
.lh-t {{ font-size: 2rem; font-weight: 800; letter-spacing: -.01em; margin: 0; line-height: 1.12; color: var(--ink); }}
.lh-l {{ color: var(--muted); font-size: .98rem; line-height: 1.6; max-width: 760px; margin: .45rem 0 0; }}
.lh-l b {{ color: var(--ink); font-weight: 600; }}
.lh-box {{ border: 1.5px solid var(--brand); padding: .45rem .7rem; font-family: var(--mono); font-size: .7rem; line-height: 1.5;
           letter-spacing: .06em; text-transform: uppercase; color: var(--brand); text-align: center; font-weight: 600; }}

/* Section heading with a heavy rule */
.sec {{ display: flex; align-items: baseline; gap: .7rem; border-bottom: 2px solid var(--rule); padding: 0 0 .35rem; margin: -.2rem 0 .3rem; }}
.sec-k {{ font-family: var(--mono); font-size: .7rem; letter-spacing: .1em; color: #fff; background: var(--brand); padding: .12rem .45rem; font-weight: 600; flex: none; }}
.sec-t {{ font-size: 1.08rem; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; margin: 0; }}
.sec-s {{ font-size: .84rem; color: var(--muted); margin: .4rem 0 .8rem; line-height: 1.45; }}
.sec-s::first-letter {{ text-transform: uppercase; }}

/* Summary row */
.stats {{ display: grid; grid-template-columns: repeat(var(--n), minmax(0, 1fr)); margin: 0 0 1rem; background: var(--panel);
          border: 1px solid var(--line); border-top: 2px solid var(--rule); }}
@media (max-width: 800px) {{ .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
.stat {{ padding: .6rem .9rem; border-right: 1px solid var(--line); }}
.stat:last-child {{ border-right: none; }}
.stat-l {{ font-family: var(--mono); font-size: .66rem; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: 0; }}
.stat-v {{ font-family: var(--mono); font-size: 1.5rem; font-weight: 600; margin: .15rem 0 .05rem; line-height: 1.15; }}
.stat-n {{ font-size: .78rem; color: var(--faint); margin: 0; }}

/* Lab result tables */
.lab {{ width: 100%; border-collapse: collapse; font-size: .9rem; }}
.lab th {{ font-family: var(--mono); font-size: .66rem; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); font-weight: 600;
           text-align: left; padding: .35rem .5rem; border-bottom: 1.5px solid var(--rule); }}
.lab td {{ padding: .42rem .5rem; border-bottom: 1px solid var(--line); vertical-align: middle; }}
.lab tr.grp td {{ background: var(--shade); font-family: var(--mono); font-size: .66rem; letter-spacing: .1em; text-transform: uppercase;
                  color: var(--brand); font-weight: 700; padding: .3rem .5rem; }}
.lab tr.em td {{ font-weight: 700; background: var(--brand-soft); }}
.lab td.r {{ font-family: var(--mono); font-weight: 600; white-space: nowrap; }}
.lab td.f {{ font-family: var(--mono); font-weight: 700; width: 2.4rem; text-align: center; }}
.lab td.ref {{ font-family: var(--mono); font-size: .78rem; color: var(--muted); background: var(--shade); white-space: nowrap; }}
.lab td.x {{ font-family: var(--mono); font-size: .84rem; white-space: nowrap; text-align: right; }}
.lab .eff {{ display: inline-block; width: 96px; height: 8px; background: var(--shade); position: relative; margin-left: .5rem; vertical-align: 1px; }}
.lab .eff::before {{ content: ""; position: absolute; left: 50%; top: -3px; bottom: -3px; width: 1px; background: var(--rule); }}
.lab .eff i {{ position: absolute; top: 0; bottom: 0; background: var(--c); }}
.flag {{ display: inline-block; min-width: 1.3rem; padding: 0 .2rem; color: #fff; background: var(--c); font-size: .74rem; }}

/* The headline result */
.res {{ display: grid; grid-template-columns: 1fr auto; gap: .5rem 1rem; align-items: end; border: 1px solid var(--line);
        border-left: 5px solid var(--c); background: var(--s); padding: .7rem .9rem; }}
.res-n {{ font-family: var(--mono); font-size: .68rem; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: 0; }}
.res-v {{ font-family: var(--mono); font-size: 2.6rem; font-weight: 700; color: var(--c); line-height: 1; margin: .3rem 0 0;
          display: flex; align-items: center; gap: .9rem; flex-wrap: wrap; }}
.res-v small {{ font-size: .9rem; font-weight: 600; color: var(--ink); display: inline-flex; }}
.res-ref {{ font-family: var(--mono); font-size: .76rem; color: var(--muted); text-align: right; line-height: 1.6; }}
.res-ref b {{ color: var(--ink); }}
.tier {{ display: inline-flex; align-items: center; gap: .35rem; padding: .22rem .6rem; font-family: var(--mono); font-weight: 700;
         font-size: .78rem; letter-spacing: .08em; text-transform: uppercase; color: var(--c); background: var(--s); border: 1.5px solid var(--c); }}
.tier .msr {{ font-size: 1rem; }}
.interp {{ margin: .7rem 0 0; font-size: .95rem; line-height: 1.6; }}
.interp-k {{ font-family: var(--mono); font-size: .68rem; letter-spacing: .1em; text-transform: uppercase; color: var(--brand); font-weight: 700; margin: .9rem 0 .2rem; }}

/* Reference interval ruler (log scale) */
.ruler {{ position: relative; margin: 2.4rem .5rem 3.5rem; height: 12px; display: flex; }}
.ruler .z {{ height: 100%; }}
.mk {{ position: absolute; top: -6px; transform: translateX(-50%); text-align: center; }}
.mk i {{ display: block; width: 2px; height: 24px; margin: 0 auto; background: var(--c); }}
.mk span {{ position: absolute; white-space: nowrap; transform: translateX(-50%); left: 50%; font-family: var(--mono); font-size: .7rem; font-weight: 600; color: var(--ink); }}
.mk.up span {{ bottom: 30px; }} .mk.down span {{ color: var(--muted); font-weight: 500; }}
.mk.me i {{ width: 14px; height: 14px; background: var(--brand); border: 3px solid #fff; box-shadow: 0 0 0 2px var(--brand); transform: rotate(45deg); margin-top: -1px; }}
.legend-z {{ display: flex; gap: 1rem; flex-wrap: wrap; font-family: var(--mono); font-size: .7rem; color: var(--muted); margin: .9rem 0 0; }}
.legend-z .lg-note {{ margin-left: auto; color: var(--faint); }}
.legend-z span:not(.lg-note)::before {{ content: ""; display: inline-block; width: .65rem; height: .65rem; background: var(--c); margin-right: .35rem; vertical-align: -1px; }}

/* Comments and cautions */
.note {{ border-top: 1px dashed var(--line); padding: .6rem 0 0; margin: .7rem 0 0; font-size: .9rem; line-height: 1.6; }}
.note::before {{ content: "Comment"; display: block; font-family: var(--mono); font-size: .66rem; letter-spacing: .1em; text-transform: uppercase;
                 color: var(--brand); font-weight: 700; margin: 0 0 .2rem; }}
.note p {{ margin: 0 0 .35rem; }} .note p:last-child {{ margin: 0; }}
.caution {{ border: 1px solid #ecd9a8; background: #fffaf0; padding: .55rem .8rem; margin: .7rem 0 0; font-size: .86rem; line-height: 1.5;
            color: #5c4510; display: flex; gap: .5rem; }}
.caution .msr {{ color: {t.TIER['Check']}; font-size: 1.15rem; }}

/* Critical alert: FAST */
.fast {{ border: 2px solid {t.TIER['Priority']}; margin: .2rem 0 .8rem; }}
.fast-h {{ background: {t.TIER['Priority']}; color: #fff; font-family: var(--mono); font-size: .7rem; letter-spacing: .1em; text-transform: uppercase;
           font-weight: 700; padding: .3rem .6rem; margin: 0; }}
.fast-g {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }}
@media (max-width: 800px) {{ .fast-g {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
.fast-g div {{ padding: .5rem .6rem; border-right: 1px solid #f1caca; }}
.fast-g div:last-child {{ border-right: none; }}
.fast-g b {{ font-family: var(--mono); font-size: 1.5rem; color: {t.TIER['Priority']}; display: block; line-height: 1.1; }}
.fast-g span {{ font-size: .82rem; }}

/* Specimen / patient block: one labelled row per field */
.sheet {{ display: grid; grid-template-columns: 1fr; border-top: 1.5px solid var(--rule); margin: .6rem 0 0; padding: 0 !important; }}
.sheet > div {{ margin: 0; }}
.sheet div {{ display: grid; grid-template-columns: minmax(7.5rem, 42%) 1fr; gap: .8rem; align-items: baseline; padding: .4rem .3rem;
              border-bottom: 1px solid var(--line); font-size: .9rem; }}
.sheet div:nth-child(even) {{ background: var(--shade); }}
.sheet dt {{ font-family: var(--mono); font-size: .68rem; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }}
.sheet dd {{ margin: 0; font-weight: 600; }}

/* Worklist (triage lanes): every patient row has the same two-line height, so rows line up across the lanes */
.lane-h {{ display: flex; justify-content: space-between; align-items: center; padding: .45rem .7rem; background: var(--c); color: #fff; margin: 0; }}
.lane-h b {{ font-family: var(--mono); font-size: .8rem; letter-spacing: .1em; text-transform: uppercase; display: inline-flex; gap: .35rem; align-items: center; }}
.lane-h > span {{ font-family: var(--mono); font-size: 1.15rem; font-weight: 700; }}
.lane-n {{ font-size: .8rem; color: var(--muted); margin: 0; padding: .5rem .7rem; line-height: 1.45; min-height: 4.6rem; box-sizing: border-box;
           background: var(--shade); border: 1px solid var(--line); border-top: none; }}
.lane-n b {{ color: var(--ink); font-weight: 600; }}
.prows {{ border: 1px solid var(--line); border-top: none; }}
.prow {{ display: grid; grid-template-columns: minmax(0, 1fr) 5.2rem; gap: .3rem .7rem; align-items: center; padding: .5rem .7rem;
         border-top: 1px solid var(--line); height: 3.75rem; box-sizing: border-box; }}
.prow:first-child {{ border-top: none; }}
.prow-id {{ font-family: var(--mono); font-weight: 600; font-size: .82rem; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.prow-id span {{ font-family: var(--sans); font-weight: 400; color: var(--muted); margin-left: .45rem; font-size: .8rem; }}
.prow-r {{ font-family: var(--mono); font-weight: 700; color: var(--c); font-size: .92rem; margin: 0; text-align: right; }}
.prow-tags {{ grid-column: 1 / -1; display: flex; gap: .3rem; overflow: hidden; white-space: nowrap; min-width: 0; }}
.tg {{ font-family: var(--mono); font-size: .64rem; letter-spacing: .03em; padding: .05rem .35rem; border: 1px solid var(--line); color: var(--ink);
       background: #fff; flex: none; }}
.tg.none {{ border-color: transparent; background: transparent; color: var(--muted); padding-left: .1rem; }}
.tg.out {{ border-color: {t.TIER['Priority']}; color: {t.TIER['Priority']}; font-weight: 700; }}
.lane-more {{ font-family: var(--mono); font-size: .72rem; color: var(--muted); margin: 0; padding: .5rem .7rem; border: 1px solid var(--line);
              border-top: none; background: var(--shade); }}

/* Natural frequency tree: boxes joined by bracket lines */
.tree {{ display: flex; align-items: center; overflow-x: auto; padding: .3rem 0 .2rem; width: fit-content; max-width: 100%; margin: 0 auto; }}
.tree .node {{ flex: none; width: 15rem; border: 1px solid var(--line); border-top: 3px solid var(--c); padding: .5rem .75rem; background: #fff; }}
.node b {{ font-family: var(--mono); font-size: 1.35rem; display: block; color: var(--ink); line-height: 1.2; }}
.node span {{ font-size: .8rem; color: var(--muted); }}
.br {{ position: relative; display: flex; flex-direction: column; gap: .7rem; margin-left: 1.5rem; padding-left: 1.5rem; }}
.br::after {{ content: ""; position: absolute; left: -1.5rem; top: 50%; width: 1.5rem; border-top: 1.5px solid #9aa2ae; }}
.br > * {{ position: relative; }}
.br > *::before {{ content: ""; position: absolute; left: -1.5rem; top: 50%; width: 1.5rem; border-top: 1.5px solid #9aa2ae; }}
.br > :first-child::after {{ content: ""; position: absolute; left: -1.5rem; top: 50%; bottom: -.35rem; border-left: 1.5px solid #9aa2ae; }}
.br > :last-child::after {{ content: ""; position: absolute; left: -1.5rem; top: -.35rem; bottom: 50%; border-left: 1.5px solid #9aa2ae; }}
.grp {{ display: flex; align-items: center; }}

/* Factor cards (kept for other pages) */
.fgroup-t {{ font-family: var(--mono); font-size: .66rem; letter-spacing: .1em; text-transform: uppercase; color: var(--brand); font-weight: 700; margin: .6rem 0 .35rem; }}
.fcards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: .5rem; }}
.fcard {{ border: 1px solid var(--line); border-top: 3px solid var(--c); padding: .45rem .65rem; }}
.fcard-n {{ font-size: .78rem; color: var(--muted); margin: 0; }} .fcard-v {{ font-weight: 600; margin: .1rem 0; }}
.fcard-x {{ font-family: var(--mono); font-size: .82rem; color: var(--c); margin: 0; font-weight: 600; }}

/* Next step */
.next {{ display: grid; grid-template-columns: auto 1fr; gap: .8rem; align-items: start; margin: 0 0 .9rem; }}
.next p {{ margin: 0; line-height: 1.6; font-size: .93rem; }}
@media (max-width: 760px) {{ .next {{ grid-template-columns: 1fr; }} }}

/* Top navigation: report tabs, the open one in maroon with a heavy underline */
header[data-testid="stHeader"] {{ box-shadow: 0 1px 0 rgba(29,35,48,.04); }}
[data-testid="stTopNavLink"] {{ border-radius: 0 !important; padding: .35rem .75rem !important; box-shadow: inset 0 -3px 0 transparent; }}
[data-testid="stTopNavLink"] p {{ font-family: var(--sans); font-weight: 600; font-size: .9rem; color: var(--muted); }}
[data-testid="stTopNavLink"]:hover {{ background: var(--brand-soft) !important; }}
[data-testid="stTopNavLink"]:hover :is(p, [data-testid="stIconMaterial"]) {{ color: var(--brand); }}
[data-testid="stTopNavLink"][aria-current="page"], [data-testid="stTopNavLinkContainer"]:has([aria-current="page"]) [data-testid="stTopNavLink"] {{
    background: var(--brand-soft) !important; box-shadow: inset 0 -3px 0 var(--brand); }}
[data-testid="stTopNavLink"][aria-current="page"] :is(p, [data-testid="stIconMaterial"]) {{ color: var(--brand); }}

.foot {{ margin: 2rem 0 .5rem; padding: .9rem 0 0; border-top: 3px double var(--rule); font-size: .8rem; color: var(--muted); line-height: 1.65; }}
.foot a {{ color: var(--brand); font-weight: 600; }}
.sig {{ font-family: var(--mono); font-size: .72rem; color: var(--muted); letter-spacing: .04em; margin: 1rem 0 0; padding-top: .5rem; border-top: 1px solid var(--line); }}
</style>
"""


CONTROLS = """<style>
/* Controls: one shape, one border weight and one focus ring for every button, segment and input */
:root { --k-a: #7b2343; --k-a-text: #5c1a32; --k-fill: #7b2343; --k-fill-2: #5c1a32; --k-soft: #f8eef2; --k-ink: #1d2330;
        --k-line: #a9b0bb; --k-panel: #ffffff; --k-r: 0px; }
[data-testid="stMain"] :is([data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"],
  [data-testid="stBaseButton-secondaryFormSubmit"], [data-testid="stBaseButton-primaryFormSubmit"],
  [data-testid="stBaseButton-segmented_control"], [data-testid="stBaseButton-segmented_controlActive"],
  [data-testid="stBaseButton-pills"], [data-testid="stBaseButton-pillsActive"]) {
    border-radius: var(--k-r) !important; border: 1.5px solid var(--k-line) !important; background: var(--k-panel) !important;
    color: var(--k-ink) !important; box-shadow: none !important; min-height: 2.45rem; padding: .35rem .95rem !important;
    transition: border-color .12s ease, background-color .12s ease, color .12s ease; }
[data-testid="stMain"] :is([data-testid^="stBaseButton-secondary"], [data-testid^="stBaseButton-primary"],
  [data-testid^="stBaseButton-segmented_control"], [data-testid^="stBaseButton-pills"]) p {
    font-family: 'Libre Franklin', 'Segoe UI', sans-serif; font-size: .88rem; font-weight: 600; letter-spacing: .01em; text-transform: none; color: inherit; }
[data-testid="stMain"] :is([data-testid^="stBaseButton-secondary"], [data-testid="stBaseButton-segmented_control"],
  [data-testid="stBaseButton-pills"]):hover { border-color: var(--k-a) !important; color: var(--k-a-text) !important; background: var(--k-soft) !important; }
[data-testid="stMain"] :is([data-testid^="stBaseButton-primary"], [data-testid="stBaseButton-segmented_controlActive"],
  [data-testid="stBaseButton-pillsActive"]) { background: var(--k-fill) !important; border-color: var(--k-fill) !important; color: #fff !important; }
[data-testid="stMain"] :is([data-testid^="stBaseButton-primary"], [data-testid="stBaseButton-segmented_controlActive"],
  [data-testid="stBaseButton-pillsActive"]):hover { background: var(--k-fill-2) !important; border-color: var(--k-fill-2) !important; color: #fff !important; }
[data-testid="stMain"] :is([data-testid^="stBaseButton-secondary"], [data-testid^="stBaseButton-primary"]):active { transform: translateY(1px); }
[data-testid="stMain"] [data-testid^="stBaseButton-"]:disabled { opacity: .45; }

/* Segmented controls: one joined strip, the chosen segment filled */
[data-testid="stMain"] [data-baseweb="button-group"] { gap: 0 !important; width: fit-content; max-width: 100%; border-radius: var(--k-r); }
[data-testid="stMain"] [data-baseweb="button-group"] > button { border-radius: 0 !important; margin: 0 0 0 -1.5px !important; position: relative;
    padding: .35rem .8rem !important; white-space: nowrap; }
[data-testid="stMain"] [data-baseweb="button-group"] > button:first-child { margin-left: 0 !important; border-radius: var(--k-r) 0 0 var(--k-r) !important; }
[data-testid="stMain"] [data-baseweb="button-group"] > button:last-child { border-radius: 0 var(--k-r) var(--k-r) 0 !important; }
[data-testid="stMain"] [data-baseweb="button-group"] > button:only-child { border-radius: var(--k-r) !important; }
[data-testid="stMain"] [data-baseweb="button-group"] > button:hover { z-index: 1; }
[data-testid="stMain"] [data-baseweb="button-group"] > [data-testid$="Active"] { z-index: 2; }

/* The focus ring: the same 2px ring, 2px off the edge, on every control (mouse click and keyboard alike) */
[data-testid="stMain"] [data-testid^="stBaseButton-"]:focus, [data-testid="stMain"] [data-testid^="stBaseButton-"]:focus-visible,
[data-testid="stPageLink"] a:focus-visible, [data-testid="stTopNavLink"]:focus-visible, [data-testid="stSidebarNavLink"]:focus-visible,
[data-testid="stMain"] [role="slider"]:focus-visible, [data-testid="stMain"] summary:focus-visible, [data-testid="stMain"] a:focus-visible {
    outline: 2px solid var(--k-a) !important; outline-offset: 2px; box-shadow: none !important; }
[data-testid="stMain"] [data-baseweb="button-group"] > button:focus, [data-testid="stMain"] [data-baseweb="button-group"] > button:focus-visible { outline: none !important; }
[data-testid="stMain"] [data-baseweb="button-group"]:focus-within { outline: 2px solid var(--k-a); outline-offset: 2px; }
[data-testid="stMain"] [data-testid="stCheckbox"] label:has(input:focus-visible) { outline: 2px solid var(--k-a); outline-offset: 3px; border-radius: var(--k-r); }

/* Inputs: square to the kit, a firm border, the accent border and ring while typing */
[data-testid="stMain"] :is([data-testid="stNumberInputContainer"], [data-testid="stTextInput"] [data-baseweb="input"],
  [data-testid="stDateInput"] [data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"]) {
    border-radius: var(--k-r) !important; border: 1.5px solid var(--k-line) !important; background: var(--k-panel) !important;
    min-height: 2.45rem; transition: border-color .12s ease; }
[data-testid="stMain"] :is([data-testid="stNumberInputContainer"], [data-testid="stTextInput"] [data-baseweb="input"],
  [data-baseweb="select"] > div, [data-baseweb="textarea"]):hover { border-color: var(--k-a) !important; }
[data-testid="stMain"] :is([data-testid="stNumberInputContainer"], [data-testid="stTextInput"] [data-baseweb="input"],
  [data-testid="stDateInput"] [data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"]):focus-within {
    border-color: var(--k-a) !important; outline: 2px solid var(--k-a); outline-offset: 2px; box-shadow: none !important; }
[data-testid="stMain"] :is([data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"] > div, input, textarea) { background: transparent !important; }
[data-testid="stMain"] [data-testid="stNumberInputContainer"] [data-baseweb="input"] { border: none !important; }
[data-testid="stMain"] :is(input, textarea) { font-family: 'Roboto Mono', Consolas, monospace; color: var(--k-ink); }
[data-testid="stMain"] [data-testid="stNumberInputContainer"] > div:last-child { border-left: 1px solid var(--k-line); }
[data-testid="stMain"] :is([data-testid="stNumberInputStepDown"], [data-testid="stNumberInputStepUp"]) { color: var(--k-ink) !important; border-radius: 0 !important; width: 2.1rem; }
[data-testid="stMain"] :is([data-testid="stNumberInputStepDown"], [data-testid="stNumberInputStepUp"]):hover:not(:disabled) { background: var(--k-soft) !important; color: var(--k-a-text) !important; }
[data-testid="stMain"] [data-testid="stNumberInputStepUp"] { border-left: 1px solid var(--k-line) !important; }
[data-baseweb="popover"] [data-baseweb="menu"], [data-baseweb="popover"] ul[role="listbox"] { border-radius: var(--k-r) !important; border: 1.5px solid var(--k-line); }
[data-baseweb="popover"] li[role="option"]:hover, [data-baseweb="popover"] li[aria-selected="true"] { background: var(--k-soft) !important; color: var(--k-a-text); }

/* Labels, sliders, expanders and the file drop zone */
[data-testid="stMain"] [data-testid="stWidgetLabel"]:not([data-testid="stCheckbox"] *) p { font-family: 'Roboto Mono', Consolas, monospace; font-size: .7rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #535b69; }
[data-testid="stMain"] [data-baseweb="slider"] [role="slider"] { box-shadow: 0 0 0 3px var(--k-panel), 0 0 0 4.5px var(--k-fill) !important; }
[data-testid="stMain"] [data-testid="stSliderThumbValue"] { font-family: 'Roboto Mono', Consolas, monospace; font-weight: 600; }
[data-testid="stMain"] [data-testid="stExpander"] details { border: 1.5px solid var(--k-line) !important; border-radius: var(--k-r) !important; background: var(--k-panel); }
[data-testid="stMain"] [data-testid="stExpander"] summary:hover { color: var(--k-a-text); }
[data-testid="stMain"] [data-testid="stFileUploaderDropzone"] { border: 1.5px dashed var(--k-line) !important; border-radius: var(--k-r) !important; background: var(--k-panel) !important; }
[data-testid="stMain"] [data-testid="stFileUploaderDropzone"]:hover { border-color: var(--k-a) !important; background: var(--k-soft) !important; }
[data-testid="stMain"] [data-testid="stAlert"] > div { border-radius: var(--k-r) !important; }
[data-baseweb="modal"] [role="dialog"] { border-radius: var(--k-r) !important; }
</style>"""


def inject_css() -> None:
    st.html(CSS + CONTROLS)


def icon(name: str) -> str:
    return f'<span class="msr" aria-hidden="true">{name}</span>'


def pct(p: float, digits: int | None = None) -> str:
    """Risk as a percentage: one decimal under 20%, none above (unless digits is given)."""
    if digits is None:
        digits = 1 if p < 0.2 else 0
    if p < 0.001:
        return "&lt;0.1%"
    return f"{p * 100:.{digits}f}%"


def page(kicker: str, title: str, lead: str) -> None:
    st.html(f'<div class="lh"><div><p class="lh-org">StrokeScope · Stroke risk screening · {html.escape(kicker)}</p>'
            f'<h1 class="lh-t">{html.escape(title)}</h1><p class="lh-l">{lead}</p></div>'
            '<div class="lh-box">Screening aid<br>not a diagnosis</div></div>')


def panel_head(letter: str, title: str, sub: str = "") -> None:
    s = f'<p class="sec-s">{sub}</p>' if sub else '<div style="height:.5rem"></div>'
    key = f"Section {letter}" if len(letter) == 1 else letter
    st.html(f'<div class="sec"><span class="sec-k">{html.escape(key.upper())}</span><p class="sec-t">{html.escape(title)}</p></div>{s}')


@contextmanager
def panel(letter: str, title: str, sub: str = ""):
    with st.container(border=True):
        panel_head(letter, title, sub)
        yield


def stats(items: list[tuple[str, str, str]]) -> None:
    cells = "".join(f'<div class="stat"><p class="stat-l">{html.escape(a)}</p><p class="stat-v">{b}</p><p class="stat-n">{c}</p></div>'
                    for a, b, c in items)
    st.html(f'<div class="stats" style="--n:{len(items)}">{cells}</div>')


def tier_badge(tier: str) -> str:
    return (f'<span class="tier" style="--c:{t.TIER[tier]};--s:{t.TIER_SOFT[tier]}">{icon(t.TIER_ICON[tier])}'
            f"{html.escape(tier)}</span>")


def verdict(p: float, tier: str, text: str, reference: str = "") -> None:
    """The headline result line: risk as a lab value with its tier flag and reference, then the interpretation."""
    st.html(f'<div class="res" style="--c:{t.TIER[tier]};--s:{t.TIER_SOFT[tier]}"><div><p class="res-n">Stroke-profile risk (model)</p>'
            f'<p class="res-v">{pct(p)}<small>{tier_badge(tier)}</small></p></div><div class="res-ref">{reference}</div></div>'
            f'<p class="interp-k">Interpretation</p><p class="interp" style="margin:0">{text}</p>')


LO, HI = 0.002, 0.5  # ruler range (log scale)


def _x(p: float) -> float:
    p = min(max(p, LO), HI)
    return 100 * (math.log(p) - math.log(LO)) / (math.log(HI) - math.log(LO))


def ruler(p: float, threshold: float, high: float, marks: list[tuple[float, str]]) -> None:
    """Log-scale reference ruler: Routine / Check / Priority zones, the patient (diamond, above) and reference marks."""
    a, b = _x(threshold), _x(high)
    zones = (f'<div class="z" style="width:{a}%;background:{t.TIER_SOFT["Routine"]};border:1px solid {t.TIER["Routine"]}77"></div>'
             f'<div class="z" style="width:{b - a}%;background:{t.TIER_SOFT["Check"]};border:1px solid {t.TIER["Check"]}77"></div>'
             f'<div class="z" style="width:{100 - b}%;background:{t.TIER_SOFT["Priority"]};border:1px solid {t.TIER["Priority"]}77"></div>')
    def side(x: float) -> str:  # keep labels near the ends inside the ruler
        return "left:auto;right:-8px;transform:none" if x > 82 else "left:-8px;transform:none" if x < 18 else ""

    ms = "".join(f'<div class="mk down" style="left:{_x(v)}%;--c:{t.FAINT}"><i></i>'
                 f'<span style="top:{28 + 16 * i}px;{side(_x(v))}">{html.escape(label)}</span></div>'
                 for i, (v, label) in enumerate(sorted(marks)))
    me = f'<div class="mk up me" style="left:{_x(p)}%"><i></i><span style="{side(_x(p))}">This patient {pct(p)}</span></div>'
    st.html(f'<div class="ruler">{zones}{ms}{me}</div>'
            f'<div class="legend-z"><span style="--c:{t.TIER["Routine"]}">Routine &lt; {pct(threshold)}</span>'
            f'<span style="--c:{t.TIER["Check"]}">Check {pct(threshold)} to {pct(high)}</span>'
            f'<span style="--c:{t.TIER["Priority"]}">Priority &ge; {pct(high)}</span>'
            '<span class="lg-note">log scale, 0.2% to 50%</span></div>')


def results(groups: list[tuple[str, list[dict]]]) -> None:
    """Lab results table. Each row: test, result, flag ('H', 'L', '+' or ''), reference, odds multiplier."""
    rows = []
    for title, items in groups:
        if not items:
            continue
        rows.append(f'<tr class="grp"><td colspan="5">{html.escape(title)}</td></tr>')
        for it in items:
            flag = it.get("flag", "")
            fc = t.FLAG_HIGH if flag in ("H", "+") else t.FLAG_LOW if flag == "L" else ""
            fl = f'<span class="flag" style="--c:{fc}">{flag}</span>' if flag else ""
            m = it["mult"]
            if m >= 1.05:
                c, word = t.RAISES, f"× {m:.2f}" if m < 10 else f"× {m:.0f}"
            elif m <= 1 / 1.05:
                c, word = t.LOWERS, f"× {m:.2f}"
            else:
                c, word = t.FAINT, "× 1.0"
            w = min(abs(math.log(max(m, 1e-6))) / math.log(8), 1) * 50
            bar = f'left:50%;width:{w:.1f}%' if m >= 1 else f'left:{50 - w:.1f}%;width:{w:.1f}%'
            rows.append(f'<tr><td>{html.escape(it["test"])}</td><td class="r">{html.escape(it["result"])}</td><td class="f">{fl}</td>'
                        f'<td class="ref">{html.escape(it.get("ref", ""))}</td>'
                        f'<td class="x" style="color:{c}">{word}<span class="eff" style="--c:{c}"><i style="{bar}"></i></span></td></tr>')
    st.html('<table class="lab"><thead><tr><th>Test</th><th>Result</th><th>Flag</th><th>Reference</th>'
            '<th style="text-align:right">Effect on odds</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>")


def factor_groups(groups: list[tuple[str, list[tuple[str, str, float]]]]) -> None:
    """groups: (title, [(factor, value text, odds multiplier)]). Red raises the risk, teal lowers it, grey ~ no effect."""
    out = []
    for title, cards in groups:
        if not cards:
            continue
        cs = []
        for name, value, mult in cards:
            c = t.RAISES if mult >= 1.05 else t.LOWERS if mult <= 1 / 1.05 else t.FAINT
            x = f"× {mult:.2f} odds" if abs(mult - 1) >= .05 else "about no effect"
            cs.append(f'<div class="fcard" style="--c:{c}"><p class="fcard-n">{html.escape(name)}</p>'
                      f'<p class="fcard-v">{html.escape(value)}</p><p class="fcard-x">{x}</p></div>')
        out.append(f'<p class="fgroup-t">{html.escape(title)}</p><div class="fcards">{"".join(cs)}</div>')
    st.html("".join(out))


def what_if(rows: list[dict]) -> None:
    """'Repeat calculation' table: the model's risk now and after one change."""
    body = "".join(f'<tr><td>{html.escape(r["label"])}</td><td class="r">{pct(r["before"])}</td>'
                   f'<td class="r" style="color:{t.LOWERS}">{pct(r["after"])}</td>'
                   f'<td class="x" style="color:{t.LOWERS}">{(r["after"] / r["before"] - 1) * 100:+.0f}%</td></tr>' for r in rows)
    st.html('<table class="lab"><thead><tr><th>Change</th><th>Now</th><th>After</th><th style="text-align:right">Relative</th>'
            f"</tr></thead><tbody>{body}</tbody></table>")


def table(df, formats: dict[str, str] | None = None, mark: str = "deployed") -> None:
    """A DataFrame as a lab table: text columns left, numbers right in mono. Rows whose first cell mentions `mark` are bold."""
    formats = formats or {}
    num = [c for c in df.columns if c in formats or pd.api.types.is_numeric_dtype(df[c])]
    head = "".join(f'<th style="text-align:{"right" if c in num else "left"}">{html.escape(str(c))}</th>' for c in df.columns)
    body = []
    for _, r in df.iterrows():
        strong = mark and mark in str(r.iloc[0])
        cells = []
        for c in df.columns:
            v = r[c]
            if c in num:
                txt = format(v, formats.get(c, "")) if formats.get(c) else str(v)
                cells.append(f'<td class="r" style="text-align:right">{html.escape(txt)}</td>')
            else:
                cells.append(f"<td>{html.escape(str(v))}</td>")
        cls = ' class="em"' if strong else ""
        body.append(f"<tr{cls}>{''.join(cells)}</tr>")
    st.html(f'<table class="lab"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>')


def note(*paras: str) -> None:
    st.html('<div class="note">' + "".join(f"<p>{p}</p>" for p in paras) + "</div>")


def caution(text: str) -> None:
    st.html(f'<div class="caution">{icon("warning")}<div>{text}</div></div>')


def fast() -> None:
    cells = "".join(f"<div><b>{k}</b><span><b style='font-size:.85rem;display:inline;font-family:inherit;color:inherit'>{w}</b> {d}</span></div>"
                    for k, w, d in (("F", "Face", "drooping on one side"), ("A", "Arm", "weakness or numbness"),
                                    ("S", "Speech", "slurred or strange"), ("T", "Time", "to call emergency services")))
    st.html('<div class="fast"><p class="fast-h">Critical: whatever the score, call emergency services at once for</p>'
            f'<div class="fast-g">{cells}</div></div>')


def sheet(rows: list[tuple[str, str]]) -> None:
    st.html('<dl class="sheet">' + "".join(f"<div><dt>{html.escape(k)}</dt><dd>{html.escape(v)}</dd></div>" for k, v in rows) + "</dl>")


def lane(tier: str, count: int, strokes: int | None, rows: list[dict], more: int) -> None:
    """One triage lane as a single block: header, description, patient rows (same height), then the overflow line."""
    outcome = f" Held-out outcome: <b>{strokes} had a stroke</b>." if strokes is not None else ""
    out = []
    for r in rows:
        tags = (["<span class='tg out'>Had a stroke</span>"] if r.get("stroke") else []) + [
            f'<span class="tg">{html.escape(x)}</span>' for x in r["tags"]]
        if len(tags) > 2:
            tags = tags[:2] + [f'<span class="tg none">+{len(tags) - 2}</span>']
        chips = "".join(tags) or '<span class="tg none">no listed risk factor</span>'
        out.append(f'<div class="prow"><p class="prow-id">#{r["id"]}<span>{html.escape(r["who"])}</span></p>'
                   f'<p class="prow-r">{pct(r["p"])}</p><div class="prow-tags">{chips}</div></div>')
    body = f'<div class="prows">{"".join(out)}</div>' if out else ""
    foot = f"+ {more:,} more in the full list below" if more else ("All shown" if out else "No patient in this lane")
    st.html(f'<div class="lane" style="--c:{t.TIER[tier]}"><div class="lane-h"><b>{icon(t.TIER_ICON[tier])} {tier}</b>'
            f'<span>{count:,}</span></div><p class="lane-n">{html.escape(t.TIER_TEXT[tier])}{outcome}</p>{body}'
            f'<p class="lane-more">{foot}</p></div>')


def freq_tree(n: int, strokes: int, found: int, alarms: int) -> None:
    """Natural frequencies: n patients -> stroke / no stroke -> found / missed, false alarm / cleared."""
    missed, others = strokes - found, n - strokes
    cleared = others - alarms

    def node(v: int, label: str, c: str) -> str:
        return f'<div class="node" style="--c:{c}"><b>{v:,}</b><span>{label}</span></div>'

    def word(w: str, c: str) -> str:
        return f"<b style='font-size:.8rem;display:inline;font-family:inherit;color:{c}'>{w}</b>"

    stroke = (f'<div class="grp">{node(strokes, "had a stroke", t.TIER["Priority"])}<div class="br">'
              + node(found, f"{word('found', t.LOWERS)}: flagged for a check", t.LOWERS)
              + node(missed, f"{word('missed', t.RAISES)}: below the line", t.RAISES) + "</div></div>")
    other = (f'<div class="grp">{node(others, "no stroke", t.FAINT)}<div class="br">'
             + node(alarms, "false alarms: checked, no stroke", t.TIER["Check"])
             + node(cleared, "correctly left to routine care", t.FAINT) + "</div></div>")
    st.html(f'<div class="tree">{node(n, "patients screened", t.BRAND)}<div class="br">{stroke}{other}</div></div>')


def signature(text: str) -> None:
    st.html(f'<p class="sig">{text}</p>')


def footer() -> None:
    st.html(f'<div class="foot">Model and app by <b>Ahmad Hassan</b>, AI Engineer · <a href="{NOTEBOOK_URL}" target="_blank">'
            f'Notebook</a> · <a href="{CODE_URL}" target="_blank">App code</a> · <a href="{LEARN_URL}" target="_blank">'
            f"Learn with Ahmad</a><br>{DATA_CREDIT}</div>")
