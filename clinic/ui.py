"""StrokeScope components: a hospital laboratory report. Every page opens with a maroon letterhead; every block is a
report section on a white sheet with a heavy rule under its heading; results are monospaced rows with H/L flags,
reference intervals and the model's effect; comments, critical-value alerts and a worklist complete the report."""

from __future__ import annotations

import html
import math
from contextlib import contextmanager

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
.sec-s {{ font-size: .84rem; color: var(--muted); margin: .25rem 0 .7rem; }}

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
.res-v {{ font-family: var(--mono); font-size: 2.6rem; font-weight: 700; color: var(--c); line-height: 1; margin: .2rem 0 0; }}
.res-v small {{ font-size: .9rem; font-weight: 600; color: var(--ink); margin-left: .5rem; }}
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
.legend-z span::before {{ content: ""; display: inline-block; width: .65rem; height: .65rem; background: var(--c); margin-right: .35rem; vertical-align: -1px; }}

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

/* Specimen / patient block */
.sheet {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); border-top: 1.5px solid var(--rule); margin: .2rem 0 0; }}
.sheet div {{ display: grid; grid-template-columns: 9rem 1fr; gap: .5rem; padding: .32rem .2rem; border-bottom: 1px solid var(--line); font-size: .86rem; }}
.sheet dt {{ font-family: var(--mono); font-size: .68rem; letter-spacing: .05em; text-transform: uppercase; color: var(--muted); padding-top: .15rem; }}
.sheet dd {{ margin: 0; font-weight: 600; }}

