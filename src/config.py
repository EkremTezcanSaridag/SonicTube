import json
import os
from pathlib import Path

DEFAULT_DOWNLOAD_DIR = str(Path.home() / "Downloads" / "SonicTube")
CONFIG_FILE = Path.home() / ".sonictube_config.json"

DEFAULT_CONFIG = {
    "download_dir": DEFAULT_DOWNLOAD_DIR,
    "default_mode": "audio",  # 'audio' or 'video'
    "audio_format": "mp3",    # 'mp3', 'm4a', 'flac'
    "audio_bitrate": "320",   # '320', '256', '128'
    "video_quality": "1080p", # '4k', '1440p', '1080p', '720p', '480p'
    "video_format": "mp4",    # 'mp4', 'mkv'
    "embed_thumbnail": True,
    "embed_metadata": True,
    "concurrent_downloads": 3,
    "theme": "dark"
}

def load_config() -> dict:
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                config.update(data)
        except Exception:
            pass
    
    # Ensure download directory exists
    os.makedirs(config["download_dir"], exist_ok=True)
    return config

def save_config(config: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")
