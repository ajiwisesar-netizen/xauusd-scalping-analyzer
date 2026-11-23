import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# 1. KONFIGURASI
# ==========================================

st.set_page_config(
    page_title="XAUUSD Market Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 XAUUSD Market Analyzer V3")
st.caption("Dashboard edukasi analisis teknikal multi-timeframe")

st.info(
    "Mode edukasi. Data simulasi bukan harga live. "
    "Data CSV berasal dari file yang kamu unggah."
)

# ==========================================
# 2. FUNGSI MEMBUAT DATA SIMULASI
# ==========================================

def create_simulation():

    np.random.seed(42)

    dates = pd.date_range(
        end=pd.Timestamp.now().floor("5min"),
        periods=600,
        freq="5min"
    )

    close = 4000 + np.cumsum(
        np.random.normal(0, 1.5, 600)
    )

    data = pd.DataFrame({
        "time": dates,
        "close": close
    })

    data["open"] = data["close"].shift(1)
    data.loc[0, "open"] = data.loc[0, "close"]

    data["high"] = (
        data[["open", "close"]].max(axis=1) + 1
    )

    data["low"] = (
        data[["open", "close"]].min(axis=1) - 1
    )

    return data

# ==========================================
# 3. FUNGSI MEMBACA CSV
# ==========================================

def load_csv(file):

    data = pd.read_csv(file)

    data.columns = [
        col.strip().lower()
        for col in data.columns
    ]

    required = [
        "time", "open", "high", "low", "close"
    ]

    if not all(col in data.columns for col in required):
        raise ValueError(
            "CSV harus memiliki kolom "
            "time, open, high, low, close."
        )

    data["time"] = pd.to_datetime(
        data["time"],
        errors="coerce"
    )

    for col in ["open", "high", "low", "close"]:
        data[col] = pd.to_numeric(
            data[col],
            errors="coerce"
        )

    data = (
        data.dropna(subset=required)
        .sort_values("time")
        .drop_duplicates(subset=["time"])
        .reset_index(drop=True)
    )

    if len(data) < 60:
        raise ValueError("Data minimal harus 60 candle.")

    return data

# ==========================================
# 4. SIDEBAR DATA
# ==========================================

st.sidebar.header("Pengaturan Data")

uploaded_file = st.sidebar.file_uploader(
    "Upload CSV XAUUSD",
    type=["csv"]
)

if uploaded_file is not None:

    try:
        base_df = load_csv(uploaded_file)
        st.sidebar.success("CSV berhasil dimuat.")

    except Exception as e:
        st.error(f"Kesalahan membaca CSV: {e}")
        st.stop()

else:

    base_df = create_simulation()

    st.sidebar.info(
        "Menggunakan data simulasi M5."
    )

# ==========================================
# 5. VALIDASI OHLC
# ==========================================

valid_ohlc = (
    (base_df["high"] >= base_df[["open", "close"]].max(axis=1))
    &
    (base_df["low"] <= base_df[["open", "close"]].min(axis=1))
    &
    (base_df["high"] >= base_df["low"])
)

if not valid_ohlc.all():
    st.error("Terdapat data OHLC yang tidak valid.")
    st.stop()

# ==========================================
# 6. FUNGSI RESAMPLING TIMEFRAME
# ==========================================

def resample_data(data, rule):

    result = (
        data.set_index("time")
        .resample(rule)
        .agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last"
        })
        .dropna()
        .reset_index()
    )

    return result

# ==========================================
# 7. FUNGSI INDIKATOR
# ==========================================

