"""Plotly charts on white report sheets: maroon for the model and the patient, red for strokes / raises the risk, teal
for found / lowers the risk. Thin marks, recessive grids, system fonts (measured correctly at first draw), hover on every mark."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from clinic import theme as t

SANS = "Segoe UI, Helvetica Neue, Arial, sans-serif"  # system fonts: measured correctly at first draw
MONO = "Consolas, Menlo, monospace"

CONFIG = {"displayModeBar": False, "scrollZoom": False}


def show(fig: go.Figure, key: str) -> None:
    st.plotly_chart(fig, theme=None, config=CONFIG, key=key)


def style(fig: go.Figure, height: int = 340, legend: bool = False) -> go.Figure:
    fig.update_layout(
        height=height, paper_bgcolor=t.PANEL, plot_bgcolor=t.PANEL, showlegend=legend,
        font=dict(family=SANS, size=13, color=t.MUTED), margin=dict(l=10, r=20, t=24, b=10),
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, font=dict(color=t.MUTED)),
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=t.LINE, font=dict(family=MONO, color=t.INK, size=12)),
    )
    axis = dict(automargin=True, gridcolor="#eceff4", zeroline=False, linecolor=t.LINE,
                tickfont=dict(family=MONO, color=t.FAINT, size=11), title_font=dict(color=t.MUTED, size=12))
    fig.update_xaxes(**axis, showgrid=False)
    fig.update_yaxes(**axis)
    return fig


def tradeoff(curve: pd.DataFrame, points: list[dict], current: float) -> go.Figure:
    """Every possible threshold as one curve: share of patients flagged (x) against share of stroke patients missed (y).
    points: [{label, flagged, missed, colour}] for named settings; current: the slider's threshold."""
    fig = go.Figure(go.Scatter(
        x=curve["flagged"], y=curve["missed"], mode="lines", line=dict(color=t.BRAND, width=2),
        customdata=curve[["threshold"]], name="Every threshold",
        hovertemplate="Line at %{customdata[0]:.1%}<br>Flagged %{x:.0%}<br>Strokes missed %{y:.0%}<extra></extra>"))
    for pnt in points:
        fig.add_trace(go.Scatter(
            x=[pnt["flagged"]], y=[pnt["missed"]], mode="markers+text", text=[pnt["label"]],
            textposition=pnt.get("pos", "top right"), textfont=dict(color=t.INK, size=12),
            marker=dict(size=11, color=pnt["colour"], symbol=pnt.get("symbol", "circle"), line=dict(color="#fff", width=2)),
            hovertemplate=f"{pnt['label']}<br>Flagged %{{x:.0%}}<br>Strokes missed %{{y:.0%}}<extra></extra>", name=pnt["label"]))
    row = curve.iloc[(curve["threshold"] - current).abs().argmin()]
    fig.add_trace(go.Scatter(x=[row["flagged"]], y=[row["missed"]], mode="markers", name="Your line",
                             marker=dict(size=16, color="rgba(0,0,0,0)", line=dict(color=t.BRAND, width=3)),
                             hovertemplate="Your line<br>Flagged %{x:.0%}<br>Strokes missed %{y:.0%}<extra></extra>"))
    fig.update_xaxes(title="Patients flagged for a check (share of all patients)", tickformat=".0%", range=[0, 1.02])
    fig.update_yaxes(title="Stroke patients missed", tickformat=".0%", range=[-0.03, 1.03])
    return style(fig, 420)


