import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="EU 4D Economic Intelligence",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE = Path(__file__).resolve().parent
DATA = BASE / "data" / "processed"
MASTER_FILE = DATA / "eu_economic_master_2020_2025.csv"
INTELLIGENCE_FILE = DATA / "country_economic_intelligence.csv"

EUROSTAT_MAP_URL = (
    "https://gisco-services.ec.europa.eu/distribution/v2/countries/"
    "geojson/CNTR_RG_60M_2024_4326.geojson"
)

EU27 = {
    "AT":"Austria", "BE":"Belgium", "BG":"Bulgaria", "HR":"Croatia",
    "CY":"Cyprus", "CZ":"Czechia", "DK":"Denmark", "EE":"Estonia",
    "FI":"Finland", "FR":"France", "DE":"Germany", "EL":"Greece",
    "HU":"Hungary", "IE":"Ireland", "IT":"Italy", "LV":"Latvia",
    "LT":"Lithuania", "LU":"Luxembourg", "MT":"Malta", "NL":"Netherlands",
    "PL":"Poland", "PT":"Portugal", "RO":"Romania", "SK":"Slovakia",
    "SI":"Slovenia", "ES":"Spain", "SE":"Sweden",
}

# ============================================================
# DATA
# ============================================================

@st.cache_data
def load_data():
    master = pd.read_csv(MASTER_FILE)
    intelligence = pd.read_csv(INTELLIGENCE_FILE)
    master["year"] = master["year"].astype(int)
    return master, intelligence


@st.cache_data(ttl=86400)
def load_eu_geojson():
    response = requests.get(EUROSTAT_MAP_URL, timeout=60)
    response.raise_for_status()
    return response.json()


def geo_id_key(geojson):
    feature = geojson.get("features", [])[0]
    props = feature.get("properties", {})
    for candidate in ["CNTR_ID", "CNTR_CODE", "ISO2", "id"]:
        if candidate in props:
            return f"properties.{candidate}"
    return None


def ensure_datasets():
    """Build processed Eurostat datasets automatically when deploying fresh."""
    if MASTER_FILE.exists() and INTELLIGENCE_FILE.exists():
        return
    try:
        from scripts import rebuild_project
        st.info("Preparing the EU analysis datasets from Eurostat. This may take a moment on first launch...")
        # Import executes the repository's deterministic rebuild script.
        _ = rebuild_project
    except Exception as exc:
        raise RuntimeError(f"Could not build the EU datasets automatically: {exc}") from exc


try:
    ensure_datasets()
    master, intelligence = load_data()
except Exception as exc:
    st.error(f"Dataset preparation failed: {exc}")
    st.stop()

# ============================================================
# HEADER
# ============================================================

st.title("🌍 EU 4D Economic Intelligence")
st.caption(
    "Geographic, temporal, economic and intelligence analysis of 27 EU countries, 2020–2025."
)

# ============================================================
# CONTROLS
# ============================================================

st.sidebar.title("🎛️ Dashboard Controls")

years = sorted(master["year"].unique())
selected_year = st.sidebar.select_slider(
    "Analysis year",
    options=years,
    value=years[-1],
)

metric_options = {
    "Economic Score": "economic_score",
    "GDP Growth": "gdp_growth_pct",
    "GDP per Capita PPS": "gdp_per_capita_pps",
    "Inflation": "inflation_pct",
    "Opportunity Score": "opportunity_score",
    "Risk Score": "risk_score",
    "Resilience Score": "resilience_score",
}

selected_metric_label = st.sidebar.selectbox(
    "Map metric",
    list(metric_options.keys()),
)
selected_metric = metric_options[selected_metric_label]

countries = sorted(master["country"].unique())
selected_country = st.sidebar.selectbox(
    "Country profile",
    countries,
)

# ============================================================
# DATA VIEWS
# ============================================================

year_data = master[master["year"] == selected_year].copy()
country_data = master[master["country"] == selected_country].sort_values("year")
profile = intelligence[intelligence["country"] == selected_country].iloc[0]

# Merge intelligence scores into selected-year country data.
map_data = year_data.merge(
    intelligence,
    on="country",
    how="left",
    suffixes=("", "_intel"),
)