def calculate_indicators(data):

    data = data.copy()

    data["EMA20"] = data["close"].ewm(
        span=20,
        adjust=False
    ).mean()

    data["EMA50"] = data["close"].ewm(
        span=50,
        adjust=False
    ).mean()

    # RSI 14

    delta = data["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1/14,
        min_periods=14,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1/14,
        min_periods=14,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    data["RSI"] = 100 - (100 / (1 + rs))

    data.loc[
        (avg_loss == 0) & (avg_gain > 0),
        "RSI"
    ] = 100

    data.loc[
        (avg_loss == 0) & (avg_gain == 0),
        "RSI"
    ] = 50

    # ATR 14

    previous_close = data["close"].shift(1)

    tr = pd.concat([
        data["high"] - data["low"],
        (data["high"] - previous_close).abs(),
        (data["low"] - previous_close).abs()
    ], axis=1).max(axis=1)

    data["ATR"] = tr.rolling(14).mean()

    return data

# ==========================================
# 8. FUNGSI MARKET STRUCTURE
# ==========================================

def calculate_structure(data, window=3):

    data = data.copy()

    data["Pivot_High"] = False
    data["Pivot_Low"] = False
    data["Structure"] = ""

    for i in range(window, len(data) - window):

        high_range = data["high"].iloc[
            i-window:i+window+1
        ]

        low_range = data["low"].iloc[
            i-window:i+window+1
        ]

        if data["high"].iloc[i] == high_range.max():
            data.loc[data.index[i], "Pivot_High"] = True

        if data["low"].iloc[i] == low_range.min():
            data.loc[data.index[i], "Pivot_Low"] = True

    previous_high = None
    previous_low = None

    for i in range(len(data)):

        if data["Pivot_High"].iloc[i]:

            current_high = data["high"].iloc[i]

            if previous_high is not None:

                if current_high > previous_high:
                    data.loc[data.index[i], "Structure"] = "HH"
                else:
                    data.loc[data.index[i], "Structure"] = "LH"

            previous_high = current_high

        if data["Pivot_Low"].iloc[i]:

            current_low = data["low"].iloc[i]

            if previous_low is not None:

                if current_low > previous_low:
                    data.loc[data.index[i], "Structure"] = "HL"
                else:
                    data.loc[data.index[i], "Structure"] = "LL"

            previous_low = current_low

    return data

# ==========================================
# 9. FUNGSI ANALISIS TIMEFRAME
# ==========================================

def analyze_timeframe(data):

    if data.empty:
        return "Data tidak cukup"

    last = data.iloc[-1]

    if last["EMA20"] > last["EMA50"]:
        return "EMA naik"

    elif last["EMA20"] < last["EMA50"]:
        return "EMA turun"

    return "EMA netral"

# ==========================================
# 10. PENGATURAN TIMEFRAME
# ==========================================

st.sidebar.header("Timeframe")

selected_tf = st.sidebar.selectbox(
    "Timeframe grafik utama",
    ["M5", "M15", "H1"]
)

window = st.sidebar.slider(
    "Sensitivitas pivot",
    2,
    8,
    3
)

# Data dasar diasumsikan M5

timeframe_data = {
    "M5": base_df.copy(),
    "M15": resample_data(base_df, "15min"),
    "H1": resample_data(base_df, "1h")
}

# Hitung indikator setiap timeframe

for tf in timeframe_data:

    timeframe_data[tf] = calculate_indicators(
        timeframe_data[tf]
    )

    timeframe_data[tf] = calculate_structure(
        timeframe_data[tf],
        window
    )

# ==========================================
# 11. PANEL MULTI-TIMEFRAME
# ==========================================

st.subheader("Perbandingan Tren Multi-Timeframe")

col1, col2, col3 = st.columns(3)

for col, tf in zip(
    [col1, col2, col3],
    ["M5", "M15", "H1"]
):

    trend = analyze_timeframe(
        timeframe_data[tf]
    )

    col.metric(
        f"Timeframe {tf}",
        trend
    )

st.caption(
    "Perbandingan ini berdasarkan posisi EMA20 dan EMA50, "
    "bukan prediksi arah harga."
)

# ==========================================
# 12. DATA TIMEFRAME TERPILIH
# ==========================================

df = timeframe_data[selected_tf].copy()

if len(df) < 60:

    st.warning(
        "Jumlah candle pada timeframe ini kurang dari 60. "
        "Tambahkan data historis."
    )

    st.stop()

last = df.iloc[-1]

# ==========================================
# 13. RINGKASAN INDIKATOR
# ==========================================

st.subheader(f"Ringkasan {selected_tf}")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Harga terakhir",
    f"{last['close']:.2f}"
)

c2.metric(
    "RSI 14",
    f"{last['RSI']:.2f}"
    if pd.notna(last["RSI"]) else "-"
)

c3.metric(
    "ATR 14",
    f"{last['ATR']:.2f}"
    if pd.notna(last["ATR"]) else "-"
)

c4.metric(
    "Jumlah candle",
    str(len(df))
)

# ==========================================
# 14. SUPPORT DAN RESISTANCE
# ==========================================

