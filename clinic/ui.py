"""StrokeScope components: a clinical report look. Serif headings (Source Serif 4), IBM Plex body and figures, lettered
panels (A, B, C...) with a header strip, a risk ruler, odds-multiplier factor cards, what-if rows, triage lanes, a
natural-frequency tree and the stroke warning signs. Every block of information sits in its own bordered panel."""

from __future__ import annotations

import html
import math
from contextlib import contextmanager

import streamlit as st

from clinic import theme as t
from clinic.site import CODE_URL, DATA_CREDIT, LEARN_URL, NOTEBOOK_URL

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&display=swap');
:root {{ --bg:{t.BG}; --panel:{t.PANEL}; --line:{t.LINE}; --ink:{t.INK}; --muted:{t.MUTED}; --faint:{t.FAINT};
         --brand:{t.BRAND}; --brand-dark:{t.BRAND_DARK}; --brand-soft:{t.BRAND_SOFT};
         --serif:{t.SERIF}; --sans:{t.SANS}; --mono:{t.MONO}; }}
html, body, [data-testid="stAppViewContainer"] {{ font-family: var(--sans); color: var(--ink); }}
[data-testid="stAppViewContainer"], [data-testid="stMain"] {{ background: var(--bg); }}
.block-container {{ padding-top: 4.6rem; max-width: 1220px; }}
h1, h2, h3 {{ font-family: var(--serif); }}
.msr {{ font-family: 'Material Symbols Rounded'; font-weight: normal; font-style: normal; line-height: 1; display: inline-block;
        -webkit-font-feature-settings: 'liga'; font-feature-settings: 'liga'; -webkit-font-smoothing: antialiased; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ border-color: var(--line) !important; border-radius: 10px !important;
    background: var(--panel); box-shadow: 0 1px 3px rgba(27, 33, 64, .06); }}
