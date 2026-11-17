import streamlit as st
import joblib
import pandas as pd
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Air Quality Prediction",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 Air Quality Prediction System")
st.write("Use the latest available CPCB pollutant readings to estimate tomorrow's AQI.")

# ---------------------------------------------------------
# LOAD EXISTING MODEL
# Keep aqi_model.pkl in the same folder as this app.py.
# ---------------------------------------------------------
@st.cache_resource
def load_model():
    return joblib.load("aqi_model.pkl")

try:
    model_data = load_model()
    model = model_data["model"]
    scaler = model_data["scaler"]
    feature_columns = model_data["feature_columns"]
    pollutants = model_data["pollutants"]
    medians = model_data["medians"]
    city_columns = model_data["city_columns"]
except Exception as exc:
    st.error(f"Could not load aqi_model.pkl: {exc}")
    st.stop()

CITIES = ["Bengaluru", "Chennai", "Delhi", "Kolkata", "Mumbai"]
CITY_SLUGS = {
    "Bengaluru": "bengaluru",
    "Chennai": "chennai",
    "Delhi": "delhi",
    "Kolkata": "kolkata",
    "Mumbai": "mumbai",
}
API_URL = "https://snapdata.dev/api/v1/aqi/in/city/{slug}.json"
REQUIRED_API_POLLUTANTS = ["PM2.5", "PM10", "NO2", "NH3", "SO2"]
MODEL_TO_API = {
    "PM 2.5": "PM2.5",
    "PM 10": "PM10",
    "NO2": "NO2",
    "NH3": "NH3",
    "SO2": "SO2",
}
IST = ZoneInfo("Asia/Kolkata")

# ---------------------------------------------------------
# CPCB-STYLE AQI CALCULATION
# Same breakpoints and interpolation used in the training
# notebook for the five model pollutants.
# ---------------------------------------------------------
BREAKPOINTS = {
    "PM 2.5": [
        (0, 30, 0, 50), (30, 60, 50, 100),
        (60, 90, 100, 200), (90, 120, 200, 300),
        (120, 250, 300, 400), (250, float("inf"), 400, 500)
    ],
    "PM 10": [
        (0, 50, 0, 50), (50, 100, 50, 100),
        (100, 250, 100, 200), (250, 350, 200, 300),
        (350, 430, 300, 400), (430, float("inf"), 400, 500)
    ],
    "NO2": [
        (0, 40, 0, 50), (40, 80, 50, 100),
        (80, 180, 100, 200), (180, 280, 200, 300),
        (280, 400, 300, 400), (400, float("inf"), 400, 500)
    ],
    "NH3": [
        (0, 200, 0, 50), (200, 400, 50, 100),
        (400, 800, 100, 200), (800, 1200, 200, 300),
        (1200, 1800, 300, 400), (1800, float("inf"), 400, 500)
    ],
    "SO2": [
        (0, 40, 0, 50), (40, 80, 50, 100),
        (80, 380, 100, 200), (380, 800, 200, 300),
        (800, 1600, 300, 400), (1600, float("inf"), 400, 500)
    ],
}

def pollutant_sub_index(value, ranges):
    value = float(value)
    if pd.isna(value) or value < 0:
        return None

    for low, high, aqi_low, aqi_high in ranges:
        if low <= value <= high:
            if high == float("inf"):
                return 500.0
            return round(
                ((aqi_high - aqi_low) / (high - low)) * (value - low) + aqi_low,
                2
            )
    return 500.0

def calculate_overall_aqi(values):
    sub_indices = {
        pollutant: pollutant_sub_index(values[pollutant], BREAKPOINTS[pollutant])
        for pollutant in BREAKPOINTS
    }
    valid = [v for v in sub_indices.values() if v is not None]

    # Match the training notebook's eligibility rule:
    # at least 3 valid pollutant sub-indices, including PM2.5 or PM10.
    pm_available = (
        sub_indices["PM 2.5"] is not None or
        sub_indices["PM 10"] is not None
    )
    if len(valid) < 3 or not pm_available:
        raise ValueError("At least three valid pollutant readings, including PM2.5 or PM10, are required.")

    return round(max(valid), 2), sub_indices

def aqi_category(value):
    if value <= 50:
        return "Good 🟢"
    if value <= 100:
        return "Satisfactory 🟡"
    if value <= 200:
        return "Moderate 🟠"
    if value <= 300:
        return "Poor 🔴"
    if value <= 400:
        return "Very Poor 🟣"
    return "Severe 🟤"

