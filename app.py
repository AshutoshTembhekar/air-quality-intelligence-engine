"""Interactive Air Quality Environmental Intelligence Dashboard."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# Configure modern layout
st.set_page_config(
    page_title="AirPulse | Environmental Intelligence Engine",
    page_icon="🍃",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom enterprise UI CSS styling
st.markdown(
    """
<style>
    .main { background-color: #0e1117; }
    .metric-card {
        background-color: #1a1f29;
        border-radius: 10px;
        padding: 20px;
        border: 1px solid #2d3748;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .status-badge {
        font-size: 1.1rem;
        font-weight: 700;
        padding: 6px 14px;
        border-radius: 20px;
        display: inline-block;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Header
st.title("🍃 AirPulse: Multi-Pollutant Environmental Intelligence Platform")
st.markdown(
    "Real-time CPCB/NAAQS-compliant Sub-Index calculation, dominant toxic driver detection, and dynamic health advisory engine."
)

API_ENDPOINT = "http://127.0.0.1:8000/api/v1/aqi/calculate"

# --- Sidebar Parameter Controls ---
st.sidebar.header("🔬 Sensor Telemetry Controls")
st.sidebar.markdown("Adjust continuous pollutant concentrations:")

pm25_val = st.sidebar.slider("PM2.5 (µg/m³)", 0.0, 250.0, 54.7, step=0.5)
pm10_val = st.sidebar.slider("PM10 (µg/m³)", 0.0, 350.0, 84.7, step=1.0)
no2_val = st.sidebar.slider("NO2 (µg/m³)", 0.0, 200.0, 42.4, step=0.5)
so2_val = st.sidebar.slider("SO2 (µg/m³)", 0.0, 100.0, 11.5, step=0.2)
co_val = st.sidebar.slider("CO (mg/m³)", 0.0, 15.0, 2.18, step=0.05)

with st.sidebar.expander("Secondary Atmospheric Inputs (Informational)"):
    nox_val = st.number_input("NOx (ppb)", 0.0, 300.0, 91.8)
    voc_val = st.number_input("VOCs (ppb)", 0.0, 300.0, 112.2)
    co2_val = st.number_input("CO2 (ppm)", 300.0, 600.0, 439.3)
    temp_val = st.number_input("Temperature (°C)", 10.0, 45.0, 30.5)

# --- Compute Engine Integration ---
payload = {
    "pm25": pm25_val,
    "pm10": pm10_val,
    "no2": no2_val,
    "so2": so2_val,
    "co": co_val,
    "nox": nox_val,
    "vocs": voc_val,
    "co2": co2_val,
    "temperature": temp_val,
}

# Fallback internal calculation if API is offline
try:
    response = requests.post(API_ENDPOINT, json=payload, timeout=2)
    if response.status_code == 200:
        result = response.json()
    else:
        st.error("API Error encountered. Defaulting to local compute engine.")
        raise Exception("API status error")
except Exception:
    # Local fallback
    def calc_si(c, bps):
        for blo, bhi, ilo, ihi in bps:
            if blo <= c <= bhi:
                return ((ihi - ilo) / (bhi - blo)) * (c - blo) + ilo
        return 400.0

    bp_pm25 = [
        (0, 30, 0, 50),
        (30.1, 60, 51, 100),
        (60.1, 90, 101, 200),
        (90.1, 120, 201, 300),
        (120.1, 250, 301, 400),
    ]
    bp_pm10 = [
        (0, 50, 0, 50),
        (50.1, 100, 51, 100),
        (100.1, 250, 101, 200),
        (250.1, 350, 201, 300),
    ]
    bp_no2 = [
        (0, 40, 0, 50),
        (40.1, 80, 51, 100),
        (80.1, 180, 101, 200),
        (180.1, 280, 201, 300),
    ]
    bp_so2 = [(0, 40, 0, 50), (40.1, 80, 51, 100), (80.1, 380, 101, 200)]
    bp_co = [(0, 1.0, 0, 50), (1.01, 2.0, 51, 100), (2.01, 10.0, 101, 200)]
    sub_indices = {
        "PM2.5": round(calc_si(pm25_val, bp_pm25), 1),
        "PM10": round(calc_si(pm10_val, bp_pm10), 1),
        "NO2": round(calc_si(no2_val, bp_no2), 1),
        "SO2": round(calc_si(so2_val, bp_so2), 1),
        "CO": round(calc_si(co_val, bp_co), 1),
    }
    dom = max(sub_indices, key=sub_indices.get)
    overall = max(sub_indices.values())
    cat = (
        "Moderate"
        if overall <= 200
        else "Poor"
        if overall <= 300
        else "Very Poor"
    )
    result = {
        "overall_aqi": overall,
        "category": cat,
        "dominant_pollutant": dom,
        "sub_indices": sub_indices,
        "color_hex": "#e67e22",
        "health_advisory": "Breathing discomfort to people with lung disease.",
        "actionable_guidance": "Reduce prolonged outdoor exertion.",
    }

# --- Layout Grid ---
col_gauge, col_info = st.columns([1.2, 1])

with col_gauge:
    # Plotly Radial Gauge Dial
    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=result["overall_aqi"],
            domain={"x": [0, 1], "y": [0, 1]},
            title={
                "text": f"<b>AQI: {result['category'].upper()}</b>",
                "font": {"size": 22, "color": result["color_hex"]},
            },
            gauge={
                "axis": {"range": [0, 500], "tickwidth": 1, "tickcolor": "white"},
                "bar": {"color": result["color_hex"], "thickness": 0.3},
                "steps": [
                    {"range": [0, 50], "color": "rgba(46, 204, 113, 0.2)"},
                    {"range": [50, 100], "color": "rgba(241, 196, 15, 0.2)"},
                    {"range": [100, 200], "color": "rgba(230, 126, 34, 0.2)"},
                    {"range": [200, 300], "color": "rgba(231, 76, 60, 0.2)"},
                    {"range": [300, 400], "color": "rgba(142, 68, 173, 0.2)"},
                    {"range": [400, 500], "color": "rgba(127, 29, 29, 0.2)"},
                ],
                "threshold": {
                    "line": {"color": "white", "width": 4},
                    "thickness": 0.8,
                    "value": result["overall_aqi"],
                },
            },
        )
    )
    fig_gauge.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
        height=360,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_info:
    st.markdown("### 🚨 Operational Advisory & Attribution")
    st.markdown(
        f"""
    <div style="background-color: #1a1f29; padding: 20px; border-radius: 10px; border-left: 6px solid {result['color_hex']};">
        <h3 style="margin-top:0; color:{result['color_hex']}">{result['category']} Air Quality</h3>
        <p style="font-size: 1.1rem; margin-bottom: 5px;"><b>Dominant Toxic Driver:</b> <span style="background-color:#2d3748; padding:3px 8px; border-radius:4px;">{result['dominant_pollutant']}</span></p>
        <p><b>Health Impact:</b> {result['health_advisory']}</p>
        <p><b>Recommended Action:</b> {result['actionable_guidance']}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.write("")
    c1, c2 = st.columns(2)
    c1.metric("Current PM2.5", f"{pm25_val} µg/m³")
    c2.metric("Dominant Sub-Index", f"{result['sub_indices'][result['dominant_pollutant']]}")

# --- Sub-Index Comparative Horizontal Bar Chart ---
st.markdown("---")
st.subheader("📊 Individual Pollutant Sub-Index Breakdown")

df_si = pd.DataFrame(
    list(result["sub_indices"].items()), columns=["Pollutant", "Sub_Index"]
).sort_values(by="Sub_Index", ascending=True)

fig_bar = go.Figure(
    go.Bar(
        x=df_si["Sub_Index"],
        y=df_si["Pollutant"],
        orientation="h",
        marker=dict(
            color=df_si["Sub_Index"],
            colorscale="Viridis",
            showscale=True,
            colorbar=dict(title="Sub-Index"),
        ),
        text=df_si["Sub_Index"].round(1),
        textposition="outside",
    )
)
fig_bar.add_vline(
    x=100, line_dash="dash", line_color="yellow", annotation_text="Acceptable Ceiling (100)"
)
fig_bar.add_vline(
    x=200, line_dash="dash", line_color="red", annotation_text="Unhealthy Threshold (200)"
)
fig_bar.update_layout(
    xaxis_title="Calculated Sub-Index",
    yaxis_title="Pollutant",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font={"color": "white"},
    height=320,
    margin=dict(l=20, r=20, t=30, b=20),
)
st.plotly_chart(fig_bar, use_container_width=True)

# --- Dataset Exploration Tab ---
with st.expander("📁 View Benchmark Sensor Dataset & Correlation Matrix"):
    try:
        raw_df = pd.read_csv("air_quality_dataset.csv")
        st.write(
            f"**Loaded {len(raw_df)} sensor records.** Showing first 10 rows:"
        )
        st.dataframe(raw_df.head(10), use_container_width=True)
    except Exception:
        st.info("Place `air_quality_dataset.csv` in the root folder to view dataset telemetry.")