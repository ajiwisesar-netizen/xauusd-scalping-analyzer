import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="XAUUSD Learning Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 XAUUSD Market Learning Dashboard")
st.caption("Dashboard edukasi analisis pasar emas")

st.info(
    "Mode edukasi: menggunakan data simulasi, "
    "bukan harga pasar langsung."
)

# Data simulasi
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

df["high"] = df[["open", "close"]].max(axis=1) + 1
df["low"] = df[["open", "close"]].min(axis=1) - 1

# EMA 20 dan EMA 50
df["EMA20"] = df["close"].ewm(span=20).mean()
df["EMA50"] = df["close"].ewm(span=50).mean()

# RSI 14
delta = df["close"].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)

avg_gain = gain.ewm(
    alpha=1/14,
    min_periods=14
).mean()

avg_loss = loss.ewm(
    alpha=1/14,
    min_periods=14
).mean()

rs = avg_gain / avg_loss.replace(0, np.nan)
df["RSI"] = 100 - (100 / (1 + rs))

# ATR 14
previous_close = df["close"].shift(1)

tr = pd.concat([
    df["high"] - df["low"],
    (df["high"] - previous_close).abs(),
    (df["low"] - previous_close).abs()
], axis=1).max(axis=1)

df["ATR"] = tr.rolling(14).mean()

# Informasi indikator
col1, col2, col3 = st.columns(3)

col1.metric(
    "Harga Simulasi",
    f"{df['close'].iloc[-1]:.2f}"
)

col2.metric(
    "RSI 14",
    f"{df['RSI'].iloc[-1]:.2f}"
)

col3.metric(
    "ATR 14",
    f"{df['ATR'].iloc[-1]:.2f}"
)

# Grafik candlestick
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

fig.update_layout(
    title="XAUUSD - Data Simulasi",
    xaxis_title="Waktu",
    yaxis_title="Harga Simulasi",
    height=550,
    xaxis_rangeslider_visible=False
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# Pembacaan indikator
st.subheader("Analisis Indikator")

if df["EMA20"].iloc[-1] > df["EMA50"].iloc[-1]:
    st.success("EMA 20 berada di atas EMA 50.")
else:
    st.warning("EMA 20 berada di bawah EMA 50.")

rsi = df["RSI"].iloc[-1]

if rsi >= 70:
    st.warning("RSI berada di area tinggi.")
elif rsi <= 30:
    st.warning("RSI berada di area rendah.")
else:
    st.info("RSI berada di area tengah.")

st.caption(
    "Data ini merupakan simulasi untuk pembelajaran. "
    "Bukan harga Valetax dan bukan sinyal transaksi."
)
