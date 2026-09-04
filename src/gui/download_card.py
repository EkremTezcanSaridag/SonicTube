import os
import subprocess
import threading
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Optional, Callable
import customtkinter as ctk
from PIL import Image

from .theme import COLORS, FONTS
from ..downloader import DownloadTask

class DownloadCard(ctk.CTkFrame):
    def __init__(self, master, media_info: dict, download_options: dict, 
                 on_remove: Optional[Callable] = None, 
                 on_status_change: Optional[Callable] = None,
                 auto_start: bool = True, **kwargs):
        super().__init__(
            master, 
            fg_color=COLORS["bg_card"], 
            corner_radius=10, 
            border_width=1, 
            border_color=COLORS["border"], 
            **kwargs
        )
        self.media_info = media_info
        self.options = download_options
        self.on_remove = on_remove
        self.on_status_change = on_status_change
        self.download_task: Optional[DownloadTask] = None
        self.output_filepath: Optional[str] = None
        self.is_completed = False
        self.is_started = False

        self._build_ui()
        self._load_thumbnail()

        if not auto_start:
            self.status_label.configure(text="⏳ Sırada bekliyor...", text_color=COLORS["text_dim"])
        else:
            self.start_download()

    def start_download(self):
        if self.is_started:
            return
        self.is_started = True
        self.status_label.configure(text="Bağlanıyor ve hazırlanıyor...", text_color=COLORS["text_dim"])
        self._start_download()

    def _build_ui(self):
        # 3 Column layout: [Thumbnail 110x62] | [Details & Progress Bar] | [Actions]
        self.grid_columnconfigure(1, weight=1)

        # 1. Thumbnail
        self.thumb_label = ctk.CTkLabel(
            self, 
            text="", 
            width=110, 
            height=65, 
            fg_color="#18181b", 
            corner_radius=6
        )
        self.thumb_label.grid(row=0, column=0, padx=(12, 12), pady=12, sticky="nw")

        # 2. Details Column
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=1, padx=(0, 12), pady=10, sticky="nsew")
        info_frame.grid_columnconfigure(0, weight=1)

        # Title and Badge Row
        title_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        title_row.grid_columnconfigure(0, weight=1)

        # Badge
        mode = self.options.get("mode", "audio")
        if mode == "audio":
            badge_text = f"🎵 {self.options.get('audio_format', 'mp3').upper()} {self.options.get('audio_bitrate', '320')}K"
            badge_color = COLORS["primary"]
        else:
            badge_text = f"🎬 {self.options.get('video_quality', '1080p').upper()} {self.options.get('video_format', 'mp4').upper()}"
            badge_color = COLORS["accent_blue"]

        self.badge = ctk.CTkLabel(
            title_row,
            text=f" {badge_text} ",
            font=FONTS["badge"],
            fg_color=badge_color,
            text_color="#ffffff",
            corner_radius=4,
            height=20
        )
        self.badge.grid(row=0, column=1, padx=(6, 0), sticky="e")

        raw_title = self.media_info.get("title", "YouTube Medyası")
        if len(raw_title) > 65:
            display_title = raw_title[:62] + "..."
        else:
            display_title = raw_title

        self.title_label = ctk.CTkLabel(
            title_row,
            text=display_title,
            font=FONTS["body_bold"],
            text_color=COLORS["text_white"],
            anchor="w"
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            info_frame, 
            height=6, 
            corner_radius=3, 
            progress_color=COLORS["primary"],
            fg_color="#33353e"
        )
        self.progress_bar.set(0.0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(4, 4))

        # Status text row (Speed, ETA, Percent)
        status_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        status_row.grid(row=2, column=0, sticky="ew")
        status_row.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            status_row,
            text="Bağlanıyor ve hazırlanıyor...",
            font=FONTS["small"],
            text_color=COLORS["text_dim"],
            anchor="w"
        )
        self.status_label.grid(row=0, column=0, sticky="w")

        self.speed_label = ctk.CTkLabel(
            status_row,
            text="",
            font=FONTS["small"],
            text_color=COLORS["text_dim"],
            anchor="e"
        )
        self.speed_label.grid(row=0, column=1, sticky="e")

        # 3. Actions Column
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.grid(row=0, column=2, padx=(0, 12), pady=10, sticky="ne")

        self.cancel_btn = ctk.CTkButton(
            self.action_frame,
            text="✕ İptal",
            width=65,
            height=28,
            font=FONTS["small"],
            fg_color="#2f313a",
            hover_color=COLORS["danger_hover"],
            command=self._cancel_download
        )
        self.cancel_btn.pack(pady=2)

    def _load_thumbnail(self):
        thumb_url = self.media_info.get("thumbnail")
        if not thumb_url:
            return

        def fetch():
            try:
                req = urllib.request.Request(thumb_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    img_data = resp.read()
                image = Image.open(BytesIO(img_data)).convert("RGB")
                image = image.resize((110, 65), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=image, dark_image=image, size=(110, 65))
                self.after(0, lambda: self.thumb_label.configure(image=ctk_img, text=""))
            except Exception:
                pass

        threading.Thread(target=fetch, daemon=True).start()

    def _start_download(self):
        url = self.media_info.get("original_url")
        self.download_task = DownloadTask(
            url=url,
            options=self.options,
            on_progress=self._on_progress_update,
            on_complete=self._on_download_success,
            on_error=self._on_download_failed
        )
        self.download_task.start()

    def _on_progress_update(self, data: dict):
        def update():
            status = data.get("status")
            if status == "downloading":
                pct = data.get("percent", 0.0) / 100.0
                self.progress_bar.set(pct)
                
                downloaded = data.get("downloaded_mb", "")
                total = data.get("total_mb", "")
                size_str = f"{downloaded} / {total}" if total else downloaded
                self.status_label.configure(
                    text=f"{int(data.get('percent', 0))}%  •  {size_str}"
                )
                
                speed = data.get("speed", "")
                eta = data.get("eta", "")
                speed_text = f"{speed}  •  Kalan: {eta}" if eta else speed
                self.speed_label.configure(text=speed_text)
            elif status == "converting":
                self.progress_bar.set(1.0)
                self.status_label.configure(text=data.get("status_text", "Dönüştürülüyor..."))
                self.speed_label.configure(text="")

        self.after(0, update)

    def _on_download_success(self, filepath: Optional[str]):
        def update():
            self.is_completed = True
            self.output_filepath = filepath
            self.progress_bar.set(1.0)
            self.progress_bar.configure(progress_color=COLORS["success"])
            self.status_label.configure(text="✓ İndirme tamamlandı!", text_color=COLORS["success"])
            self.speed_label.configure(text="")

            # Clear cancel button and add Finished buttons
            for widget in self.action_frame.winfo_children():
                widget.destroy()

            open_btn = ctk.CTkButton(
                self.action_frame,
                text="▶ Aç",
                width=65,
                height=26,
                font=FONTS["small"],
                fg_color=COLORS["primary"],
                hover_color=COLORS["primary_hover"],
                command=self._open_file
            )
            open_btn.pack(pady=(0, 4))

            folder_btn = ctk.CTkButton(
                self.action_frame,
                text="📁 Klasör",
                width=65,
                height=26,
                font=FONTS["small"],
                fg_color="#2f313a",
                hover_color="#3b3d47",
                command=self._open_folder
            )
            folder_btn.pack(pady=(0, 4))

            remove_btn = ctk.CTkButton(
                self.action_frame,
                text="✕ Sil",
                width=65,
                height=24,
                font=FONTS["small"],
                fg_color="transparent",
                hover_color=COLORS["danger_hover"],
                text_color=COLORS["text_dim"],
                command=self._remove_self
            )
            if self.on_status_change:
                self.on_status_change(self)

        self.after(0, update)

    def _on_download_failed(self, error_msg: str):
        def update():
            self.progress_bar.configure(progress_color=COLORS["danger"])
            self.status_label.configure(text=f"Hata: {error_msg[:45]}", text_color=COLORS["danger"])
            self.speed_label.configure(text="")

            for widget in self.action_frame.winfo_children():
                widget.destroy()

            remove_btn = ctk.CTkButton(
                self.action_frame,
                text="✕ Kaldır",
                width=65,
                height=26,
                font=FONTS["small"],
                fg_color=COLORS["danger"],
                hover_color=COLORS["danger_hover"],
                command=self._remove_self
            )
            remove_btn.pack()

            if self.on_status_change:
                self.on_status_change(self)

        self.after(0, update)

    def _cancel_download(self):
        if self.download_task:
            self.download_task.cancel()
        self.status_label.configure(text="İptal ediliyor...", text_color=COLORS["warning"])
        if self.on_status_change:
            self.on_status_change(self)

    def _open_file(self):
        if self.output_filepath and os.path.exists(self.output_filepath):
            try:
                os.startfile(self.output_filepath)
            except Exception as e:
                print(f"Error opening file: {e}")

    def _open_folder(self):
        if self.output_filepath and os.path.exists(self.output_filepath):
            try:
                subprocess.run(['explorer', '/select,', os.path.normpath(self.output_filepath)])
            except Exception:
                folder = os.path.dirname(self.output_filepath)
                os.startfile(folder)
        else:
            folder = self.options.get("download_dir", str(Path.home() / "Downloads" / "SonicTube"))
            if os.path.exists(folder):
                os.startfile(folder)

    def _remove_self(self):
        if self.on_remove:
            self.on_remove(self)
        self.destroy()
