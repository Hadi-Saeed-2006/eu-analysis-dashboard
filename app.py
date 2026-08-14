import streamlit as st
import pandas as pd
from pathlib import Path

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

@st.cache_data
def load_data():
    master = pd.read_csv(MASTER_FILE)
    intelligence = pd.read_csv(INTELLIGENCE_FILE)
    master["year"] = master["year"].astype(int)
    return master, intelligence

st.title("🌍 EU 4D Economic Intelligence")
st.caption("A six-year economic intelligence dashboard covering 27 EU countries from 2020–2025.")

try:
    master, intelligence = load_data()
except FileNotFoundError:
    st.error("Dataset files are missing. Run the Eurostat recovery script in `scripts/recover_data.py` first.")
    st.stop()

st.sidebar.title("Dashboard Controls")
countries = sorted(master["country"].unique())
selected_country = st.sidebar.selectbox("Country", countries)
years = sorted(master["year"].unique())
selected_year = st.sidebar.selectbox("Year", years, index=len(years) - 1)

country_data = master[master["country"] == selected_country].sort_values("year")
current = country_data[country_data["year"] == selected_year].iloc[0]
profile = intelligence[intelligence["country"] == selected_country].iloc[0]

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("GDP Growth", f"{current['gdp_growth_pct']:.2f}%")
with c2:
    st.metric("GDP per Capita PPS", f"{current['gdp_per_capita_pps']:,.1f}")
with c3:
    st.metric("Inflation", f"{current['inflation_pct']:.2f}%")
with c4:
    st.metric("Economic Score", f"{profile['economic_score']:.1f}/100")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["⏳ Time", "🌍 Countries", "📊 Economy", "🧠 Intelligence"])

with tab1:
    st.subheader(f"{selected_country} — Economic Timeline")
    timeline = country_data.set_index("year")[["gdp_growth_pct", "gdp_per_capita_pps", "inflation_pct"]]
    st.line_chart(timeline)
    st.dataframe(country_data, use_container_width=True, hide_index=True)

with tab2:
    st.subheader(f"EU Country Comparison — {selected_year}")
    comparison = master[master["year"] == selected_year].copy()
    metric = st.selectbox(
        "Compare countries by",
        ["gdp_growth_pct", "gdp_per_capita_pps", "inflation_pct"],
        key="comparison_metric",
    )
    comparison = comparison.sort_values(metric, ascending=False)
    st.bar_chart(comparison.set_index("country")[[metric]])
    st.dataframe(
        comparison[["country", "gdp_growth_pct", "gdp_per_capita_pps", "inflation_pct"]],
        use_container_width=True,
        hide_index=True,
    )

with tab3:
    st.subheader("EU Economic Performance")
    eu_year = master.groupby("year").agg(
        avg_growth=("gdp_growth_pct", "mean"),
        avg_pps=("gdp_per_capita_pps", "mean"),
        avg_inflation=("inflation_pct", "mean"),
    )
    e1, e2 = st.columns(2)
    with e1:
        st.write("Average EU GDP Growth")
        st.line_chart(eu_year[["avg_growth"]])
    with e2:
        st.write("Average EU Inflation")
        st.line_chart(eu_year[["avg_inflation"]])
    st.write("Average GDP per Capita PPS")
    st.line_chart(eu_year[["avg_pps"]])

with tab4:
    st.subheader(f"🧠 Intelligence Profile — {selected_country}")
    i1, i2, i3, i4 = st.columns(4)
    with i1:
        st.metric("Economic Score", f"{profile['economic_score']:.1f}")
    with i2:
        st.metric("Opportunity", f"{profile['opportunity_score']:.1f}")
    with i3:
        st.metric("Risk", f"{profile['risk_score']:.1f}")
    with i4:
        st.metric("Resilience", f"{profile['resilience_score']:.1f}")

    st.divider()
    scores = pd.DataFrame({
        "Indicator": ["Growth", "Prosperity", "Price Stability", "Resilience"],
        "Score": [
            profile["growth_score"],
            profile["prosperity_score"],
            profile["price_stability_score"],
            profile["resilience_score"],
        ],
    })
    st.bar_chart(scores.set_index("Indicator"))

    st.subheader("EU Economic Ranking")
    ranking = intelligence[[
        "country", "economic_score", "opportunity_score",
        "risk_score", "resilience_score", "economic_rank"
    ]].sort_values("economic_rank")
    st.dataframe(ranking, use_container_width=True, hide_index=True)

st.divider()
st.caption("EU 4D Economic Intelligence • Data period: 2020–2025 • 27 countries • Python, Pandas and Streamlit")