def score_strip(df: pd.DataFrame, threshold: float, high: float) -> go.Figure:
    """Each held-out patient as a dot on a log risk axis, stroke patients on their own row."""
    fig = go.Figure()
    rng = np.random.default_rng(3)
    for label, val, colour, size in [("No stroke", 0, "#9aa3b5", 5), ("Stroke", 1, t.RAISES, 8)]:
        d = df[df["stroke"] == val]
        fig.add_trace(go.Scatter(
            x=d["proba"], y=val + rng.uniform(-0.28, 0.28, len(d)), mode="markers", name=label,
            marker=dict(size=size, color=colour, opacity=0.55 if val == 0 else 0.9, line=dict(color="#fff", width=0.5)),
            customdata=d[["age"]], hovertemplate=f"{label}<br>Risk %{{x:.1%}}<br>Age %{{customdata[0]:.0f}}<extra></extra>"))
    for x, label, c in [(threshold, "Screening line", t.TIER["Check"]), (high, "High-risk line", t.TIER["Priority"])]:
        fig.add_vline(x=x, line=dict(color=c, width=2, dash="dash"))
        fig.add_annotation(x=np.log10(x), y=1.55, text=label, showarrow=False, font=dict(color=c, size=12), xanchor="left", xshift=4)
    ticks = [0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4]
    fig.update_xaxes(type="log", title="Model risk (log scale)", tickvals=ticks, ticktext=[f"{v:.1%}".replace(".0%", "%") for v in ticks],
                     range=[np.log10(0.0015), np.log10(0.45)], showgrid=True)
    fig.update_yaxes(tickvals=[0, 1], ticktext=["No stroke", "Stroke"], range=[-0.5, 1.75], showgrid=False)
    return style(fig, 300)


def age_lines(table: pd.DataFrame, by_label: dict[int, str]) -> go.Figure:
    """Stroke rate by age band, one line per group (table: index = band, columns = group values)."""
    fig = go.Figure()
    colours = ["#5b6b8c", t.RAISES]  # slate for "without the condition", red for "with it"
    for (val, label), c in zip(by_label.items(), colours):
        if val not in table.columns:
            continue
        s = table[val]
        fig.add_trace(go.Scatter(x=s.index.astype(str), y=s.values, mode="lines+markers", name=label,
                                 line=dict(color=c, width=2), marker=dict(size=9, color=c, line=dict(color="#fff", width=2)),
                                 hovertemplate=f"{label}<br>%{{x}}: %{{y:.1%}} had a stroke<extra></extra>"))
    fig.update_yaxes(title="Had a stroke", tickformat=".0%", rangemode="tozero")
    fig.update_xaxes(title="Age")
    return style(fig, 340, legend=True)


def rate_bars(labels: list[str], rates: list[float], counts: list[int], overall: float, highlight: list[bool] | None = None) -> go.Figure:
    """Share with a stroke per group. Values sit in their own column at the right, clear of the bars and the average line."""
    highlight = highlight or [False] * len(labels)
    top = max(max(rates), overall) * 1.12
    fig = go.Figure(go.Bar(
        x=rates, y=labels, orientation="h", marker=dict(color=[t.RAISES if h else "#9aa3b5" for h in highlight]),
        customdata=np.array(counts)[:, None], hovertemplate="%{y}<br>%{x:.1%} of %{customdata[0]:,} patients<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=[top * 1.2] * len(labels), y=labels, mode="text", text=[f"{r:.1%}" for r in rates], textposition="middle left",
        textfont=dict(family=MONO, color=[t.RAISES if h else t.INK for h in highlight], size=12), hoverinfo="skip"))
    fig.add_vline(x=overall, line=dict(color=t.BRAND, width=1.5, dash="dot"), layer="below")
    fig.add_annotation(x=overall, y=1.0, yref="paper", text=f"All patients {overall:.1%}", showarrow=False,
                       font=dict(color=t.BRAND, size=11), xanchor="left", xshift=4, yanchor="bottom")
    fig.update_xaxes(tickformat=".0%", range=[0, top * 1.2], title="Had a stroke",
                     tickvals=[v for v in np.linspace(0, top, 5)], ticktext=[f"{v:.0%}" if top > .1 else f"{v:.1%}" for v in np.linspace(0, top, 5)])
    fig.update_yaxes(autorange="reversed")
    return style(fig, 60 + 46 * len(labels))


