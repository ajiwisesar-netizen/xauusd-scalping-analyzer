# CSV Historical Monitor — Streamlit + Telegram

Aplikasi membaca CSV publik dari Google Drive, menampilkan grafik OHLC dan statistik deskriptif di Streamlit, serta mengirim laporan kualitas data ke Telegram saat file berubah.

## Format CSV
Kolom wajib: `time,open,high,low,close`

Contoh:
`2026-11-24 05:00:00,4000,4001,3999,4000.5`

Gunakan file yang memang boleh dibagikan. Siapa pun yang memiliki tautan Anyone with the link dapat mengunduh file tersebut.

## 1. Google Drive
- Atur file menjadi **Anyone with the link — Viewer**.
- Ambil File ID dari tautan `https://drive.google.com/file/d/FILE_ID/view`.

## 2. Deploy Streamlit
- Upload seluruh isi folder ini ke GitHub.
- Buat aplikasi di Streamlit Community Cloud, pilih `app.py`.
- Pada App Settings → Secrets, isi:
  `DRIVE_FILE_ID = "FILE_ID_KAMU"`
- Buka aplikasi. Atau isi link/File ID melalui sidebar.

## 3. Buat Telegram Bot
- Cari `@BotFather` di Telegram, jalankan `/newbot`, dan simpan token secara pribadi.
- Buka chat bot baru lalu tekan Start.
- Isi Chat ID milikmu pada konfigurasi worker. Jangan bagikan token.

## 4. Jalankan worker Telegram
Buat Background Worker di Render dari repository yang sama:
- Build command: `pip install -r requirements.txt`
- Start command: `python bot.py`

Tambahkan environment variables:
- `DRIVE_FILE_ID` = File ID Google Drive
- `TELEGRAM_BOT_TOKEN` = token BotFather
- `TELEGRAM_CHAT_ID` = Chat ID Telegram
- `POLL_SECONDS` = `300`

Worker memeriksa file setiap lima menit dan mengirim laporan jika isi CSV berubah. Perintah: `/start`, `/status`, `/laporan`.

## Catatan
- Streamlit dan worker Telegram adalah dua proses terpisah.
- Jangan commit token, `secrets.toml`, atau data pribadi ke GitHub.
- Unduhan Google Drive dapat gagal jika izin salah, file terlalu besar, atau Google meminta konfirmasi.
- Aplikasi ini hanya untuk pemantauan dan ringkasan kualitas data historis, bukan sinyal BUY/SELL atau rekomendasi entry.