# ============================================================
# TOP OVERVIEW KPIs
# ============================================================

avg_growth = year_data["gdp_growth_pct"].mean()
avg_inflation = year_data["inflation_pct"].mean()
avg_pps = year_data["gdp_per_capita_pps"].mean()
best_country = intelligence.sort_values("economic_score", ascending=False).iloc[0]
best_opportunity = intelligence.sort_values("opportunity_score", ascending=False).iloc[0]
lowest_risk = intelligence.sort_values("risk_score", ascending=True).iloc[0]

k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("EU Countries", "27")
k2.metric("Observations", f"{len(master):,}")
k3.metric("Avg GDP Growth", f"{avg_growth:.2f}%")
k4.metric("Avg Inflation", f"{avg_inflation:.2f}%")
k5.metric("Avg GDP/Capita PPS", f"{avg_pps:,.0f}")
k6.metric("Top Economy", best_country["country"])

st.divider()

# ============================================================
# MAIN GEOGRAPHIC OVERVIEW
# ============================================================

st.header(f"🗺️ EU Economic Map — {selected_year}")
st.write(
    f"Geographic view of **{selected_metric_label}**. Hover over a country to inspect its economic indicators."
)

try:
    geojson = load_eu_geojson()
    feature_key = geo_id_key(geojson)

    if feature_key:
        fig = px.choropleth(
            map_data,
            geojson=geojson,
            locations="geo",
            featureidkey=feature_key,
            color=selected_metric,
            hover_name="country",
            hover_data={
                "geo": False,
                "gdp_growth_pct": ":.2f",
                "gdp_per_capita_pps": ":,.0f",
                "inflation_pct": ":.2f",
                "economic_score": ":.1f",
                "opportunity_score": ":.1f",
                "risk_score": ":.1f",
                "resilience_score": ":.1f",
                selected_metric: False,
            },
            labels={
                "gdp_growth_pct": "GDP growth %",
                "gdp_per_capita_pps": "GDP per capita PPS",
                "inflation_pct": "Inflation %",
                "economic_score": "Economic score",
                "opportunity_score": "Opportunity",
                "risk_score": "Risk",
                "resilience_score": "Resilience",
            },
            color_continuous_scale="RdYlGn",
            projection="mercator",
        )
        fig.update_geos(
            fitbounds="locations",
            visible=False,
            bgcolor="rgba(0,0,0,0)",
        )
        fig.update_layout(
            height=620,
            margin=dict(l=0, r=0, t=10, b=0),
            coloraxis_colorbar_title=selected_metric_label,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})
    else:
        st.warning("Could not identify the country-code field in the Eurostat GISCO geometry.")
except Exception as exc:
    st.warning(f"Map could not be loaded: {exc}")
    st.info("The analytical dashboard remains available below.")

# ============================================================
# SNAPSHOT / RANKINGS
# ============================================================

st.header("🏆 EU Economic Snapshot")

r1, r2, r3 = st.columns(3)

with r1:
    st.subheader("🏅 Strongest Economic Score")
    st.metric(best_country["country"], f"{best_country['economic_score']:.1f}/100")

with r2:
    st.subheader("🚀 Highest Opportunity")
    st.metric(best_opportunity["country"], f"{best_opportunity['opportunity_score']:.1f}/100")

with r3:
    st.subheader("🛡️ Lowest Risk")
    st.metric(lowest_risk["country"], f"{lowest_risk['risk_score']:.1f}/100")

rank1, rank2 = st.columns(2)

with rank1:
    st.subheader("Top 10 Economic Scores")
    top10 = intelligence[
        ["country", "economic_score", "economic_rank"]
    ].sort_values("economic_rank").head(10)
    st.dataframe(top10, use_container_width=True, hide_index=True)

with rank2:
    st.subheader("Top 10 Opportunities")
    opportunity = intelligence[
        ["country", "opportunity_score", "opportunity_rank"]
    ].sort_values("opportunity_rank").head(10)
    st.dataframe(opportunity, use_container_width=True, hide_index=True)

# ============================================================
# 4D ANALYTICS
# ============================================================

st.header("📊 4D Economic Analytics")

