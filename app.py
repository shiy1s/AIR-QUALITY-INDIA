import streamlit as st
import joblib
import pandas as pd
import requests
import time
from html import escape
from datetime import datetime, timezone
from textwrap import dedent
from zoneinfo import ZoneInfo

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="AirSense AI | Air quality intelligence",
    page_icon=":material/air:",
    layout="wide"
)

st.markdown(
    """
    <style>
    .airsense-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1.25rem;
        padding: 1.25rem 1.5rem;
        margin: 0 0 1.5rem;
        background: #123528;
        border: 1px solid #315344;
        border-radius: 18px;
    }
    .airsense-brand {
        display: flex;
        align-items: center;
        gap: 1rem;
        min-width: 0;
    }
    .airsense-mark {
        display: grid;
        flex: 0 0 48px;
        width: 48px;
        height: 48px;
        place-items: center;
        border: 1px solid #65c18c;
        border-radius: 15px;
        color: #b6efca;
        font-size: 1.15rem;
        font-weight: 750;
        background: #193d2d;
        box-shadow: inset 0 0 0 5px #123528;
    }
    .airsense-name {
        margin: 0;
        color: #fff;
        font-size: 1.35rem;
        font-weight: 720;
        letter-spacing: -0.035em;
        line-height: 1.25;
    }
    .airsense-subtitle {
        margin: 0.25rem 0 0;
        color: #b8c8bf;
        font-size: 0.92rem;
    }
    .live-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.55rem;
        flex: 0 0 auto;
        padding: 0.5rem 0.8rem;
        border: 1px solid #426b55;
        border-radius: 999px;
        color: #d7e6dc;
        background: #193d2d;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .live-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #65c18c;
        box-shadow: 0 0 0 3px #65c18c24;
    }
    .live-badge.pending .live-dot {
        background: #a4b3aa;
        box-shadow: 0 0 0 3px #a4b3aa24;
    }
    .metadata-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(min(100%, 190px), 1fr));
        gap: 0.75rem;
        margin: 1rem 0 1.4rem;
    }
    .metadata-item, .pollutant-card, .kpi-card {
        background: #193d2d;
        border: 1px solid #315344;
        border-radius: 15px;
    }
    .metadata-item {
        min-width: 0;
        padding: 0.9rem 1rem;
    }
    .metadata-label, .kpi-label, .pollutant-label {
        color: #b8c8bf;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.035em;
        text-transform: uppercase;
    }
    .metadata-value {
        overflow-wrap: anywhere;
        margin-top: 0.35rem;
        color: #fff;
        font-size: 0.98rem;
        font-weight: 620;
    }
    .kpi-grid, .pollutant-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
        gap: 0.9rem;
        margin: 0.75rem 0 1.1rem;
    }
    .kpi-card {
        min-width: 0;
        padding: 1.15rem 1.2rem;
        border-top: 2px solid #65c18c;
    }
    .kpi-card.featured {
        padding: 1.35rem 1.4rem;
        border-color: #46795b;
        border-top: 3px solid #65c18c;
        background: linear-gradient(145deg, #1d4935 0%, #193d2d 72%);
    }
    .kpi-value {
        margin: 0.45rem 0 0.3rem;
        color: #fff;
        font-size: clamp(1.8rem, 3.2vw, 2.6rem);
        font-weight: 740;
        letter-spacing: -0.045em;
        line-height: 1.1;
        font-variant-numeric: tabular-nums;
    }
    .kpi-card.featured .kpi-value {
        font-size: clamp(2.2rem, 4vw, 3rem);
    }
    .kpi-detail {
        color: #b8c8bf;
        font-size: 0.88rem;
    }
    .kpi-delta {
        display: inline-block;
        margin-top: 0.65rem;
        padding: 0.3rem 0.55rem;
        border-radius: 7px;
        color: #d5e5db;
        background: #ffffff0d;
        font-size: 0.8rem;
    }
    .pollutant-card {
        min-width: 0;
        padding: 1rem 1.05rem;
    }
    .pollutant-value {
        margin: 0.45rem 0 0.2rem;
        color: #fff;
        font-size: 1.65rem;
        font-weight: 700;
        letter-spacing: -0.035em;
        font-variant-numeric: tabular-nums;
    }
    .pollutant-unit, .pollutant-subindex {
        color: #b8c8bf;
        font-size: 0.82rem;
    }
    .pollutant-subindex {
        margin-top: 0.75rem;
        padding-top: 0.65rem;
        border-top: 1px solid #315344;
    }
    .aqi-scale {
        position: relative;
        display: flex;
        overflow: visible;
        height: 12px;
        margin: 1.35rem 0 0.55rem;
        border-radius: 999px;
        background: #65c18c;
    }
    .aqi-segment:nth-child(1) { width: 10%; background: #65c18c; border-radius: 999px 0 0 999px; }
    .aqi-segment:nth-child(2) { width: 10%; background: #a4cf61; }
    .aqi-segment:nth-child(3) { width: 20%; background: #edc85d; }
    .aqi-segment:nth-child(4) { width: 20%; background: #e99854; }
    .aqi-segment:nth-child(5) { width: 20%; background: #d96865; }
    .aqi-segment:nth-child(6) { width: 20%; background: #9977ad; border-radius: 0 999px 999px 0; }
    .aqi-marker {
        position: absolute;
        top: 50%;
        width: 18px;
        height: 18px;
        border: 3px solid #fff;
        border-radius: 50%;
        background: #0b2118;
        box-shadow: 0 1px 5px #0008;
        transform: translate(-50%, -50%);
    }
    .aqi-scale-labels {
        display: flex;
        justify-content: space-between;
        color: #b8c8bf;
        font-size: 0.73rem;
    }
    @media (max-width: 600px) {
        .airsense-header {
            align-items: flex-start;
            flex-direction: column;
            padding: 1rem;
        }
        .airsense-mark {
            flex-basis: 42px;
            width: 42px;
            height: 42px;
        }
        .airsense-name { font-size: 1.18rem; }
        .airsense-subtitle { font-size: 0.82rem; }
        .kpi-grid { grid-template-columns: 1fr; }
        .pollutant-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

header_placeholder = st.empty()

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
def render_kpi(label, value, detail, featured=False, delta=None):
    card_class = "kpi-card featured" if featured else "kpi-card"
    delta_html = (
        f'<div class="kpi-delta">{escape(delta)}</div>'
        if delta is not None
        else ""
    )
    st.markdown(
        dedent(f"""
        <div class="{card_class}">
          <div class="kpi-label">{escape(label)}</div>
          <div class="kpi-value">{escape(value)}</div>
          <div class="kpi-detail">{escape(detail)}</div>
          {delta_html}
        </div>
        """).strip(),
        unsafe_allow_html=True,
    )


def render_aqi_gauge(value):
    marker_position = min(100, max(0, value / 5))
    category = escape(aqi_category(value))
    st.markdown(
        dedent(f"""
        <div class="aqi-scale" role="img"
             aria-label="AQI {value:.0f} of 500, category {category}">
          <span class="aqi-segment"></span><span class="aqi-segment"></span>
          <span class="aqi-segment"></span><span class="aqi-segment"></span>
          <span class="aqi-segment"></span><span class="aqi-segment"></span>
          <span class="aqi-marker" style="left: {marker_position:.2f}%"></span>
        </div>
        <div class="aqi-scale-labels">
          <span>0</span><span>50</span><span>100</span><span>200</span>
          <span>300</span><span>400</span><span>500</span>
        </div>
        """).strip(),
        unsafe_allow_html=True,
    )


def render_station_metadata(city, station, updated_at, age_hours):
    station_text = escape(str(station))
    updated_text = updated_at.astimezone(IST).strftime("%d %b %Y, %I:%M %p IST")
    values = [
        ("Selected city", escape(city)),
        ("Monitoring station", station_text),
        ("Latest measurement", escape(updated_text)),
        ("Data freshness", f"{age_hours:.1f} hours ago"),
    ]
    cards = "".join(
        dedent(f"""
        <div class="metadata-item">
          <div class="metadata-label">{label}</div>
          <div class="metadata-value">{value}</div>
        </div>
        """).strip()
        for label, value in values
    )
    st.markdown(f'<div class="metadata-grid">{cards}</div>', unsafe_allow_html=True)


def render_brand_header():
    result = st.session_state.get("live_result")
    selected_city = st.session_state.get("live_city", "Bengaluru")
    has_live_data = bool(
        result
        and result["city"] == selected_city
        and (datetime.now(timezone.utc) - result["updated_at"]).total_seconds()
        <= 6 * 3600
    )
    status = "Live data available" if has_live_data else "Awaiting live readings"
    status_class = "" if has_live_data else " pending"
    header_placeholder.markdown(
        f"""
        <header class="airsense-header">
          <div class="airsense-brand">
            <div class="airsense-mark" aria-hidden="true">A</div>
            <div>
              <h1 class="airsense-name">AirSense AI</h1>
              <p class="airsense-subtitle">Intelligent Air Quality Monitoring &amp; Prediction</p>
            </div>
          </div>
          <div class="live-badge{status_class}">
            <span class="live-dot" aria-hidden="true"></span>{status}
          </div>
        </header>
        """,
        unsafe_allow_html=True,
    )


live_tab, manual_tab = st.tabs(
    [":material/sensors: Live monitoring", ":material/tune: Manual prediction"]
)

with live_tab:
    st.subheader("Live air quality")
    st.caption("Fetch the latest complete, recent station snapshot and estimate tomorrow's AQI.")
    live_city = st.selectbox("Select city", CITIES, key="live_city")

    if st.button(
        "Refresh live readings and predict",
        type="primary",
        key="fetch_live",
        icon=":material/refresh:",
    ):
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
        render_station_metadata(
            result["city"],
            result["station"],
            result["updated_at"],
            result["age_hours"],
        )
        st.caption(
            f"{result['qualified_count']} stations met the completeness and freshness rules. "
            "Latest available API averages are used as today's prediction inputs."
        )

        st.markdown("#### AQI overview")
        kpi_col1, kpi_col2 = st.columns(2)
        change = result["tomorrow_aqi"] - result["today_aqi"]
        with kpi_col1:
            render_kpi(
                "Today's AQI",
                f"{result['today_aqi']:.2f}",
                f"Calculated · {aqi_category(result['today_aqi'])}",
                featured=True,
            )
        with kpi_col2:
            render_kpi(
                "Tomorrow's predicted AQI",
                f"{result['tomorrow_aqi']:.2f}",
                f"Model estimate · {aqi_category(result['tomorrow_aqi'])}",
                featured=True,
                delta=f"{change:+.2f} vs today's calculated AQI",
            )

        with st.container(border=True):
            st.markdown("**AQI category**")
            st.markdown(
                f"Current reading: **{aqi_category(result['today_aqi'])}**"
            )
            render_aqi_gauge(result["today_aqi"])
            st.caption(
                "CPCB-style AQI scale · Good 0–50 · Satisfactory 51–100 · "
                "Moderate 101–200 · Poor 201–300 · Very Poor 301–400 · Severe 401–500"
            )

        st.markdown("#### Particulate matter")
        pm_col1, pm_col2 = st.columns(2)
        with pm_col1:
            render_kpi(
                "PM2.5",
                f"{result['api_values']['PM2.5']:.2f}",
                "Fine particulate matter · µg/m³",
            )
        with pm_col2:
            render_kpi(
                "PM10",
                f"{result['api_values']['PM10']:.2f}",
                "Coarse particulate matter · µg/m³",
            )

        st.markdown("#### Pollutant details")
        pollutant_labels = {
            "PM2.5": "PM2.5",
            "PM10": "PM10",
            "NO2": "NO2",
            "NH3": "NH3",
            "SO2": "SO2",
        }
        api_to_model = {
            api_name: model_name for model_name, api_name in MODEL_TO_API.items()
        }
        pollutant_cards = []
        for pollutant in REQUIRED_API_POLLUTANTS:
            sub_index = result["sub_indices"][api_to_model[pollutant]]
            pollutant_cards.append(
                dedent(f"""
                <div class="pollutant-card">
                  <div class="pollutant-label">{pollutant_labels[pollutant]}</div>
                  <div class="pollutant-value">{result['api_values'][pollutant]:.2f}</div>
                  <div class="pollutant-unit">µg/m³</div>
                  <div class="pollutant-subindex">AQI sub-index <strong>
                    {f"{sub_index:.2f}" if sub_index is not None else "Not available"}
                  </strong></div>
                </div>
                """).strip()
            )
        st.markdown(
            '<div class="pollutant-grid">' + "".join(pollutant_cards) + "</div>",
            unsafe_allow_html=True,
        )

        with st.expander("View pollutant concentration chart"):
            chart_data = pd.DataFrame(
                {
                    "Pollutant": REQUIRED_API_POLLUTANTS,
                    "Concentration (µg/m³)": [
                        result["api_values"][pollutant]
                        for pollutant in REQUIRED_API_POLLUTANTS
                    ],
                }
            ).set_index("Pollutant")
            st.bar_chart(
                chart_data,
                height=280,
                alt="Latest measured concentration for each station pollutant in micrograms per cubic meter",
            )

        st.warning(
            "The model was trained on historical daily records. Live API values are the latest available "
            "station averages, not verified daily averages. The prediction is therefore an experimental "
            "estimate, not an official forecast or CPCB AQI."
        )
    else:
        st.info(
            "Choose a city and refresh live readings to see station measurements and an AQI estimate.",
            icon=":material/info:",
        )

with manual_tab:
    st.subheader("Manual prediction")
    st.caption(
        "Enter pollutant concentrations and today's AQI to estimate tomorrow's air quality."
    )

    with st.form("aqi_prediction_form"):
        manual_city = st.selectbox("Select city", CITIES, key="manual_city")
        st.markdown("**Pollutant concentrations**")
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

        manual_submit = st.form_submit_button(
            "Predict tomorrow's AQI",
            type="primary",
            icon=":material/arrow_forward:",
            width="stretch",
        )

    if manual_submit:
        manual_values = {
            "PM 2.5": pm25,
            "PM 10": pm10,
            "NO2": no2,
            "NH3": nh3,
            "SO2": so2,
        }
        try:
            with st.spinner("Fetching AQI data ...."):
                time.sleep(4)
                prediction = predict_tomorrow(manual_city, manual_values, manual_aqi)
            st.markdown("#### Prediction result")
            result_col1, result_col2 = st.columns(2)
            with result_col1:
                render_kpi(
                    "Tomorrow's predicted AQI",
                    f"{prediction:.2f}",
                    f"Model estimate · {aqi_category(prediction)}",
                    featured=True,
                    delta=f"{prediction - manual_aqi:+.2f} vs today's AQI",
                )
            with result_col2:
                render_kpi(
                    "Today's AQI",
                    f"{manual_aqi:.2f}",
                    f"Provided input · {aqi_category(manual_aqi)}",
                    featured=True,
                )
            with st.container(border=True):
                st.markdown("**Predicted AQI category**")
                st.markdown(f"Tomorrow: **{aqi_category(prediction)}**")
                render_aqi_gauge(prediction)
            st.caption("This is a machine-learning estimate, not an official AQI reading.")
        except Exception as exc:
            st.error(f"Prediction failed: {exc}")

render_brand_header()

st.caption(
    "Data source: Snapdata mirror of CPCB / data.gov.in readings. "
    "Machine-learning predictions are estimates and should not be used as official public-health advice."
)
