import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==================================
# KONFIGURASI DASHBOARD
# ==================================

st.set_page_config(
    page_title="Historical Data Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Historical Data Analysis Dashboard")
st.caption(
    "Dashboard pembelajaran untuk pengolahan "
    "dan analisis statistik data historis."
)

# ==================================
# FUNGSI DATA SINTETIS
# ==================================

def generate_sample_data(n=300):

    np.random.seed(42)

    dates = pd.date_range(
        end=pd.Timestamp.now(),
        periods=n,
        freq="5min"
    )

    close = 100 + np.cumsum(
        np.random.normal(0, 0.5, n)
    )

    open_price = np.insert(close[:-1], 0, close[0])

    high = np.maximum(open_price, close) + np.random.uniform(
        0.05, 0.5, n
    )

    low = np.minimum(open_price, close) - np.random.uniform(
        0.05, 0.5, n
    )

    return pd.DataFrame({
        "time": dates,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close
    })


# ==================================
# VALIDASI DATA
# ==================================

def validate_data(raw_df):

    required = [
        "time", "open", "high", "low", "close"
    ]

    missing = [
        col for col in required
        if col not in raw_df.columns
    ]

    if missing:
        return None, (
            "Kolom wajib tidak ditemukan: "
            + ", ".join(missing)
        )

    df = raw_df[required].copy()

    df["time"] = pd.to_datetime(
        df["time"],
        errors="coerce"
    )

    numeric_cols = [
        "open", "high", "low", "close"
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    before = len(df)

    df = df.dropna(subset=required)

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

    df = df.sort_values("time").reset_index(drop=True)

    removed = before - len(df)

    if df.empty:
        return None, "Tidak ada data valid."

    return (df, removed), None


# ==================================
# INDIKATOR STATISTIK
# ==================================

def calculate_indicators(df):

    df = df.copy()

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

    rs = avg_gain / avg_loss.replace(0, np.nan)

    df["RSI14"] = 100 - (100 / (1 + rs))

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

    df["Change"] = df["close"].diff()

    return df


# ==================================
# PILIH SUMBER DATA
# ==================================

st.sidebar.header("Pengaturan Data")

source = st.sidebar.radio(
    "Sumber data",
    [
        "Data contoh sintetis",
        "Upload CSV historical"
    ]
)

if source == "Upload CSV historical":

    uploaded_file = st.sidebar.file_uploader(
        "Pilih file CSV",
        type=["csv"]
    )

    if uploaded_file is None:
        st.info(
            "Silakan upload file CSV untuk memulai."
        )
        st.stop()

    try:
        raw_df = pd.read_csv(uploaded_file)

        result, error = validate_data(raw_df)

        if error:
            st.error(error)
            st.stop()

        df, removed = result

    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
        st.stop()

else:

    df = generate_sample_data()
    removed = 0


# ==================================
# HITUNG INDIKATOR
# ==================================

df = calculate_indicators(df)

# ==================================
# INFORMASI DATA
# ==================================

st.subheader("Ringkasan Data")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Jumlah Data",
    f"{len(df):,}"
)

col2.metric(
    "Nilai Terakhir",
    f"{df['close'].iloc[-1]:.3f}"
)

col3.metric(
    "Nilai Tertinggi",
    f"{df['high'].max():.3f}"
)

col4.metric(
    "Nilai Terendah",
    f"{df['low'].min():.3f}"
)

st.caption(
    f"Periode: {df['time'].min()} sampai "
    f"{df['time'].max()}"
)

st.caption(
    f"Baris yang dibersihkan: {removed}"
)

# ==================================
# GRAFIK CANDLESTICK
# ==================================

st.subheader("Grafik Historical Data")

fig = go.Figure()

fig.add_trace(
    go.Candlestick(
        x=df["time"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="Historical Data"
    )
)

fig.add_trace(
    go.Scatter(
        x=df["time"],
        y=df["EMA20"],
        name="EMA 20",
        line=dict(width=1.5)
    )
)

fig.add_trace(
    go.Scatter(
        x=df["time"],
        y=df["EMA50"],
        name="EMA 50",
        line=dict(width=1.5)
    )
)

fig.update_layout(
    height=550,
    xaxis_title="Waktu",
    yaxis_title="Nilai",
    xaxis_rangeslider_visible=False,
    template="plotly_dark"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# ==================================
# GRAFIK RSI
# ==================================

st.subheader("Grafik RSI 14")

rsi_fig = go.Figure()

rsi_fig.add_trace(
    go.Scatter(
        x=df["time"],
        y=df["RSI14"],
        name="RSI 14"
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
    yaxis_title="RSI",
    yaxis_range=[0, 100]
)

st.plotly_chart(
    rsi_fig,
    use_container_width=True
)

# ==================================
# GRAFIK ATR
# ==================================

st.subheader("Grafik ATR 14")

atr_fig = go.Figure()

atr_fig.add_trace(
    go.Scatter(
        x=df["time"],
        y=df["ATR14"],
        name="ATR 14"
    )
)

atr_fig.update_layout(
    height=300,
    template="plotly_dark",
    yaxis_title="ATR"
)

st.plotly_chart(
    atr_fig,
    use_container_width=True
)

# ==================================
# STATISTIK HISTORIS
# ==================================

st.subheader("Statistik Historical Data")

stats = df[
    ["open", "high", "low", "close", "RSI14", "ATR14"]
].describe().T

st.dataframe(
    stats,
    use_container_width=True
)

# ==================================
# TABEL DATA
# ==================================

st.subheader("Tabel Data Terbaru")

st.dataframe(
    df.tail(20),
    use_container_width=True
)

# ==================================
# DOWNLOAD HASIL
# ==================================

st.subheader("Download Hasil Analisis")

csv = df.to_csv(
    index=False
).encode("utf-8")

st.download_button(
    label="📥 Download Hasil CSV",
    data=csv,
    file_name="historical_analysis.csv",
    mime="text/csv"
)

st.success(
    "Dashboard berhasil memproses data."
)

st.caption(
    "Catatan: Data sintetis hanya untuk demonstrasi. "
    "Indikator merupakan perhitungan historis, "
    "bukan prediksi atau rekomendasi transaksi."
    )