support_levels = (
    df.loc[df["Pivot_Low"], "low"]
    .tail(5)
    .tolist()
)

resistance_levels = (
    df.loc[df["Pivot_High"], "high"]
    .tail(5)
    .tolist()
)

# ==========================================
# 15. GRAFIK CANDLESTICK
# ==========================================

st.subheader(f"Grafik XAUUSD {selected_tf}")

fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=df["time"],
    open=df["open"],
    high=df["high"],
    low=df["low"],
    close=df["close"],
    name="Candlestick"
))

fig.add_trace(go.Scatter(
    x=df["time"],
    y=df["EMA20"],
    name="EMA 20"
))

fig.add_trace(go.Scatter(
    x=df["time"],
    y=df["EMA50"],
    name="EMA 50"
))

for level in support_levels:

    fig.add_hline(
        y=level,
        line_dash="dash",
        annotation_text=f"Support {level:.2f}"
    )

for level in resistance_levels:

    fig.add_hline(
        y=level,
        line_dash="dot",
        annotation_text=f"Resistance {level:.2f}"
    )

for i, row in df.iterrows():

    if row["Structure"] in ["HH", "LH"]:

        fig.add_annotation(
            x=row["time"],
            y=row["high"],
            text=row["Structure"],
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-25
        )

    elif row["Structure"] in ["HL", "LL"]:

        fig.add_annotation(
            x=row["time"],
            y=row["low"],
            text=row["Structure"],
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=25
        )

fig.update_layout(
    title=f"XAUUSD {selected_tf} - Analisis Teknikal",
    xaxis_title="Waktu",
    yaxis_title="Harga",
    height=650,
    xaxis_rangeslider_visible=False
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# ==========================================
# 16. ANALISIS INDIKATOR
# ==========================================

st.subheader("Pembacaan Indikator")

if last["EMA20"] > last["EMA50"]:

    st.success("EMA20 berada di atas EMA50.")

elif last["EMA20"] < last["EMA50"]:

    st.warning("EMA20 berada di bawah EMA50.")

else:

    st.info("EMA20 dan EMA50 berada pada nilai yang sama.")

if pd.notna(last["RSI"]):

    if last["RSI"] >= 70:

        st.warning("RSI berada di area tinggi.")

    elif last["RSI"] <= 30:

        st.warning("RSI berada di area rendah.")

    else:

        st.info("RSI berada di area tengah.")

# ==========================================
# 17. TABEL SUPPORT DAN RESISTANCE
# ==========================================

st.subheader("Support & Resistance")

col1, col2 = st.columns(2)

with col1:

    st.write("**Support terbaru**")

    if support_levels:

        for level in reversed(support_levels):
            st.write(f"- {level:.2f}")

    else:

        st.write("Belum ditemukan support.")

with col2:

    st.write("**Resistance terbaru**")

    if resistance_levels:

        for level in reversed(resistance_levels):
            st.write(f"- {level:.2f}")

    else:

        st.write("Belum ditemukan resistance.")

# ==========================================
# 18. MARKET STRUCTURE
# ==========================================

st.subheader("Riwayat Market Structure")

structures = df[
    df["Structure"] != ""
][["time", "Structure", "high", "low"]].tail(10)

if not structures.empty:

    st.dataframe(
        structures.sort_values(
            "time",
            ascending=False
        ),
        use_container_width=True
    )

else:

    st.write("Belum ditemukan struktur pasar.")

# ==========================================
# 19. PANDUAN
# ==========================================

with st.expander("Panduan membaca dashboard"):

    st.markdown("""
    **EMA**
    - EMA20: rata-rata pergerakan 20 periode.
    - EMA50: rata-rata pergerakan 50 periode.

    **Momentum dan volatilitas**
    - RSI: indikator momentum.
    - ATR: ukuran volatilitas.

    **Market Structure**
    - HH: Higher High.
    - HL: Higher Low.
    - LH: Lower High.
    - LL: Lower Low.

    **Timeframe**
    - M5: 5 menit.
    - M15: 15 menit.
    - H1: 1 jam.

    Data dasar CSV harus berupa candle M5 agar
    resampling ke M15 dan H1 sesuai.
    """)

st.caption(
    "Dashboard edukasi dan analisis historis. "
    "Bukan sinyal transaksi atau jaminan keuntungan."
)
