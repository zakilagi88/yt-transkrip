import streamlit as st
import streamlit_shadcn_ui as ui
from youtube_transcript_api import YouTubeTranscriptApi
import json
import re
import os
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

st.set_page_config(page_title="YouTube Transcript", layout="wide")

# Custom CSS for cleaner readability and better dark mode contrast
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

st.title("📺 YouTube Transcript Extractor")
st.markdown("Mudah mengekstrak, mencari, dan mengunduh transkrip dari video YouTube.")

# Handle Sidebar Clicks
if 'selected_url' not in st.session_state:
    st.session_state.selected_url = ""

# Sidebar - History
st.sidebar.header("🕒 Riwayat Pencarian")
history = load_history()
if history:
    for item in history:
        # Provide a button to load the history item instead of a direct link
        if st.sidebar.button(f"🎥 {item['video_id']}", key=f"hist_{item['video_id']}", use_container_width=True):
            st.session_state.selected_url = item['url']
else:
    st.sidebar.write("Belum ada riwayat.")

# Main Input inside a Card with a Form
with ui.card(key="input_card"):
    with st.form("youtube_form"):
        # Pre-fill with selected URL from history if available
        url_input = st.text_input("🔗 Tempelkan Link YouTube di sini:", value=st.session_state.selected_url, placeholder="https://www.youtube.com/watch?v=...")
        submit_button = st.form_submit_button("Ekstrak Transkrip")

if submit_button and url_input:
    # Clear the selected url so the input is free for next time
    st.session_state.selected_url = ""
    
    video_id = get_video_id(url_input)
    
    if not video_id:
        st.error("Tautan YouTube tidak valid. Harap periksa kembali.")
    else:
        # Fetching process
        if 'current_video_id' not in st.session_state or st.session_state.current_video_id != video_id:
            st.session_state.current_video_id = video_id
            try:
                with st.spinner('Sedang mengambil transkrip...'):
                    transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
                    st.session_state.transcript_data = transcript_data
                    save_history(url_input, video_id)
            except Exception as e:
                try:
                    transcript_list = YouTubeTranscriptApi().list(video_id)
                    transcript_data = [t for t in transcript_list][0].fetch()
                    st.session_state.transcript_data = transcript_data
                    save_history(url_input, video_id)
                except Exception as inner_e:
                    st.error(f"Gagal mengambil transkrip. Mungkin transkrip dinonaktifkan. Detail: {inner_e}")
                    st.session_state.transcript_data = None
                
# Only show the rest if we have successfully loaded data
if st.session_state.get('transcript_data') and st.session_state.get('current_video_id'):
    transcript = st.session_state.transcript_data
    video_id = st.session_state.current_video_id
    
    full_text = "\\n".join([
        f"[{format_time(t.start)}] {t.text}" if hasattr(t, 'start') else f"[{format_time(t['start'])}] {t['text']}" 
        for t in transcript
    ])
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Tools row inside a card (Only visible after fetching)
    with ui.card(key="tools_card"):
        col1, col2 = st.columns([3, 1])
        with col1:
            # We use an empty string for the label since it's obvious, or a simple text
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
    
    # Expandable transcript display (Defaults to collapsed)
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
        
        # Render all HTML at once to prevent Streamlit from lagging
        if count_results > 0:
            st.markdown(transcript_html, unsafe_allow_html=True)
        elif search_query:
            st.warning(f"Kata '{search_query}' tidak ditemukan dalam transkrip.")
