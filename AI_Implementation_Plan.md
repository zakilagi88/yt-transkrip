# Goal Description
Mem-bypass batasan **250K TPM (Tokens Per Minute)** dari Google AI Studio Free Tier agar bisa mentranskripsi video panjang (seperti video 2 jam 48 menit) secara **100% Gratis**.

## Analisis Masalah (Matematika Token)
- **1 detik audio** yang dikirim ke Gemini dikonversi menjadi sekitar **258 token**.
- Video **15 menit** = 900 detik = **~232.000 token** (Hampir menyentuh batas 250K TPM).
- Video **2 jam 48 menit** = 10.080 detik = **~2.600.000 token** (Melebihi batas TPM hingga 10x lipat!).

Oleh karena itu, jika kita mengirim seluruh audio sekaligus, Gemini akan menolak dengan error `429 Resource Exhausted`.

## Solusi: Portabel Chunking (Pemotongan Audio Otomatis)
Kita akan memotong audio menjadi segmen-segmen kecil berdurasi **10 menit** (~154.000 token per segmen), mentranskripsinya secara bertahap (sequential), lalu menggabungkannya kembali.

Agar proses pemotongan ini berjalan lancar di komputer Anda (Localhost) maupun di Streamlit Cloud **tanpa perlu menginstal FFmpeg secara manual**, kita akan menggunakan trik berikut:
1. Menambahkan library `imageio-ffmpeg` ke dalam `requirements.txt`. Library ini akan mengunduh file program `ffmpeg.exe` portabel secara otomatis saat aplikasi dijalankan.
2. Memotong audio menggunakan perintah `ffmpeg` portabel tersebut secara instan (tanpa membebani CPU karena hanya memotong *stream*).
3. Mengirimkan potongan audio (maksimal 10 menit) satu per satu ke Gemini dengan jeda waktu aman (*rate limit delay*) agar tidak terkena blokir TPM.

## Proposed Changes

### 1. `requirements.txt`
Menambahkan library pendukung:
- `imageio-ffmpeg` (untuk menyediakan FFmpeg portabel secara otomatis).

### 2. `app.py`
Mengubah fungsi `gemini_transcribe_audio`:
- Menggunakan `imageio_ffmpeg.get_ffmpeg_exe()` untuk memotong audio utama menjadi beberapa file berdurasi 10 menit.
- Mengunggah dan mentranskripsi setiap segmen secara berurutan.
- Menggabungkan teks transkrip dengan penyesuaian penanda waktu (*timestamp offset*).

---

## Rencana Verifikasi

### Manual Verification
- Uji coba dengan video berdurasi pendek (< 5 menit) untuk memastikan alur kerja pemotongan berfungsi.
- Uji coba dengan video berdurasi panjang (> 30 menit) menggunakan Gemini API Key Anda.

Harap klik **Proceed** jika Anda menyetujui rencana ini!
