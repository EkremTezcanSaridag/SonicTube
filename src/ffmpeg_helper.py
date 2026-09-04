import os
import shutil
import zipfile
import urllib.request
import threading
import sys
from pathlib import Path
from typing import Optional, Callable
import subprocess

# SonicTube root dir / bin dir (handles both script mode and frozen .exe mode)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

BIN_DIR = BASE_DIR / "bin"
FFMPEG_EXE = BIN_DIR / "ffmpeg.exe"
FFPROBE_EXE = BIN_DIR / "ffprobe.exe"

# yt-dlp recommended lightweight Windows builds of FFmpeg
FFMPEG_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

def get_ffmpeg_path() -> Optional[str]:
    """Returns the path to ffmpeg executable or its folder if available."""
    # 1. Check local bin directory
    if FFMPEG_EXE.exists():
        return str(BIN_DIR)
    
    # 2. Check PyInstaller _internal or _MEIPASS bin directory
    internal_bin = BASE_DIR / "_internal" / "bin"
    if (internal_bin / "ffmpeg.exe").exists():
        return str(internal_bin)

    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        meipass_bin = Path(meipass) / "bin"
        if (meipass_bin / "ffmpeg.exe").exists():
            return str(meipass_bin)
    
    # 3. Check system PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return str(Path(system_ffmpeg).parent)
        
    return None

def is_ffmpeg_available() -> bool:
    return get_ffmpeg_path() is not None

def download_ffmpeg(progress_callback: Optional[Callable[[str, float], None]] = None) -> bool:
    """
    Downloads and extracts portable FFmpeg binaries into the bin/ directory.
    progress_callback receives (status_message, percent_0_to_100)
    """
    try:
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = BIN_DIR / "ffmpeg.zip"

        if progress_callback:
            progress_callback("FFmpeg indiriliyor...", 0.0)

        def report_hook(block_num, block_size, total_size):
            if total_size > 0 and progress_callback:
                percent = min(100.0, (block_num * block_size / total_size) * 100.0)
                downloaded_mb = (block_num * block_size) / (1024 * 1024)
                total_mb = total_size / (1024 * 1024)
                progress_callback(
                    f"FFmpeg indiriliyor: {downloaded_mb:.1f}MB / {total_mb:.1f}MB ({int(percent)}%)",
                    percent
                )

        req = urllib.request.Request(
            FFMPEG_URL,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )

        with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
            total_size = int(response.info().get('Content-Length', -1))
            block_size = 1024 * 64
            block_num = 0
            while True:
                chunk = response.read(block_size)
                if not chunk:
                    break
                out_file.write(chunk)
                block_num += 1
                report_hook(block_num, block_size, total_size)

        if progress_callback:
            progress_callback("FFmpeg arşivden çıkarılıyor...", 100.0)

        # Extract ffmpeg.exe and ffprobe.exe
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.namelist():
                filename = os.path.basename(member)
                if filename in ("ffmpeg.exe", "ffprobe.exe"):
                    source = zip_ref.open(member)
                    target = open(BIN_DIR / filename, "wb")
                    with source, target:
                        shutil.copyfileobj(source, target)

        # Clean up zip file
        if zip_path.exists():
            zip_path.unlink()

        if progress_callback:
            progress_callback("FFmpeg hazır!", 100.0)

        return FFMPEG_EXE.exists()
    except Exception as e:
        if progress_callback:
            progress_callback(f"FFmpeg indirilemedi: {e}", 0.0)
        return False

def ensure_ffmpeg_async(callback: Optional[Callable[[bool], None]] = None):
    """Runs ffmpeg download in a background thread if missing."""
    if is_ffmpeg_available():
        if callback:
            callback(True)
        return

    def worker():
        success = download_ffmpeg()
        if callback:
            callback(success)

    threading.Thread(target=worker, daemon=True).start()
