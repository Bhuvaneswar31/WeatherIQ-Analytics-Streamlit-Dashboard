import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# -----------------------------
# CONFIG
# -----------------------------
API_KEY = "2392d803d7c0a5cd0416390290e72f58"
st.set_page_config(page_title="Weather Dashboard", layout="wide")

# -----------------------------
# SIDEBAR SETTINGS
# -----------------------------
st.sidebar.header("⚙️ Settings")

refresh_minutes = st.sidebar.selectbox(
    "🔄 Refresh Interval (minutes)",
    [30, 60]
)

unit = st.sidebar.radio(
    "🌡️ Temperature Unit",
    ["Celsius (°C)", "Fahrenheit (°F)"]
)

refresh_interval = refresh_minutes * 60
st_autorefresh(interval=refresh_interval * 1000, key="refresh")

# -----------------------------
# HEADER
# -----------------------------
st.title("🌦️ Live Weather Intelligence Dashboard")

current_time = datetime.now().strftime("%d %B %Y, %I:%M:%S %p")
st.markdown(f"📅 **Current Time:** {current_time}")

st.info("ℹ️ Shows real-time current weather + short-term forecast")

# -----------------------------
# CITY SELECTION
# -----------------------------
city = st.selectbox(
    "📍 Select City",
    ["Chennai", "Coimbatore", "Mumbai", "Delhi", "Salem", "Bangalore", "Hyderabad"]
)

coords = {
    "Chennai": (13.0827, 80.2707),
    "Coimbatore": (11.0168, 76.9558),
    "Mumbai": (19.0760, 72.8777),
    "Delhi": (28.7041, 77.1025),
    "Salem": (11.6643, 78.1460),
    "Bangalore": (12.9716, 77.5946),
    "Hyderabad": (17.3850, 78.4867)
}

lat, lon = coords[city]

# -----------------------------
# CACHE FIX
# -----------------------------
if "prev_city" not in st.session_state:
    st.session_state.prev_city = city

if st.session_state.prev_city != city:
    st.cache_data.clear()
    st.session_state.prev_city = city

# -----------------------------
# API FUNCTION
# -----------------------------
@st.cache_data(ttl=60)
def load_data(city, lat, lon):
    try:
        current = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        ).json()

        forecast = requests.get(
            f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric"
        ).json()

        aqi = requests.get(
            f"https://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
        ).json()

        uv = requests.get(
            f"https://api.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lon}&appid={API_KEY}"
        ).json()

    except:
        return {}, {}, {}, {}

    return current, forecast, aqi, uv

# -----------------------------
# LOAD DATA
# -----------------------------
with st.spinner("Loading weather data..."):
    current, forecast, aqi, uv = load_data(city, lat, lon)

# -----------------------------
# ERROR CHECK
# -----------------------------
if "main" not in current:
    st.error("❌ Failed to fetch data. Check API key.")
    st.stop()

# -----------------------------
# UNIT CONVERSION
# -----------------------------
def convert_temp(temp):
    if unit == "Fahrenheit (°F)":
        return (temp * 9/5) + 32
    return temp

unit_symbol = "°F" if "Fahrenheit" in unit else "°C"

# -----------------------------
# WIND DIRECTION
# -----------------------------
def get_wind_direction(deg):
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    ix = int((deg + 22.5) / 45) % 8
    return directions[ix]

# -----------------------------
# UV CATEGORY
# -----------------------------
def uv_category(uvi):
    if uvi <= 2:
        return f"{uvi} (Low)"
    elif uvi <= 5:
        return f"{uvi} (Moderate)"
    elif uvi <= 7:
        return f"{uvi} (High)"
    elif uvi <= 10:
        return f"{uvi} (Very High)"
    else:
        return f"{uvi} (Extreme )"

# -----------------------------
# UV LOGIC (NO FAIL)
# -----------------------------
try:
    uvi = uv.get('current', {}).get('uvi', None)
except:
    uvi = None

