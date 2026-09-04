import os
import subprocess
import threading
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
import customtkinter as ctk
from PIL import Image

from .theme import COLORS, FONTS
from ..downloader import DownloadTask, clean_filename

class PlaylistCard(ctk.CTkFrame):
    def __init__(self, master, media_info: dict, download_options: dict, 
                 on_remove: Optional[Callable] = None, 
                 on_status_change: Optional[Callable] = None, **kwargs):
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
        
        self.entries: List[Dict[str, Any]] = media_info.get("entries", [])
        self.total_count = len(self.entries)
        self.completed_count = 0
        self.current_index = 0
        self.current_task: Optional[DownloadTask] = None
        self.is_cancelled = False
        self.is_completed = False
        self.is_expanded = False
        
        # Subfolder setup
        self.playlist_title = media_info.get("title", "Çalma Listesi")
        self.download_dir = Path(self.options.get("download_dir", str(Path.home() / "Downloads" / "SonicTube")))
        if self.options.get("subfolder", True):
            self.download_dir = self.download_dir / clean_filename(self.playlist_title)

        # Track items status for accordion: 'waiting', 'downloading', 'completed', 'error'
        self.item_statuses = [{"title": e.get("title", f"Parça {i+1}"), "status": "waiting", "pct": 0} for i, e in enumerate(self.entries)]

        self._build_ui()
        self._load_thumbnail()
        self.start_download()

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)

        # 1. Main Header Row
        self.main_row = ctk.CTkFrame(self, fg_color="transparent")
        self.main_row.grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=10)
        self.main_row.grid_columnconfigure(1, weight=1)

        # Thumbnail (Compact 95x58)
        self.thumb_label = ctk.CTkLabel(
            self.main_row, 
            text="", 
            width=95, 
            height=58, 
            fg_color="#18181b", 
            corner_radius=6
        )
        self.thumb_label.grid(row=0, column=0, padx=(0, 12), sticky="nw")

        # Details Column
        info_col = ctk.CTkFrame(self.main_row, fg_color="transparent")
        info_col.grid(row=0, column=1, padx=(0, 10), sticky="nsew")
        info_col.grid_columnconfigure(0, weight=1)

        # Title & Badge Row
        title_row = ctk.CTkFrame(info_col, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew")
        title_row.grid_columnconfigure(0, weight=1)

        raw_title = f"📑 {self.playlist_title}"
        short_title = raw_title if len(raw_title) <= 50 else raw_title[:47] + "..."
        self.title_lbl = ctk.CTkLabel(
            title_row,
            text=short_title,
            font=FONTS["body_bold"],
            text_color=COLORS["text_white"],
            anchor="w"
        )
        self.title_lbl.grid(row=0, column=0, sticky="w")

        mode = self.options.get("mode", "audio")
        if mode == "audio":
            badge_text = f"🎵 {self.options.get('audio_format', 'mp3').upper()} {self.options.get('audio_bitrate', '320')}K • {self.total_count} Parça"
            badge_color = COLORS["primary"]
        else:
            badge_text = f"🎬 {self.options.get('video_quality', '1080p').upper()} • {self.total_count} Video"
            badge_color = COLORS["accent_blue"]

        self.badge = ctk.CTkLabel(
            title_row,
            text=f" {badge_text} ",
            font=FONTS["badge"],
            fg_color=badge_color,
            text_color="#ffffff",
            corner_radius=4,
            height=18
        )
        self.badge.grid(row=0, column=1, padx=(6, 0), sticky="e")

        # Progress Bar (Overall)
        self.progress_bar = ctk.CTkProgressBar(
            info_col,
            height=6,
            corner_radius=3,
            progress_color=COLORS["primary"],
            fg_color="#33353e"
        )
        self.progress_bar.set(0.0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(4, 4))

        # Status text row
        status_row = ctk.CTkFrame(info_col, fg_color="transparent")
        status_row.grid(row=2, column=0, sticky="ew")
        status_row.grid_columnconfigure(0, weight=1)

        self.status_lbl = ctk.CTkLabel(
            status_row,
            text=f"Hazırlanıyor... (0 / {self.total_count} tamamlandı)",
            font=FONTS["small"],
            text_color=COLORS["text_dim"],
            anchor="w"
        )
        self.status_lbl.grid(row=0, column=0, sticky="w")

        self.speed_lbl = ctk.CTkLabel(
            status_row,
            text="",
            font=FONTS["small"],
            text_color=COLORS["text_dim"],
            anchor="e"
        )
        self.speed_lbl.grid(row=0, column=1, sticky="e")

        # Action Buttons Column
        self.actions_col = ctk.CTkFrame(self.main_row, fg_color="transparent")
        self.actions_col.grid(row=0, column=2, sticky="ne")

        self.toggle_btn = ctk.CTkButton(
            self.actions_col,
            text="▼ Liste",
            width=65,
            height=26,
            font=FONTS["small"],
            fg_color="#2f313a",
            hover_color="#3b3d47",
            command=self._toggle_expand
        )
        self.toggle_btn.pack(pady=(0, 3))

        self.folder_btn = ctk.CTkButton(
            self.actions_col,
            text="📁 Klasör",
            width=65,
            height=26,
            font=FONTS["small"],
            fg_color="#27272a",
            hover_color="#3b3d47",
            command=self._open_folder
        )
        self.folder_btn.pack(pady=(0, 3))

        self.cancel_btn = ctk.CTkButton(
            self.actions_col,
            text="✕ İptal",
            width=65,
            height=26,
            font=FONTS["small"],
            fg_color="#2f313a",
            hover_color=COLORS["danger_hover"],
            command=self.cancel
        )
        self.cancel_btn.pack()

        # 2. Collapsible Item List Frame (Hidden by default for max performance)
        self.items_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="#18191e",
            corner_radius=6,
            height=160,
            scrollbar_button_color="#2f313a"
        )
        # Not packed initially (compact!)

    def _toggle_expand(self):
        if self.is_expanded:
            self.items_frame.grid_forget()
            self.toggle_btn.configure(text="▼ Liste")
            self.is_expanded = False
        else:
            self._render_items_list()
            self.items_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 10))
            self.toggle_btn.configure(text="▲ Kapat")
            self.is_expanded = True

    def _render_items_list(self):
        for widget in self.items_frame.winfo_children():
            widget.destroy()

        for idx, item in enumerate(self.item_statuses):
            row = ctk.CTkFrame(self.items_frame, fg_color="transparent", height=24)
            row.pack(fill="x", pady=2, padx=6)
            row.grid_columnconfigure(1, weight=1)

            status = item["status"]
            if status == "completed":
                icon = "✓"
                color = COLORS["success"]
            elif status == "downloading":
                icon = "▶"
                color = COLORS["primary"]
            elif status == "error":
                icon = "✕"
                color = COLORS["danger"]
            else:
                icon = "⏳"
                color = COLORS["text_dim"]

            ctk.CTkLabel(row, text=icon, width=20, font=FONTS["small"], text_color=color).grid(row=0, column=0, sticky="w")
            
            raw_t = item["title"]
            disp_t = raw_t if len(raw_t) <= 60 else raw_t[:57] + "..."
            ctk.CTkLabel(row, text=f"{idx+1}. {disp_t}", font=FONTS["small"], text_color=COLORS["text_white"], anchor="w").grid(row=0, column=1, sticky="w", padx=6)

            st_text = "Tamamlandı" if status == "completed" else ("İndiriliyor..." if status == "downloading" else "Sırada")
            ctk.CTkLabel(row, text=st_text, font=FONTS["small"], text_color=color, anchor="e").grid(row=0, column=2, sticky="e")

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
                image = image.resize((95, 58), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=image, dark_image=image, size=(95, 58))
                self.after(0, lambda: self.thumb_label.configure(image=ctk_img, text=""))
            except Exception:
                pass

        threading.Thread(target=fetch, daemon=True).start()

    def start_download(self):
        threading.Thread(target=self._playlist_worker, daemon=True).start()

    def _playlist_worker(self):
        for idx, entry in enumerate(self.entries):
            if self.is_cancelled:
                break

            self.current_index = idx
            self.item_statuses[idx]["status"] = "downloading"
            
            entry_url = entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}"
            entry_title = entry.get("title", f"Parça {idx+1}")

            # Update UI for current track
            self.after(0, lambda i=idx, t=entry_title: self._update_current_track_ui(i, t))

            # Prepare options for single track
            track_options = self.options.copy()
            track_options["download_dir"] = str(self.download_dir)

            task_finished = threading.Event()
            success = [False]

            def on_prog(d):
                if self.is_cancelled:
                    return
                pct = d.get("percent", 0.0)
                speed = d.get("speed", "")
                self.after(0, lambda: self._update_track_progress(pct, speed))

            def on_comp(f):
                success[0] = True
                task_finished.set()

            def on_err(e):
                success[0] = False
                task_finished.set()

            self.current_task = DownloadTask(
                url=entry_url,
                options=track_options,
                on_progress=on_prog,
                on_complete=on_comp,
                on_error=on_err
            )
            self.current_task.start()
            task_finished.wait()

            if self.is_cancelled:
                self.item_statuses[idx]["status"] = "cancelled"
                break

            if success[0]:
                self.item_statuses[idx]["status"] = "completed"
                self.completed_count += 1
            else:
                self.item_statuses[idx]["status"] = "error"

            # Update overall progress
            self.after(0, self._update_overall_progress)

        # All finished or cancelled
        self.after(0, self._on_playlist_finished)

    def _update_current_track_ui(self, idx: int, title: str):
        short_t = title if len(title) <= 40 else title[:37] + "..."
        self.status_lbl.configure(
            text=f"İndiriliyor ({self.completed_count}/{self.total_count}): {short_t}",
            text_color=COLORS["primary"]
        )
        if self.is_expanded:
            self._render_items_list()

    def _update_track_progress(self, pct: float, speed: str):
        overall_pct = (self.completed_count + (pct / 100.0)) / max(1, self.total_count)
        self.progress_bar.set(overall_pct)
        if speed:
            self.speed_lbl.configure(text=speed)

    def _update_overall_progress(self):
        overall_pct = self.completed_count / max(1, self.total_count)
        self.progress_bar.set(overall_pct)
        self.status_lbl.configure(
            text=f"Tamamlanan: {self.completed_count} / {self.total_count} parça"
        )
        if self.is_expanded:
            self._render_items_list()

    def _on_playlist_finished(self):
        self.is_completed = True
        self.speed_lbl.configure(text="")
        if self.is_cancelled:
            self.status_lbl.configure(text=f"İptal Edildi ({self.completed_count}/{self.total_count} indirildi)", text_color=COLORS["warning"])
            self.cancel_btn.configure(text="✕ Sil", command=self._remove_self, fg_color=COLORS["danger"])
        else:
            self.progress_bar.set(1.0)
            self.progress_bar.configure(progress_color=COLORS["success"])
            self.status_lbl.configure(text=f"✓ Çalma Listesi Tamamlandı! ({self.completed_count} parça)", text_color=COLORS["success"])
            self.cancel_btn.configure(text="✕ Sil", command=self._remove_self, fg_color="#2f313a")

        if self.is_expanded:
            self._render_items_list()

        if self.on_status_change:
            self.on_status_change(self)

    def cancel(self):
        self.is_cancelled = True
        if self.current_task:
            self.current_task.cancel()
        self.status_lbl.configure(text="İptal ediliyor...", text_color=COLORS["warning"])

    def _open_folder(self):
        os.makedirs(self.download_dir, exist_ok=True)
        try:
            os.startfile(self.download_dir)
        except Exception:
            subprocess.run(['explorer', os.path.normpath(str(self.download_dir))])

    def _remove_self(self):
        if self.on_remove:
            self.on_remove(self)
        self.destroy()