/* Worklist (triage lanes) */
.lane-h {{ display: flex; justify-content: space-between; align-items: center; padding: .4rem .6rem; background: var(--c); color: #fff; margin: 0; }}
.lane-h b {{ font-family: var(--mono); font-size: .8rem; letter-spacing: .1em; text-transform: uppercase; display: inline-flex; gap: .3rem; align-items: center; }}
.lane-h > span {{ font-family: var(--mono); font-size: 1.15rem; font-weight: 700; }}
.lane-n {{ font-size: .78rem; color: var(--muted); margin: .4rem 0 .5rem; line-height: 1.45; }}
.pcard {{ display: grid; grid-template-columns: 1fr auto; gap: .1rem .6rem; padding: .4rem .2rem; border-bottom: 1px solid var(--line); }}
.pcard-t {{ font-family: var(--mono); font-weight: 600; font-size: .82rem; margin: 0; }}
.pcard-r {{ font-family: var(--mono); font-weight: 700; color: var(--c); font-size: .9rem; margin: 0; text-align: right; }}
.pcard-s {{ grid-column: 1 / -1; font-size: .76rem; color: var(--muted); margin: 0; }}

/* Natural frequency tree */
.tree {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: .6rem 1.2rem; align-items: center; }}
.node {{ border: 1px solid var(--line); border-top: 3px solid var(--c); padding: .5rem .75rem; background: #fff; }}
.node b {{ font-family: var(--mono); font-size: 1.35rem; display: block; color: var(--ink); }}
.node span {{ font-size: .8rem; color: var(--muted); }}
.node.root {{ grid-row: span 4; }} .node.mid {{ grid-row: span 2; }}

/* Factor cards (kept for other pages) */
.fgroup-t {{ font-family: var(--mono); font-size: .66rem; letter-spacing: .1em; text-transform: uppercase; color: var(--brand); font-weight: 700; margin: .6rem 0 .35rem; }}
.fcards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: .5rem; }}
.fcard {{ border: 1px solid var(--line); border-top: 3px solid var(--c); padding: .45rem .65rem; }}
.fcard-n {{ font-size: .78rem; color: var(--muted); margin: 0; }} .fcard-v {{ font-weight: 600; margin: .1rem 0; }}
.fcard-x {{ font-family: var(--mono); font-size: .82rem; color: var(--c); margin: 0; font-weight: 600; }}

.foot {{ margin: 2rem 0 .5rem; padding: .9rem 0 0; border-top: 3px double var(--rule); font-size: .8rem; color: var(--muted); line-height: 1.65; }}
.foot a {{ color: var(--brand); font-weight: 600; }}
.sig {{ font-family: var(--mono); font-size: .72rem; color: var(--muted); letter-spacing: .04em; margin: 1rem 0 0; padding-top: .5rem; border-top: 1px solid var(--line); }}
</style>
"""


def inject_css() -> None:
    st.html(CSS)


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
    ms = "".join(f'<div class="mk down" style="left:{_x(v)}%;--c:{t.FAINT}"><i></i>'
                 f'<span style="top:{28 + 16 * i}px">{html.escape(label)}</span></div>'
                 for i, (v, label) in enumerate(sorted(marks)))
    me = f'<div class="mk up me" style="left:{_x(p)}%"><i></i><span>This patient {pct(p)}</span></div>'
    st.html(f'<div class="ruler">{zones}{ms}{me}</div>'
            f'<div class="legend-z"><span style="--c:{t.TIER["Routine"]}">Routine &lt; {pct(threshold)}</span>'
            f'<span style="--c:{t.TIER["Check"]}">Check {pct(threshold)} to {pct(high)}</span>'
            f'<span style="--c:{t.TIER["Priority"]}">Priority &ge; {pct(high)}</span>'
            '<span style="--c:transparent">log scale, 0.2% to 50%</span></div>')


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


def lane_head(tier: str, count: int, strokes: int | None) -> None:
    st.html(f'<div class="lane-h" style="--c:{t.TIER[tier]}"><b>{icon(t.TIER_ICON[tier])} {tier}</b><span>{count:,}</span></div>'
            f'<p class="lane-n">{html.escape(t.TIER_TEXT[tier])}'
            + (f" Held-out outcome: {strokes} had a stroke." if strokes is not None else "") + "</p>")


def patient_card(title: str, p: float, tier: str, summary: str) -> str:
    return (f'<div class="pcard" style="--c:{t.TIER[tier]}"><p class="pcard-t">{html.escape(title)}</p><p class="pcard-r">{pct(p)}</p>'
            f'<p class="pcard-s">{html.escape(summary)}</p></div>')


def freq_tree(n: int, strokes: int, found: int, alarms: int) -> None:
    """Natural frequencies: n patients -> stroke / no stroke -> found / missed, false alarm / cleared."""
    missed, others = strokes - found, n - strokes
    cleared = others - alarms
    node = lambda v, label, c, cls="": (f'<div class="node {cls}" style="--c:{c}"><b>{v:,}</b><span>{label}</span></div>')  # noqa: E731
    st.html('<div class="tree">'
            + node(n, "patients screened", t.BRAND, "root")
            + node(strokes, "had a stroke", t.TIER["Priority"], "mid")
            + node(found, f"<b style='font-size:.8rem;display:inline;font-family:inherit;color:{t.LOWERS}'>found</b>: flagged for a check", t.LOWERS)
            + node(missed, f"<b style='font-size:.8rem;display:inline;font-family:inherit;color:{t.RAISES}'>missed</b>: below the line", t.RAISES)
            + node(others, "no stroke", t.FAINT, "mid")
            + node(alarms, "false alarms: checked, no stroke", t.TIER["Check"])
            + node(cleared, "correctly left to routine care", t.FAINT)
            + "</div>")


def signature(text: str) -> None:
    st.html(f'<p class="sig">{text}</p>')


def footer() -> None:
    st.html(f'<div class="foot">Model and app by <b>Ahmad Hassan</b>, AI Engineer · <a href="{NOTEBOOK_URL}" target="_blank">'
            f'Notebook</a> · <a href="{CODE_URL}" target="_blank">App code</a> · <a href="{LEARN_URL}" target="_blank">'
            f"Learn with Ahmad</a><br>{DATA_CREDIT}</div>")
