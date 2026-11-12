import json
import joblib
import numpy as np
import pandas as pd
import requests
from common import FEATURES, make_features
from advisor import advise

model = joblib.load("models/expected_power.pkl")
FEAT = json.load(open("models/baseline.json"))["features"]
forecaster = joblib.load("models/forecaster.pkl")
NOISE = float(pd.read_csv("data/daily_baseline.csv")["clean_loss"].std())


def _fetch_weather(lat, lon, past=14, future=8):
    w = requests.get("https://api.open-meteo.com/v1/forecast", params=dict(
        latitude=lat, longitude=lon,
        hourly="temperature_2m,shortwave_radiation,precipitation",
        past_days=past, forecast_days=future, timezone="auto"), timeout=30).json()
    a = requests.get("https://air-quality-api.open-meteo.com/v1/air-quality", params=dict(
        latitude=lat, longitude=lon, hourly="pm10",
        past_days=past, forecast_days=1, timezone="auto"), timeout=30).json()
    h = pd.DataFrame(w["hourly"])
    p = pd.DataFrame(a["hourly"])
    h["time"] = pd.to_datetime(h["time"])
    p["time"] = pd.to_datetime(p["time"])
    h = h.merge(p, on="time", how="left")
    h["pm10"] = h["pm10"].interpolate().bfill().ffill()
    h["date"] = h["time"].dt.date
    return h

_cache = {}


def get_weather(lat, lon, past=14, future=8):
    key = (round(lat, 2), round(lon, 2), str(pd.Timestamp.now().floor("h")))
    if key not in _cache:
        _cache[key] = _fetch_weather(lat, lon, past, future)
    return _cache[key].copy()

    
def expected_kw(h):
    _cache = {}

    def get_weather(lat, lon, past=14, future=8):
        key = (round(lat, 2), round(lon, 2), str(pd.Timestamp.now().floor("h")))
        if key not in _cache:
            _cache[key] = _fetch_weather(lat, lon, past, future)
        return _cache[key].copy()
    
    """Model 1: what a CLEAN panel should produce each hour."""
    irr = h["shortwave_radiation"] / 1000          # W/m2 -> kW/m2
    X = pd.DataFrame({
        "irradiation": irr,
        "module_temp": h["temperature_2m"] + 25 * irr,
        "ambient_temp": h["temperature_2m"],
        "hour": h["time"].dt.hour,
    })[FEAT]
    kw = model.predict(X)
    kw[irr.values < 0.1] = 0
    return kw


def build_report(lat, lon, tariff=6.0, clean_cost=500.0, system_kw=100.0,
                 days_since_clean=14, pm10=None, rain_next3=None):
    h = get_weather(lat, lon)
    h["expected"] = expected_kw(h)
    h["expected"] = h["expected"] * system_kw / max(h["expected"].max(), 1e-6)
    today = pd.Timestamp.now().date()

    d = h.groupby("date").agg(expected=("expected", "sum"),
                              rain=("precipitation", "sum"),
                              pm10=("pm10", "mean")).reset_index()
    past = d[d["date"] < today].tail(14).reset_index(drop=True).copy()
    fut = d[d["date"] >= today].reset_index(drop=True)
    if len(past) < 8 or len(fut) < 7:
        raise ValueError("not enough weather data returned")

    if pm10 is not None:                      # manual what-if dust level
        past["pm10"] = float(pm10)

    # ---- simulated panel sensor (replace with real inverter data) ----
    n = len(past)
    clean_i = n - 1 - int(days_since_clean)   # day the panel was last cleaned
    pm_avg = min(float(past["pm10"].mean()), 150)
    s = 0.0
    for _ in range(max(0, -clean_i)):         # dust built up before this window
        s = min(s + 0.001 + 0.00005 * pm_avg, 0.40)
    soil = []
    for i, row in past.iterrows():
        if i == clean_i:
            s = 0.0                           # panel was cleaned this day
        else:
            s += 0.001 + 0.00005 * min(row["pm10"], 150)
            if row["rain"] >= 5:   s *= 0.3
            elif row["rain"] >= 2: s *= 0.7
        soil.append(min(s, 0.40))
    rng = np.random.RandomState(42)
    observed = np.array(soil) + rng.normal(0, NOISE, n)
    past["actual"] = past["expected"] * (1 - observed)
    past["loss"] = 1 - past["actual"] / past["expected"]

    # ---- Model 2: forecast the loss ----
    last7 = past["loss"].values[-7:]
    pm_recent = float(min(past["pm10"].tail(3).mean(), 150))
    rain3 = float(fut["rain"].iloc[:3].sum())
    rain7 = float(fut["rain"].iloc[:7].sum())
    if rain_next3 is not None:                # manual what-if rain
        rain3 = float(rain_next3)
        rain7 = max(rain7, rain3)
    X = pd.DataFrame([make_features(last7, pm_recent, rain3, rain7)], columns=FEATURES)
    now, f3, f7 = [max(0.0, float(x)) for x in forecaster.predict(X)[0]]

    a = advise(last7, now, f3, f7, rain3,
               daily_kwh=float(past["expected"].tail(7).mean()),
               tariff=tariff, clean_cost=clean_cost)
    a.setdefault("forecast_3d_pct", f3 * 100)
    a.setdefault("forecast_7d_pct", f7 * 100)
    a.setdefault("money_next_7d", 0.0)

    history = [dict(date=str(r["date"]), expected_kwh=round(float(r["expected"]), 1),
                    actual_kwh=round(float(r["actual"]), 1),
                    loss_pct=round(float(r["loss"]) * 100, 2),
                    rain_mm=round(float(r["rain"]), 1), pm10=round(float(r["pm10"]), 1))
               for _, r in past.iterrows()]
    return dict(lat=lat, lon=lon, as_of=str(past["date"].iloc[-1]),
                rain_next3_mm=rain3, rain_next7_mm=rain7, pm10_recent=pm_recent,
                assessment=a, history=history)

if __name__ == "__main__":
    r = build_report(28.61, 77.21)          # New Delhi
    print("As of:", r["as_of"], "| PM10:", round(r["pm10_recent"]),
          "| rain next 3 days:", r["rain_next3_mm"], "mm")
    print(r["assessment"])
    for x in r["history"][-7:]:
        print(x["date"], x["loss_pct"], "%")