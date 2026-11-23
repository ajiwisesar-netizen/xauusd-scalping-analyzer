import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==================================================
# 1. CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="Historical Data Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 HISTORICAL DATA ANALYZER")
st.caption(
    "Historical data processing and multi-interval "
    "statistical analysis."
)

# ==================================================
# 2. SYNTHETIC DATA
# ==================================================

def generate_sample_data(n=1500):

    np.random.seed(42)

    dates = pd.date_range(
        end=pd.Timestamp.now().floor("min"),
        periods=n,
        freq="1min"
    )

    close = 100 + np.cumsum(
        np.random.normal(0, 0.08, n)
    )

    open_price = np.insert(
        close[:-1],
        0,
        close[0]
    )

    high = np.maximum(
        open_price,
        close
    ) + np.random.uniform(0.01, 0.08, n)

    low = np.minimum(
        open_price,
        close
    ) - np.random.uniform(0.01, 0.08, n)

    return pd.DataFrame({
        "time": dates,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close
    })


# ==================================================
# 3. VALIDATION
# ==================================================

def validate_data(raw):

    required = [
        "time", "open", "high", "low", "close"
    ]

    missing = [
        col for col in required
        if col not in raw.columns
    ]

    if missing:
        return None, (
            "Kolom tidak ditemukan: "
            + ", ".join(missing)
        )

    df = raw[required].copy()

    df["time"] = pd.to_datetime(
        df["time"],
        errors="coerce"
    )

    for col in [
        "open", "high", "low", "close"
    ]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    original_count = len(df)

    df = df.dropna(
        subset=required
    )

    duplicate_count = int(
        df["time"].duplicated().sum()
    )

    df = df.drop_duplicates(
        subset=["time"]
    )

    valid = (
        (df["high"] >= df["low"]) &
        (df["high"] >= df["open"]) &
        (df["high"] >= df["close"]) &
        (df["low"] <= df["open"]) &
        (df["low"] <= df["close"])
    )

    df = df[valid]

    df = df.sort_values(
        "time"
    ).reset_index(drop=True)

    removed = original_count - len(df)

    if df.empty:
        return None, "Tidak ada data valid."

    return {
        "data": df,
        "removed": removed,
        "duplicates": duplicate_count
    }, None


# ==================================================
# 4. INDICATORS
# ==================================================

def calculate_indicators(data):

    df = data.copy()

    df["EMA20"] = df["close"].ewm(
        span=20,
        adjust=False
    ).mean()

    df["EMA50"] = df["close"].ewm(
        span=50,
        adjust=False
    ).mean()

    delta = df["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1/14,
        adjust=False,
        min_periods=14
    ).mean()

    avg_loss = loss.ewm(
        alpha=1/14,
        adjust=False,
        min_periods=14
    ).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan
    )

    df["RSI14"] = 100 - (
        100 / (1 + rs)
    )

    df.loc[
        (avg_loss == 0) & (avg_gain > 0),
        "RSI14"
    ] = 100

    df.loc[
        (avg_loss == 0) & (avg_gain == 0),
        "RSI14"
    ] = 50

    previous_close = df["close"].shift(1)

    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    df["ATR14"] = tr.ewm(
        alpha=1/14,
        adjust=False,
        min_periods=14
    ).mean()

    df["Return_Pct"] = (
        df["close"].pct_change() * 100
    )

    df["Volatility20"] = (
        df["Return_Pct"].rolling(20).std()
    )

    return df


# ==================================================
# 5. RESAMPLING
# ==================================================

def resample_data(data, interval):

    temp = data.copy()

    temp = temp.set_index("time")

    result = temp.resample(
        interval,
        origin="start_day",
        label="left",
        closed="left"
    ).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last"
    })

    return result.dropna().reset_index()


# ==================================================
# 6. DATA SOURCE
# ==================================================

st.sidebar.header("DATA SETTINGS")

source = st.sidebar.radio(
    "Pilih sumber data",
    [
        "Upload Historical CSV",
        "Synthetic Data"
    ]
)

