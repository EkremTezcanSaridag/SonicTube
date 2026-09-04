import os
import re
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import yt_dlp

from .ffmpeg_helper import get_ffmpeg_path

class DownloadCancelledException(Exception):
    pass

def clean_filename(name: str) -> str:
    """Removes or replaces invalid characters for Windows paths."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def fetch_media_info(url: str) -> Dict[str, Any]:
    """
    Fetches media metadata (title, uploader, thumbnail, duration, is_playlist)
    without downloading the file.
    """
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
    is_playlist = info.get('_type') == 'playlist' or ('entries' in info and info['entries'] is not None)
    
    if is_playlist:
        raw_entries = list(info.get('entries', []) or [])
        clean_entries = []
        for e in raw_entries:
            if not e:
                continue
            entry_id = e.get('id')
            entry_url = e.get('url') or (f"https://www.youtube.com/watch?v={entry_id}" if entry_id else None)
            if not entry_url:
                continue
            d_sec = e.get('duration', 0) or 0
            d_str = f"{d_sec//60:02d}:{d_sec%60:02d}" if d_sec else ""
            clean_entries.append({
                'id': entry_id,
                'title': e.get('title') or 'Bilinmeyen Başlık',
                'url': entry_url,
                'thumbnail': e.get('thumbnail') or (e.get('thumbnails', [{}])[-1].get('url') if e.get('thumbnails') else None),
                'duration': d_str,
                'uploader': e.get('uploader') or e.get('channel') or info.get('uploader', 'YouTube')
            })

        first_thumb = clean_entries[0].get('thumbnail') if clean_entries else None
        return {
            'is_playlist': True,
            'title': info.get('title', 'Çalma Listesi'),
            'uploader': info.get('uploader', info.get('channel', 'Bilinmeyen Kanal')),
            'playlist_count': len(clean_entries),
            'thumbnail': first_thumb,
            'entries': clean_entries,
            'original_url': url,
            'has_single_video': bool(info.get('id') or 'v=' in url)
        }
    else:
        # Format duration to MM:SS or HH:MM:SS
        duration_sec = info.get('duration', 0) or 0
        hours = duration_sec // 3600
        mins = (duration_sec % 3600) // 60
        secs = duration_sec % 60
        if hours > 0:
            duration_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
        else:
            duration_str = f"{mins:02d}:{secs:02d}"

        # Get best thumbnail
        thumbnails = info.get('thumbnails', [])
        thumbnail_url = info.get('thumbnail')
        if thumbnails:
            thumbnail_url = thumbnails[-1].get('url', thumbnail_url)

        return {
            'is_playlist': False,
            'id': info.get('id'),
            'title': info.get('title', 'Bilinmeyen Başlık'),
            'uploader': info.get('uploader', info.get('channel', 'Bilinmeyen Sanatçı')),
            'duration': duration_str,
            'duration_seconds': duration_sec,
            'thumbnail': thumbnail_url,
            'original_url': url
        }

class DownloadTask:
    def __init__(self, url: str, options: Dict[str, Any], 
                 on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
                 on_complete: Optional[Callable[[Optional[str]], None]] = None,
                 on_error: Optional[Callable[[str], None]] = None):
        self.url = url
        self.options = options
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error
        self.is_cancelled = False
        self.final_filepath = None
        self._thread = None

    def cancel(self):
        self.is_cancelled = True

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            download_dir = Path(self.options.get("download_dir", str(Path.home() / "Downloads" / "SonicTube")))
            if self.options.get("subfolder") and self.options.get("playlist_title"):
                download_dir = download_dir / clean_filename(self.options.get("playlist_title"))
            download_dir.mkdir(parents=True, exist_ok=True)
            
            mode = self.options.get("mode", "audio") # 'audio' or 'video'
            ffmpeg_dir = get_ffmpeg_path()
            
            postprocessors = []
            
            if mode == "audio":
                audio_fmt = self.options.get("audio_format", "mp3")
                bitrate = self.options.get("audio_bitrate", "320")
                
                # Audio extraction postprocessor
                postprocessors.append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': audio_fmt,
                    'preferredquality': bitrate,
                })
                
                # Convert YouTube webp thumbnail to jpg first
                if self.options.get("embed_thumbnail", True):
                    postprocessors.append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
                    postprocessors.append({'key': 'EmbedThumbnail'})

                # Metadata tagger (Artist, Title, Album)
                if self.options.get("embed_metadata", True):
                    postprocessors.append({'key': 'FFmpegMetadata'})

                format_str = 'bestaudio/best'
            else:
                # Video Mode
                video_res = self.options.get("video_quality", "1080p") # 4k, 1440p, 1080p, 720p, etc.
                video_fmt = self.options.get("video_format", "mp4")
                
                height_map = {
                    '4k': 2160,
                    '1440p': 1440,
                    '1080p': 1080,
                    '720p': 720,
                    '480p': 480,
                    '360p': 360
                }
                max_height = height_map.get(video_res, 1080)
                
                format_str = f'bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best'
                
                if self.options.get("embed_metadata", True):
                    postprocessors.append({'key': 'FFmpegMetadata'})

            def ydl_progress_hook(d):
                if self.is_cancelled:
                    raise DownloadCancelledException("İndirme kullanıcı tarafından iptal edildi.")

                status = d.get('status')
                if status == 'downloading':
                    total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded_bytes = d.get('downloaded_bytes', 0)
                    
                    percent = 0.0
                    if total_bytes > 0:
                        percent = (downloaded_bytes / total_bytes) * 100.0

                    speed_bytes = d.get('speed', 0) or 0
                    if speed_bytes > 1024 * 1024:
                        speed_str = f"{speed_bytes / (1024 * 1024):.1f} MB/s"
                    elif speed_bytes > 1024:
                        speed_str = f"{speed_bytes / 1024:.0f} KB/s"
                    else:
                        speed_str = "-- KB/s"

                    eta_sec = d.get('eta', 0) or 0
                    eta_str = f"{eta_sec // 60:02d}:{eta_sec % 60:02d}" if eta_sec else "--:--"
                    
                    # Total size in MB
                    total_mb = f"{total_bytes / (1024 * 1024):.1f} MB" if total_bytes else ""
                    downloaded_mb = f"{downloaded_bytes / (1024 * 1024):.1f} MB"

                    if self.on_progress:
                        self.on_progress({
                            'status': 'downloading',
                            'percent': percent,
                            'speed': speed_str,
                            'eta': eta_str,
                            'downloaded_mb': downloaded_mb,
                            'total_mb': total_mb
                        })
                elif status == 'finished':
                    if self.on_progress:
                        self.on_progress({
                            'status': 'converting',
                            'percent': 100.0,
                            'speed': '',
                            'eta': '',
                            'status_text': 'Format dönüştürülüyor & kapak işleniyor...'
                        })

            def postprocessor_hook(d):
                if d.get('status') == 'finished':
                    filename = d.get('info_dict', {}).get('_filename')
                    if filename:
                        self.final_filepath = filename

            ydl_opts = {
                'format': format_str,
                'outtmpl': str(download_dir / '%(title)s.%(ext)s'),
                'progress_hooks': [ydl_progress_hook],
                'postprocessor_hooks': [postprocessor_hook],
                'writethumbnail': self.options.get("embed_thumbnail", True) and mode == "audio",
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
            }
            
            if mode == "video":
                ydl_opts['merge_output_format'] = self.options.get("video_format", "mp4")

            if postprocessors:
                ydl_opts['postprocessors'] = postprocessors

            if ffmpeg_dir:
                ydl_opts['ffmpeg_location'] = ffmpeg_dir

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(self.url, download=True)
                if not self.final_filepath:
                    # Resolve expected output file path
                    self.final_filepath = ydl.prepare_filename(info_dict)
                    if mode == "audio":
                        audio_ext = self.options.get("audio_format", "mp3")
                        self.final_filepath = str(Path(self.final_filepath).with_suffix(f".{audio_ext}"))

            if self.on_complete:
                self.on_complete(self.final_filepath)

        except DownloadCancelledException:
            if self.on_error:
                self.on_error("İptal edildi")
        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
