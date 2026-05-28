# F1 Driver Performance Comparison Dashboard

A Streamlit web app that compares Formula 1 driver performance using live timing data from the **FastF1** library. Pick a year, Grand Prix, session (Race or Qualifying), and two drivers to see lap-by-lap pace, sector times, tire strategy, and consistency side by side.

---

## Screenshot

<!-- Add a screenshot of the dashboard here, e.g. ![Dashboard](screenshot.png) -->

*Screenshot placeholder: run the app and add an image of the Summary and Charts sections.*

---

## Install

```bash
pip install -r requirements.txt
```

Dependencies: `fastf1`, `pandas`, `numpy`, `plotly`, `streamlit`.

---

## Run

From the `f1_dashboard` directory:

```bash
streamlit run app.py
```

The app opens in your browser (typically http://localhost:8501).

---

## FastF1 cache

The app uses a local cache at `./data/cache`. FastF1 stores downloaded session data there so repeat loads for the same event are much faster. The first time you load a session for a given year/event, it may take a few seconds.

---

## Features

- **Session selection**: Year (2017–2026), Grand Prix (from schedule), and session type (Race or Qualifying).
- **Driver comparison**: Choose any two drivers from the session; all metrics and charts compare them.
- **Summary cards**: Fastest lap, average pace, lap consistency (σ), finishing position (race) or best quali lap, and position change (race only).
- **Charts (Plotly)**:
  - **Lap time progression**: Lap time vs lap number for both drivers (with compound hint where available).
  - **Sector time comparison**: Grouped bar chart of average S1, S2, S3.
  - **Tire stint strategy**: Gantt-style view of compounds by lap number, one row per driver.
  - **Lap time consistency**: Box plot of lap time distribution.
  - **Qualifying delta** (Qualifying only): Per-sector delta vs the faster driver.
- **Insights**: Short auto-generated text comparing one-lap pace, consistency, position change (race), and sector strength (when sector data exists).
- **Robustness**: Handles missing sector data (e.g. some 2017–2021 sessions) and future years (2025/2026) with clear warnings instead of crashes.

---

## Data availability

- **2018–2024**: Generally the most complete and reliable (lap times, sector times, results).
- **2017, 2021**: Telemetry and sector data may be partially missing for some events; the app skips sector-dependent charts and shows a warning.
- **2025 and 2026**: Data appears as the season progresses; if the schedule or session is not yet available, the app shows a clear message (e.g. “Schedule data for 2026 is not yet available”).

---

## Example comparison

- **Max Verstappen vs Sergio Pérez**, **2023 Bahrain Grand Prix**, **Race**  
  After loading that session, select VER and PER to compare fastest lap, average pace, consistency, tire usage, and position change for that race.

---

## Project structure

```
f1_dashboard/
├── app.py              # Main Streamlit app
├── data/
│   └── cache/          # FastF1 cache directory
├── modules/
│   ├── loader.py       # FastF1 data loading (schedule, session, laps, drivers)
│   ├── metrics.py      # Metric calculations (best/avg/median lap, consistency, position change, sectors)
│   └── charts.py       # Plotly chart functions
├── requirements.txt
└── README.md
```
