import streamlit as st
import yt_dlp
import os
import re
import subprocess
import uuid
import time
import shutil

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="YouTube Downloader Pro",
    page_icon="🎬",
    layout="centered"
)

DOWNLOAD_DIR = "downloads"
ENCODE_DIR = "encoded"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(ENCODE_DIR, exist_ok=True)

# =========================
# FFMPEG AUTO DETECT (WAJIB)
# =========================
def get_ffmpeg_path():
    if os.name == "nt":  # Windows
        return r"C:\ffmpeg\bin\ffmpeg.exe"
    return shutil.which("ffmpeg")  # Linux (Streamlit Cloud)

FFMPEG_PATH = get_ffmpeg_path()

# =========================
# SESSION STATE
# =========================
if "last_file" not in st.session_state:
    st.session_state.last_file = None

# =========================
# HELPER
# =========================
def clean_filename(title, max_length=80):
    title = re.sub(r'[\\/*?:"<>|]', '', title)
    title = title.encode("ascii", "ignore").decode()
    title = re.sub(r'\s+', ' ', title).strip()
    if len(title) > max_length:
        title = title[:max_length].rstrip()
    return title


def cleanup_old_files(folder, max_age_minutes=20):
    now = time.time()
    max_age = max_age_minutes * 60

    if not os.path.exists(folder):
        return

    for f in os.listdir(folder):
        path = os.path.join(folder, f)
        if os.path.isfile(path):
            if now - os.path.getmtime(path) > max_age:
                try:
                    os.remove(path)
                except Exception:
                    pass


def reencode_video(input_path):
    output_path = os.path.join(
        ENCODE_DIR,
        f"EDIT_READY_{uuid.uuid4().hex[:8]}.mp4"
    )

    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "16",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path


def download_video(url, mode, video_mode):
    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "quiet": True,

        # ⬇️ WAJIB: ffmpeg_location TIDAK hardcode
        "ffmpeg_location": os.path.dirname(FFMPEG_PATH)
    }

    if mode == "mp3":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }]
        })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        title = clean_filename(info.get("title", "video"))

        if mode == "mp3":
            file_path = os.path.splitext(file_path)[0] + ".mp3"

    # 🔥 MODE EDITING READY (RE-ENCODE)
    if mode == "mp4" and video_mode == "Editing Ready (Besar & Jernih)":
        file_path = reencode_video(file_path)

    return file_path, title


# =========================
# UI
# =========================
st.title("🎥 YouTube Downloader Pro")

st.markdown("""
### 🔥 Mode Video
- **Asli YouTube (MAX Quality)** → codec & bitrate asli YouTube
- **Editing Ready (Besar & Jernih)** → re-encode H.264 bitrate tinggi
""")

menu = st.radio("Pilih Output:", ["MP4 (Video)", "MP3 (Audio)"])

video_mode = None
if "MP4" in menu:
    video_mode = st.selectbox(
        "Pilih Mode Video:",
        ["Asli YouTube (MAX Quality)", "Editing Ready (Besar & Jernih)"]
    )

url = st.text_input("Masukkan URL YouTube / Shorts")

if st.button("⬇️ Download"):
    # 🧹 AUTO CLEANUP FILE LAMA
    cleanup_old_files(DOWNLOAD_DIR, max_age_minutes=20)
    cleanup_old_files(ENCODE_DIR, max_age_minutes=20)

    if not url:
        st.warning("Masukkan URL YouTube terlebih dahulu!")
    else:
        with st.spinner("Memproses video..."):
            mode = "mp3" if "MP3" in menu else "mp4"
            file_path, title = download_video(url, mode, video_mode)

        st.success("Download selesai!")
        st.write(f"**Judul:** {title}")

        st.session_state.last_file = file_path


# =========================
# DOWNLOAD + AUTO DELETE
# =========================
if st.session_state.last_file and os.path.exists(st.session_state.last_file):
    with open(st.session_state.last_file, "rb") as f:
        downloaded = st.download_button(
            label="📥 Download File",
            data=f,
            file_name=os.path.basename(st.session_state.last_file),
            mime="audio/mpeg" if menu.startswith("MP3") else "video/mp4"
        )

    # 🗑️ HAPUS SETELAH USER DOWNLOAD
    if downloaded:
        try:
            os.remove(st.session_state.last_file)
            st.session_state.last_file = None
            st.success("🧹 File otomatis dihapus setelah download")
        except Exception:
            pass

st.caption("🧹 File akan otomatis dihapus jika tidak diunduh (±20 menit)")
