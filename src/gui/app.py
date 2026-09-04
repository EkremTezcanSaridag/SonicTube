import os
import sys
import threading
import subprocess
import webbrowser
from tkinter import messagebox
from typing import Optional, List
from pathlib import Path
import customtkinter as ctk
from PIL import Image

from .theme import COLORS, FONTS
from .download_card import DownloadCard
from .playlist_card import PlaylistCard
from .format_dialog import FormatSelectionDialog
from ..config import load_config, save_config
from ..downloader import fetch_media_info
from ..ffmpeg_helper import is_ffmpeg_available, download_ffmpeg

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# Asset path helper for both script and frozen exe mode
if getattr(sys, 'frozen', False):
    APP_ROOT = Path(sys.executable).resolve().parent
else:
    APP_ROOT = Path(__file__).resolve().parent.parent.parent

def get_asset_file(filename: str) -> Optional[Path]:
    search_dirs = [
        APP_ROOT / "assets",
        APP_ROOT / "_internal" / "assets",
    ]
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        search_dirs.append(Path(meipass) / "assets")

    for d in search_dirs:
        p = d / filename
        if p.exists():
            return p
    return None

class SonicTubeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SonicTube - YouTube Video & Müzik İndirici")
        self.geometry("880x660")
        self.minsize(780, 520)
        self.configure(fg_color=COLORS["bg_main"])

        self._set_window_icon()

        self.config = load_config()
        self.download_cards: List[ctk.CTkFrame] = []
        self.download_queue: List[DownloadCard] = []
        self.active_downloads: List[DownloadCard] = []
        self.max_concurrent_downloads = 2

        self._build_ui()
        self._check_ffmpeg_status()

    def _set_window_icon(self):
        ico_path = get_asset_file("icon.ico")
        if ico_path:
            try:
                self.iconbitmap(str(ico_path))
            except Exception:
                pass

    def _build_ui(self):
        # 1. Header Toolbar
        self.header_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], height=76, corner_radius=0)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        header_inner = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        header_inner.pack(fill="both", expand=True, padx=16, pady=12)

        # Brand Logo and Name
        brand_frame = ctk.CTkFrame(header_inner, fg_color="transparent")
        brand_frame.pack(side="left", padx=(0, 14))

        logo_path = get_asset_file("icon.png")
        if logo_path:
            try:
                img = Image.open(logo_path).convert("RGBA")
                self.logo_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(38, 38))
                logo_lbl = ctk.CTkLabel(brand_frame, image=self.logo_ctk, text="")
                logo_lbl.pack(side="left", padx=(0, 8))
            except Exception:
                pass

        brand_text_box = ctk.CTkFrame(brand_frame, fg_color="transparent")
        brand_text_box.pack(side="left")
        ctk.CTkLabel(
            brand_text_box,
            text="SonicTube",
            font=("Segoe UI", 16, "bold"),
            text_color="#ffffff"
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand_text_box,
            text="v1.0 Pro",
            font=("Segoe UI", 9, "bold"),
            text_color=COLORS["primary"]
        ).pack(anchor="w")

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
        self.paste_btn.pack(side="left", padx=(0, 10))

        # URL entry input for manual pasting
        self.url_entry = ctk.CTkEntry(
            header_inner,
            placeholder_text="YouTube video, müzik veya playlist bağlantısını yapıştırın...",
            font=FONTS["body"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            height=42,
            corner_radius=8
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.url_entry.bind("<Return>", lambda event: self._process_url(self.url_entry.get().strip()))

        # Examine / Enter button
        self.fetch_btn = ctk.CTkButton(
            header_inner,
            text="İncele",
            font=FONTS["body_bold"],
            fg_color="#2f313a",
            hover_color="#3b3d47",
            text_color=COLORS["text_white"],
            width=70,
            height=42,
            corner_radius=8,
            command=lambda: self._process_url(self.url_entry.get().strip())
        )
        self.fetch_btn.pack(side="left", padx=(0, 6))

        # Cancel All Downloads Button
        self.cancel_all_btn = ctk.CTkButton(
            header_inner,
            text="⏹️ İptal Et",
            font=FONTS["small"],
            fg_color="#27272a",
            hover_color=COLORS["danger_hover"],
            text_color=COLORS["text_white"],
            width=75,
            height=42,
            corner_radius=8,
            command=self._cancel_all_downloads
        )
        self.cancel_all_btn.pack(side="left", padx=(0, 6))

        # Clear Finished Downloads Button
        self.clear_btn = ctk.CTkButton(
            header_inner,
            text="🗑️ Temizle",
            font=FONTS["small"],
            fg_color="#27272a",
            hover_color="#3b3d47",
            width=75,
            height=42,
            corner_radius=8,
            command=self._clear_finished_downloads
        )
        self.clear_btn.pack(side="left", padx=(0, 6))

        # Open Downloads Folder Button
        self.folder_btn = ctk.CTkButton(
            header_inner,
            text="📁 Klasör",
            font=FONTS["small"],
            fg_color="#27272a",
            hover_color="#3b3d47",
            width=70,
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

        if logo_path:
            try:
                big_logo_img = Image.open(logo_path).convert("RGBA")
                self.big_logo_ctk = ctk.CTkImage(light_image=big_logo_img, dark_image=big_logo_img, size=(110, 110))
                ctk.CTkLabel(self.empty_state_frame, image=self.big_logo_ctk, text="").pack(pady=(45, 12))
            except Exception:
                ctk.CTkLabel(self.empty_state_frame, text="🎵", font=("Segoe UI", 48)).pack(pady=(50, 10))
        else:
            ctk.CTkLabel(self.empty_state_frame, text="🎵", font=("Segoe UI", 48)).pack(pady=(50, 10))

        ctk.CTkLabel(
            self.empty_state_frame,
            text="İndirmeye Başlamak İçin YouTube Bağlantısı Yapıştırın",
            font=FONTS["title"],
            text_color=COLORS["text_white"]
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            self.empty_state_frame,
            text="• 320 kbps Stüdyo Kalitesinde MP3, M4A, FLAC\n• 4K, 2K, 1080p Full HD Video\n• Otomatik Albüm Kapağı & Sanatçı Etiketleri\n• Tek Kart Kompakt Çalma Listesi (Playlist) Desteği",
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

        # 4. Bottom Footer Bar (with Developer Credit)
        self.footer_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], height=36, corner_radius=0)
        self.footer_frame.pack(fill="x", side="bottom")
        self.footer_frame.pack_propagate(False)

        footer_inner = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        footer_inner.pack(fill="both", expand=True, padx=20)

        # Left: Download folder path (clickable)
        self.footer_path_lbl = ctk.CTkLabel(
            footer_inner,
            text=f"📂 {self.config.get('download_dir')}",
            font=FONTS["small"],
            text_color=COLORS["text_dim"],
            cursor="hand2"
        )
        self.footer_path_lbl.pack(side="left")
        self.footer_path_lbl.bind("<Button-1>", lambda e: self._open_downloads_folder())

        # Center: Developer Signature (Ekrem Tezcan Sarıdağ) with clickable GitHub link
        self.dev_btn = ctk.CTkButton(
            footer_inner,
            text="✨ Geliştirici: Ekrem Tezcan Sarıdağ",
            font=("Segoe UI", 11, "bold"),
            fg_color="transparent",
            hover_color="#27272a",
            text_color="#10b981",
            cursor="hand2",
            height=26,
            command=self._open_developer_profile
        )
        self.dev_btn.pack(side="left", expand=True)

        # Right: FFmpeg Status
        self.ffmpeg_status_lbl = ctk.CTkLabel(
            footer_inner,
            text="FFmpeg: Kontrol ediliyor...",
            font=FONTS["small"],
            text_color=COLORS["text_dim"],
            anchor="e"
        )
        self.ffmpeg_status_lbl.pack(side="right")

    def _open_developer_profile(self):
        webbrowser.open("https://github.com/EkremTezcanSaridag")

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
                    text="⚠️ FFmpeg otomatik temin edilemedi.",
                    text_color=COLORS["danger"]
                )
        self.after(0, on_done)

    def _on_paste_link_clicked(self):
        try:
            clipboard_text = self.clipboard_get().strip()
        except Exception:
            clipboard_text = ""

        if clipboard_text and any(k in clipboard_text for k in ["youtube.com", "youtu.be"]):
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, clipboard_text)
            self._process_url(clipboard_text)
        else:
            entry_text = self.url_entry.get().strip()
            if entry_text:
                self._process_url(entry_text)
            else:
                self.url_entry.focus()
                messagebox.showinfo(
                    "Bağlantı Bekleniyor", 
                    "Panoda geçerli bir YouTube bağlantısı bulunamadı.\nLütfen bir video veya şarkı linki kopyalayıp tekrar deneyin."
                )

    def _process_url(self, url: str):
        if not url:
            return

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
        if not self.download_cards:
            self.empty_state_frame.pack_forget()
            self.scroll_frame.pack(fill="both", expand=True)

        self.url_entry.delete(0, "end")

        # 1. PLAYLIST MODE: Use single compact PlaylistCard (saves CPU & memory!)
        if options.get("download_all_playlist") and options.get("entries"):
            card = PlaylistCard(
                self.scroll_frame,
                media_info=options,
                download_options=options,
                on_remove=self._remove_card,
                on_status_change=self._on_card_status_changed
            )
            card.pack(fill="x", pady=6)
            self.download_cards.append(card)
        else:
            # 2. SINGLE VIDEO / TRACK MODE
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
                on_remove=self._remove_card,
                on_status_change=self._on_card_status_changed,
                auto_start=False
            )
            card.pack(fill="x", pady=6)
            self.download_cards.append(card)
            self.download_queue.append(card)
            self._process_queue()

    def _on_card_status_changed(self, card):
        self.after(50, self._process_queue)

    def _process_queue(self):
        # Filter active downloads to remove finished/cancelled ones
        self.active_downloads = [
            c for c in self.active_downloads 
            if hasattr(c, "is_completed") and not c.is_completed and c.winfo_exists() and (not c.download_task or not c.download_task.is_cancelled)
        ]

        while len(self.active_downloads) < self.max_concurrent_downloads and self.download_queue:
            next_card = self.download_queue.pop(0)
            if next_card.winfo_exists() and not next_card.is_completed:
                self.active_downloads.append(next_card)
                next_card.start_download()

    def _cancel_all_downloads(self):
        # 1. Clear queued items
        self.download_queue.clear()
        
        # 2. Cancel all active cards (both single cards and playlist cards)
        cancelled_count = 0
        for card in list(self.download_cards):
            if hasattr(card, "cancel"):
                card.cancel()
                cancelled_count += 1

        self.active_downloads.clear()
        messagebox.showinfo("İptal Edildi", "Tüm aktif ve sıradaki indirme işlemleri iptal edildi.")

    def _remove_card(self, card):
        if card in self.download_cards:
            self.download_cards.remove(card)
        if card in self.download_queue:
            self.download_queue.remove(card)
        if card in self.active_downloads:
            self.active_downloads.remove(card)
        self._process_queue()

        if not self.download_cards:
            self.scroll_frame.pack_forget()
            self.empty_state_frame.pack(fill="both", expand=True)

    def _clear_finished_downloads(self):
        finished = [c for c in self.download_cards if getattr(c, "is_completed", False)]
        for c in finished:
            c._remove_self()

    def _open_downloads_folder(self):
        download_dir = self.config.get("download_dir", os.path.expanduser("~/Downloads/SonicTube"))
        os.makedirs(download_dir, exist_ok=True)
        try:
            os.startfile(download_dir)
        except Exception:
            subprocess.run(['explorer', os.path.normpath(download_dir)])

if __name__ == "__main__":
    app = SonicTubeApp()
    app.mainloop()
