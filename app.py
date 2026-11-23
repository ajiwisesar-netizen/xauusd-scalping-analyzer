import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# 1. KONFIGURASI DASHBOARD
# ==========================================

st.set_page_config(
    page_title="XAUUSD Market Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 XAUUSD Market Analyzer")
st.caption("Dashboard edukasi analisis teknikal emas")

st.info(
    "Mode edukasi. Data simulasi bukan harga live. "
    "Data CSV berasal dari file yang kamu unggah."
)

# ==========================================
# 2. UPLOAD DATA CSV
# ==========================================

st.sidebar.header("Pengaturan Data")

uploaded_file = st.sidebar.file_uploader(
    "Upload data candle XAUUSD",
    type=["csv"]
)

if uploaded_file is not None:

    try:
        df = pd.read_csv(uploaded_file)

        df.columns = [
            col.strip().lower()
            for col in df.columns
        ]

        required = [
            "time", "open", "high", "low", "close"
        ]

        if not all(col in df.columns for col in required):
            st.error(
                "CSV harus memiliki kolom: "
                "time, open, high, low, close."
            )
            st.stop()

        df["time"] = pd.to_datetime(
            df["time"],
            errors="coerce"
        )

        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        df = df.dropna(
            subset=required
        ).sort_values("time").reset_index(drop=True)

        if len(df) < 60:
            st.error("Data minimal harus 60 candle.")
            st.stop()

        st.success("Data CSV berhasil dimuat.")

    except Exception as e:
        st.error(f"Gagal membaca CSV: {e}")
        st.stop()

else:

    st.sidebar.info("Menggunakan data simulasi.")

    np.random.seed(42)

    dates = pd.date_range(
        end=pd.Timestamp.now(),
        periods=150,
        freq="5min"
    )

    close = 4000 + np.cumsum(
        np.random.normal(0, 1.5, 150)
    )

    df = pd.DataFrame({
        "time": dates,
        "close": close
    })

    df["open"] = df["close"].shift(1)
    df.loc[0, "open"] = df.loc[0, "close"]

    df["high"] = (
        df[["open", "close"]].max(axis=1) + 1
    )

    df["low"] = (
        df[["open", "close"]].min(axis=1) - 1
    )

# ==========================================
# 3. VALIDASI DATA
# ==========================================

if not (
    (df["high"] >= df[["open", "close"]].max(axis=1)).all()
    and
    (df["low"] <= df[["open", "close"]].min(axis=1)).all()
    and
    (df["high"] >= df["low"]).all()
):
    st.error("Terdapat data OHLC yang tidak valid.")
    st.stop()

# ==========================================
# 4. EMA 20 DAN EMA 50
# ==========================================

df["EMA20"] = df["close"].ewm(
    span=20,
    adjust=False
).mean()

df["EMA50"] = df["close"].ewm(
    span=50,
    adjust=False
).mean()

# ==========================================
# 5. RSI 14
# ==========================================

delta = df["close"].diff()

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

df["RSI"] = 100 - (100 / (1 + rs))

df.loc[
    (avg_loss == 0) & (avg_gain > 0),
    "RSI"
] = 100

df.loc[
    (avg_loss == 0) & (avg_gain == 0),
    "RSI"
] = 50

# ==========================================
# 6. ATR 14
# ==========================================

previous_close = df["close"].shift(1)

tr = pd.concat([
    df["high"] - df["low"],
    (df["high"] - previous_close).abs(),
    (df["low"] - previous_close).abs()
], axis=1).max(axis=1)

df["ATR"] = tr.rolling(14).mean()

# ==========================================
# 7. PIVOT HIGH DAN PIVOT LOW
# ==========================================

window = st.sidebar.slider(
    "Sensitivitas pivot",
    min_value=2,
    max_value=8,
    value=3
)

df["Pivot_High"] = False
df["Pivot_Low"] = False

