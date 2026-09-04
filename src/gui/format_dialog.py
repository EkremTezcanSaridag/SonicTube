import os
import threading
import urllib.request
from io import BytesIO
from tkinter import filedialog
from typing import Dict, Any, Optional, Callable
import customtkinter as ctk
from PIL import Image

from .theme import COLORS, FONTS
from ..config import load_config, save_config

class FormatSelectionDialog(ctk.CTkToplevel):
    def __init__(self, master, media_info: Dict[str, Any], on_confirm: Callable[[Dict[str, Any]], None]):
        super().__init__(master)
        self.media_info = media_info
        self.on_confirm = on_confirm
        self.config = load_config()

        self.title("SonicTube - İndirme Seçenekleri")
        self.geometry("540x620")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_main"])
        
        # Center the dialog on master
        self.transient(master)
        self.grab_set()

        self._build_ui()
        self._load_thumbnail()

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=20)

        # 1. Media Preview Card
        preview_card = ctk.CTkFrame(
            container, 
            fg_color=COLORS["bg_card"], 
            corner_radius=10, 
            border_width=1, 
            border_color=COLORS["border"]
        )
        preview_card.pack(fill="x", pady=(0, 16))
        preview_card.grid_columnconfigure(1, weight=1)

        self.thumb_label = ctk.CTkLabel(
            preview_card, 
            text="", 
            width=120, 
            height=70, 
            fg_color="#18181b", 
            corner_radius=6
        )
        self.thumb_label.grid(row=0, column=0, padx=12, pady=12, sticky="nw")

        info_box = ctk.CTkFrame(preview_card, fg_color="transparent")
        info_box.grid(row=0, column=1, padx=(0, 12), pady=12, sticky="nsew")

        raw_title = self.media_info.get("title", "Video")
        short_title = raw_title if len(raw_title) <= 55 else raw_title[:52] + "..."
        
        self.title_lbl = ctk.CTkLabel(
            info_box, 
            text=short_title, 
            font=FONTS["body_bold"], 
            text_color=COLORS["text_white"], 
            anchor="w"
        )
        self.title_lbl.pack(fill="x", anchor="w")

        uploader = self.media_info.get("uploader", "YouTube")
        duration = self.media_info.get("duration", "")
        detail_text = f"👤 {uploader}"
        if duration:
            detail_text += f"   ⏱️ {duration}"
        if self.media_info.get("is_playlist"):
            detail_text += f"   📑 {self.media_info.get('playlist_count', 0)} Video"

        self.sub_lbl = ctk.CTkLabel(
            info_box, 
            text=detail_text, 
            font=FONTS["small"], 
            text_color=COLORS["text_dim"], 
            anchor="w"
        )
        self.sub_lbl.pack(fill="x", anchor="w", pady=(4, 0))

        # Playlist Choice if detected
        if self.media_info.get("is_playlist"):
            pl_frame = ctk.CTkFrame(container, fg_color=COLORS["bg_card"], corner_radius=8, border_width=1, border_color=COLORS["border"])
            pl_frame.pack(fill="x", pady=(0, 12), padx=2)
            
            self.playlist_choice_var = ctk.StringVar(value="all")
            ctk.CTkRadioButton(
                pl_frame,
                text=f"Tüm Çalma Listesini İndir ({self.media_info.get('playlist_count')} video)",
                variable=self.playlist_choice_var,
                value="all",
                font=FONTS["body"],
                fg_color=COLORS["primary"]
            ).pack(anchor="w", padx=14, pady=(8, 4))

            ctk.CTkRadioButton(
                pl_frame,
                text="Sadece İlk / Tek Videoyu İndir",
                variable=self.playlist_choice_var,
                value="single",
                font=FONTS["body"],
                fg_color=COLORS["primary"]
            ).pack(anchor="w", padx=14, pady=(0, 8))
        else:
            self.playlist_choice_var = None

        # 2. Mode Selector: [🎵 Ses / Müzik Çıkar] vs [🎬 Video İndir]
        self.mode_var = ctk.StringVar(value=self.config.get("default_mode", "audio"))
        self.mode_selector = ctk.CTkSegmentedButton(
            container,
            values=["🎵 Müzik / Ses Çıkar", "🎬 Video İndir"],
            command=self._on_mode_change,
            selected_color=COLORS["primary"],
            selected_hover_color=COLORS["primary_hover"],
            font=FONTS["body_bold"],
            height=38
        )
        self.mode_selector.pack(fill="x", pady=(0, 16))
        if self.mode_var.get() == "audio":
            self.mode_selector.set("🎵 Müzik / Ses Çıkar")
        else:
            self.mode_selector.set("🎬 Video İndir")

        # 3. Dynamic Options Container
        self.options_container = ctk.CTkFrame(container, fg_color=COLORS["bg_card"], corner_radius=10, border_width=1, border_color=COLORS["border"])
        self.options_container.pack(fill="both", expand=True, pady=(0, 16))
        
        self._render_options()

        # 4. Save Location row
        loc_frame = ctk.CTkFrame(container, fg_color="transparent")
        loc_frame.pack(fill="x", pady=(0, 16))
        loc_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(loc_frame, text="Kaydet:", font=FONTS["body_bold"], text_color=COLORS["text_dim"]).grid(row=0, column=0, padx=(0, 8), sticky="w")
        
        self.path_entry = ctk.CTkEntry(
            loc_frame, 
            height=32, 
            font=FONTS["small"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"]
        )
        self.path_entry.insert(0, self.config.get("download_dir"))
        self.path_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        browse_btn = ctk.CTkButton(
            loc_frame, 
            text="Gözat...", 
            width=70, 
            height=32, 
            font=FONTS["small"],
            fg_color="#2f313a",
            hover_color="#3b3d47",
            command=self._browse_dir
        )
        browse_btn.grid(row=0, column=2, sticky="e")

        # 5. Bottom Action Buttons
        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x")
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)

        cancel_btn = ctk.CTkButton(
            btn_row,
            text="İptal",
            height=40,
            font=FONTS["body"],
            fg_color="#2f313a",
            hover_color="#3b3d47",
            command=self.destroy
        )
        cancel_btn.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        download_btn = ctk.CTkButton(
            btn_row,
            text="İndir",
            height=40,
            font=FONTS["body_bold"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            command=self._on_download_click
        )
        download_btn.grid(row=0, column=1, padx=(6, 0), sticky="ew")

    def _on_mode_change(self, value):
        if "Müzik" in value:
            self.mode_var.set("audio")
        else:
            self.mode_var.set("video")
        self._render_options()

    def _render_options(self):
        # Clear previous options
        for widget in self.options_container.winfo_children():
            widget.destroy()

        mode = self.mode_var.get()
        if mode == "audio":
            self._render_audio_options()
        else:
            self._render_video_options()

    def _render_audio_options(self):
        pad = {"padx": 16, "pady": 8}
        
        # Audio Format Dropdown
        row1 = ctk.CTkFrame(self.options_container, fg_color="transparent")
        row1.pack(fill="x", **pad)
        ctk.CTkLabel(row1, text="Ses Formatı:", font=FONTS["body"], width=110, anchor="w").pack(side="left")
        self.audio_format_var = ctk.StringVar(value=self.config.get("audio_format", "mp3"))
        ctk.CTkOptionMenu(
            row1, 
            values=["mp3", "m4a", "flac", "wav"], 
            variable=self.audio_format_var,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            width=180
        ).pack(side="left")

        # Audio Bitrate
        row2 = ctk.CTkFrame(self.options_container, fg_color="transparent")
        row2.pack(fill="x", **pad)
        ctk.CTkLabel(row2, text="Ses Kalitesi:", font=FONTS["body"], width=110, anchor="w").pack(side="left")
        self.audio_bitrate_var = ctk.StringVar(value="320 kbps (En Yüksek)")
        bitrate_display_map = {
            "320": "320 kbps (En Yüksek)",
            "256": "256 kbps (Yüksek)",
            "192": "192 kbps (Standart)",
            "128": "128 kbps (Hafif)"
        }
        current_val = bitrate_display_map.get(self.config.get("audio_bitrate", "320"), "320 kbps (En Yüksek)")
        self.audio_bitrate_var.set(current_val)
        
        ctk.CTkOptionMenu(
            row2,
            values=["320 kbps (En Yüksek)", "256 kbps (Yüksek)", "192 kbps (Standart)", "128 kbps (Hafif)"],
            variable=self.audio_bitrate_var,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            width=180
        ).pack(side="left")

        # Checkboxes for cover art and tags
        row3 = ctk.CTkFrame(self.options_container, fg_color="transparent")
        row3.pack(fill="x", padx=16, pady=(12, 8))
        self.cover_art_var = ctk.BooleanVar(value=self.config.get("embed_thumbnail", True))
        ctk.CTkCheckBox(
            row3, 
            text="Albüm kapağını (küçük resmi) müziğe göm", 
            variable=self.cover_art_var,
            fg_color=COLORS["primary"],
            font=FONTS["small"]
        ).pack(anchor="w", pady=2)

        self.tags_var = ctk.BooleanVar(value=self.config.get("embed_metadata", True))
        ctk.CTkCheckBox(
            row3, 
            text="Sanatçı, başlık ve albüm etiketlerini ekle", 
            variable=self.tags_var,
            fg_color=COLORS["primary"],
            font=FONTS["small"]
        ).pack(anchor="w", pady=2)

    def _render_video_options(self):
        pad = {"padx": 16, "pady": 8}

        # Video Resolution
        row1 = ctk.CTkFrame(self.options_container, fg_color="transparent")
        row1.pack(fill="x", **pad)
        ctk.CTkLabel(row1, text="Çözünürlük:", font=FONTS["body"], width=110, anchor="w").pack(side="left")
        self.video_res_var = ctk.StringVar(value="1080p (Full HD)")
        res_display_map = {
            "4k": "4K (2160p)",
            "1440p": "2K (1440p)",
            "1080p": "1080p (Full HD)",
            "720p": "720p (HD)",
            "480p": "480p (SD)"
        }
        self.video_res_var.set(res_display_map.get(self.config.get("video_quality", "1080p"), "1080p (Full HD)"))

        ctk.CTkOptionMenu(
            row1,
            values=["4K (2160p)", "2K (1440p)", "1080p (Full HD)", "720p (HD)", "480p (SD)"],
            variable=self.video_res_var,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            width=180
        ).pack(side="left")

        # Video Container Format
        row2 = ctk.CTkFrame(self.options_container, fg_color="transparent")
        row2.pack(fill="x", **pad)
        ctk.CTkLabel(row2, text="Konteyner:", font=FONTS["body"], width=110, anchor="w").pack(side="left")
        self.video_fmt_var = ctk.StringVar(value=self.config.get("video_format", "mp4"))
        ctk.CTkOptionMenu(
            row2,
            values=["mp4", "mkv"],
            variable=self.video_fmt_var,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            width=180
        ).pack(side="left")

    def _browse_dir(self):
        dir_selected = filedialog.askdirectory(initialdir=self.path_entry.get())
        if dir_selected:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, dir_selected)

    def _load_thumbnail(self):
        thumb_url = self.media_info.get("thumbnail")
        if not thumb_url:
            return

        def fetch():
            try:
                req = urllib.request.Request(thumb_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = resp.read()
                img = Image.open(BytesIO(data)).convert("RGB")
                img = img.resize((120, 70), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(120, 70))
                self.after(0, lambda: self.thumb_label.configure(image=ctk_img, text=""))
            except Exception:
                pass

        threading.Thread(target=fetch, daemon=True).start()

    def _on_download_click(self):
        mode = self.mode_var.get()
        save_dir = self.path_entry.get().strip() or self.config.get("download_dir")
        
        # Save last used settings to config
        self.config["download_dir"] = save_dir
        self.config["default_mode"] = mode

        options = {
            "mode": mode,
            "download_dir": save_dir,
            "original_url": self.media_info.get("original_url"),
            "title": self.media_info.get("title"),
            "thumbnail": self.media_info.get("thumbnail"),
            "uploader": self.media_info.get("uploader"),
            "duration": self.media_info.get("duration"),
            "entries": self.media_info.get("entries", []),
        }

        if mode == "audio":
            options["audio_format"] = self.audio_format_var.get()
            raw_bitrate = self.audio_bitrate_var.get()
            bitrate_val = "320"
            for b in ["320", "256", "192", "128"]:
                if b in raw_bitrate:
                    bitrate_val = b
                    break
            options["audio_bitrate"] = bitrate_val
            options["embed_thumbnail"] = self.cover_art_var.get()
            options["embed_metadata"] = self.tags_var.get()

            self.config["audio_format"] = options["audio_format"]
            self.config["audio_bitrate"] = options["audio_bitrate"]
        else:
            raw_res = self.video_res_var.get()
            res_val = "1080p"
            for r in ["4k", "1440p", "1080p", "720p", "480p"]:
                if r.lower() in raw_res.lower():
                    res_val = r
                    break
            options["video_quality"] = res_val
            options["video_format"] = self.video_fmt_var.get()
            options["embed_metadata"] = True

            self.config["video_quality"] = options["video_quality"]
            self.config["video_format"] = options["video_format"]

        if self.playlist_choice_var:
            options["download_all_playlist"] = (self.playlist_choice_var.get() == "all")

        save_config(self.config)
        self.destroy()
        self.on_confirm(options)
