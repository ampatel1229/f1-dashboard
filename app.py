"""
F1 Driver Performance Comparison Dashboard — Main Streamlit app.
"""
import pandas as pd
import streamlit as st
from modules.loader import (
    get_event_schedule,
    get_session,
    get_driver_laps,
    get_driver_laps_all,
    get_all_drivers,
    get_driver_team_color,
    get_qualifying_stage_times,
    get_stint_summary,
)
from modules.metrics import (
    best_lap_time,
    average_lap_time,
    median_lap_time,
    lap_consistency,
    position_change,
    sector_averages,
)
from modules import charts

# Page config: wide mode, dark-friendly
st.set_page_config(page_title="F1 Driver Comparison", layout="wide", initial_sidebar_state="expanded")

# Dark-friendly custom CSS — ensure metric times are fully visible (no truncation)
st.markdown(
    """
    <style>
    .stApp { background-color: #0e1117; }
    .main .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    div[data-testid="stMetricValue"] {
        color: #fafafa;
        overflow: visible !important;
        text-overflow: clip !important;
        white-space: nowrap !important;
        min-width: 7rem;
        font-variant-numeric: tabular-nums;
    }
    [data-testid="stMetric"] { min-width: 7rem; overflow: visible; }
    div[data-testid="stVerticalBlock"] > div[data-testid="stMetric"] { flex: 1 1 auto; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Session state for loaded data
if "loaded_year" not in st.session_state:
    st.session_state.loaded_year = None
if "loaded_gp" not in st.session_state:
    st.session_state.loaded_gp = None
if "loaded_session_type" not in st.session_state:
    st.session_state.loaded_session_type = None
if "session_obj" not in st.session_state:
    st.session_state.session_obj = None
if "schedule" not in st.session_state:
    st.session_state.schedule = None
if "event_names" not in st.session_state:
    st.session_state.event_names = []
if "drivers" not in st.session_state:
    st.session_state.drivers = []


def _format_lap_time(seconds):
    """Format seconds as minutes:seconds:milliseconds (e.g. 1:17.244). Returns N/A if invalid."""
    if seconds is None or (isinstance(seconds, float) and (seconds != seconds)):  # NaN
        return "N/A"
    try:
        m = int(seconds // 60)
        s = seconds % 60
        # Minutes:Seconds.Milliseconds — no leading zero on minutes to keep it compact
        return f"{m}:{s:06.3f}"  # e.g. 1:17.244
    except Exception:
        return "N/A"


def _ensure_schedule(year: int):
    """Load schedule for year; store in session_state; return (success, event_names)."""
    try:
        schedule = get_event_schedule(year)
        if schedule is None or schedule.empty:
            return False, []
        event_names = schedule["EventName"].dropna().astype(str).tolist()
        st.session_state.schedule = schedule
        st.session_state.event_names = event_names
        return True, event_names
    except Exception:
        return False, []


def _clear_loaded_session():
    """Clear cached session and dependent selectors."""
    st.session_state.session_obj = None
    st.session_state.drivers = []
    st.session_state.loaded_gp = None
    st.session_state.loaded_session_type = None


def _session_options_for_gp(gp_name: str) -> list[str]:
    """Return valid session options for the selected GP (adds sprint sessions only on sprint weekends)."""
    options = ["Race", "Qualifying", "FP1", "FP2", "FP3"]
    schedule = st.session_state.get("schedule")
    if schedule is None or getattr(schedule, "empty", True) or not gp_name:
        return options
    try:
        rows = schedule[schedule["EventName"].astype(str) == str(gp_name)]
        if rows.empty:
            return options
        row = rows.iloc[0]
        event_format = str(row.get("EventFormat", "")).strip().lower()
        is_sprint_weekend = "sprint" in event_format
        for col in ("Session1", "Session2", "Session3", "Session4", "Session5"):
            if col in rows.columns and "sprint" in str(row.get(col, "")).strip().lower():
                is_sprint_weekend = True
                break
        if is_sprint_weekend:
            options.extend(["Sprint", "Sprint Qualifying"])
    except Exception:
        return options
    return options


# Explanations for each section — what the chart/section means
HELP_SUMMARY = """
**What this section shows:** A side-by-side snapshot of the two drivers’ key numbers for this session. All times are in **minutes:seconds:milliseconds** (e.g. 1:17.244).

- **Fastest Lap** — The single quickest lap time set by the driver. In races this can earn a bonus point.
- **Average Pace** — Mean lap time across valid laps; reflects sustained performance, not just one flyer.
- **Lap Consistency (σ)** — Standard deviation of lap times. Lower = more consistent; important for tire management and strategy.
- **Finishing Position** — Where the driver finished (race) or their best qualifying lap time (qualifying).
- **Position Change** — Grid position → finishing position. Positive = gained places; negative = lost. Race only. In qualifying, the fifth column shows **Starting Position** (where they qualified / grid slot for the race).
"""
HELP_LAP_PROGRESSION = """
**What this chart shows:** Lap-by-lap pace for both drivers. Each point is one lap; the line shows how fast they went on every lap. Hover to see the exact time in **minutes:seconds:milliseconds**.

- **Lower on the chart = faster** (faster laps are shown lower on the y-axis).
- The **gap between the two lines** shows who was quicker at each point in the session.
- **Compounds** (Soft/Medium/Hard) affect grip and degradation; strategy and tire changes show up as changes in pace over the laps.
"""
HELP_SECTORS = """
**What this chart shows:** Average time in each of the three track sectors for both drivers. Each bar is the mean sector time; lower bars = faster in that sector.

- Tracks are split into **Sector 1, Sector 2, Sector 3**. Shorter time = faster in that part of the lap.
- Comparing the bars shows **where each driver is stronger** (e.g. corners vs straights) and where time is lost or gained. Times are in **minutes:seconds:milliseconds** where shown.
"""
HELP_TIRE_STRATEGY = """
**What this chart shows:** When each driver used which tire compound and for how many laps. Each horizontal bar is one stint (one set of tires). The table below lists compound, lap count, lap range, and tyre age.

- **Compound** — Soft (red), Medium (yellow), Hard (blue); Wet/Intermediate for rain.
- **Laps** — Number of laps on that set. **Tyre age** — how many laps that set had already done (0 = new). Higher age usually means more degradation and slower pace.
- This view shows **strategy at a glance**: who pitted when and who ran longer stints.
"""
HELP_CONSISTENCY = """
**What this chart shows:** The spread (distribution) of each driver’s lap times. The box is the middle 50% of their times; the “whiskers” extend toward their slowest and fastest laps.

- **Tighter box = more consistent** laps; a wider box means more variation in pace.
- Consistency matters for tire life, fuel management, and avoiding mistakes. Times on the axis are in seconds; you can interpret them as **minutes:seconds** (e.g. 77 s ≈ 1:17).
"""
HELP_QUALI_DELTA = """
**What this chart shows:** The time difference (delta) to the faster driver in each sector. It answers: “Where did the slower driver lose (or gain) time compared to the quicker one?”

- **Green bar** — that driver was faster in that sector (negative delta vs the reference).
- **Red bar** — that driver was slower (positive delta). The chart is referenced to the faster overall driver.
"""
HELP_QUALI_STAGES = """
**What this section shows:** Each driver’s best time in Q1, Q2, and Q3. Qualifying has three stages; the slowest cars are eliminated after Q1 and Q2, so only the top 10 run in Q3.

- **Q1** — All cars run; slowest 5 are eliminated. **Q2** — Next 5 eliminated. **Q3** — Top 10 fight for pole.
- Times are in **minutes:seconds:milliseconds**. Comparing Q1/Q2/Q3 shows who improved with track evolution and who was quick in which stage.
"""
HELP_INSIGHTS = """
**What this section shows:** Short, auto-generated takeaways from the numbers above: who had better one-lap pace, who was more consistent, who gained more positions (in a race), and which sectors each driver was stronger in. Use these as a quick summary of the comparison.
"""


# --- Sidebar ---
st.sidebar.header("Session & drivers")

year_options = list(range(2017, 2027))
default_year_idx = year_options.index(2024) if 2024 in year_options else 0
year = st.sidebar.selectbox(
    "Year",
    options=year_options,
    index=default_year_idx,
    key="year_select",
)
st.sidebar.caption(
    "⚠️ Data availability depends on FastF1 support. 2018–2024 is most reliable. "
    "2025/2026 data loads as the season progresses."
)

# When year changes, clear loaded session and reset GP/drivers
if st.session_state.loaded_year != year:
    _clear_loaded_session()
    st.session_state.loaded_year = year

success, event_names = _ensure_schedule(year)
if not success:
    st.sidebar.warning(f"Schedule data for {year} is not yet available. Try 2024 or earlier.")
    event_names = []
    gp_name = None
else:
    # GP selector: show EventName; we need to pass round name to FastF1 (event name is often the location)
    # FastF1 get_session(year, gp_name, session) expects the event name as in schedule (e.g. "Bahrain")
    current_gp = st.session_state.get("loaded_gp") or (event_names[0] if event_names else None)
    gp_index = event_names.index(current_gp) if current_gp and current_gp in event_names else 0
    gp_name = st.sidebar.selectbox(
        "Grand Prix",
        options=event_names,
        index=min(gp_index, len(event_names) - 1) if event_names else 0,
        key="gp_select",
    )

session_options = _session_options_for_gp(gp_name)
current_session_type = (
    st.session_state.get("loaded_session_type")
    or st.session_state.get("session_type_select")
    or session_options[0]
)
session_index = session_options.index(current_session_type) if current_session_type in session_options else 0
session_type = st.sidebar.selectbox("Session type", options=session_options, index=session_index, key="session_type_select")

load_clicked = st.sidebar.button("Load Data")

# --- Load session when "Load Data" is clicked (must run before driver selectboxes so dropdowns get the new list) ---
session = st.session_state.session_obj
if load_clicked and gp_name and event_names:
    with st.spinner("Loading session data (FastF1 may take a moment on first load)..."):
        try:
            session = get_session(year, gp_name, session_type)
            session.load()
            st.session_state.session_obj = session
            st.session_state.loaded_gp = gp_name
            st.session_state.loaded_session_type = session_type
            drivers = get_all_drivers(session)
            st.session_state.drivers = drivers or []
        except Exception as e:
            st.sidebar.error(f"Could not load session: {e}")
            session = None
            st.session_state.session_obj = None

# Re-read session and drivers after possible load
session = st.session_state.session_obj
drivers = st.session_state.drivers

# Driver selectors: options from loaded session (rendered after load so dropdowns show drivers on same run)
driver_options = drivers if drivers else [""]
driver1 = st.sidebar.selectbox("Driver 1", options=driver_options, key="driver1_select", index=0)
driver2 = st.sidebar.selectbox(
    "Driver 2",
    options=[d for d in driver_options if d != driver1] if driver_options and driver_options != [""] else [""],
    key="driver2_select",
    index=0,
)

# If we have session but driver selectors were not yet populated, show message
if session is not None and not drivers:
    st.sidebar.info("No driver list for this session. Try another event or year.")

# --- Main area: show content only when we have session and two drivers ---
if session is None:
    st.info("Select Year, Grand Prix, and Session type, then click **Load Data** to compare drivers.")
    st.stop()

if not driver1 or not driver2:
    st.warning("Please select Driver 1 and Driver 2.")
    st.stop()

# Load lap data for both drivers
try:
    laps1 = get_driver_laps(session, driver1)
    laps2 = get_driver_laps(session, driver2)
except Exception as e:
    st.error(f"Error loading laps: {e}")
    st.stop()

# Check sector data availability
sector_cols = ["Sector1Time", "Sector2Time", "Sector3Time"]
has_sector = all(
    (laps1 is not None and c in laps1.columns and laps1[c].notna().any())
    or (laps2 is not None and c in laps2.columns and laps2[c].notna().any())
    for c in sector_cols
)
if not has_sector:
    for c in sector_cols:
        if (laps1 is not None and c in laps1.columns) or (laps2 is not None and c in laps2.columns):
            has_sector = True
            break
# If either driver has any sector data, we allow sector charts (they may have NaNs)
has_any_sector = False
for df in [laps1, laps2]:
    if df is not None and not df.empty:
        for c in sector_cols:
            if c in df.columns and df[c].notna().any():
                has_any_sector = True
                break

# --- Metrics ---
best1 = best_lap_time(laps1)
best2 = best_lap_time(laps2)
avg1 = average_lap_time(laps1)
avg2 = average_lap_time(laps2)
med1 = median_lap_time(laps1)
med2 = median_lap_time(laps2)
cons1 = lap_consistency(laps1)
cons2 = lap_consistency(laps2)
pos_change1 = position_change(session, driver1)
pos_change2 = position_change(session, driver2)

# Finishing position or best quali lap
def _get_finish_position(session, driver_code):
    res = getattr(session, "results", None)
    if res is None or res.empty:
        return None
    if "Abbreviation" in res.columns:
        row = res[res["Abbreviation"] == driver_code]
    else:
        row = res[res["DriverNumber"].astype(str) == str(driver_code)]
    if row.empty:
        return None
    return row.iloc[0].get("Position") or row.iloc[0].get("ClassifiedPosition")

finish_pos1 = _get_finish_position(session, driver1)
finish_pos2 = _get_finish_position(session, driver2)


def _safe_int(val):
    """Coerce to int; return None if NaN, None, or invalid."""
    if val is None:
        return None
    try:
        if hasattr(val, "item"):
            v = val.item()
        else:
            v = val
        if v != v or v is None:  # NaN check
            return None
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _get_starting_position(session, driver_code):
    """Starting/grid position as integer (qualifying result = where they start). Returns None if missing/invalid."""
    res = getattr(session, "results", None)
    if res is None or res.empty:
        return None
    if "Abbreviation" in res.columns:
        row = res[res["Abbreviation"] == driver_code]
    else:
        row = res[res["DriverNumber"].astype(str) == str(driver_code)]
    if row.empty:
        return None
    r = row.iloc[0]
    # For qualifying: Position is the quali result (= grid/starting position). GridPosition for race/sprint.
    # Try each in order; use first that yields a valid int (avoids returning NaN when one column is missing).
    for col in ("Position", "GridPosition", "ClassifiedPosition"):
        val = r.get(col)
        if val is None:
            continue
        if hasattr(val, "__float__") and val != val:  # NaN
            continue
        if isinstance(val, str) and val.strip() in ("", "R", "D", "E", "W", "F", "N"):
            continue
        out = _safe_int(val)
        if out is not None and out >= 1:
            return out
    return None


def _get_penalty_info(session, driver_code):
    """
    If the driver had a grid penalty, return dict with 'positions' (int) and 'reason' (str).
    Otherwise return None. Only shown when penalty data is present in results.
    """
    res = getattr(session, "results", None)
    if res is None or res.empty:
        return None
    if "Abbreviation" in res.columns:
        row = res[res["Abbreviation"] == driver_code]
    else:
        row = res[res["DriverNumber"].astype(str) == str(driver_code)]
    if row.empty:
        return None
    r = row.iloc[0]
    # FastF1 may not expose these; check common column names (Ergast/supplements sometimes add them)
    cols_lower = {str(c).lower(): c for c in r.index}
    positions = None
    reason = None
    if "gridpenalty" in cols_lower or "grid_penalty" in cols_lower:
        c = cols_lower.get("gridpenalty") or cols_lower.get("grid_penalty")
        positions = _safe_int(r.get(c))
    if "penalty" in cols_lower and positions is None:
        positions = _safe_int(r.get(cols_lower["penalty"]))
    if "penaltyreason" in cols_lower or "penalty_reason" in cols_lower or "penaltyreasonreason" in cols_lower:
        c = cols_lower.get("penaltyreason") or cols_lower.get("penalty_reason") or cols_lower.get("penaltyreasonreason")
        reason = r.get(c)
    if reason is not None and isinstance(reason, float) and reason != reason:
        reason = None
    if reason is not None and not isinstance(reason, str):
        reason = str(reason).strip() if reason else None
    if positions is not None and positions > 0:
        return {"positions": positions, "reason": reason or "Grid penalty"}
    return None


starting_pos1 = _get_starting_position(session, driver1)
starting_pos2 = _get_starting_position(session, driver2)
penalty1 = _get_penalty_info(session, driver1)
penalty2 = _get_penalty_info(session, driver2)

is_race = session_type == "Race"
is_qualifying = session_type == "Qualifying"

# Team colors for charts (driver color = team color in this session)
try:
    team_color1 = get_driver_team_color(session, driver1)
    team_color2 = get_driver_team_color(session, driver2)
except Exception:
    team_color1 = team_color2 = None

# --- Summary cards (5 columns x 2 drivers: side by side) ---
st.subheader("Summary")
with st.expander("What do these numbers mean?"):
    st.markdown(HELP_SUMMARY)

# Column labels so users know what each number means
label_col1, label_col2, label_col3, label_col4, label_col5 = st.columns(5)
with label_col1:
    st.caption("**Fastest Lap**")
with label_col2:
    st.caption("**Average Pace**")
with label_col3:
    st.caption("**Lap Consistency (σ)**")
with label_col4:
    if is_race:
        st.caption("**Finishing Position**")
    elif is_qualifying:
        st.caption("**Best Quali Lap**")
    else:
        st.caption("**Best Lap**")
with label_col5:
    if is_race:
        st.caption("**Position Change**")
    elif is_qualifying:
        st.caption("**Starting Position**")
    else:
        st.caption("**Classified Position**")

st.caption(f"**{driver1}**")
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Fastest Lap", _format_lap_time(best1), label_visibility="collapsed")
with col2:
    st.metric("Average Pace", _format_lap_time(avg1), label_visibility="collapsed")
with col3:
    std1 = f"{cons1:.3f}s" if cons1 is not None else "N/A"
    st.metric("Lap Consistency (σ)", std1, label_visibility="collapsed")
with col4:
    if is_race:
        st.metric("Finishing Position", str(finish_pos1) if finish_pos1 is not None else "N/A", label_visibility="collapsed")
    elif is_qualifying:
        st.metric("Best Quali Lap", _format_lap_time(best1), label_visibility="collapsed")
    else:
        st.metric("Best Lap", _format_lap_time(best1), label_visibility="collapsed")
with col5:
    if is_race:
        pc1 = f"{pos_change1:+d}" if pos_change1 is not None else "N/A"
        st.metric("Position Change", pc1, label_visibility="collapsed")
    elif is_qualifying:
        pos_str = str(starting_pos1) if starting_pos1 is not None else "N/A"
        st.metric("Starting Position", pos_str, label_visibility="collapsed")
        if penalty1:
            st.caption(f"↓ {penalty1['positions']}-place penalty: {penalty1.get('reason') or 'Grid penalty'}")
    else:
        st.metric("Classified Position", str(finish_pos1) if finish_pos1 is not None else "N/A", label_visibility="collapsed")

st.caption(f"**{driver2}**")
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Fastest Lap", _format_lap_time(best2), label_visibility="collapsed")
with col2:
    st.metric("Average Pace", _format_lap_time(avg2), label_visibility="collapsed")
with col3:
    std2 = f"{cons2:.3f}s" if cons2 is not None else "N/A"
    st.metric("Lap Consistency (σ)", std2, label_visibility="collapsed")
with col4:
    if is_race:
        st.metric("Finishing Position", str(finish_pos2) if finish_pos2 is not None else "N/A", label_visibility="collapsed")
    elif is_qualifying:
        st.metric("Best Quali Lap", _format_lap_time(best2), label_visibility="collapsed")
    else:
        st.metric("Best Lap", _format_lap_time(best2), label_visibility="collapsed")
with col5:
    if is_race:
        pc2 = f"{pos_change2:+d}" if pos_change2 is not None else "N/A"
        st.metric("Position Change", pc2, label_visibility="collapsed")
    elif is_qualifying:
        pos_str = str(starting_pos2) if starting_pos2 is not None else "N/A"
        st.metric("Starting Position", pos_str, label_visibility="collapsed")
        if penalty2:
            st.caption(f"↓ {penalty2['positions']}-place penalty: {penalty2.get('reason') or 'Grid penalty'}")
    else:
        st.metric("Classified Position", str(finish_pos2) if finish_pos2 is not None else "N/A", label_visibility="collapsed")

# --- Charts in tabs ---
tab_names = ["Lap Time Progression", "Sector Time Comparison", "Tire Stint Strategy", "Lap Time Consistency"]
if is_qualifying:
    tab_names.extend(["Qualifying Q1/Q2/Q3", "Qualifying Delta"])

tabs = st.tabs(tab_names)
with tabs[0]:
    with st.expander("How to read this chart"):
        st.markdown(HELP_LAP_PROGRESSION)
    st.plotly_chart(
        charts.lap_time_chart(laps1, laps2, driver1, driver2, team_color1, team_color2),
        use_container_width=True,
    )

with tabs[1]:
    with st.expander("How to read this chart"):
        st.markdown(HELP_SECTORS)
    if not has_any_sector:
        st.warning("Sector data not available for this session.")
    else:
        st.plotly_chart(
            charts.sector_comparison_chart(laps1, laps2, driver1, driver2, team_color1, team_color2),
            use_container_width=True,
        )

with tabs[2]:
    with st.expander("How to read tire strategy"):
        st.markdown(HELP_TIRE_STRATEGY)
    laps_all1 = get_driver_laps_all(session, driver1)
    laps_all2 = get_driver_laps_all(session, driver2)
    stints1 = get_stint_summary(laps_all1, driver1)
    stints2 = get_stint_summary(laps_all2, driver2)
    if stints1 or stints2:
        st.plotly_chart(
            charts.tire_stint_chart(stints1, stints2, driver1, driver2),
            use_container_width=True,
        )
        # Stint summary table
        st.caption("Stint summary")
        rows = []
        for label, stints in [(driver1, stints1), (driver2, stints2)]:
            for s in stints:
                age = ""
                if s.get("tyre_age_start") is not None or s.get("tyre_age_end") is not None:
                    age = f"{int(s.get('tyre_age_start') or 0)}→{int(s.get('tyre_age_end') or 0)}"
                rows.append({
                    "Driver": label,
                    "Compound": s["compound"],
                    "Laps": s["laps"],
                    "Lap range": f"{s['start_lap']}–{s['end_lap']}",
                    "Tyre age (start→end)": age or "—",
                })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.warning("No tire stint data available for this session.")

with tabs[3]:
    with st.expander("How to read this chart"):
        st.markdown(HELP_CONSISTENCY)
    st.plotly_chart(
        charts.consistency_boxplot(laps1, laps2, driver1, driver2, team_color1, team_color2),
        use_container_width=True,
    )

# Qualifying: Q1/Q2/Q3 tab
if is_qualifying:
    q_times_df = get_qualifying_stage_times(session)
    idx_qual_stages = tab_names.index("Qualifying Q1/Q2/Q3") if "Qualifying Q1/Q2/Q3" in tab_names else 4
    with tabs[idx_qual_stages]:
        with st.expander("What are Q1, Q2, Q3?"):
            st.markdown(HELP_QUALI_STAGES)
        if q_times_df is not None and not q_times_df.empty:
            fig_q = charts.qualifying_q1_q2_q3_chart(q_times_df, driver1, driver2, team_color1, team_color2, _format_lap_time)
            if fig_q:
                st.plotly_chart(fig_q, use_container_width=True)
            # Table of Q1/Q2/Q3 times
            r1 = q_times_df[q_times_df["Driver"] == driver1]
            r2 = q_times_df[q_times_df["Driver"] == driver2]
            if not r1.empty or not r2.empty:
                q_table = []
                for stage in ["Q1", "Q2", "Q3"]:
                    v1 = r1[stage].iloc[0] if not r1.empty and stage in r1.columns else None
                    v2 = r2[stage].iloc[0] if not r2.empty and stage in r2.columns else None
                    q_table.append({"Stage": stage, driver1: _format_lap_time(v1) if v1 == v1 else "—", driver2: _format_lap_time(v2) if v2 == v2 else "—"})
                st.dataframe(pd.DataFrame(q_table), use_container_width=True, hide_index=True)
        else:
            st.info("Q1/Q2/Q3 times not available for this session.")

    idx_delta = tab_names.index("Qualifying Delta") if "Qualifying Delta" in tab_names else 5
    with tabs[idx_delta]:
        with st.expander("How to read qualifying delta"):
            st.markdown(HELP_QUALI_DELTA)
        if not has_any_sector:
            st.warning("Sector data not available for this session.")
        else:
            st.plotly_chart(
                charts.qualifying_delta_chart(laps1, laps2, driver1, driver2, team_color1, team_color2),
                use_container_width=True,
            )

# --- Insights (2–3 auto-generated from metrics) ---
st.subheader("Insights")
with st.expander("What are these insights?"):
    st.markdown(HELP_INSIGHTS)
insights = []

# One-lap pace
if best1 is not None and best2 is not None:
    if best1 < best2:
        delta = best2 - best1
        insights.append(f"**{driver1}** had better one-lap pace, with fastest lap {_format_lap_time(best1)} ({delta:.3f}s faster than {driver2}).")
    elif best2 < best1:
        delta = best1 - best2
        insights.append(f"**{driver2}** had better one-lap pace, with fastest lap {_format_lap_time(best2)} ({delta:.3f}s faster than {driver1}).")
    else:
        insights.append(f"Both drivers set the same fastest lap time: {_format_lap_time(best1)}.")

# Consistency (lower std wins)
if cons1 is not None and cons2 is not None:
    if cons1 < cons2:
        insights.append(f"**{driver1}** was more consistent (lap time σ = {cons1:.3f}s vs {driver2}'s {cons2:.3f}s).")
    elif cons2 < cons1:
        insights.append(f"**{driver2}** was more consistent (lap time σ = {cons2:.3f}s vs {driver1}'s {cons1:.3f}s).")

# Position change (race only)
if is_race and pos_change1 is not None and pos_change2 is not None:
    if pos_change1 > pos_change2:
        insights.append(f"**{driver1}** gained more positions during the race (grid → finish: {pos_change1:+d} vs {driver2}'s {pos_change2:+d}).")
    elif pos_change2 > pos_change1:
        insights.append(f"**{driver2}** gained more positions during the race (grid → finish: {pos_change2:+d} vs {driver1}'s {pos_change1:+d}).")

# Sector strength (if sector data available)
if has_any_sector:
    sa1 = sector_averages(laps1)
    sa2 = sector_averages(laps2)
    s1_1, s2_1, s3_1 = sa1["Sector1Time"], sa1["Sector2Time"], sa1["Sector3Time"]
    s1_2, s2_2, s3_2 = sa2["Sector1Time"], sa2["Sector2Time"], sa2["Sector3Time"]
    sector_wins = []
    if s1_1 is not None and s1_2 is not None and not (s1_1 != s1_1 and s1_2 != s1_2):
        sector_wins.append(("Sector 1", driver1 if s1_1 < s1_2 else driver2))
    if s2_1 is not None and s2_2 is not None and not (s2_1 != s2_1 and s2_2 != s2_2):
        sector_wins.append(("Sector 2", driver1 if s2_1 < s2_2 else driver2))
    if s3_1 is not None and s3_2 is not None and not (s3_1 != s3_1 and s3_2 != s3_2):
        sector_wins.append(("Sector 3", driver1 if s3_1 < s3_2 else driver2))
    if sector_wins:
        parts = [f"{sec}: **{dr}**" for sec, dr in sector_wins]
        insights.append("Sector strength (average): " + "; ".join(parts) + ".")

for text in insights[:3]:  # Cap at 3
    st.info(text)

if not insights:
    st.info("Load a session and select two drivers to see auto-generated insights.")