header[data-testid="stHeader"] {{ border-bottom: 1px solid var(--line); background: #ffffffee; }}

/* Page head: product line, serif title, purpose, a permanent "screening aid" ribbon */
.head {{ display: grid; grid-template-columns: 1fr auto; gap: 1rem; align-items: end; margin: 0 0 1.1rem; }}
.kicker {{ font-size: .78rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--brand); margin: 0 0 .3rem; }}
.title {{ font-family: var(--serif); font-size: 2.15rem; font-weight: 700; margin: 0; line-height: 1.12; color: var(--ink); }}
.lead {{ color: var(--muted); font-size: 1rem; line-height: 1.6; max-width: 780px; margin: .5rem 0 0; }}
.lead b {{ color: var(--ink); font-weight: 600; }}
.ribbon {{ display: inline-flex; gap: .4rem; align-items: center; background: var(--brand-soft); color: var(--brand-dark);
           border: 1px solid #d9dcfb; border-radius: 999px; padding: .3rem .8rem; font-size: .8rem; font-weight: 600; white-space: nowrap; }}
.ribbon .msr {{ font-size: 1rem; }}
@media (max-width: 760px) {{ .head {{ grid-template-columns: 1fr; }} }}

/* Lettered panel header */
.ph {{ display: flex; gap: .75rem; align-items: flex-start; margin: -.1rem 0 .8rem; }}
.ph-l {{ flex: 0 0 auto; width: 1.9rem; height: 1.9rem; border-radius: 7px; background: var(--brand); color: #fff;
         font-family: var(--serif); font-weight: 700; font-size: 1.05rem; display: grid; place-items: center; }}
.ph-t {{ font-family: var(--serif); font-size: 1.28rem; font-weight: 600; margin: 0; line-height: 1.25; color: var(--ink); }}
.ph-s {{ font-size: .86rem; color: var(--muted); margin: .15rem 0 0; }}

/* Stat tiles */
.stats {{ display: grid; grid-template-columns: repeat(var(--n), minmax(0, 1fr)); gap: .7rem; margin: 0 0 1rem; }}
@media (max-width: 800px) {{ .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
.stat {{ background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: .8rem 1rem; }}
.stat-l {{ font-size: .78rem; color: var(--muted); margin: 0; font-weight: 500; }}
.stat-v {{ font-family: var(--mono); font-size: 1.7rem; font-weight: 600; margin: .2rem 0 .1rem; color: var(--ink); line-height: 1.1; }}
.stat-n {{ font-size: .78rem; color: var(--faint); margin: 0; }}

/* Tier badge */
.tier {{ display: inline-flex; align-items: center; gap: .35rem; border-radius: 6px; padding: .25rem .65rem; font-weight: 700;
         font-size: .85rem; color: var(--c); background: var(--s); border: 1px solid var(--c); }}
.tier .msr {{ font-size: 1.05rem; }}

/* Result header on the patient report */
.verdict {{ display: grid; grid-template-columns: auto 1fr; gap: 1.2rem; align-items: center; padding: .2rem 0 .8rem; }}
.risk-big {{ font-family: var(--mono); font-size: 3.1rem; font-weight: 600; line-height: 1; color: var(--c); margin: 0; }}
.risk-cap {{ font-size: .8rem; color: var(--muted); margin: .35rem 0 0; }}
.verdict-t {{ margin: .45rem 0 0; color: var(--ink); line-height: 1.55; font-size: .95rem; }}

/* Risk ruler (log scale) */
.ruler {{ position: relative; margin: 2.2rem .6rem 3.4rem; height: 14px; border-radius: 7px; display: flex; overflow: visible; }}
.ruler .z {{ height: 100%; }}
.ruler .z:first-child {{ border-radius: 7px 0 0 7px; }} .ruler .z:last-child {{ border-radius: 0 7px 7px 0; }}
.mk {{ position: absolute; top: -6px; transform: translateX(-50%); text-align: center; }}
.mk i {{ display: block; width: 3px; height: 26px; margin: 0 auto; border-radius: 2px; background: var(--c); }}
.mk span {{ position: absolute; white-space: nowrap; transform: translateX(-50%); left: 50%; font-size: .74rem; font-weight: 600; color: var(--ink); }}
.mk.up span {{ bottom: 30px; }} .mk.down span {{ top: 30px; color: var(--muted); font-weight: 500; }}
.mk.me i {{ width: 16px; height: 16px; border-radius: 50%; background: var(--brand); border: 3px solid #fff; box-shadow: 0 0 0 2px var(--brand); margin-top: -1px; }}
.ticks {{ display: flex; justify-content: space-between; font-family: var(--mono); font-size: .7rem; color: var(--faint); margin: -1.9rem .6rem 0; }}
.legend-z {{ display: flex; gap: 1rem; flex-wrap: wrap; font-size: .78rem; color: var(--muted); margin: .9rem 0 0; }}
.legend-z span::before {{ content: ""; display: inline-block; width: .7rem; height: .7rem; border-radius: 2px; background: var(--c); margin-right: .35rem; vertical-align: -1px; }}

/* Factor cards */
.fgroup {{ margin: 0 0 .9rem; }}
.fgroup-t {{ font-size: .76rem; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; color: var(--faint); margin: 0 0 .45rem; }}
.fcards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: .55rem; }}
.fcard {{ border: 1px solid var(--line); border-left: 4px solid var(--c); border-radius: 8px; padding: .55rem .75rem; background: #fff; }}
.fcard-n {{ font-size: .8rem; color: var(--muted); margin: 0; }}
.fcard-v {{ font-size: .95rem; font-weight: 600; margin: .1rem 0; color: var(--ink); }}
.fcard-x {{ font-family: var(--mono); font-size: .86rem; color: var(--c); margin: 0; font-weight: 600; }}

/* What-if rows */
.wi {{ display: grid; grid-template-columns: 1fr auto; gap: .6rem; align-items: center; padding: .6rem .2rem; border-bottom: 1px dashed var(--line); }}
.wi:last-child {{ border-bottom: 0; }}
.wi-l {{ font-weight: 600; margin: 0; }}
.wi-v {{ font-family: var(--mono); margin: 0; white-space: nowrap; }}
.wi-v b {{ color: {t.LOWERS}; }}

/* Notes, cautions, warning signs */
.note {{ background: var(--brand-soft); border: 1px solid #dfe2fb; border-radius: 8px; padding: .7rem .9rem; margin: .6rem 0 0;
         font-size: .9rem; line-height: 1.55; color: var(--ink); }}
.note p {{ margin: 0 0 .35rem; }} .note p:last-child {{ margin: 0; }}
.caution {{ background: #fff8eb; border: 1px solid #f3dfb5; border-radius: 8px; padding: .65rem .9rem; margin: .6rem 0 0;
            font-size: .86rem; line-height: 1.5; color: #5c4510; display: flex; gap: .5rem; }}
.caution .msr {{ color: {t.TIER['Check']}; font-size: 1.15rem; }}
.fast {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .5rem; }}
@media (max-width: 800px) {{ .fast {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
.fast div {{ border: 1px solid #f1caca; background: #fdf3f3; border-radius: 8px; padding: .55rem .7rem; }}
.fast b {{ font-family: var(--serif); font-size: 1.5rem; color: {t.TIER['Priority']}; display: block; line-height: 1; }}
.fast span {{ font-size: .82rem; color: var(--ink); }}

/* Triage lanes */
.lane-h {{ display: flex; justify-content: space-between; align-items: center; border-radius: 8px; padding: .55rem .8rem;
           background: var(--s); border: 1px solid var(--c); margin: 0 0 .6rem; }}
.lane-h b {{ color: var(--c); display: inline-flex; gap: .3rem; align-items: center; }} .lane-h > span {{ font-family: var(--mono); font-size: 1.3rem; font-weight: 600; color: var(--ink); }}
.lane-n {{ font-size: .8rem; color: var(--muted); margin: -.2rem 0 .6rem; }}
.pcard {{ border: 1px solid var(--line); border-radius: 8px; padding: .5rem .7rem; margin: 0 0 .45rem; background: #fff; }}
.pcard-t {{ display: flex; justify-content: space-between; font-weight: 600; font-size: .88rem; margin: 0; }}
.pcard-t span {{ font-family: var(--mono); color: var(--c); }}
.pcard-s {{ font-size: .78rem; color: var(--muted); margin: .15rem 0 0; }}

/* Natural frequency tree */
.tree {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: .6rem 1.2rem; align-items: center; }}
.node {{ border: 1px solid var(--line); border-radius: 9px; padding: .55rem .8rem; background: #fff; border-left: 4px solid var(--c); }}
.node b {{ font-family: var(--mono); font-size: 1.35rem; display: block; color: var(--ink); }}
.node span {{ font-size: .82rem; color: var(--muted); }}
.node.root {{ grid-row: span 4; }} .node.mid {{ grid-row: span 2; }}

/* Profile sheet */
.sheet {{ display: grid; grid-template-columns: auto 1fr; gap: .3rem 1rem; margin: .2rem 0 0; font-size: .9rem; }}
.sheet dt {{ color: var(--muted); }} .sheet dd {{ margin: 0; font-weight: 600; }}

.foot {{ margin: 2rem 0 .5rem; padding-top: 1rem; border-top: 1px solid var(--line); font-size: .82rem; color: var(--muted); line-height: 1.6; }}
.foot a {{ color: var(--brand-dark); }}
</style>
"""


def inject_css() -> None:
    st.html(CSS)


def icon(name: str) -> str:
    return f'<span class="msr">{name}</span>'


def pct(p: float, digits: int | None = None) -> str:
    """Risk as a percentage: one decimal under 20%, none above (unless digits is given)."""
    if digits is None:
        digits = 1 if p < 0.2 else 0
    if p < 0.001:
        return "&lt;0.1%"
    return f"{p * 100:.{digits}f}%"


def page(kicker: str, title: str, lead: str) -> None:
    st.html(f'<div class="head"><div><p class="kicker">{html.escape(kicker)}</p><h1 class="title">{html.escape(title)}</h1>'
            f'<p class="lead">{lead}</p></div><span class="ribbon">{icon("health_and_safety")} Screening aid, not a diagnosis'
            "</span></div>")


def panel_head(letter: str, title: str, sub: str = "") -> None:
    s = f'<p class="ph-s">{sub}</p>' if sub else ""
    st.html(f'<div class="ph"><span class="ph-l">{html.escape(letter)}</span><div><p class="ph-t">{html.escape(title)}</p>{s}</div></div>')


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


def verdict(p: float, tier: str, text: str) -> None:
    st.html(f'<div class="verdict" style="--c:{t.TIER[tier]}"><div><p class="risk-big">{pct(p)}</p>'
            f'<p class="risk-cap">model risk</p></div><div>{tier_badge(tier)}<p class="verdict-t">{text}</p></div></div>')


LO, HI = 0.002, 0.5  # ruler range (log scale)


def _x(p: float) -> float:
    p = min(max(p, LO), HI)
    return 100 * (math.log(p) - math.log(LO)) / (math.log(HI) - math.log(LO))


def ruler(p: float, threshold: float, high: float, marks: list[tuple[float, str]]) -> None:
    """Log-scale risk ruler: Routine / Check / Priority zones, the patient (dot, above) and reference marks (below)."""
    a, b = _x(threshold), _x(high)
    zones = (f'<div class="z" style="width:{a}%;background:{t.TIER_SOFT["Routine"]};border:1px solid {t.TIER["Routine"]}55"></div>'
             f'<div class="z" style="width:{b - a}%;background:{t.TIER_SOFT["Check"]};border:1px solid {t.TIER["Check"]}55"></div>'
             f'<div class="z" style="width:{100 - b}%;background:{t.TIER_SOFT["Priority"]};border:1px solid {t.TIER["Priority"]}55"></div>')
    ms = "".join(f'<div class="mk down" style="left:{_x(v)}%;--c:{t.FAINT}"><i></i>'
                 f'<span style="top:{30 + 17 * i}px">{html.escape(label)}</span></div>'
                 for i, (v, label) in enumerate(sorted(marks)))
    me = f'<div class="mk up me" style="left:{_x(p)}%"><i></i><span>This patient {pct(p)}</span></div>'
    st.html(f'<div class="ruler">{zones}{ms}{me}</div>'
            f'<div class="legend-z"><span style="--c:{t.TIER["Routine"]}">Routine: under {pct(threshold)}</span>'
            f'<span style="--c:{t.TIER["Check"]}">Check: {pct(threshold)} to {pct(high)}</span>'
            f'<span style="--c:{t.TIER["Priority"]}">Priority: {pct(high)} and above</span></div>'
            f'<p style="font-size:.74rem;color:{t.FAINT};margin:.4rem 0 0">Scale from 0.2% to 50%, spaced so that equal '
            "steps multiply the risk by the same amount.</p>")


def factor_groups(groups: list[tuple[str, list[tuple[str, str, float]]]]) -> None:
    """groups: (title, [(factor, value text, odds multiplier)]). Red raises the risk, teal lowers it, grey ~ no effect."""
    out = []
    for title, cards in groups:
        if not cards:
            continue
        cs = []
        for name, value, mult in cards:
            if mult >= 1.05:
                c, x = t.RAISES, f"× {mult:.2f} odds" if mult < 10 else f"× {mult:.0f} odds"
            elif mult <= 1 / 1.05:
                c, x = t.LOWERS, f"× {mult:.2f} odds"
            else:
                c, x = t.FAINT, "about no effect"
            cs.append(f'<div class="fcard" style="--c:{c}"><p class="fcard-n">{html.escape(name)}</p>'
                      f'<p class="fcard-v">{html.escape(value)}</p><p class="fcard-x">{x}</p></div>')
        out.append(f'<div class="fgroup"><p class="fgroup-t">{html.escape(title)}</p><div class="fcards">{"".join(cs)}</div></div>')
    st.html("".join(out))


def what_if(rows: list[dict]) -> None:
    st.html("".join(
        f'<div class="wi"><p class="wi-l">{html.escape(r["label"])}</p>'
        f'<p class="wi-v">{pct(r["before"])} → <b>{pct(r["after"])}</b></p></div>' for r in rows))


def note(*paras: str) -> None:
    st.html('<div class="note">' + "".join(f"<p>{p}</p>" for p in paras) + "</div>")


def caution(text: str) -> None:
    st.html(f'<div class="caution">{icon("warning")}<div>{text}</div></div>')


def fast() -> None:
    st.html('<div class="fast">'
            "<div><b>F</b><span><b style='font-size:.85rem;display:inline;font-family:inherit'>Face</b> drooping on one side</span></div>"
            "<div><b>A</b><span><b style='font-size:.85rem;display:inline;font-family:inherit'>Arm</b> weakness or numbness</span></div>"
            "<div><b>S</b><span><b style='font-size:.85rem;display:inline;font-family:inherit'>Speech</b> slurred or strange</span></div>"
            "<div><b>T</b><span><b style='font-size:.85rem;display:inline;font-family:inherit'>Time</b> to call emergency services</span></div>"
            "</div>")


def sheet(rows: list[tuple[str, str]]) -> None:
    st.html('<dl class="sheet">' + "".join(f"<dt>{html.escape(k)}</dt><dd>{html.escape(v)}</dd>" for k, v in rows) + "</dl>")


def lane_head(tier: str, count: int, strokes: int) -> None:
    st.html(f'<div class="lane-h" style="--c:{t.TIER[tier]};--s:{t.TIER_SOFT[tier]}"><b>{icon(t.TIER_ICON[tier])} {tier}</b>'
            f"<span>{count:,}</span></div>"
            f'<p class="lane-n">{html.escape(t.TIER_TEXT[tier])} Held-out outcome: {strokes} had a stroke.</p>')


def patient_card(title: str, p: float, tier: str, summary: str) -> str:
    return (f'<div class="pcard" style="--c:{t.TIER[tier]}"><p class="pcard-t">{html.escape(title)}<span>{pct(p)}</span></p>'
            f'<p class="pcard-s">{html.escape(summary)}</p></div>')


def freq_tree(n: int, strokes: int, found: int, alarms: int) -> None:
    """Natural frequencies: n patients -> stroke / no stroke -> found / missed, false alarm / cleared."""
    missed, others = strokes - found, n - strokes
    cleared = others - alarms
    node = lambda v, label, c, cls="": (f'<div class="node {cls}" style="--c:{c}"><b>{v:,}</b><span>{label}</span></div>')  # noqa: E731
    st.html('<div class="tree">'
            + node(n, "patients screened", t.BRAND, "root")
            + node(strokes, "had a stroke", t.TIER["Priority"], "mid")
            + node(found, "<b style='font-size:.82rem;display:inline;font-family:inherit;color:#0f9b8e'>found</b>: flagged for a check", t.LOWERS)
            + node(missed, "<b style='font-size:.82rem;display:inline;font-family:inherit;color:#c53030'>missed</b>: below the line", t.RAISES)
            + node(others, "no stroke", t.FAINT, "mid")
            + node(alarms, "false alarms: checked, no stroke", t.TIER["Check"])
            + node(cleared, "correctly left to routine care", t.FAINT)
            + "</div>")


def footer() -> None:
    st.html(f'<div class="foot">Model and app by <b>Ahmad Hassan</b>, AI Engineer · <a href="{NOTEBOOK_URL}" target="_blank">'
            f'Notebook</a> · <a href="{CODE_URL}" target="_blank">App code</a> · <a href="{LEARN_URL}" target="_blank">'
            f"Learn with Ahmad</a><br>{DATA_CREDIT}</div>")
