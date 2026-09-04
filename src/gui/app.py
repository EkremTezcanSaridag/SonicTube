import os
import threading
import subprocess
from tkinter import messagebox
from typing import Optional, List
import customtkinter as ctk

from .theme import COLORS, FONTS
from .download_card import DownloadCard
from .format_dialog import FormatSelectionDialog
from ..config import load_config, save_config
from ..downloader import fetch_media_info
from ..ffmpeg_helper import is_ffmpeg_available, download_ffmpeg

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

class SonicTubeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SonicTube - YouTube Video & Müzik İndirici")
        self.geometry("820x640")
        self.minsize(720, 500)
        self.configure(fg_color=COLORS["bg_main"])

        self.config = load_config()
        self.download_cards: List[DownloadCard] = []

        self._build_ui()
        self._check_ffmpeg_status()

    def _build_ui(self):
        # 1. Header Toolbar
        self.header_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], height=70, corner_radius=0)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        header_inner = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        header_inner.pack(fill="both", expand=True, padx=20, pady=12)

        # Big "Paste Link" Button (4K Video Downloader style)
        self.paste_btn = ctk.CTkButton(
            header_inner,
            text="➕  Bağlantıyı Yapıştır",
            font=FONTS["body_bold"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color="#ffffff",
            height=42,
            corner_radius=8,
            command=self._on_paste_link_clicked
        )
        self.paste_btn.pack(side="left", padx=(0, 15))

        # URL entry input for manual pasting if preferred
        self.url_entry = ctk.CTkEntry(
            header_inner,
            placeholder_text="YouTube video, müzik veya playlist bağlantısını buraya yapıştırın...",
            font=FONTS["body"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            height=42,
            corner_radius=8
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.url_entry.bind("<Return>", lambda event: self._process_url(self.url_entry.get().strip()))

        # Download / Enter button
        self.fetch_btn = ctk.CTkButton(
            header_inner,
            text="İncele",
            font=FONTS["body_bold"],
            fg_color="#2f313a",
            hover_color="#3b3d47",
            text_color=COLORS["text_white"],
            width=80,
            height=42,
            corner_radius=8,
            command=lambda: self._process_url(self.url_entry.get().strip())
        )
        self.fetch_btn.pack(side="left", padx=(0, 10))

        # Open Downloads Folder Button
        self.folder_btn = ctk.CTkButton(
            header_inner,
            text="📁 İndirilenler",
            font=FONTS["small"],
            fg_color="#27272a",
            hover_color="#3b3d47",
            width=100,
            height=42,
            corner_radius=8,
            command=self._open_downloads_folder
        )
        self.folder_btn.pack(side="right")

        # 2. Status Banner (FFmpeg / Alerts)
        self.banner_frame = ctk.CTkFrame(self, fg_color="#1e293b", height=32, corner_radius=0)
        self.banner_label = ctk.CTkLabel(
            self.banner_frame, 
            text="", 
            font=FONTS["small"], 
            text_color="#94a3b8"
        )
        self.banner_label.pack(pady=4)

        # 3. Content Area: Empty State vs Downloads List
        self.content_container = ctk.CTkFrame(self, fg_color=COLORS["bg_main"])
        self.content_container.pack(fill="both", expand=True, padx=20, pady=(15, 10))

        # Empty State Placeholder
        self.empty_state_frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.empty_state_frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            self.empty_state_frame,
            text="🎵",
            font=("Segoe UI", 48)
        ).pack(pady=(70, 10))

        ctk.CTkLabel(
            self.empty_state_frame,
            text="İndirmeye Başlamak İçin YouTube Bağlantısı Yapıştırın",
            font=FONTS["title"],
            text_color=COLORS["text_white"]
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            self.empty_state_frame,
            text="• 320 kbps Stüdyo Kalitesinde MP3, M4A, FLAC\n• 4K, 2K, 1080p Full HD Video\n• Otomatik Albüm Kapağı & Sanatçı Etiketleri\n• Çalma Listesi (Playlist) Desteği",
            font=FONTS["body"],
            text_color=COLORS["text_dim"],
            justify="center"
        ).pack(pady=(0, 20))

        # Scrollable Downloads List Frame (hidden when empty)
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.content_container,
            fg_color="transparent",
            scrollbar_button_color="#2f313a",
            scrollbar_button_hover_color="#3b3d47"
        )

        # 4. Bottom Footer Bar
        self.footer_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], height=32, corner_radius=0)
        self.footer_frame.pack(fill="x", side="bottom")
        self.footer_frame.pack_propagate(False)

        footer_inner = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        footer_inner.pack(fill="both", expand=True, padx=20)

        self.footer_path_lbl = ctk.CTkLabel(
            footer_inner,
            text=f"📂 Konum: {self.config.get('download_dir')}",
            font=FONTS["small"],
            text_color=COLORS["text_dim"],
            anchor="w"
        )
        self.footer_path_lbl.pack(side="left")

        self.ffmpeg_status_lbl = ctk.CTkLabel(
            footer_inner,
            text="FFmpeg: Kontrol ediliyor...",
            font=FONTS["small"],
            text_color=COLORS["text_dim"],
            anchor="e"
        )
        self.ffmpeg_status_lbl.pack(side="right")

    def _check_ffmpeg_status(self):
        if is_ffmpeg_available():
            self.ffmpeg_status_lbl.configure(text="✓ FFmpeg Hazır (320kbps & Kapak Aktif)", text_color=COLORS["success"])
            self.banner_frame.pack_forget()
        else:
            self.ffmpeg_status_lbl.configure(text="⚠️ FFmpeg Bulunamadı", text_color=COLORS["warning"])
            self.banner_frame.pack(fill="x", after=self.header_frame)
            self.banner_label.configure(
                text="⚡ En yüksek MP3 kalitesi ve albüm kapakları için FFmpeg indiriliyor... Lütfen bekleyin.",
                text_color="#38bdf8"
            )
            threading.Thread(target=self._auto_download_ffmpeg, daemon=True).start()

    def _auto_download_ffmpeg(self):
        def progress(msg, pct):
            self.after(0, lambda: self.banner_label.configure(text=f"⚡ {msg}"))

        success = download_ffmpeg(progress_callback=progress)
        def on_done():
            if success:
                self.banner_frame.pack_forget()
                self.ffmpeg_status_lbl.configure(text="✓ FFmpeg Hazır", text_color=COLORS["success"])
            else:
                self.banner_label.configure(
                    text="⚠️ FFmpeg otomatik indirilemedi. İnternet bağlantınızı kontrol edin.",
                    text_color=COLORS["danger"]
                )
        self.after(0, on_done)

    def _on_paste_link_clicked(self):
        try:
            clipboard_text = self.clipboard_get().strip()
        except Exception:
            clipboard_text = ""

        if clipboard_text and ("youtube.com" in clipboard_text or "youtu.be" in clipboard_text):
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, clipboard_text)
            self._process_url(clipboard_text)
        else:
            # If clipboard does not have a youtube link, check if input box has one
            entry_text = self.url_entry.get().strip()
            if entry_text:
                self._process_url(entry_text)
            else:
                self.url_entry.focus()
                messagebox.showinfo(
                    "Bağlantı Bekleniyor", 
                    "Panoda YouTube bağlantısı bulunamadı.\nLütfen önce bir YouTube linki kopyalayın veya arama kutusuna yapıştırın."
                )

    def _process_url(self, url: str):
        if not url:
            return

        # Show loading on button
        self.fetch_btn.configure(text="Taranıyor...", state="disabled")
        self.paste_btn.configure(state="disabled")

        def worker():
            try:
                media_info = fetch_media_info(url)
                self.after(0, lambda: self._show_format_dialog(media_info))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Hata", f"Bağlantı bilgileri alınamadı:\n{e}"))
            finally:
                self.after(0, lambda: (
                    self.fetch_btn.configure(text="İncele", state="normal"),
                    self.paste_btn.configure(state="normal")
                ))

        threading.Thread(target=worker, daemon=True).start()

    def _show_format_dialog(self, media_info: dict):
        FormatSelectionDialog(self, media_info, on_confirm=self._start_download_flow)

    def _start_download_flow(self, options: dict):
        # Switch to download list view if this is the first download
        if not self.download_cards:
            self.empty_state_frame.pack_forget()
            self.scroll_frame.pack(fill="both", expand=True)

        # Clear input field
        self.url_entry.delete(0, "end")

        # Check if user chose to download entire playlist
        if options.get("download_all_playlist") and options.get("entries"):
            for entry in options.get("entries"):
                entry_url = entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}"
                entry_info = {
                    "title": entry.get("title", "Video"),
                    "thumbnail": entry.get("thumbnail") or options.get("thumbnail"),
                    "uploader": entry.get("uploader", options.get("uploader")),
                    "original_url": entry_url
                }
                entry_options = options.copy()
                entry_options["original_url"] = entry_url
                card = DownloadCard(
                    self.scroll_frame,
                    media_info=entry_info,
                    download_options=entry_options,
                    on_remove=self._remove_card
                )
                card.pack(fill="x", pady=6)
                self.download_cards.append(card)
        else:
            media_info = {
                "title": options.get("title", options.get("original_url")),
                "thumbnail": options.get("thumbnail"),
                "uploader": options.get("uploader"),
                "duration": options.get("duration"),
                "original_url": options.get("original_url")
            }
            card = DownloadCard(
                self.scroll_frame,
                media_info=media_info,
                download_options=options,
                on_remove=self._remove_card
            )
            card.pack(fill="x", pady=6)
            self.download_cards.append(card)

    def _remove_card(self, card: DownloadCard):
        if card in self.download_cards:
            self.download_cards.remove(card)

        if not self.download_cards:
            self.scroll_frame.pack_forget()
            self.empty_state_frame.pack(fill="both", expand=True)

    def _open_downloads_folder(self):
        download_dir = self.config.get("download_dir", os.path.expanduser("~/Downloads/SonicTube"))
        os.makedirs(download_dir, exist_ok=True)
        try:
            os.startfile(download_dir)
        except Exception as e:
            subprocess.run(['explorer', os.path.normpath(download_dir)])

if __name__ == "__main__":
    app = SonicTubeApp()
    app.mainloop()