def forest(df: pd.DataFrame) -> go.Figure:
    """Odds ratios with 95% bootstrap intervals (df: label, odds_ratio, lo, hi), log axis, 1 = no effect."""
    df = df.sort_values("odds_ratio")
    colour = [t.RAISES if lo > 1 else t.LOWERS if hi < 1 else "#9aa3b5" for lo, hi in zip(df["lo"], df["hi"])]
    fig = go.Figure(go.Scatter(
        x=df["odds_ratio"], y=df["label"], mode="markers",
        marker=dict(size=10, color=colour, symbol="square", line=dict(color="#fff", width=1)),
        error_x=dict(type="data", symmetric=False, array=df["hi"] - df["odds_ratio"], arrayminus=df["odds_ratio"] - df["lo"],
                     color="#9aa3b5", thickness=2, width=0),
        customdata=df[["lo", "hi"]], hovertemplate="%{y}<br>Odds × %{x:.2f} (95%: %{customdata[0]:.2f} to %{customdata[1]:.2f})<extra></extra>"))
    fig.add_vline(x=1, line=dict(color=t.INK, width=1))
    fig.update_xaxes(type="log", title="Odds ratio (log scale; right of 1 raises the risk)", showgrid=True,
                     tickvals=[0.5, 0.75, 1, 1.5, 2, 3, 4], ticktext=["0.5", "0.75", "1", "1.5", "2", "3", "4"])
    return style(fig, 70 + 30 * len(df))


def calibration(predicted: list[float], observed: list[float], n: list[int]) -> go.Figure:
    top = max(max(predicted), max(observed)) * 1.15
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, top], y=[0, top], mode="lines", line=dict(color="#b8bfcc", dash="dot", width=1.5),
                             hoverinfo="skip", name="Perfect"))
    fig.add_trace(go.Scatter(x=predicted, y=observed, mode="lines+markers", line=dict(color=t.BRAND, width=2),
                             marker=dict(size=[8 + 10 * (v / max(n)) for v in n], color=t.BRAND, line=dict(color="#fff", width=2)),
                             customdata=np.array(n)[:, None], name="Model",
                             hovertemplate="Predicted %{x:.1%}<br>Actual %{y:.1%}<br>%{customdata[0]:,} patients<extra></extra>"))
    fig.update_xaxes(title="Average predicted risk", tickformat=".0%", range=[0, top])
    fig.update_yaxes(title="Share who had a stroke", tickformat=".0%", range=[0, top])
    return style(fig, 330)


def roc(fpr: np.ndarray, tpr: np.ndarray, auc: float, point: tuple[float, float]) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color="#b8bfcc", dash="dot", width=1.5), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=fpr, y=tpr, mode="lines", line=dict(color=t.BRAND, width=2),
                             hovertemplate="False alarm rate %{x:.0%}<br>Strokes found %{y:.0%}<extra></extra>"))
    fig.add_trace(go.Scatter(x=[point[0]], y=[point[1]], mode="markers+text", text=["Screening line"], textposition="bottom right",
                             marker=dict(size=11, color=t.TIER["Check"], line=dict(color="#fff", width=2)), hoverinfo="skip"))
    fig.add_annotation(x=0.98, y=0.06, text=f"AUC-ROC {auc:.3f}", showarrow=False, xanchor="right", font=dict(family=MONO, color=t.INK))
    fig.update_xaxes(title="Share of non-stroke patients flagged", tickformat=".0%", range=[0, 1])
    fig.update_yaxes(title="Share of stroke patients found", tickformat=".0%", range=[0, 1.02])
    return style(fig, 330)


def tier_mix(df: pd.DataFrame) -> go.Figure:
    """Patients in each tier, split by held-out outcome (stacked horizontal bars, 2px gaps)."""
    order = ["Priority", "Check", "Routine"]
    g = df.groupby(["tier", "stroke"]).size().unstack(fill_value=0).reindex(order, fill_value=0)
    fig = go.Figure()
    for val, label, c in [(1, "Had a stroke", t.RAISES), (0, "No stroke", "#c5cbd8")]:
        fig.add_trace(go.Bar(y=order, x=g.get(val, 0), orientation="h", name=label, marker=dict(color=c, line=dict(color="#fff", width=2)),
                             hovertemplate=f"%{{y}}: %{{x:,}} {label.lower()}<extra></extra>"))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="Patients")
    fig.update_yaxes(autorange="reversed")
    return style(fig, 220, legend=True)
