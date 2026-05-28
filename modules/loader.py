"""
FastF1 data loading functions for the F1 Driver Performance Comparison Dashboard.
Cache is enabled at ./data/cache relative to the app root.
"""
import os
from pathlib import Path

import numpy as np
import fastf1
import pandas as pd


def get_driver_team_color(session, driver_code: str):
    """Return hex color for the driver's team in this session, or None to use default."""
    if session is None:
        return None
    try:
        from fastf1.plotting import get_driver_color
        return get_driver_color(driver_code, session)
    except Exception:
        return None


def _get_cache_path():
    """Return absolute path to the FastF1 cache directory."""
    # Resolve relative to this file: f1_dashboard/modules/loader.py -> f1_dashboard/data/cache
    base = Path(__file__).resolve().parent.parent
    return str(base / "data" / "cache")


def _setup_cache():
    """Enable FastF1 cache at ./data/cache."""
    cache_dir = _get_cache_path()
    os.makedirs(cache_dir, exist_ok=True)
    fastf1.Cache.enable_cache(cache_dir)


def get_event_schedule(year: int):
    """
    Load and return the event schedule for a given year.
    Excludes testing events (EventFormat != 'testing').
    """
    _setup_cache()
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
    except TypeError:
        schedule = fastf1.get_event_schedule(year)
    if schedule is None or schedule.empty:
        return pd.DataFrame()
    # Filter out testing events if column exists (e.g. older FastF1)
    if "EventFormat" in schedule.columns:
        schedule = schedule[schedule["EventFormat"] != "testing"].copy()
    return schedule.reset_index(drop=True)


def get_session(year: int, gp_name: str, session_type: str):
    """
    Load and return a FastF1 session for the given year, GP name, and session type.
    session_type supports Race, Qualifying, FP1, FP2, FP3.
    """
    _setup_cache()
    session_type_map = {
        "Race": "Race",
        "Qualifying": "Qualifying",
        "FP1": "FP1",
        "FP2": "FP2",
        "FP3": "FP3",
        "Sprint": "Sprint",
        "Sprint Qualifying": "Sprint Qualifying",
    }
    st = session_type_map.get(session_type, session_type)
    return fastf1.get_session(year, gp_name, st)


def get_driver_laps_all(session, driver_code: str) -> pd.DataFrame:
    """
    Return all lap data for one driver (including in/out laps) for tire stint analysis.
    Converts LapTime and sector times to total seconds. Does not filter in/out laps.
    """
    laps = session.laps.pick_driver(driver_code).copy()
    if laps.empty:
        return laps
    laps = laps[laps["LapTime"].notna()]
    laps = laps.sort_values("LapNumber").reset_index(drop=True)
    def is_timedelta(series):
        try:
            return pd.api.types.is_timedelta64_dtype(series)
        except AttributeError:
            return str(getattr(series.dtype, "name", "")).startswith("timedelta")
    for col in ["LapTime", "Sector1Time", "Sector2Time", "Sector3Time"]:
        if col in laps.columns and is_timedelta(laps[col]):
            laps[col] = laps[col].dt.total_seconds()
    return laps


def get_driver_laps(session, driver_code: str) -> pd.DataFrame:
    """
    Return cleaned lap data for one driver.
    Filters out: in-laps, out-laps, and laps where LapTime is null.
    Converts LapTime and sector times to total seconds where present.
    """
    laps = session.laps.pick_driver(driver_code).copy()
    if laps.empty:
        return laps
    # Exclude laps with null LapTime
    laps = laps[laps["LapTime"].notna()]
    # Exclude in-laps (lap where driver pitted - has PitInTime) and out-laps (PitOutTime)
    if "PitInTime" in laps.columns:
        laps = laps[laps["PitInTime"].isna()]
    if "PitOutTime" in laps.columns:
        laps = laps[laps["PitOutTime"].isna()]
    laps = laps.sort_values("LapNumber").reset_index(drop=True)
    # Convert Timedelta columns to total seconds for metrics/plotting
    def is_timedelta(series):
        try:
            return pd.api.types.is_timedelta64_dtype(series)
        except AttributeError:
            return str(getattr(series.dtype, "name", "")).startswith("timedelta")
    for col in ["LapTime", "Sector1Time", "Sector2Time", "Sector3Time"]:
        if col in laps.columns and is_timedelta(laps[col]):
            laps[col] = laps[col].dt.total_seconds()
    return laps


