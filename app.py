import streamlit as st
import streamlit_shadcn_ui as ui
from youtube_transcript_api import YouTubeTranscriptApi
import json
import re
import os
import requests
from urllib.parse import urlparse, parse_qs

HISTORY_FILE = "history.json"

def get_video_id(url):
    """Extracts video ID from a YouTube URL."""
    try:
        parsed_url = urlparse(url)
        if parsed_url.hostname in ('youtu.be', 'www.youtu.be'):
            return parsed_url.path[1:]
        if parsed_url.hostname in ('youtube.com', 'www.youtube.com'):
            if parsed_url.path == '/watch':
                return parse_qs(parsed_url.query)['v'][0]
            if parsed_url.path.startswith('/embed/'):
                return parsed_url.path.split('/')[2]
            if parsed_url.path.startswith('/v/'):
                return parsed_url.path.split('/')[2]
            if parsed_url.path.startswith('/shorts/'):
                return parsed_url.path.split('/')[2]
            if parsed_url.path.startswith('/live/'):
                return parsed_url.path.split('/')[2]
    except Exception:
        pass
    return None

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_history(url, video_id):
    history = load_history()
    if not any(entry['video_id'] == video_id for entry in history):
        history.insert(0, {'url': url, 'video_id': video_id})
        history = history[:20]
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)