if uvi is None:
    clouds = current.get('clouds', {}).get('all', 0)
    temp_raw = current['main']['temp']

    if temp_raw > 35 and clouds < 20:
        uvi = 9
    elif temp_raw > 30 and clouds < 40:
        uvi = 7
    elif temp_raw > 25:
        uvi = 5
    else:
        uvi = 3

    uv_note = " (Estimated)"
else:
    uv_note = ""

uv_display = uv_category(uvi) + uv_note

# -----------------------------
# KPI SECTION
# -----------------------------
st.subheader("📊 Current Conditions")

col1, col2, col3, col4, col5, col6 = st.columns(6)

temp = convert_temp(current['main']['temp'])
feels = convert_temp(current['main']['feels_like'])
humidity = current['main']['humidity']
pressure = current['main']['pressure']
visibility = current.get('visibility', 0) / 1000
condition = current['weather'][0]['description']

wind_speed = current['wind']['speed']
wind_deg = current['wind'].get('deg', 0)
wind_dir = get_wind_direction(wind_deg)

col1.metric("🌡️ Temp", f"{temp:.1f} {unit_symbol}")
col2.metric("🤗 Feels", f"{feels:.1f} {unit_symbol}")
col3.metric("💧 Humidity", f"{humidity}%")
col4.metric("Pressure", f"{pressure} hPa")
col5.metric("👁️ Visibility", f"{visibility:.1f} km")

# ✅ FIXED UV UI (NO TRUNCATION)
with col6:
    st.metric("☀️ UV Index", f"{uvi}")
    st.caption(f"{uv_display}")

st.markdown(f"**🌤️ Condition:** {condition.capitalize()}")
st.markdown(f"🌬️ Wind: {wind_speed} m/s | {wind_dir} ({wind_deg}°)")

# -----------------------------
# AQI
# -----------------------------
aqi_value = aqi.get('list', [{}])[0].get('main', {}).get('aqi', 1)

aqi_map = {
    1: "Good ✅",
    2: "Fair 🙂",
    3: "Moderate ⚠️",
    4: "Poor ❌",
    5: "Very Poor 🚫"
}

st.subheader("🌫️ Air Quality")
st.metric("AQI", f"{aqi_value} - {aqi_map.get(aqi_value)}")

# -----------------------------
# FORECAST
# -----------------------------
data = []
for item in forecast.get('list', []):
    data.append({
        "time": pd.to_datetime(item['dt_txt']),
        "temp": convert_temp(item['main']['temp']),
        "feels": convert_temp(item['main']['feels_like'])
    })

df = pd.DataFrame(data)

if not df.empty:
    df_small = df.tail(8)

    st.subheader("📈 Temperature Trend")
    chart_df = df_small.set_index('time')[['temp', 'feels']]
    st.line_chart(chart_df)

    avg_temp = df_small['temp'].mean()
    difference = temp - avg_temp

    st.subheader("⚖️ Comparison")

    c1, c2, c3 = st.columns(3)
    c1.metric("Current", f"{temp:.1f} {unit_symbol}")
    c2.metric("Average", f"{avg_temp:.1f} {unit_symbol}")
    c3.metric("Difference", f"{difference:.1f} {unit_symbol}")

# -----------------------------
# ALERTS
# -----------------------------
st.subheader("⚠️ Alerts")

heat_status = "High 🔥" if temp > 35 else "Normal"
rain_status = "Yes 🌧️" if "rain" in condition.lower() else "No"
aqi_status = "Poor 🌫️" if aqi_value >= 4 else "Good"

if temp > 35 or "rain" in condition.lower() or aqi_value >= 4:
    st.error("⚠️ Critical weather conditions detected")
else:
    st.success("✅ No critical alerts")

col1, col2, col3 = st.columns(3)
col1.metric("🔥 Heat", heat_status)
col2.metric("🌧️ Rain", rain_status)
col3.metric("🌫️ AQI", aqi_status)

# -----------------------------
# FOOTER
# -----------------------------
st.markdown("---")
st.markdown("🔗 OpenWeather API | Premium Weather Dashboard")