# ---------------------------------------------------------
# LIVE SNAPDATA FETCH + COMPLETE-STATION SELECTION
# The API snapshot is refreshed on a roughly three-hourly
# cadence. We use the latest returned average for each
# pollutant and label it as the latest available reading.
# ---------------------------------------------------------
def parse_timestamp(value):
    if not value:
        return None
    try:
        ts = pd.Timestamp(value)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        return ts.to_pydatetime()
    except Exception:
        return None

@st.cache_data(ttl=180)
def fetch_city_records(city):
    url = API_URL.format(slug=CITY_SLUGS[city])
    response = requests.get(
        url,
        headers={"User-Agent": "AQI-Prediction-Student-Project/1.0"},
        timeout=20
    )
    response.raise_for_status()
    payload = response.json()

    records = payload.get("records", [])
    if not isinstance(records, list):
        raise ValueError("Unexpected API response: 'records' is not a list.")
    return records

def select_latest_complete_station(records):
    now_utc = datetime.now(timezone.utc)
    station_groups = {}

    for record in records:
        station = record.get("station")
        pollutant = str(record.get("pollutant", "")).strip().upper()
        if not station or pollutant not in REQUIRED_API_POLLUTANTS:
            continue

        avg = record.get("avg")
        updated_at = parse_timestamp(record.get("updated_at"))

        if avg is None or updated_at is None:
            continue

        try:
            avg = float(avg)
        except (TypeError, ValueError):
            continue

        if pd.isna(avg) or avg < 0:
            continue

        station_groups.setdefault(station, {})
        previous = station_groups[station].get(pollutant)

        # Keep the newest record if an API response contains duplicates.
        if previous is None or updated_at > previous["updated_at"]:
            station_groups[station][pollutant] = {
                "value": avg,
                "updated_at": updated_at
            }

    qualified = []
    for station, readings in station_groups.items():
        if not all(p in readings for p in REQUIRED_API_POLLUTANTS):
            continue

        timestamps = [readings[p]["updated_at"] for p in REQUIRED_API_POLLUTANTS]
        oldest = min(timestamps)
        newest = max(timestamps)
        age_hours = (now_utc - oldest).total_seconds() / 3600
        spread_hours = (newest - oldest).total_seconds() / 3600

        # Accept recent readings and avoid combining widely separated updates.
        if age_hours <= 6 and spread_hours <= 3:
            qualified.append({
                "station": station,
                "readings": readings,
                "oldest": oldest,
                "newest": newest,
                "age_hours": age_hours,
                "spread_hours": spread_hours
            })

    if not qualified:
        raise ValueError(
            "No station currently has all five required pollutants with sufficiently recent, "
            "closely timed readings. Try again later."
        )

    # Prefer the station whose oldest required pollutant reading is freshest.
    # Alphabetical station name provides a stable tie-break.
    qualified.sort(key=lambda item: (-item["oldest"].timestamp(), item["station"].casefold()))
    return qualified[0], len(qualified)

def build_model_input(city, pollutant_values, today_aqi):
    new_data = pd.DataFrame(0.0, index=[0], columns=feature_columns, dtype="float64")

    for pollutant in pollutants:
        new_data.loc[0, pollutant] = pollutant_values[pollutant]

    new_data.loc[0, "AQI"] = today_aqi

    # Bengaluru is the reference category; other cities have dummy columns.
    if city in city_columns:
        new_data.loc[0, city] = 1

    # Preserve the exact scaling used during model training.
    new_data[pollutants] = scaler.transform(new_data[pollutants])
    return new_data

def predict_tomorrow(city, pollutant_values, today_aqi):
    model_input = build_model_input(city, pollutant_values, today_aqi)
    prediction = float(model.predict(model_input)[0])
    return max(0.0, min(500.0, prediction))

# ---------------------------------------------------------
# USER INTERFACE
# ---------------------------------------------------------
live_tab, manual_tab = st.tabs(["🌐 Live AQI Prediction", "✍️ Manual Prediction"])