removed = 0
duplicate_count = 0

if source == "Upload Historical CSV":

    uploaded = st.sidebar.file_uploader(
        "Upload file CSV M1",
        type=["csv"]
    )

    if uploaded is None:

        st.info(
            "Silakan upload file CSV dengan kolom "
            "time, open, high, low, close."
        )

        st.stop()

    try:

        raw = pd.read_csv(uploaded)

        result, error = validate_data(raw)

        if error:

            st.error(error)
            st.stop()

        df = result["data"]
        removed = result["removed"]
        duplicate_count = result["duplicates"]

    except Exception as e:

        st.error(
            f"Kesalahan membaca CSV: {e}"
        )

        st.stop()

else:

    df = generate_sample_data()


# ==================================================
# 7. SOURCE INTERVAL CHECK
# ==================================================

time_diff = (
    df["time"]
    .diff()
    .dropna()
)

if time_diff.empty:

    st.error("Data terlalu sedikit.")
    st.stop()

source_interval = time_diff.median()

is_m1 = (
    source_interval == pd.Timedelta(minutes=1)
)

if not is_m1:

    st.warning(
        "Data sumber bukan M1 murni berdasarkan "
        "median jarak timestamp. Periksa file CSV."
    )


# ==================================================
# 8. DATE FILTER
# ==================================================

st.header("1. HISTORICAL DATA OVERVIEW")

min_date = df["time"].min().date()
max_date = df["time"].max().date()

date_range = st.date_input(
    "Filter tanggal",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:

    start_date, end_date = date_range

    filtered = df[
        (df["time"].dt.date >= start_date) &
        (df["time"].dt.date <= end_date)
    ].copy()

else:

    filtered = df.copy()

if filtered.empty:

    st.warning("Data tidak tersedia.")
    st.stop()

filtered = calculate_indicators(filtered)


# ==================================================
# 9. OVERVIEW
# ==================================================

st.subheader("Ringkasan Data")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Total Observasi",
    len(filtered)
)

c2.metric(
    "Nilai Terakhir",
    f"{filtered['close'].iloc[-1]:.4f}"
)

c3.metric(
    "Nilai Maksimum",
    f"{filtered['high'].max():.4f}"
)

c4.metric(
    "Nilai Minimum",
    f"{filtered['low'].min():.4f}"
)

st.caption(
    f"Periode: {filtered['time'].min()} - "
    f"{filtered['time'].max()}"
)

st.caption(
    f"Interval median sumber: {source_interval}"
)


# ==================================================
# 10. CANDLESTICK
# ==================================================

st.header("2. HISTORICAL CHART")

fig = go.Figure()

fig.add_trace(
    go.Candlestick(
        x=filtered["time"],
        open=filtered["open"],
        high=filtered["high"],
        low=filtered["low"],
        close=filtered["close"],
        name="Historical Data"
    )
)

fig.add_trace(
    go.Scatter(
        x=filtered["time"],
        y=filtered["EMA20"],
        name="EMA20"
    )
)

fig.add_trace(
    go.Scatter(
        x=filtered["time"],
        y=filtered["EMA50"],
        name="EMA50"
    )
)

