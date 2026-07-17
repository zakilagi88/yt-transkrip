# Goal Description
Menambahkan fitur **AI Auto-Transcription (Speech-to-Text)** untuk mengatasi video YouTube yang sama sekali tidak memiliki *subtitle* atau *auto-caption* (termasuk video *live* berbahasa Indonesia).

## Akar Masalah
Library `youtube-transcript-api` hanya bertugas "mencuri/mengambil" teks yang sudah disiapkan oleh YouTube. Jika teks itu tidak ada, ia akan menyerah. 
Untuk mendapatkan teks dari video yang kosong, kita harus **mendengarkan audionya dan mengubahnya menjadi teks menggunakan AI**.

## Solusi Arsitektur
Kita akan mengubah alur kerja aplikasi kita jika video tidak memiliki transkrip bawaan:
1. **Unduh Audio:** Menggunakan `yt-dlp` (ekstrak audio MP3/M4A dari YouTube).
2. **Transkripsi dengan AI:** Mengirimkan audio tersebut ke model AI *Speech-to-Text* (seperti **Whisper**) yang sangat pintar memahami bahasa Indonesia.

## User Review Required & Open Questions

> [!WARNING]
> Menjalankan AI untuk mendengar dan mengetik teks membutuhkan tenaga komputasi yang besar. Karena aplikasi ini ditargetkan untuk di-deploy di **Streamlit Cloud (Gratis)**, server mereka tidak cukup kuat untuk menjalankan AI ini secara mandiri (akan langsung *crash* karena kehabisan RAM).

Oleh karena itu, Anda harus memilih salah satu dari dua opsi berikut:

### Opsi 1: Menggunakan API AI Cloud (Sangat Direkomendasikan)
Kita akan menyambungkan aplikasi kita ke layanan penyedia AI seperti **Groq** atau **OpenAI**. 
- **Cara Kerja:** Aplikasi mendownload audio berukuran kecil -> Dikirim ke server Groq -> Groq membalas dengan teks transkrip instan.
- **Kelebihan:** Sangat cepat (hanya hitungan detik), sangat akurat untuk Bahasa Indonesia, dan 100% lancar di Streamlit Cloud.
- **Syarat:** Anda harus mendaftar dan menempelkan **API Key** (Kunci Akses) di aplikasi. *(Catatan: Saat ini API Groq menyediakan akses gratis yang sangat cepat untuk model Whisper).*

### Opsi 2: Menjalankan AI Lokal (Hanya untuk Localhost)
Kita menginstal model AI Whisper langsung di dalam kode Python kita.
- **Cara Kerja:** Komputer Anda sendiri yang akan mendengarkan audio dan mengetik teksnya.
- **Kelebihan:** Gratis 100% selamanya, tidak butuh API Key.
- **Kekurangan Utama:** **TIDAK BISA** di-deploy di Streamlit Cloud (pasti gagal). Prosesnya lambat (bisa bermenit-menit tergantung spesifikasi Laptop/PC Anda). Anda juga harus menginstal *software* tambahan bernama `FFmpeg` di komputer Anda.

## Tindakan Selanjutnya
Beri tahu saya di chat, **Opsi mana yang Anda pilih (Opsi 1 atau Opsi 2)?** 
Jika memilih Opsi 1, apakah Anda setuju menggunakan **Groq API** (karena gratis dan cepat)? 

Setelah Anda memilih, tekan tombol **Proceed** atau balas chat, dan saya akan merombak kodenya.