analytics_tab1, analytics_tab2, analytics_tab3, analytics_tab4 = st.tabs([
    "⏳ Time", "🌍 Country", "💼 Opportunity", "⚠️ Risk & Resilience"
])

with analytics_tab1:
    st.subheader(f"Economic trajectory — {selected_country}")
    time_fig = px.line(
        country_data,
        x="year",
        y=["gdp_growth_pct", "inflation_pct"],
        markers=True,
        labels={"value": "Percent", "variable": "Indicator"},
        title="GDP Growth vs Inflation",
    )
    st.plotly_chart(time_fig, use_container_width=True)

with analytics_tab2:
    st.subheader("Country economic profile")
    profile_cols = [
        "growth_score", "prosperity_score", "price_stability_score",
        "resilience_score", "economic_score"
    ]
    profile_long = pd.DataFrame({
        "Indicator": profile_cols,
        "Score": [float(profile[c]) for c in profile_cols],
    })
    radar = px.bar(
        profile_long,
        x="Indicator",
        y="Score",
        range_y=[0, 100],
        title=f"{selected_country} — Intelligence Profile",
    )
    st.plotly_chart(radar, use_container_width=True)

with analytics_tab3:
    st.subheader("Opportunity landscape")
    opp_fig = px.scatter(
        intelligence,
        x="prosperity_score",
        y="growth_score",
        size="opportunity_score",
        hover_name="country",
        color="opportunity_score",
        labels={
            "prosperity_score": "Prosperity score",
            "growth_score": "Growth score",
            "opportunity_score": "Opportunity score",
        },
        title="Growth vs Prosperity — Opportunity Mapping",
    )
    st.plotly_chart(opp_fig, use_container_width=True)

with analytics_tab4:
    st.subheader("Risk vs resilience")
    risk_fig = px.scatter(
        intelligence,
        x="risk_score",
        y="resilience_score",
        size="economic_score",
        hover_name="country",
        color="economic_score",
        labels={
            "risk_score": "Risk score",
            "resilience_score": "Resilience score",
            "economic_score": "Economic score",
        },
        title="Risk vs Resilience",
    )
    st.plotly_chart(risk_fig, use_container_width=True)

# ============================================================
# COUNTRY PROFILE
# ============================================================

st.header(f"🇪🇺 Country Intelligence Profile — {selected_country}")

p1, p2, p3, p4 = st.columns(4)
p1.metric("Economic Score", f"{profile['economic_score']:.1f}")
p2.metric("Opportunity", f"{profile['opportunity_score']:.1f}")
p3.metric("Risk", f"{profile['risk_score']:.1f}")
p4.metric("Resilience", f"{profile['resilience_score']:.1f}")

st.dataframe(
    country_data[
        ["year", "gdp_growth_pct", "gdp_per_capita_pps", "inflation_pct"]
    ].rename(columns={
        "year": "Year",
        "gdp_growth_pct": "GDP Growth %",
        "gdp_per_capita_pps": "GDP per Capita PPS",
        "inflation_pct": "Inflation %",
    }),
    use_container_width=True,
    hide_index=True,
)

# ============================================================
# METHODOLOGY
# ============================================================

with st.expander("📚 Methodology & Data Sources"):
    st.markdown(
        """
        **Coverage:** 27 EU Member States, annual observations from 2020–2025.

        **Primary source:** Eurostat official statistics API.

        **Indicators:**
        - Real GDP growth (%)
        - GDP per capita in PPS (EU27=100)
        - HICP inflation (%)

        **Composite intelligence scores:**
        - Growth score: min-max normalized average GDP growth.
        - Prosperity score: min-max normalized average GDP per capita PPS.
        - Price stability score: inverse min-max normalized average inflation.
        - Resilience score: inverse min-max normalized GDP-growth volatility.
        - Opportunity score = 40% growth + 35% prosperity + 25% price stability.
        - Economic score = 30% growth + 25% prosperity + 20% price stability + 25% resilience.
        - Risk score = 55% inverse growth + 45% inverse price stability.

        Scores are analytical constructs for comparative intelligence and are not official Eurostat measures.
        """
    )

st.caption("Built with Python, Pandas, Plotly, Requests and Streamlit. Data source: Eurostat.")
