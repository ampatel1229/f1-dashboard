# 🏎️ F1 Data Dashboard

F1 Data Dashboard is an interactive Streamlit app that compares two Formula 1 drivers in a selected Grand Prix session using FastF1 timing data.

I built this project to make Formula 1 data easier to explore and understand. F1 sessions generate a lot of timing information, but raw lap and sector data can be hard to interpret on its own. This dashboard turns that data into clear side-by-side comparisons, interactive charts, and simple explanations so users can quickly understand how two drivers performed in the same session.

The app supports race, qualifying, and sprint-related sessions when available. Users can choose the season, Grand Prix, session type, and drivers they want to compare. From there, the dashboard calculates key metrics like fastest lap, average pace, lap consistency, finishing or qualifying context, and position change.

The main goal was to build something that feels useful for both casual F1 fans and people who want a deeper analytical view of driver performance.

## 📦 Technologies

- Python
- Streamlit
- FastF1
- pandas
- NumPy
- Plotly

## ✨ Features

- Select sessions by:
  - Year
  - Grand Prix
  - Session type
  - Race
  - Qualifying
  - Sprint sessions when available
- Side-by-side driver comparison
- Key driver metrics:
  - Fastest lap
  - Average pace
  - Lap consistency using standard deviation
  - Finishing position or qualifying context
  - Position change
- Interactive visualizations:
  - Lap time progression
  - Sector time comparison
  - Tire stint strategy
  - Lap consistency distribution
  - Qualifying sector delta
- Built-in explanation and help text for each visualization
- Caching support for faster repeat loads using `./data/cache`
- Graceful handling of missing or incomplete historical data

## ⌨️ Keyboard Shortcuts

No custom keyboard shortcuts are currently implemented.

## 🧠 The Process

I built this dashboard by connecting FastF1 session data to a modular Streamlit app. I started by creating the session selection flow so users could choose a season, Grand Prix, and session type. From there, I worked on loading the timing data and making sure the app could handle different session formats, including races, qualifying sessions, and sprint sessions when available.

After the data-loading flow was working, I built reusable metric and chart modules. This made it easier to compare any two drivers consistently without rewriting the same logic for every visualization. I wanted each comparison to feel organized, so I separated the dashboard into clear sections for pace, lap progression, sector performance, tire strategy, and consistency.

One of the biggest challenges was handling incomplete or inconsistent historical data. Not every Formula 1 session has the same level of available information, so I added checks to make the app fail gracefully when certain data is missing instead of breaking completely.

I also added explanation text for the charts because visual analytics are more useful when users understand what they are looking at. The goal was not just to show numbers, but to make the driver comparison easier to interpret.

## 📚 What I Learned

This project taught me how to work with real sports timing and telemetry-style data. Formula 1 data has a lot of detail, but it also requires careful cleaning, filtering, and context before it becomes useful.

I learned how to compare drivers across different performance dimensions, such as pace, consistency, sector times, tire strategy, and race position changes. I also got more comfortable designing interactive dashboards with Streamlit and Plotly.

Another major lesson was that historical sports data is not always perfect. Some sessions may have missing laps, incomplete tire information, or differences in available timing data. Building around those issues helped me think more carefully about reliability and user experience.

## 🔧 How It Can Be Improved

- Add head-to-head comparison history across multiple races
- Add team-level and season-level trend views
- Add export or report generation for selected comparisons
- Add richer race-strategy analytics
- Add pit window analysis
- Add tire degradation modeling
- Add driver performance summaries across a full season
- Add more advanced qualifying analysis
- Improve mobile layout for smaller screens

## 🚀 Running the Project

```bash
git clone <repo-url>
cd "F1 Data Dashboard/f1_dashboard"

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

streamlit run app.py
```

Then open the local Streamlit URL shown in your terminal, usually:

```bash
http://localhost:8501
```

## 📝 Notes

This project is meant to make Formula 1 timing data easier to understand through clean comparisons and visual explanations. The focus is on turning raw session data into insights that are useful, readable, and interesting for F1 fans and analytics-focused users.