fig.update_layout(
    height=500,
    template="plotly_dark",
    xaxis_rangeslider_visible=False
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# ==================================================
# 11. RSI
# ==================================================

st.header("3. RSI 14")

rsi_fig = go.Figure()

rsi_fig.add_trace(
    go.Scatter(
        x=filtered["time"],
        y=filtered["RSI14"],
        name="RSI14"
    )
)

rsi_fig.add_hline(
    y=70,
    line_dash="dash"
)

rsi_fig.add_hline(
    y=30,
    line_dash="dash"
)

rsi_fig.update_layout(
    height=300,
    template="plotly_dark",
    yaxis_range=[0, 100]
)

st.plotly_chart(
    rsi_fig,
    use_container_width=True
)


# ==================================================
# 12. ATR
# ==================================================

st.header("4. ATR 14")

atr_fig = go.Figure()

atr_fig.add_trace(
    go.Scatter(
        x=filtered["time"],
        y=filtered["ATR14"],
        name="ATR14"
    )
)

atr_fig.update_layout(
    height=300,
    template="plotly_dark"
)

st.plotly_chart(
    atr_fig,
    use_container_width=True
)


# ==================================================
# 13. STATISTICS
# ==================================================

st.header("5. HISTORICAL STATISTICS")

stats = filtered[
    [
        "open",
        "high",
        "low",
        "close",
        "RSI14",
        "ATR14"
    ]
].describe().T

st.dataframe(
    stats.round(4),
    use_container_width=True
)


# ==================================================
# 14. VOLATILITY
# ==================================================

st.header("6. VOLATILITY ANALYSIS")

vol_fig = go.Figure()

vol_fig.add_trace(
    go.Scatter(
        x=filtered["time"],
        y=filtered["Volatility20"],
        name="Volatility20"
    )
)

vol_fig.update_layout(
    height=300,
    template="plotly_dark",
    yaxis_title="Standard Deviation (%)"
)

st.plotly_chart(
    vol_fig,
    use_container_width=True
)


# ==================================================
# 15. MULTI INTERVAL
# ==================================================

st.divider()

st.header("7. MULTI-INTERVAL ANALYSIS")

intervals = {
    "M1": ("1min", 1),
    "M5": ("5min", 5),
    "M15": ("15min", 15),
    "H1": ("1h", 60)
}

interval_data = {}

for name, (rule, minutes) in intervals.items():

    if minutes < source_interval.total_seconds() / 60:

        interval_data[name] = None

    elif minutes == source_interval.total_seconds() / 60:

        interval_data[name] = filtered[
            ["time", "open", "high", "low", "close"]
        ].copy()

    else:

        interval_data[name] = resample_data(
            filtered[
                ["time", "open", "high", "low", "close"]
            ],
            rule
        )


# ==================================================
# 16. INTERVAL SUMMARY
# ==================================================

def summarize_interval(data, name):

    if data is None or data.empty:

        return {
            "Interval": name,
            "Observasi": 0,
            "Rata-rata": np.nan,
            "Maksimum": np.nan,
            "Minimum": np.nan,
            "Rentang": np.nan
        }

    return {
        "Interval": name,
        "Observasi": len(data),
        "Rata-rata": data["close"].mean(),
        "Maksimum": data["high"].max(),
        "Minimum": data["low"].min(),
        "Rentang": (
            data["high"].max() -
            data["low"].min()
        )
    }


summary = pd.DataFrame([
    summarize_interval(
        interval_data[name],
        name
    )
    for name in intervals
])

st.subheader("Perbandingan Statistik")

st.dataframe(
    summary.round(4),
    use_container_width=True
)


# ==================================================
# 17. OBSERVATION CHART
# ==================================================

count_fig = go.Figure()

count_fig.add_trace(
    go.Bar(
        x=summary["Interval"],
        y=summary["Observasi"],
        name="Observasi"
    )
)

count_fig.update_layout(
    template="plotly_dark",
    height=350
)

st.plotly_chart(
    count_fig,
    use_container_width=True
)


# ==================================================
# 18. INTERVAL DETAIL
# ==================================================

st.subheader("Detail Interval")

selected_interval = st.selectbox(
    "Pilih interval",
    list(intervals.keys())
)

selected_data = interval_data[
    selected_interval
]

if selected_data is None:

    st.warning(
        "Data interval ini tidak tersedia."
    )

else:

    st.write(
        f"Jumlah observasi: {len(selected_data)}"
    )

    st.dataframe(
        selected_data.tail(100),
        use_container_width=True
    )

    st.download_button(
        f"Download {selected_interval}",
        data=selected_data.to_csv(
            index=False
        ).encode("utf-8"),
        file_name=f"historical_{selected_interval}.csv",
        mime="text/csv",
        key=f"download_{selected_interval}"
    )


# ==================================================
# 19. DATA QUALITY
# ==================================================

st.divider()

st.header("8. DATA QUALITY MONITOR")

m1_base = filtered.sort_values(
    "time"
).copy()

expected_times = pd.date_range(
    start=m1_base["time"].min(),
    end=m1_base["time"].max(),
    freq="1min"
)

actual_times = pd.DatetimeIndex(
    m1_base["time"]
)

missing_times = expected_times.difference(
    actual_times
)

invalid_ohlc = (
    (m1_base["high"] < m1_base["low"]) |
    (m1_base["high"] < m1_base["open"]) |
    (m1_base["high"] < m1_base["close"]) |
    (m1_base["low"] > m1_base["open"]) |
    (m1_base["low"] > m1_base["close"])
)

q1, q2, q3, q4 = st.columns(4)

q1.metric(
    "Total M1",
    len(m1_base)
)

q2.metric(
    "Missing Timestamp",
    len(missing_times)
)

q3.metric(
    "Duplicate",
    duplicate_count
)

q4.metric(
    "Invalid OHLC",
    int(invalid_ohlc.sum())
)

if not is_m1:

    st.warning(
        "Pemeriksaan kelengkapan M1 tidak dapat "
        "dianggap valid karena sumber bukan M1."
    )

elif len(missing_times) == 0:

    st.success(
        "Tidak ditemukan timestamp hilang "
        "dalam rentang pemeriksaan."
    )

else:

    st.warning(
        f"Ditemukan {len(missing_times)} "
        "timestamp yang tidak tersedia."
    )

    st.dataframe(
        pd.DataFrame({
            "Missing Time": missing_times
        }).head(100),
        use_container_width=True
    )


# ==================================================
# 20. TIME GAP ANALYSIS
# ==================================================

st.subheader("Timestamp Gap Analysis")

time_gaps = (
    m1_base["time"]
    .diff()
    .dropna()
    .dt.total_seconds()
    .div(60)
)

gap_counts = (
    time_gaps.value_counts()
    .sort_index()
    .reset_index()
)

if not gap_counts.empty:

    gap_counts.columns = [
        "Interval Menit",
        "Jumlah"
    ]

    gap_fig = go.Figure()

    gap_fig.add_trace(
        go.Bar(
            x=gap_counts["Interval Menit"].astype(str),
            y=gap_counts["Jumlah"],
            name="Gap"
        )
    )

    gap_fig.update_layout(
        template="plotly_dark",
        height=350
    )

    st.plotly_chart(
        gap_fig,
        use_container_width=True
    )


# ==================================================
# 21. RETURN DISTRIBUTION
# ==================================================

st.header("9. RETURN DISTRIBUTION")

return_fig = go.Figure()

return_fig.add_trace(
    go.Histogram(
        x=filtered["Return_Pct"].dropna(),
        nbinsx=30,
        name="Return"
    )
)

return_fig.update_layout(
    template="plotly_dark",
    height=350
)

st.plotly_chart(
    return_fig,
    use_container_width=True
)


# ==================================================
# 22. DOWNLOAD COMPLETE REPORT
# ==================================================

st.divider()

st.header("10. DOWNLOAD REPORT")

st.download_button(
    "Download Complete Historical Analysis",
    data=filtered.to_csv(
        index=False
    ).encode("utf-8"),
    file_name="historical_complete_analysis.csv",
    mime="text/csv"
)

st.download_button(
    "Download Missing Timestamp Report",
    data=pd.DataFrame({
        "Missing Timestamp": missing_times
    }).to_csv(
        index=False
    ).encode("utf-8"),
    file_name="missing_timestamp_report.csv",
    mime="text/csv"
)

st.success(
    "Historical Data Analyzer berhasil dijalankan."
)

st.caption(
    "Dashboard ini digunakan untuk pembelajaran "
    "pengolahan data historis dan analisis statistik. "
    "Hasilnya bukan prediksi atau rekomendasi transaksi."
)
