import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

API = "http://127.0.0.1:8000"
CITIES = {"New Delhi": (28.61, 77.21), "Jaipur": (26.91, 75.79),
          "Mumbai": (19.08, 72.88), "Bengaluru": (12.97, 77.59),
          "Chennai": (13.08, 80.27)}
SEV = {"NORMAL": "#15803d", "LOW": "#a16207", "MEDIUM": "#c2410c", "HIGH": "#b91c1c"}
BRAND_A, BRAND_B = "Panel", "Watch"
BRAND = BRAND_A + BRAND_B

st.set_page_config(page_title=f"{BRAND} | Panel Performance", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stApp {font-family: 'Inter', sans-serif;}
#MainMenu, footer {visibility: hidden;}
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}
[data-testid="stAppViewContainer"] {padding-top: 0 !important;}
[data-testid="stMain"], [data-testid="stMainBlockContainer"], .block-container {padding-top: 0 !important; margin-top: 0 !important;}
.stApp {background: #ffffff;}
.block-container {max-width: 100%; padding: 0 2.5rem 2rem 2.5rem !important;}

.nav {background: #000000; margin: 0 -2.5rem 28px -2.5rem; padding: 20px 2.5rem;
      display: flex; justify-content: space-between; align-items: center;margin-top: -1rem;}
.brand {font-size: 22px; font-weight: 700; color: #ffffff; letter-spacing: -0.02em;}
.brand span {color: #9ca3af;}
.nav-right {font-size: 13px; color: #d1d5db; display: flex; align-items: center; gap: 8px;}
.dot {width: 8px; height: 8px; border-radius: 50%; background: #22c55e; display: inline-block;}

.h1 {font-size: 26px; font-weight: 700; color: #111827; letter-spacing: -0.02em;}
.sub {font-size: 14px; color: #6b7280; margin: 4px 0 22px 0;}

.card {background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px;
       padding: 20px 22px; height: 100%;}
.label {font-size: 12px; font-weight: 500; color: #6b7280; margin-bottom: 10px;}
.value {font-size: 30px; font-weight: 600; color: #111827; letter-spacing: -0.02em;}
.note {font-size: 12px; color: #6b7280; margin-top: 6px;}
.advice {font-size: 15px; color: #1f2937; line-height: 1.65;}
.badge {display: inline-block; padding: 5px 14px; border-radius: 999px;
        font-size: 13px; font-weight: 600; letter-spacing: 0.04em;}
.type {font-size: 13px; color: #6b7280; margin-top: 12px;}

[data-testid="stVerticalBlockBorderWrapper"] {background: #ffffff;
        border: 1px solid #e5e7eb !important; border-radius: 12px;}
[data-testid="stPlotlyChart"] {background: #ffffff; border: 1px solid #e5e7eb;
        border-radius: 12px; padding: 10px;}
label, .stCheckbox p {color: #374151 !important; font-size: 13px !important;}

.foot {border-top: 1px solid #e5e7eb; margin-top: 36px; padding-top: 16px;
       font-size: 12px; color: #6b7280; display: flex; justify-content: space-between;}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=600)
def get_report(city, days, pm10, rain3, kw):
    lat, lon = CITIES[city]
    params = dict(lat=lat, lon=lon, system_kw=kw, days_since_clean=days)
    if pm10 is not None:
        params["pm10"] = pm10
    if rain3 is not None:
        params["rain_next3"] = rain3
    resp = requests.get(f"{API}/report", params=params, timeout=90)
    if resp.status_code != 200:
        raise RuntimeError(resp.text[:300])
    return resp.json()


def kpi(label, value, note=""):
    return (f"<div class='card'><div class='label'>{label}</div>"
            f"<div class='value'>{value}</div><div class='note'>{note}</div></div>")


# ---------- header bar ----------
st.markdown(
    f"<div class='nav'><div class='brand'>{BRAND_A}<span>{BRAND_B}</span></div>"
    f"<div class='nav-right'><span class='dot'></span>Live weather connected</div></div>",
    unsafe_allow_html=True)

st.markdown("<div class='h1'>Panel performance overview</div>"
            "<div class='sub'>Estimate soiling loss, forecast it, and get a maintenance "
            "recommendation.</div>", unsafe_allow_html=True)

# ---------- inputs ----------
with st.container(border=True):
    i1, i2, i3 = st.columns(3)
    city = i1.selectbox("Location", list(CITIES))
    days = i2.slider("Days since last cleaning", 0, 60, 14)
    kw = i3.number_input("System size (kW)", 1.0, 5000.0, 100.0)
    manual = st.checkbox("Run a what-if scenario (set dust and rain manually)")
    pm10 = rain3 = None
    if manual:
        m1, m2 = st.columns(2)
        pm10 = m1.slider("Dust level, PM10 (µg/m³)", 0, 300, 100)
        rain3 = m2.slider("Rain expected in next 3 days (mm)", 0, 30, 0)

try:
    r = get_report(city, days, pm10, rain3, kw)
except Exception as e:
    st.error(f"Could not get the report: {e}")
    st.stop()

a = r["assessment"]
color = SEV[a["severity"]]
st.write("")

# ---------- status and recommendation ----------
c1, c2 = st.columns([1, 2])
c1.markdown(
    f"<div class='card'><div class='label'>Current status</div>"
    f"<span class='badge' style='background:{color}1a; color:{color};'>{a['severity']}</span>"
    f"<div class='type'>{a['type'].title()}</div></div>", unsafe_allow_html=True)
c2.markdown(
    f"<div class='card'><div class='label'>Recommended action</div>"
    f"<div class='advice'>{a['advice']}</div></div>", unsafe_allow_html=True)
st.write("")

# ---------- key numbers ----------
k = st.columns(4)
k[0].markdown(kpi("Power loss now", f"{a['loss_pct']:.1f}%", "Compared with a clean panel"),
              unsafe_allow_html=True)
k[1].markdown(kpi("Forecast, 3 days", f"{a['forecast_3d_pct']:.1f}%",
                  f"Rain expected: {r['rain_next3_mm']:.0f} mm"), unsafe_allow_html=True)
k[2].markdown(kpi("Forecast, 7 days", f"{a['forecast_7d_pct']:.1f}%",
                  f"Rain expected: {r['rain_next7_mm']:.0f} mm"), unsafe_allow_html=True)
k[3].markdown(kpi("Revenue lost per day", f"₹{a['money_per_day']:,.0f}",
                  f"Dust level: {r['pm10_recent']:.0f} µg/m³"), unsafe_allow_html=True)
st.write("")

# ---------- chart ----------
h = pd.DataFrame(r["history"])
last = pd.to_datetime(h["date"].iloc[-1])

fig = go.Figure()
fig.add_trace(go.Scatter(x=h["date"], y=h["loss_pct"], mode="lines+markers",
                         name="Measured loss", line=dict(color="#2563eb", width=3),
                         marker=dict(size=6)))
fig.add_trace(go.Scatter(
    x=[last, last + pd.Timedelta(days=3), last + pd.Timedelta(days=7)],
    y=[a["loss_pct"], a["forecast_3d_pct"], a["forecast_7d_pct"]],
    mode="lines+markers", name="Forecast",
    line=dict(color="#ea580c", width=3, dash="dash")))
for y, name in [(3, "Low"), (8, "Medium"), (15, "High")]:
    fig.add_hline(y=y, line_dash="dot", line_color="#9ca3af",
                  annotation_text=name, annotation_position="top left",
                  annotation_font_color="#6b7280")
fig.update_layout(
    title=dict(text="Power loss trend and forecast", font=dict(size=16, color="#111827")),
    yaxis_title="Loss (%)", height=400, dragmode=False,
    plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
    font=dict(color="#374151", family="Inter"),
    margin=dict(l=40, r=20, t=60, b=40),
    legend=dict(orientation="h", y=1.12, x=1, xanchor="right"))
fig.update_xaxes(showgrid=False, linecolor="#e5e7eb")
fig.update_yaxes(gridcolor="#eef0f3", rangemode="tozero")
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ---------- footer ----------
st.markdown(
    f"<div class='foot'><div>{BRAND} · Solar power loss forecasting and predictive "
    f"maintenance</div><div>Data up to {r['as_of']} · Weather and dust: Open-Meteo · "
    f"Panel readings: simulated · Money assumes ₹6 per kWh and ₹500 per cleaning</div></div>",
    unsafe_allow_html=True)