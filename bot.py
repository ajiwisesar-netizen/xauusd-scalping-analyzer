import os, time, hashlib, requests
from common import download_drive_csv, parse_csv_bytes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","").strip()
FILE_ID = os.getenv("DRIVE_FILE_ID","").strip()
INTERVAL = int(os.getenv("POLL_SECONDS","300"))
if not all([TOKEN, CHAT_ID, FILE_ID]):
    raise SystemExit("Atur TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, dan DRIVE_FILE_ID.")

API = f"https://api.telegram.org/bot{TOKEN}"

def send(text):
    r = requests.post(API+"/sendMessage", json={"chat_id":CHAT_ID,"text":text}, timeout=25)
    r.raise_for_status()

def report():
    raw = download_drive_csv(FILE_ID)
    df, q = parse_csv_bytes(raw)
    msg = (
        "📊 LAPORAN PEMANTAUAN CSV\\n\\n"
        f"Baris valid: {q['clean_rows']}\\nBaris awal: {q['raw_rows']}\\n"
        f"Timestamp duplikat: {q['duplicate_timestamps']}\\n"
        f"Timestamp tidak valid: {q['invalid_timestamps']}\\n"
        f"Nilai numerik tidak valid: {q['invalid_numeric_rows']}\\n"
        f"OHLC tidak valid: {q['invalid_ohlc_rows']}\\n"
        f"Interval median: {q['median_interval']}\\n"
        f"Rentang: {q['first_time']} — {q['last_time']}\\n\\n"
        "Ringkasan kualitas data historis, bukan sinyal atau rekomendasi transaksi."
    )
    return hashlib.sha256(raw).hexdigest(), msg

def main():
    send("✅ CSV Monitor Bot aktif. Perintah: /start, /status, /laporan")
    last_hash = None
    offset = None
    while True:
        try:
            digest, msg = report()
            if last_hash is not None and digest != last_hash:
                send("🔄 File Google Drive berubah.\\n\\n"+msg)
            last_hash = digest
        except Exception as e:
            print("Pemeriksaan CSV gagal:", repr(e))
        try:
            params = {"timeout":10}
            if offset is not None: params["offset"] = offset
            data = requests.get(API+"/getUpdates", params=params, timeout=20).json()
            for item in data.get("result", []):
                offset = item["update_id"] + 1
                m = item.get("message", {})
                chat = str(m.get("chat",{}).get("id",""))
                cmd = (m.get("text") or "").split()
                if chat != CHAT_ID or not cmd: continue
                command = cmd[0].lower()
                if command == "/start": send("Bot aktif. Gunakan /status atau /laporan.")
                elif command == "/status": send(f"🟢 Bot aktif. Pemeriksaan setiap {INTERVAL} detik.")
                elif command == "/laporan":
                    _, text = report()
                    send(text)
        except Exception as e:
            print("Polling Telegram gagal:", repr(e))
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
