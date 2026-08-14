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

The project is designed so the datasets can be regenerated from Eurostat if a temporary Colab runtime is reset.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project status

Current milestone: functional 4D Streamlit dashboard with validated Eurostat data-recovery pipeline.