with live_tab:
    st.subheader("Live station readings")
    live_city = st.selectbox("Select city", CITIES, key="live_city")

    if st.button("Fetch latest readings & predict", type="primary", key="fetch_live"):
        with st.spinner(f"Fetching the latest {live_city} station readings..."):
            try:
                records = fetch_city_records(live_city)
                selected, qualified_count = select_latest_complete_station(records)

                api_values = {
                    pollutant: selected["readings"][pollutant]["value"]
                    for pollutant in REQUIRED_API_POLLUTANTS
                }
                model_values = {
                    model_name: api_values[api_name]
                    for model_name, api_name in MODEL_TO_API.items()
                }

                today_aqi, sub_indices = calculate_overall_aqi(model_values)
                tomorrow_aqi = predict_tomorrow(live_city, model_values, today_aqi)

                st.session_state["live_result"] = {
                    "city": live_city,
                    "station": selected["station"],
                    "api_values": api_values,
                    "model_values": model_values,
                    "today_aqi": today_aqi,
                    "sub_indices": sub_indices,
                    "tomorrow_aqi": tomorrow_aqi,
                    "updated_at": selected["newest"],
                    "age_hours": selected["age_hours"],
                    "qualified_count": qualified_count,
                }
            except requests.RequestException as exc:
                st.error(f"Could not fetch data from Snapdata: {exc}")
            except Exception as exc:
                st.error(str(exc))

    result = st.session_state.get("live_result")
    if result and result["city"] == live_city:
        st.success(f"Selected station: {result['station']}")
        updated_ist = result["updated_at"].astimezone(IST)
        st.caption(
            f"Latest pollutant update: {updated_ist:%d %b %Y, %I:%M %p IST} "
            f"({result['age_hours']:.1f} hours old). "
            f"{result['qualified_count']} stations met the completeness and freshness rules."
        )

        st.markdown("#### Latest pollutant measurements")
        display_names = {
            "PM2.5": "PM2.5 (µg/m³)",
            "PM10": "PM10 (µg/m³)",
            "NO2": "NO2 (µg/m³)",
            "NH3": "NH3 (µg/m³)",
            "SO2": "SO2 (µg/m³)",
        }
        cols = st.columns(5)
        for col, pollutant in zip(cols, REQUIRED_API_POLLUTANTS):
            col.metric(display_names[pollutant], f"{result['api_values'][pollutant]:.2f}")

        st.caption("These are the latest available API averages, treated as today's input values for this prediction.")

        col1, col2 = st.columns(2)
        col1.metric("Today's calculated AQI", f"{result['today_aqi']:.2f}")
        col2.metric(
            "Tomorrow's predicted AQI",
            f"{result['tomorrow_aqi']:.2f}",
            delta=f"{result['tomorrow_aqi'] - result['today_aqi']:.2f} vs today's calculated AQI"
        )
        st.info(f"Today's AQI category: **{aqi_category(result['today_aqi'])}**")
        st.success(f"Predicted tomorrow's AQI category: **{aqi_category(result['tomorrow_aqi'])}**")

        with st.expander("View pollutant AQI sub-indices"):
            st.dataframe(
                pd.DataFrame(
                    [{"Pollutant": k, "AQI sub-index": v} for k, v in result["sub_indices"].items()]
                ),
                hide_index=True,
                use_container_width=True
            )

        st.warning(
            "The model was trained on historical daily records. Live API values are the latest available "
            "station averages, not verified daily averages. The prediction is therefore an experimental "
            "estimate, not an official forecast or CPCB AQI."
        )
    else:
        st.info("Select a city and click **Fetch latest readings & predict**.")

with manual_tab:
    st.subheader("Manual prediction")
    st.write("Enter pollutant concentrations yourself. This keeps the original manual prediction workflow.")

    with st.form("aqi_prediction_form"):
        manual_city = st.selectbox("Select City", CITIES, key="manual_city")
        col1, col2 = st.columns(2)

        with col1:
            pm25 = st.number_input("PM 2.5 (µg/m³)", min_value=0.0, value=85.0)
            pm10 = st.number_input("PM 10 (µg/m³)", min_value=0.0, value=180.0)
            no2 = st.number_input("NO2 (µg/m³)", min_value=0.0, value=40.0)

        with col2:
            nh3 = st.number_input("NH3 (µg/m³)", min_value=0.0, value=20.0)
            so2 = st.number_input("SO2 (µg/m³)", min_value=0.0, value=15.0)
            manual_aqi = st.number_input(
                "Today's AQI", min_value=0.0, max_value=500.0, value=187.0
            )

        manual_submit = st.form_submit_button("Predict Tomorrow's AQI")

    if manual_submit:
        manual_values = {
            "PM 2.5": pm25,
            "PM 10": pm10,
            "NO2": no2,
            "NH3": nh3,
            "SO2": so2,
        }
        try:
            prediction = predict_tomorrow(manual_city, manual_values, manual_aqi)
            st.divider()
            st.subheader("📊 Manual Prediction Result")
            st.metric(
                "Predicted Tomorrow's AQI",
                f"{prediction:.2f}",
                delta=f"{prediction - manual_aqi:.2f} compared with today's AQI"
            )
            st.info(f"Predicted AQI Category: **{aqi_category(prediction)}**")
            st.caption("This is a machine-learning estimate, not an official AQI reading.")
        except Exception as exc:
            st.error(f"Prediction failed: {exc}")

st.divider()
st.caption(
    "Data source: Snapdata mirror of CPCB / data.gov.in readings. "
    "Machine-learning predictions are estimates and should not be used as official public-health advice."
)