def format_time(seconds):
    """Format seconds to HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def gemini_transcribe_audio(video_id, api_key):
    import tempfile
    import time
    import yt_dlp
    import google.generativeai as genai
    import imageio_ffmpeg
    import subprocess
    import glob
    
    genai.configure(api_key=api_key)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_template = os.path.join(temp_dir, "input.%(ext)s")
        ydl_opts = {
            'format': 'm4a/bestaudio/best',
            'outtmpl': output_template,
            'noplaylist': True,
        }
        
        # 1. Download best audio
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
                downloaded_file = ydl.prepare_filename(info_dict)
        except Exception as e:
            raise Exception(f"Gagal mengunduh audio: {str(e)}")
            
        if not os.path.exists(downloaded_file):
            raise Exception("File audio tidak ditemukan setelah diunduh.")
            
        # 2. Split audio into 10-minute (600s) chunks using ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        chunk_pattern = os.path.join(temp_dir, "chunk_%03d.m4a")
        
        split_cmd = [
            ffmpeg_path,
            "-y",
            "-i", downloaded_file,
            "-f", "segment",
            "-segment_time", "600",
            "-c", "copy",
            chunk_pattern
        ]
        
        try:
            subprocess.run(split_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception as e:
            raise Exception(f"Gagal memotong audio menjadi segmen: {str(e)}")
            
        # 3. Find and sort chunks
        chunk_files = sorted(glob.glob(os.path.join(temp_dir, "chunk_*.m4a")))
        if not chunk_files:
            raise Exception("Gagal memotong audio. Tidak ada file chunk yang dihasilkan.")
            
        result = []
        import re
        pattern = re.compile(r"\[(?:(\d{1,2}):)?(\d{2}):(\d{2})\]\s*(.*)")
        
        total_chunks = len(chunk_files)
        # We can display a progress message on Streamlit if we use st.info but since this is a background function, 
        # let's write to output or return segments smoothly
        for idx, chunk_file in enumerate(chunk_files):
            offset_seconds = idx * 600
            
            try:
                # Upload the chunk
                audio_file = genai.upload_file(path=chunk_file)
                
                # Wait for file processing to complete
                while audio_file.state.name == "PROCESSING":
                    time.sleep(2)
                    audio_file = genai.get_file(audio_file.name)
                    
                if audio_file.state.name == "FAILED":
                    raise Exception(f"Gagal memproses segmen {idx+1} di Google AI.")
                    
                # Transcribe using Gemini 1.5 Flash
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content([
                    audio_file,
                    "Transcribe this audio precisely. Return the transcript with timestamps at the beginning of each sentence or logical segment in the format: [HH:MM:SS] Text. Write the transcript in the original language of the audio (Indonesian)."
                ])
                
                # Clean up the file on the cloud
                audio_file.delete()
                
                # Parse segments
                for line in response.text.split("\n"):
                    cleaned_line = line.replace("**", "").replace("- ", "").strip()
                    match = pattern.match(cleaned_line)
                    if match:
                        h, m, s, content = match.groups()
                        h = int(h) if h else 0
                        m = int(m)
                        s = int(s)
                        start_seconds = offset_seconds + (h * 3600 + m * 60 + s)
                        result.append({
                            "start": start_seconds,
                            "text": content.strip()
                        })
                
                # Delay to prevent rate limits
                if idx < total_chunks - 1:
                    time.sleep(10)
            except Exception as e:
                raise Exception(f"Gagal memproses segmen {idx+1} dari {total_chunks}: {str(e)}")
                
        if not result:
            raise Exception("Gagal menghasilkan transkrip dari segmen audio.")
            
        return result

def fetch_transcript(video_id, custom_proxy=None, use_auto=False, gemini_api_key=None):
    """Fetches the transcript, handling proxies if configured."""
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.proxies import GenericProxyConfig
    
    def get_with_proxy(proxy_url):
        config = GenericProxyConfig(http_url=proxy_url, https_url=proxy_url) if proxy_url else None
        api = YouTubeTranscriptApi(proxy_config=config)
        t_list = api.list(video_id)
        return [t for t in t_list][0].fetch()

    # Try standard fetch first (with or without proxies)
    try:
        if custom_proxy:
            return get_with_proxy(custom_proxy)
            
        if use_auto:
            res = requests.get("https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all", timeout=5)
            proxy_list = [p for p in res.text.strip().split("\\r\\n") if p]
            last_err = None
            for proxy in proxy_list[:3]:
                proxy_url = f"http://{proxy}"
                try:
                    return get_with_proxy(proxy_url)
                except Exception as e:
                    last_err = e
                    continue
            raise Exception(f"Semua Auto Proxy gagal/diblokir. Error terakhir: {str(last_err)}")
            
        # Default (No Proxy)
        return get_with_proxy(None)
        
    except Exception as e:
        error_msg = str(e)
        if "Subtitles are disabled" in error_msg or "No transcripts" in error_msg:
            if gemini_api_key:
                return gemini_transcribe_audio(video_id, gemini_api_key)
            else:
                raise Exception("Subtitles tidak tersedia dari YouTube. Masukkan Gemini API Key di sidebar untuk meng-generate AI Transcript secara otomatis.")
        else:
            raise e


st.set_page_config(page_title="YouTube Transcript", layout="wide")

st.markdown("""
<style>
.transcript-line {
    font-size: 15px;
    line-height: 1.6;
    margin-bottom: 8px;
    padding: 8px 12px;
    border-radius: 6px;
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    color: #1e293b;
}
@media (prefers-color-scheme: dark) {
    .transcript-line {
        background-color: #1e293b;
        border: 1px solid #334155;
        color: #f1f5f9;
    }
    .timestamp-badge {
        color: #f8fafc !important;
        background-color: #475569 !important;
    }
}
.timestamp-badge {
    font-weight: 600;
    color: #0f172a;
    background-color: #cbd5e1;
    padding: 3px 8px;
    border-radius: 4px;
    margin-right: 8px;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)

st.title("📺 YT Transkrip")
st.markdown("Mudah mengekstrak, mencari, dan mengunduh transkrip dari video YouTube.")

if 'selected_url' not in st.session_state:
    st.session_state.selected_url = ""

