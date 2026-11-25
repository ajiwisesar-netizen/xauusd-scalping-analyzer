import os, hashlib
import streamlit as st
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from common import extract_drive_id, download_drive_csv, parse_csv_bytes, aggregate_ohlc

st.set_page_config(page_title="CSV Historical Monitor", page_icon="📊", layout="wide")
st.title("Dashboard Pemantauan Data Historis")
st.caption("Google Drive • grafik OHLC • statistik • kualitas data • unduh CSV")

def secret(key, default=""):
    try: return st.secrets.get(key, default)
    except Exception: return os.getenv(key, default)

drive_value = st.sidebar.text_input("Google Drive link atau File ID", value=secret("DRIVE_FILE_ID"))
refresh = st.sidebar.selectbox("Pembaruan tampilan", [30, 60, 120, 300], index=1)
st_autorefresh(interval=refresh*1000, key="auto_refresh")

@st.cache_data(ttl=30, show_spinner=False)
def load(file_id):
    b = download_drive_csv(file_id)
    return parse_csv_bytes(b), hashlib.sha256(b).hexdigest()

if not drive_value:
    st.info("Masukkan link atau File ID CSV Google Drive di panel kiri.")
    st.stop()
try:
    file_id = extract_drive_id(drive_value)
    with st.spinner("Mengambil CSV dari Google Drive..."):
        (df, q), fingerprint = load(file_id)
except Exception as e:
    st.error(f"Gagal membaca CSV: {e}")
    st.stop()

if df.empty:
    st.warning("Tidak ada baris data valid.")
    st.stop()

st.success(f"CSV berhasil dibaca • refresh tampilan setiap {refresh} detik")
a,b,c,d = st.columns(4)
a.metric("Baris valid", f"{q['clean_rows']:,}")
b.metric("Baris awal", f"{q['raw_rows']:,}")
c.metric("Timestamp duplikat", f"{q['duplicate_timestamps']:,}")
d.metric("Interval median", q["median_interval"])

st.subheader("Grafik historis OHLC")
choice = st.selectbox("Interval tampilan", ["M1","M5","M15","H1"])
rule = {"M1":"1min","M5":"5min","M15":"15min","H1":"1h"}[choice]
view = df if choice == "M1" else aggregate_ohlc(df, rule)
fig = go.Figure([go.Candlestick(x=view.time, open=view.open, high=view.high,
                                low=view.low, close=view.close, name="OHLC")])
fig.update_layout(height=540, xaxis_rangeslider_visible=False,
                  xaxis_title="Waktu", yaxis_title="Nilai")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Statistik deskriptif")
st.dataframe({
    "Metrik":["Close terakhir","Rata-rata close","Low minimum","High maksimum",
              "Rata-rata rentang high-low","Perubahan close awal ke akhir"],
    "Nilai":[df.close.iloc[-1],df.close.mean(),df.low.min(),df.high.max(),
             (df.high-df.low).mean(),df.close.iloc[-1]-df.close.iloc[0]]
}, use_container_width=True, hide_index=True)

st.subheader("Kualitas data")
st.dataframe({
    "Pemeriksaan":["Timestamp tidak valid","Nilai numerik tidak valid",
                   "OHLC tidak valid","Timestamp duplikat"],
    "Jumlah":[q["invalid_timestamps"],q["invalid_numeric_rows"],
              q["invalid_ohlc_rows"],q["duplicate_timestamps"]]
}, use_container_width=True, hide_index=True)
st.caption(f"Rentang waktu: {q['first_time']} sampai {q['last_time']}. Jeda waktu perlu ditafsirkan sesuai sesi dan sumber data.")
st.subheader("Data terbaru")
st.dataframe(df.tail(100), use_container_width=True, hide_index=True)
st.download_button("Download CSV hasil pembersihan", df.to_csv(index=False).encode("utf-8"),
                   "historical_cleaned.csv", "text/csv", use_container_width=True)
st.caption("Aplikasi ini merangkum data historis dan kualitasnya; bukan prediksi atau rekomendasi transaksi.")
