import re, os, tempfile
import gdown
import pandas as pd

REQUIRED = ["time", "open", "high", "low", "close"]

def extract_drive_id(value):
    value = (value or "").strip()
    m = re.search(r"/file/d/([A-Za-z0-9_-]+)", value) or re.search(r"[?&]id=([A-Za-z0-9_-]+)", value)
    if m: return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{10,}", value): return value
    raise ValueError("Link Google Drive/File ID tidak dikenali.")

def download_drive_csv(file_id):
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        path = tmp.name
    try:
        result = gdown.download(id=file_id, output=path, quiet=True, fuzzy=True)
        if not result or os.path.getsize(path) == 0:
            raise RuntimeError("Unduhan gagal. Periksa izin Anyone with the link dan File ID.")
        with open(path, "rb") as f: return f.read()
    finally:
        try: os.remove(path)
        except OSError: pass

def parse_csv_bytes(content):
    import io
    raw = pd.read_csv(io.BytesIO(content))
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    missing = [c for c in REQUIRED if c not in raw.columns]
    if missing: raise ValueError("Kolom wajib tidak ditemukan: " + ", ".join(missing))
    raw_count = len(raw)
    duplicate_count = int(raw.duplicated(subset=["time"]).sum())
    df = raw[REQUIRED].copy()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    bad_time = int(df["time"].isna().sum())
    bad_numeric = int(df[["open","high","low","close"]].isna().any(axis=1).sum())
    valid = ((df["high"] >= df[["open","close","low"]].max(axis=1)) &
             (df["low"] <= df[["open","close","high"]].min(axis=1)) &
             (df["high"] >= df["low"]))
    bad_ohlc = int((~valid & df["time"].notna()).sum())
    clean = df.dropna(subset=REQUIRED).copy()
    clean = clean[valid.loc[clean.index]].drop_duplicates("time", keep="last")
    clean = clean.sort_values("time").reset_index(drop=True)
    gaps = clean["time"].diff().dropna()
    med = str(gaps.median()) if not gaps.empty else "Tidak cukup data"
    q = {
        "raw_rows": raw_count, "clean_rows": len(clean),
        "duplicate_timestamps": duplicate_count, "invalid_timestamps": bad_time,
        "invalid_numeric_rows": bad_numeric, "invalid_ohlc_rows": bad_ohlc,
        "median_interval": med,
        "first_time": clean["time"].min() if len(clean) else None,
        "last_time": clean["time"].max() if len(clean) else None
    }
    return clean, q

def aggregate_ohlc(df, rule):
    if df.empty: return df.copy()
    return (df.set_index("time").resample(rule)
            .agg({"open":"first","high":"max","low":"min","close":"last"})
            .dropna().reset_index())
