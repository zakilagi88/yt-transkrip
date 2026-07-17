# Goal Description
Mengatasi keterbatasan durasi video (pemotongan 25MB / ~30 menit) menggunakan layanan yang **100% Gratis** untuk video panjang hingga 3 jam.

## Pilihan Solusi Gratis (User Review Required)

Kami memiliki dua metode gratis untuk memproses video berdurasi sangat panjang:

### Opsi 1: Google Gemini 1.5 Flash API (100% GRATIS) - DIREKOMENDASIKAN
Google menyediakan akses API **Gemini 1.5 Flash secara GRATIS** melalui Google AI Studio. 
- **Kelebihan:** 
  - Mendukung file audio berukuran raksasa (hingga 2 Gigabyte / ~9 jam video!).
  - Sangat cepat dan sangat akurat untuk bahasa Indonesia karena model Gemini memahami konteks percakapan dengan sangat baik.
  - Alur kodenya bersih dan tidak membebani komputer Anda.
- **Kekurangan:** Anda perlu mendaftar untuk mendapatkan kunci API Gemini gratis di Google AI Studio (hanya butuh akun Gmail).

### Opsi 2: Pemotongan Audio Otomatis (Audio Chunking) via Groq (100% GRATIS)
Jika Anda bersikeras tetap ingin menggunakan API Groq yang sudah didaftarkan sebelumnya, kita bisa mengakalinya lewat kode program.
- **Kelebihan:** Tidak perlu mendaftar API baru lagi.
- **Kekurangan:** 
  - Komputer Anda harus memotong file audio secara otomatis setiap 20 menit sekali, kemudian mengirimkannya satu per satu ke Groq, lalu menggabungkannya kembali.
  - Memerlukan instalasi *software* tambahan bernama `FFmpeg` di komputer Anda agar program Python bisa memotong audio.
  - Proses transkripsinya menjadi jauh lebih lama karena harus mengantri banyak file ke API.

## Tindakan Selanjutnya
Beri tahu saya di chat, **Opsi mana yang Anda pilih?**
- Jika memilih **Opsi 1 (Gemini)**, saya akan mengubah kode ke Gemini dan memandu Anda mendapatkan API Key gratisnya dalam 2 langkah mudah.
- Jika memilih **Opsi 2 (Groq Chunking)**, kita harus menginstal FFmpeg terlebih dahulu.

Setelah Anda memilih, ketik pilihan Anda di chat atau klik **Proceed**!
