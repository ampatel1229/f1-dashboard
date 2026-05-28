"""
Plotly chart functions for the F1 Driver Performance Comparison Dashboard.
All functions expect lap times in seconds.
"""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Compound to marker symbol mapping for lap_time_chart
_COMPOUND_SYMBOLS = {
    "SOFT": "circle",
    "MEDIUM": "square",
    "HARD": "diamond",
    "INTERMEDIATE": "triangle-up",
    "WET": "x",
}


def _compound_symbol(compound):
    if pd.isna(compound):
        return "circle"
    c = str(compound).upper()
    return _COMPOUND_SYMBOLS.get(c, "circle")


def _seconds_to_m_s_mmm(seconds):
    """Format seconds as minutes:seconds:milliseconds (e.g. 1:17.244)."""
    if seconds is None or (isinstance(seconds, float) and np.isnan(seconds)):
        return "—"
    try:
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m}:{s:06.3f}"
    except Exception:
        return "—"


def lap_time_chart(laps1: pd.DataFrame, laps2: pd.DataFrame, d1: str, d2: str, color1: str = None, color2: str = None):
    """
    Line chart of LapTime vs LapNumber for both drivers.
    Hover shows times in minutes:seconds:milliseconds. Colors can follow team colors.
    """
    c1 = color1 or "#1f77b4"
    c2 = color2 or "#ff7f0e"
    fig = go.Figure()
    if laps1 is not None and not laps1.empty and "LapNumber" in laps1.columns and "LapTime" in laps1.columns:
        compounds = laps1["Compound"].map(_compound_symbol).tolist() if "Compound" in laps1.columns else ["circle"] * len(laps1)
        hover_times = [_seconds_to_m_s_mmm(t) for t in laps1["LapTime"]]
        fig.add_trace(
            go.Scatter(
                x=laps1["LapNumber"],
                y=laps1["LapTime"],
                mode="lines+markers",
                name=d1,
                line=dict(color=c1, width=2),
                marker=dict(symbol=compounds[0] if len(set(compounds)) == 1 else "circle", size=8),
                customdata=hover_times,
                hovertemplate=f"<b>Lap %{{x}}</b><br>{d1}: %{{customdata}}<extra></extra>",
            )
        )
    if laps2 is not None and not laps2.empty and "LapNumber" in laps2.columns and "LapTime" in laps2.columns:
        compounds2 = laps2["Compound"].map(_compound_symbol).tolist() if "Compound" in laps2.columns else ["square"] * len(laps2)
        hover_times2 = [_seconds_to_m_s_mmm(t) for t in laps2["LapTime"]]
        fig.add_trace(
            go.Scatter(
                x=laps2["LapNumber"],
                y=laps2["LapTime"],
                mode="lines+markers",
                name=d2,
                line=dict(color=c2, width=2),
                marker=dict(symbol=compounds2[0] if len(set(compounds2)) == 1 else "square", size=8),
                customdata=hover_times2,
                hovertemplate=f"<b>Lap %{{x}}</b><br>{d2}: %{{customdata}}<extra></extra>",
            )
        )
    fig.update_layout(
        title="Lap Time Progression",
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (min:sec.ms)",
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(autorange="reversed", title="Lap Time (min:sec.ms)")
    return fig


def sector_comparison_chart(laps1: pd.DataFrame, laps2: pd.DataFrame, d1: str, d2: str, color1: str = None, color2: str = None):
    """
    Grouped bar chart comparing average S1, S2, S3 for each driver.
    Expects Sector1Time, Sector2Time, Sector3Time in seconds.
    """
    c1 = color1 or "#1f77b4"
    c2 = color2 or "#ff7f0e"
    sectors = ["Sector 1", "Sector 2", "Sector 3"]
    keys = ["Sector1Time", "Sector2Time", "Sector3Time"]
    s1 = [np.nan, np.nan, np.nan]
    s2 = [np.nan, np.nan, np.nan]
    if laps1 is not None and not laps1.empty:
        for i, k in enumerate(keys):
            if k in laps1.columns:
                v = laps1[k].dropna()
                if not v.empty:
                    s1[i] = v.mean()
    if laps2 is not None and not laps2.empty:
        for i, k in enumerate(keys):
            if k in laps2.columns:
                v = laps2[k].dropna()
                if not v.empty:
                    s2[i] = v.mean()
    fig = go.Figure(
        data=[
            go.Bar(name=d1, x=sectors, y=s1, marker_color=c1),
            go.Bar(name=d2, x=sectors, y=s2, marker_color=c2),
        ]
    )
    fig.update_layout(
        title="Sector Time Comparison (average)",
        xaxis_title="Sector",
        yaxis_title="Time (s)",
        barmode="group",
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(autorange="reversed")
    return fig


# Compound colors for tire stint
COMPOUND_COLORS = {"SOFT": "#e74c3c", "MEDIUM": "#f39c12", "HARD": "#3498db", "INTERMEDIATE": "#2ecc71", "WET": "#9b59b6"}


def tire_stint_chart(stints1: list, stints2: list, d1: str, d2: str):
    """
    Gantt-style chart: X = lap number, color = compound, one row per driver.
    stints1/stints2 are lists of dicts: compound, start_lap, end_lap, laps, tyre_age_start, tyre_age_end.
    """
    fig = go.Figure()
    y_d1, y_d2 = 0, 1
    seen_compounds = set()

    def add_stints(stints, driver_label, y_val):
        if not stints:
            return
        for s in stints:
            comp = s.get("compound", "?")
            start = s["start_lap"]
            end = s["end_lap"]
            laps = s.get("laps", end - start + 1)
            age_start = s.get("tyre_age_start")
            age_end = s.get("tyre_age_end")
            age_str = ""
            if age_start is not None or age_end is not None:
                parts = []
                if age_start is not None:
                    parts.append(f"Age start: {int(age_start)} laps")
                if age_end is not None:
                    parts.append(f"Age end: {int(age_end)} laps")
                age_str = "<br>".join(parts)
            color = COMPOUND_COLORS.get(str(comp).upper(), "#95a5a6")
            show_leg = comp not in seen_compounds
            if show_leg:
                seen_compounds.add(comp)
            fig.add_trace(
                go.Bar(
                    x=[end - start + 1],
                    y=[y_val],
                    base=[start],
                    orientation="h",
                    marker=dict(color=color),
                    name=comp,
                    showlegend=show_leg,
                    width=0.35,
                    hovertemplate=(
                        f"<b>{driver_label}</b><br>"
                        f"Compound: {comp}<br>"
                        f"Laps: {laps} (Lap {start}–{end})<br>"
                        f"{age_str}"
                        "<extra></extra>"
                    ),
                )
            )

    add_stints(stints1, d1, y_d1)
    add_stints(stints2, d2, y_d2)
    fig.update_layout(
        title="Tire Stint Strategy",
        xaxis_title="Lap Number",
        yaxis_title="Driver",
        barmode="overlay",
        template="plotly_dark",
        height=220,
        margin=dict(l=80),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.update_yaxes(
        tickvals=[y_d1, y_d2],
        ticktext=[d1, d2],
        categoryorder="array",
        categoryarray=[d1, d2],
    )
    return fig


def consistency_boxplot(laps1: pd.DataFrame, laps2: pd.DataFrame, d1: str, d2: str, color1: str = None, color2: str = None):
    """Box plot of lap time distribution; y-axis and hover show times in minutes:seconds:milliseconds."""
    c1 = color1 or "#1f77b4"
    c2 = color2 or "#ff7f0e"
    fig = go.Figure()

    def add_box(laps, name, color):
        if laps is None or laps.empty or "LapTime" not in laps.columns:
            return
        y = laps["LapTime"].dropna()
        if y.empty:
            return
        q1, med, q3 = y.quantile(0.25), y.quantile(0.5), y.quantile(0.75)
        iqr = q3 - q1
        lf = max(y.min(), q1 - 1.5 * iqr)
        uf = min(y.max(), q3 + 1.5 * iqr)
        row = [
            _seconds_to_m_s_mmm(y.min()),
            _seconds_to_m_s_mmm(lf),
            _seconds_to_m_s_mmm(q1),
            _seconds_to_m_s_mmm(med),
            _seconds_to_m_s_mmm(q3),
            _seconds_to_m_s_mmm(uf),
            _seconds_to_m_s_mmm(y.max()),
        ]
        # One row per y so hover works; same summary for each
        customdata = np.tile(row, (len(y), 1))
        fig.add_trace(
            go.Box(
                y=y,
                name=name,
                marker_color=color,
                customdata=customdata,
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "min: %{customdata[0]}<br>"
                    "lower fence: %{customdata[1]}<br>"
                    "Q1: %{customdata[2]}<br>"
                    "median: %{customdata[3]}<br>"
                    "Q3: %{customdata[4]}<br>"
                    "upper fence: %{customdata[5]}<br>"
                    "max: %{customdata[6]}"
                    "<extra></extra>"
                ),
            )
        )

    add_box(laps1, d1, c1)
    add_box(laps2, d2, c2)
    fig.update_layout(
        title="Lap Time Consistency",
        yaxis_title="Lap Time (min:sec.ms)",
        template="plotly_dark",
        showlegend=True,
    )
    fig.update_yaxes(autorange="reversed")

    # Y-axis tick labels in minutes:seconds:milliseconds
    y_min = float("inf")
    y_max = float("-inf")
    for t in fig.data:
        if hasattr(t, "y") and t.y is not None and len(t.y) > 0:
            y_min = min(y_min, min(t.y))
            y_max = max(y_max, max(t.y))
    if y_max > y_min:
        # About 6–8 ticks over the range
        n_ticks = 8
        tickvals = np.linspace(y_min, y_max, n_ticks)
        ticktext = [_seconds_to_m_s_mmm(float(t)) for t in tickvals]
        fig.update_yaxes(tickvals=tickvals, ticktext=ticktext)

    return fig


def qualifying_q1_q2_q3_chart(q_times: pd.DataFrame, d1: str, d2: str, color1: str = None, color2: str = None, format_seconds=None):
    """
    Grouped bar chart of Q1, Q2, Q3 best times for both drivers.
    q_times: DataFrame with Driver, Q1, Q2, Q3 (seconds). format_seconds(sec) -> display string.
    """
    if q_times is None or q_times.empty or "Driver" not in q_times.columns:
        return None
    c1 = color1 or "#1f77b4"
    c2 = color2 or "#ff7f0e"
    fmt = format_seconds or (lambda s: f"{s:.2f}s" if s == s else "—")
    row1 = q_times[q_times["Driver"] == d1]
    row2 = q_times[q_times["Driver"] == d2]
    stages = ["Q1", "Q2", "Q3"]
    y1 = [row1[s].iloc[0] if not row1.empty and s in row1.columns else np.nan for s in stages]
    y2 = [row2[s].iloc[0] if not row2.empty and s in row2.columns else np.nan for s in stages]
    fig = go.Figure(
        data=[
            go.Bar(name=d1, x=stages, y=y1, marker_color=c1, text=[fmt(v) for v in y1], textposition="outside"),
            go.Bar(name=d2, x=stages, y=y2, marker_color=c2, text=[fmt(v) for v in y2], textposition="outside"),
        ]
    )
    fig.update_layout(
        title="Qualifying by stage (Q1, Q2, Q3)",
        xaxis_title="Stage",
        yaxis_title="Time",
        barmode="group",
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.update_yaxes(autorange="reversed")
    return fig


def qualifying_delta_chart(laps1: pd.DataFrame, laps2: pd.DataFrame, d1: str, d2: str, color1: str = None, color2: str = None):
    """
    Bar chart of lap time delta per sector vs the faster driver.
    Faster driver is the one with lower total (or sum of sectors); deltas are (slower - faster) per sector.
    """
    keys = ["Sector1Time", "Sector2Time", "Sector3Time"]
    labels = ["Sector 1", "Sector 2", "Sector 3"]
    avg1 = [np.nan, np.nan, np.nan]
    avg2 = [np.nan, np.nan, np.nan]
    if laps1 is not None and not laps1.empty:
        for i, k in enumerate(keys):
            if k in laps1.columns:
                v = laps1[k].dropna()
                if not v.empty:
                    avg1[i] = v.mean()
    if laps2 is not None and not laps2.empty:
        for i, k in enumerate(keys):
            if k in laps2.columns:
                v = laps2[k].dropna()
                if not v.empty:
                    avg2[i] = v.mean()
    sum1 = np.nansum(avg1)
    sum2 = np.nansum(avg2)
    if sum1 <= sum2:
        faster_name, slower_name = d1, d2
        faster_avg, slower_avg = avg1, avg2
    else:
        faster_name, slower_name = d2, d1
        faster_avg, slower_avg = avg2, avg1
    deltas = [np.nan if (np.isnan(s) or np.isnan(f)) else s - f for s, f in zip(slower_avg, faster_avg)]
    colors = ["#e74c3c" if d > 0 else "#2ecc71" for d in deltas]
    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=deltas,
                marker_color=colors,
                text=[f"+{x:.3f}s" if x > 0 else f"{x:.3f}s" for x in deltas],
                textposition="outside",
            )
        ]
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        title=f"Qualifying Delta vs {faster_name} (slower: {slower_name})",
        xaxis_title="Sector",
        yaxis_title="Delta (s)",
        template="plotly_dark",
        showlegend=False,
    )
    return fig