# Sidebar - Settings (Proxy & AI)
st.sidebar.header("⚙️ Pengaturan Jaringan & AI")
st.sidebar.markdown("<small>Opsi jika video terblokir IP atau tidak memiliki Subtitle.</small>", unsafe_allow_html=True)
use_auto_proxy = st.sidebar.checkbox("Gunakan Proxy Publik (Otomatis)", value=False, help="Mencari proxy gratis. Sering kali tidak stabil.")
custom_proxy = st.sidebar.text_input("Custom Proxy URL:", placeholder="http://12.34.56.78:8080", help="Jika Anda punya proxy yang stabil.")
gemini_api_key = st.sidebar.text_input("Gemini API Key (Opsional - Untuk AI):", type="password", help="Masukkan API Key Gemini Anda (dapatkan gratis di Google AI Studio) agar AI bisa mendengarkan video tanpa subtitle.")

st.sidebar.markdown("---")

# Sidebar - History
st.sidebar.header("🕒 Riwayat Pencarian")
history = load_history()
if history:
    for item in history:
        if st.sidebar.button(f"🎥 {item['video_id']}", key=f"hist_{item['video_id']}", use_container_width=True):
            st.session_state.selected_url = item['url']
else:
    st.sidebar.write("Belum ada riwayat.")


# Main Input
st.markdown("### 📥 Masukkan Link YouTube")
with st.container():
    with st.form("youtube_form"):
        url_input = st.text_input("🔗 Tempelkan Link YouTube di sini:", value=st.session_state.selected_url, placeholder="https://www.youtube.com/watch?v=...")
        submit_button = st.form_submit_button("Ekstrak Transkrip")

if submit_button and url_input:
    st.session_state.selected_url = ""
    video_id = get_video_id(url_input)
    
    if not video_id:
        st.error("Tautan YouTube tidak valid. Harap periksa kembali.")
    else:
        if 'current_video_id' not in st.session_state or st.session_state.current_video_id != video_id:
            st.session_state.current_video_id = video_id
            try:
                with st.spinner('Sedang mengambil transkrip... Mohon tunggu (jika pakai proxy/AI, bisa butuh waktu lebih lama)'):
                    transcript_data = fetch_transcript(video_id, custom_proxy=custom_proxy, use_auto=use_auto_proxy, gemini_api_key=gemini_api_key)
                    st.session_state.transcript_data = transcript_data
                    save_history(url_input, video_id)
            except Exception as e:
                st.error(f"Gagal mengambil transkrip. Detail: {e}")
                st.session_state.transcript_data = None
                
# Display results
if st.session_state.get('transcript_data') and st.session_state.get('current_video_id'):
    transcript = st.session_state.transcript_data
    video_id = st.session_state.current_video_id
    
    full_text = "\\n".join([
        f"[{format_time(t.start)}] {t.text}" if hasattr(t, 'start') else f"[{format_time(t['start'])}] {t['text']}" 
        for t in transcript
    ])
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            search_query = st.text_input("🔍 Cari kata spesifik di transkrip:")
        with col2:
            st.write("")
            st.write("")
            st.download_button(
                label="⬇️ Download (.txt)",
                data=full_text,
                file_name=f"transcript_{video_id}.txt",
                mime="text/plain",
                use_container_width=True
            )
    
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📝 Buka Hasil Transkrip", expanded=False):
        count_results = 0
        transcript_html = ""
        
        for entry in transcript:
            text = entry.text if hasattr(entry, 'text') else entry['text']
            start = entry.start if hasattr(entry, 'start') else entry['start']
            timestamp = format_time(start)
            
            if search_query.lower() in text.lower():
                if search_query:
                    text = re.sub(
                        f"({re.escape(search_query)})", 
                        r"<mark style='background-color: #fde047; color: black; padding: 0 4px; border-radius: 2px;'>\1</mark>", 
                        text, 
                        flags=re.IGNORECASE
                    )
                
                transcript_html += f"<div class='transcript-line'><span class='timestamp-badge'>{timestamp}</span> {text}</div>"
                count_results += 1
        
        if count_results > 0:
            st.markdown(transcript_html, unsafe_allow_html=True)
        elif search_query:
            st.warning(f"Kata '{search_query}' tidak ditemukan dalam transkrip.")