def get_all_drivers(session) -> list:
    """Return list of driver codes (e.g. ['VER', 'PER']) in the given session."""
    if session is None:
        return []
    # Ensure we have a DataFrame (SessionResults may be a subclass or custom type)
    results = getattr(session, "results", None)
    if results is not None and not (hasattr(results, "empty") and results.empty):
        try:
            df = pd.DataFrame(results) if not isinstance(results, pd.DataFrame) else results
        except Exception:
            df = None
        if df is not None and not df.empty:
            cols_lower = {c.lower(): c for c in df.columns}
            if "abbreviation" in cols_lower:
                abbrevs = df[cols_lower["abbreviation"]].dropna().astype(str).unique().tolist()
                if abbrevs:
                    return sorted(abbrevs)
            if "drivernumber" in cols_lower:
                return sorted(df[cols_lower["drivernumber"]].dropna().astype(str).unique().tolist())
    # Fallback: from laps (may have 'Abbreviation' or only 'DriverNumber')
    laps = getattr(session, "laps", None)
    if laps is not None and hasattr(laps, "columns") and not laps.empty:
        cols_lower = {c.lower(): c for c in laps.columns}
        if "abbreviation" in cols_lower:
            abbrevs = laps[cols_lower["abbreviation"]].dropna().astype(str).unique().tolist()
            if abbrevs:
                return sorted(abbrevs)
        if "drivernumber" in cols_lower:
            return sorted(laps[cols_lower["drivernumber"]].dropna().astype(str).unique().tolist())
    return []


def get_qualifying_stage_times(session):
    """
    Return a DataFrame with columns Driver (abbrev), Q1, Q2, Q3 as total seconds, if session is Qualifying.
    Otherwise return None.
    """
    if session is None:
        return None
    res = getattr(session, "results", None)
    if res is None or res.empty:
        return None
    try:
        df = pd.DataFrame(res) if not isinstance(res, pd.DataFrame) else res.copy()
    except Exception:
        return None
    cols_lower = {c.lower(): c for c in df.columns}
    abbrev_col = cols_lower.get("abbreviation")
    if not abbrev_col:
        return None
    out = df[[abbrev_col]].rename(columns={abbrev_col: "Driver"})
    for stage in ["Q1", "Q2", "Q3"]:
        if stage not in df.columns:
            out[stage] = np.nan
            continue
        ser = df[stage]
        try:
            if hasattr(pd.api.types, "is_timedelta64_dtype") and pd.api.types.is_timedelta64_dtype(ser):
                out[stage] = ser.dt.total_seconds().values
            else:
                out[stage] = pd.to_timedelta(ser, errors="coerce").dt.total_seconds().values
        except Exception:
            out[stage] = np.nan
    return out


def get_stint_summary(laps: pd.DataFrame, driver_code: str):
    """
    From a driver's laps DataFrame, return a list of dicts: compound, start_lap, end_lap, laps, tyre_age_start, tyre_age_end.
    Uses Stint and Compound if present; else groups by consecutive same Compound.
    """
    if laps is None or laps.empty or "LapNumber" not in laps.columns:
        return []
    laps = laps.sort_values("LapNumber").reset_index(drop=True)
    has_stint = "Stint" in laps.columns
    has_compound = "Compound" in laps.columns
    has_tyre_life = "TyreLife" in laps.columns
    stints = []
    if has_stint and has_compound:
        for _, g in laps.groupby(["Stint", "Compound"]):
            comp = str(g["Compound"].iloc[0]).upper()
            start_lap = int(g["LapNumber"].min())
            end_lap = int(g["LapNumber"].max())
            n_laps = len(g)
            tyre_start = float(g["TyreLife"].iloc[0]) if has_tyre_life and g["TyreLife"].notna().any() else None
            tyre_end = float(g["TyreLife"].iloc[-1]) if has_tyre_life and g["TyreLife"].notna().any() else None
            stints.append({"compound": comp, "start_lap": start_lap, "end_lap": end_lap, "laps": n_laps, "tyre_age_start": tyre_start, "tyre_age_end": tyre_end})
    elif has_compound:
        start_lap = None
        end_lap = None
        compound = None
        for _, row in laps.iterrows():
            ln = row["LapNumber"]
            comp = str(row.get("Compound", "UNKNOWN")).upper()
            if compound is None:
                start_lap = ln
                end_lap = ln
                compound = comp
                continue
            if comp != compound:
                seg = laps[(laps["LapNumber"] >= start_lap) & (laps["LapNumber"] <= end_lap)]
                tyre_start = float(seg["TyreLife"].iloc[0]) if has_tyre_life and "TyreLife" in seg.columns and seg["TyreLife"].notna().any() else None
                tyre_end = float(seg["TyreLife"].iloc[-1]) if has_tyre_life and "TyreLife" in seg.columns and seg["TyreLife"].notna().any() else None
                stints.append({"compound": compound, "start_lap": int(start_lap), "end_lap": int(end_lap), "laps": int(end_lap - start_lap + 1), "tyre_age_start": tyre_start, "tyre_age_end": tyre_end})
                start_lap = ln
                compound = comp
            end_lap = ln
        if start_lap is not None:
            seg = laps[(laps["LapNumber"] >= start_lap) & (laps["LapNumber"] <= end_lap)]
            tyre_start = float(seg["TyreLife"].iloc[0]) if has_tyre_life and "TyreLife" in seg.columns and seg["TyreLife"].notna().any() else None
            tyre_end = float(seg["TyreLife"].iloc[-1]) if has_tyre_life and "TyreLife" in seg.columns and seg["TyreLife"].notna().any() else None
            stints.append({"compound": compound, "start_lap": int(start_lap), "end_lap": int(end_lap), "laps": int(end_lap - start_lap + 1), "tyre_age_start": tyre_start, "tyre_age_end": tyre_end})
    return stints
