# EU 4D Economic Intelligence Dashboard

A Streamlit-based economic intelligence dashboard for 27 EU countries covering 2020–2025.

## Dimensions

- **Time:** 2020–2025 economic trends
- **Country:** 27-country comparison
- **Economy:** GDP growth, GDP per capita PPS, and inflation
- **Intelligence:** economic score, opportunity, risk, and resilience

## Data

The canonical dataset contains 162 rows: 27 countries × 6 years.

Primary source: Eurostat.

The project includes an automated GitHub Actions pipeline that rebuilds the processed datasets from Eurostat and commits them to `data/processed/`.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project status

Current milestone: functional 4D Streamlit dashboard with automated Eurostat data-recovery and dataset-build pipeline.
