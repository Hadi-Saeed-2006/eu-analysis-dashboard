from pathlib import Path
import requests
import pandas as pd
import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
PROCESSED = PROJECT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

COUNTRIES = {
    "AT":"Austria","BE":"Belgium","BG":"Bulgaria","HR":"Croatia","CY":"Cyprus","CZ":"Czechia","DK":"Denmark","EE":"Estonia","FI":"Finland","FR":"France","DE":"Germany","EL":"Greece","HU":"Hungary","IE":"Ireland","IT":"Italy","LV":"Latvia","LT":"Lithuania","LU":"Luxembourg","MT":"Malta","NL":"Netherlands","PL":"Poland","PT":"Portugal","RO":"Romania","SK":"Slovakia","SI":"Slovenia","ES":"Spain","SE":"Sweden"
}
GEOS = list(COUNTRIES)
YEARS = list(range(2020, 2026))


def get_json(url, params):
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def parse_json(data, value_name):
    ids = data["id"]
    sizes = data["size"]
    labels = {}
    for dim in ids:
        category = data["dimension"][dim]["category"]
        ordered = sorted(category.get("index", {}).items(), key=lambda x: x[1])
        labels[dim] = [code for code, _ in ordered]

    def decode(flat):
        coords = []
        n = int(flat)
        for size in reversed(sizes):
            coords.append(n % size)
            n //= size
        return list(reversed(coords))

    rows = []
    for flat, value in data.get("value", {}).items():
        coords = decode(flat)
        row = {dim: labels[dim][coords[i]] for i, dim in enumerate(ids)}
        row[value_name] = value
        rows.append(row)
    return pd.DataFrame(rows)


def fetch_metric(url, params, value_name):
    df = parse_json(get_json(url, params), value_name)
    df["year"] = df["time"].astype(int)
    df[value_name] = pd.to_numeric(df[value_name])
    return df[["geo", "year", value_name]]


gdp = fetch_metric(
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10_gdp",
    {"freq":"A","unit":"CLV_PCH_PRE","na_item":"B1GQ","geo":GEOS,"sinceTimePeriod":"2020","untilTimePeriod":"2025"},
    "gdp_growth_pct",
)

pc = fetch_metric(
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10_pc",
    {"freq":"A","unit":"CP_PPS_EU27_2020_HAB","na_item":"B1GQ","geo":GEOS,"sinceTimePeriod":"2020","untilTimePeriod":"2025"},
    "gdp_per_capita_pps",
)

inflation = fetch_metric(
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_aind",
    {"lang":"en","freq":"A","unit":"RCH_A_AVG","coicop":"CP00","geo":GEOS,"sinceTimePeriod":"2020","untilTimePeriod":"2025"},
    "inflation_pct",
)

master = gdp.merge(pc, on=["geo","year"]).merge(inflation, on=["geo","year"])
master["country"] = master["geo"].map(COUNTRIES)
master = master[["country","geo","year","gdp_growth_pct","gdp_per_capita_pps","inflation_pct"]].sort_values(["country","year"]).reset_index(drop=True)

assert len(master) == 162
assert master["country"].nunique() == 27
assert set(master["year"]) == set(YEARS)
assert master.isna().sum().sum() == 0

master.to_csv(PROCESSED / "eu_economic_master_2020_2025.csv", index=False)
master.to_csv(PROCESSED / "economic_timeline_data.csv", index=False)

summary = master.groupby("year").agg(
    countries=("country","nunique"),
    avg_gdp_growth_pct=("gdp_growth_pct","mean"),
    avg_gdp_per_capita_pps=("gdp_per_capita_pps","mean"),
    avg_inflation_pct=("inflation_pct","mean"),
).reset_index()
summary.to_csv(PROCESSED / "r16_time_dimension_summary.csv", index=False)

country_stats = master.groupby("country").agg(
    avg_growth=("gdp_growth_pct","mean"),
    avg_inflation=("inflation_pct","mean"),
    avg_pps=("gdp_per_capita_pps","mean"),
).reset_index()

def minmax(s):
    if s.max() == s.min():
        return pd.Series(np.full(len(s), 50.0), index=s.index)
    return (s - s.min()) / (s.max() - s.min()) * 100

country_stats["growth_score"] = minmax(country_stats["avg_growth"])
country_stats["prosperity_score"] = minmax(country_stats["avg_pps"])
country_stats["price_stability_score"] = 100 - minmax(country_stats["avg_inflation"])
country_stats["risk_score"] = 0.55 * (100-country_stats["growth_score"]) + 0.45 * (100-country_stats["price_stability_score"])
country_stats["opportunity_score"] = 0.40*country_stats["growth_score"] + 0.35*country_stats["prosperity_score"] + 0.25*country_stats["price_stability_score"]
volatility = master.groupby("country")["gdp_growth_pct"].std().fillna(0)
country_stats["growth_volatility"] = country_stats["country"].map(volatility)
country_stats["resilience_score"] = 100 - minmax(country_stats["growth_volatility"])
country_stats["economic_score"] = 0.30*country_stats["growth_score"] + 0.25*country_stats["prosperity_score"] + 0.20*country_stats["price_stability_score"] + 0.25*country_stats["resilience_score"]
country_stats["economic_rank"] = country_stats["economic_score"].rank(ascending=False, method="min").astype(int)
country_stats["opportunity_rank"] = country_stats["opportunity_score"].rank(ascending=False, method="min").astype(int)
country_stats["risk_rank"] = country_stats["risk_score"].rank(ascending=True, method="min").astype(int)

score_cols = ["growth_score","prosperity_score","price_stability_score","risk_score","opportunity_score","resilience_score","economic_score"]
country_stats[score_cols] = country_stats[score_cols].round(2)
country_stats.to_csv(PROCESSED / "country_economic_intelligence.csv", index=False)

print("Recovery complete:", len(master), "rows", master["country"].nunique(), "countries", sorted(master["year"].unique()))
