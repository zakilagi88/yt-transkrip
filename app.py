import streamlit as st
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
    # Check if already exists
    if not any(entry['video_id'] == video_id for entry in history):
        history.insert(0, {'url': url, 'video_id': video_id})
        # Keep only the last 20
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

st.set_page_config(page_title="YouTube Transcript Extractor", layout="wide")

st.title("📺 YouTube Transcript Extractor")
st.markdown("Mudah mengekstrak, mencari, dan mengunduh transkrip dari video YouTube.")

# Sidebar - History
st.sidebar.header("🕒 Riwayat Pencarian")
history = load_history()
if history:
    for item in history:
        st.sidebar.markdown(f"- [{item['video_id']}]({item['url']})")
else:
    st.sidebar.write("Belum ada riwayat.")

# Main input
url_input = st.text_input("🔗 Tempelkan Link YouTube di sini:", placeholder="https://www.youtube.com/watch?v=...")

if url_input:
    video_id = get_video_id(url_input)
    
    if not video_id:
        st.error("Tautan YouTube tidak valid. Harap periksa kembali.")
    else:
        st.success(f"Video ID ditemukan: `{video_id}`")
        
        # We can store the transcript in session state so it doesn't reload on every UI interaction
        if 'current_video_id' not in st.session_state or st.session_state.current_video_id != video_id:
            st.session_state.current_video_id = video_id
            try:
                with st.spinner('Sedang mengambil transkrip...'):
                    transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
                    st.session_state.transcript_data = transcript_data
                    save_history(url_input, video_id)
            except Exception as e:
                # Try fetching list and getting first available
                try:
                    transcript_list = YouTubeTranscriptApi().list(video_id)
                    # get the first available transcript (could be any language)
                    transcript_data = [t for t in transcript_list][0].fetch()
                    st.session_state.transcript_data = transcript_data
                    save_history(url_input, video_id)
                except Exception as inner_e:
                    st.error(f"Gagal mengambil transkrip. Mungkin transkrip dinonaktifkan untuk video ini. Detail: {inner_e}")
                    st.session_state.transcript_data = None
                
        if st.session_state.get('transcript_data'):
            transcript = st.session_state.transcript_data
            
            # Formatting full text for download
            full_text = "\\n".join([
                f"[{format_time(t.start)}] {t.text}" if hasattr(t, 'start') else f"[{format_time(t['start'])}] {t['text']}" 
                for t in transcript
            ])
            
            # Tools row
            col1, col2 = st.columns([1, 1])
            with col1:
                search_query = st.text_input("🔍 Cari kata di dalam transkrip:")
            with col2:
                # Add some spacing to align with text input
                st.write("")
                st.write("")
                st.download_button(
                    label="⬇️ Download (.txt)",
                    data=full_text,
                    file_name=f"transcript_{video_id}.txt",
                    mime="text/plain"
                )
            
            st.markdown("### 📝 Transkrip")
            st.markdown("---")
            
            # Display transcript
            count_results = 0
            for entry in transcript:
                text = entry.text if hasattr(entry, 'text') else entry['text']
                start = entry.start if hasattr(entry, 'start') else entry['start']
                timestamp = format_time(start)
                
                # Filter by search
                if search_query.lower() in text.lower():
                    # Highlight keyword
                    if search_query:
                        highlighted_text = re.sub(
                            f"({re.escape(search_query)})", 
                            r"<mark>\\1</mark>", 
                            text, 
                            flags=re.IGNORECASE
                        )
                        st.markdown(f"**[{timestamp}]** {highlighted_text}", unsafe_allow_html=True)
                    else:
                        st.markdown(f"**[{timestamp}]** {text}")
                    count_results += 1
                    
            if search_query and count_results == 0:
                st.warning(f"Kata '{search_query}' tidak ditemukan dalam transkrip.")