for i in range(window, len(df) - window):

    high_range = df["high"].iloc[
        i-window:i+window+1
    ]

    low_range = df["low"].iloc[
        i-window:i+window+1
    ]

    if df["high"].iloc[i] == high_range.max():
        df.loc[i, "Pivot_High"] = True

    if df["low"].iloc[i] == low_range.min():
        df.loc[i, "Pivot_Low"] = True

# ==========================================
# 8. MARKET STRUCTURE
# ==========================================

df["Structure"] = ""

previous_high = None
previous_low = None

for i in range(len(df)):

    if df["Pivot_High"].iloc[i]:

        current_high = df["high"].iloc[i]

        if previous_high is not None:

            if current_high > previous_high:
                df.loc[i, "Structure"] = "HH"
            else:
                df.loc[i, "Structure"] = "LH"

        previous_high = current_high

    if df["Pivot_Low"].iloc[i]:

        current_low = df["low"].iloc[i]

        if previous_low is not None:

            if current_low > previous_low:
                df.loc[i, "Structure"] = "HL"
            else:
                df.loc[i, "Structure"] = "LL"

        previous_low = current_low

# ==========================================
# 9. SUPPORT DAN RESISTANCE
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
# 10. RINGKASAN DASHBOARD
# ==========================================

st.subheader("Ringkasan Pasar")

last = df.iloc[-1]

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
    f"{len(df)}"
)

# ==========================================
# 11. GRAFIK CANDLESTICK
# ==========================================

st.subheader("Grafik Analisis XAUUSD")

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

# Garis support

for level in support_levels:

    fig.add_hline(
        y=level,
        line_dash="dash",
        annotation_text=f"Support {level:.2f}"
    )

# Garis resistance

for level in resistance_levels:

    fig.add_hline(
        y=level,
        line_dash="dot",
        annotation_text=f"Resistance {level:.2f}"
    )

# Label market structure

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
    title="Candlestick + EMA + Support & Resistance",
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
# 12. ANALISIS INDIKATOR
# ==========================================

st.subheader("Analisis Indikator")

if last["EMA20"] > last["EMA50"]:
    st.success("EMA20 berada di atas EMA50.")
else:
    st.warning("EMA20 berada di bawah EMA50.")

if pd.notna(last["RSI"]):

    if last["RSI"] >= 70:
        st.warning("RSI berada di area tinggi.")

    elif last["RSI"] <= 30:
        st.warning("RSI berada di area rendah.")

    else:
        st.info("RSI berada di area tengah.")

# ==========================================
# 13. SUPPORT DAN RESISTANCE
# ==========================================

st.subheader("Support & Resistance")

col1, col2 = st.columns(2)

with col1:

    st.write("**Support terbaru**")

    if support_levels:

        for level in reversed(support_levels):
            st.write(f"- {level:.2f}")

    else:
        st.write("Belum ditemukan pivot support.")

with col2:

    st.write("**Resistance terbaru**")

    if resistance_levels:

        for level in reversed(resistance_levels):
            st.write(f"- {level:.2f}")

    else:
        st.write("Belum ditemukan pivot resistance.")

# ==========================================
# 14. MARKET STRUCTURE
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
# 15. PENJELASAN
# ==========================================

with st.expander("Panduan membaca indikator"):

    st.write("""
    - EMA20: rata-rata pergerakan harga periode 20.
    - EMA50: rata-rata pergerakan harga periode 50.
    - RSI: indikator momentum.
    - ATR: ukuran volatilitas harga.
    - Support: area yang berasal dari pivot low.
    - Resistance: area yang berasal dari pivot high.
    - HH: Higher High.
    - HL: Higher Low.
    - LH: Lower High.
    - LL: Lower Low.

    Pivot baru diketahui setelah sejumlah candle
    di sebelah kanannya terbentuk.
    """)

st.caption(
    "Dashboard ini untuk pembelajaran dan analisis historis. "
    "Bukan rekomendasi transaksi atau jaminan hasil."
)
