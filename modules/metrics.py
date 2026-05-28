"""
Metric calculation functions for driver lap DataFrames.
Lap times are expected in seconds (e.g. from loader after .dt.total_seconds()).
"""
import numpy as np
import pandas as pd


def best_lap_time(laps: pd.DataFrame):
    """Return fastest lap time in seconds, or None if no valid laps."""
    if laps is None or laps.empty or "LapTime" not in laps.columns:
        return None
    s = laps["LapTime"].dropna()
    if s.empty:
        return None
    return float(s.min())


def average_lap_time(laps: pd.DataFrame):
    """Return mean lap time in seconds, or None if no valid laps."""
    if laps is None or laps.empty or "LapTime" not in laps.columns:
        return None
    s = laps["LapTime"].dropna()
    if s.empty:
        return None
    return float(s.mean())


def median_lap_time(laps: pd.DataFrame):
    """Return median lap time in seconds, or None if no valid laps."""
    if laps is None or laps.empty or "LapTime" not in laps.columns:
        return None
    s = laps["LapTime"].dropna()
    if s.empty:
        return None
    return float(s.median())


def lap_consistency(laps: pd.DataFrame):
    """Return standard deviation of lap times in seconds, or None if insufficient data."""
    if laps is None or laps.empty or "LapTime" not in laps.columns:
        return None
    s = laps["LapTime"].dropna()
    if s.size < 2:
        return None
    return float(s.std())


def position_change(session, driver_code: str):
    """
    Return finishing position minus starting grid position.
    Positive = gained positions, negative = lost positions.
    Returns None if session or positions not available.
    """
    if session is None:
        return None
    results = getattr(session, "results", None)
    if results is None or results.empty:
        return None
    # Match driver: Abbreviation or DriverNumber
    if "Abbreviation" in results.columns:
        row = results[results["Abbreviation"] == driver_code]
    elif "DriverNumber" in results.columns:
        row = results[results["DriverNumber"].astype(str) == str(driver_code)]
    else:
        return None
    if row.empty:
        return None
    row = row.iloc[0]
    finish = row.get("Position") or row.get("ClassifiedPosition")
    start = row.get("GridPosition") or row.get("Position")
    if finish is None or start is None:
        return None
    try:
        return int(finish) - int(start)
    except (TypeError, ValueError):
        return None


def sector_averages(laps: pd.DataFrame) -> dict:
    """
    Return dict with keys 'Sector1Time', 'Sector2Time', 'Sector3Time' and mean
    values in seconds. Missing columns/series yield NaN for that sector.
    """
    out = {"Sector1Time": np.nan, "Sector2Time": np.nan, "Sector3Time": np.nan}
    if laps is None or laps.empty:
        return out
    for key in out:
        if key in laps.columns:
            s = laps[key].dropna()
            if not s.empty:
                out[key] = float(s.mean())
    return out
