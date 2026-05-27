import flet as ft
import os
import time
from src.ui.theme import AppTheme
from src.backend.history import HistoryManager

class DownloadCard(ft.Container):
    def __init__(self, page: ft.Page, info: dict, backend, format_id: str, is_audio: bool, output_path: str, settings,
                 video_ext=None, audio_codec=None, audio_quality=None,
                 embed_thumbnail=None, embed_subtitles=None, subtitle_lang=None, custom_filename=None, 
                 is_image=False, image_ext=None, is_thumbnail=False,
                 on_state_change=None, restored_task_id=None, restored_state=None, final_filepath=None,
                 on_redownload=None, restored_log_text="", source_mode=None):
        super().__init__()
        self._page = page
        self.info = info
        self.backend = backend
        self.format_id = format_id
        self.is_audio = is_audio
        self.output_path = output_path
        self.settings = settings
        self.video_ext = video_ext
        self.audio_codec = audio_codec
        self.audio_quality = audio_quality
        self.embed_thumbnail = embed_thumbnail
        self.embed_subtitles = embed_subtitles
        self.subtitle_lang = subtitle_lang
        self.custom_filename = custom_filename
        self.is_image = is_image
        self.image_ext = image_ext
        self.is_thumbnail = is_thumbnail
        self.on_state_change = on_state_change
        self.download_state = restored_state if restored_state else "active"
        self.task_id = restored_task_id
        self.last_update_time = 0
        self.is_deleted = False
        self.final_filepath = final_filepath
        self.on_redownload = on_redownload
        self.log_text = restored_log_text
        self.history_manager = HistoryManager()
        self.source_mode = source_mode if source_mode else ('audio' if is_audio else 'video')
        self._build_ui()

    def _build_ui(self):
        self.bgcolor = AppTheme.SURFACE
        self.border_radius = 10
        self.padding = 15
        self.margin = ft.Margin(left=0, top=0, right=0, bottom=10)

        # Thumbnail
        thumb_url = self.info.get('thumbnail')
        if not thumb_url and self.info.get('thumbnails'):
            thumb_url = self.info['thumbnails'][0]['url']

        # Determine if thumbnail should be square (1:1) or 16:9
        is_square = False
        extractor = self.info.get('extractor', '').lower()
        extractor_key = self.info.get('extractor_key', '').lower()
        if any(x in extractor or x in extractor_key for x in ['tidal', 'spotify', 'apple', 'qobuz', 'soundcloud', 'deezer', 'gaana', 'lastfm']):
            is_square = True
            
        thumbnails = self.info.get('thumbnails', [])
        if thumbnails and isinstance(thumbnails, list):
            for t in thumbnails:
                w = t.get('width')
                h = t.get('height')
                if w and h:
                    if abs(w / h - 1.0) < 0.1:
                        is_square = True
                    else:
                        is_square = False
                    break
                    
        thumb_height = 56
        thumb_width = 56 if is_square else 100

        thumb_b64 = self.info.get('thumbnail_base64')
        thumb_src = None
        if thumb_b64:
            import base64
            thumb_src = base64.b64decode(thumb_b64)
        elif thumb_url:
            thumb_src = thumb_url
        else:
            thumb_src = "https://via.placeholder.com/150"
        
        fallback_icon = ft.Icons.MUSIC_NOTE_ROUNDED if self.is_audio else ft.Icons.ONDEMAND_VIDEO_ROUNDED
        self.thumbnail = ft.Image(
            src=thumb_src,
            width=thumb_width,
            height=thumb_height,
            fit=ft.BoxFit.COVER,
            border_radius=5,
            error_content=ft.Container(
                content=ft.Icon(fallback_icon, size=40, color=AppTheme.TEXT_SECONDARY),
                width=thumb_width,
                height=thumb_height,
                bgcolor=AppTheme.SURFACE_VARIANT,
                border_radius=5,
                alignment=ft.Alignment(0, 0)
            )
        )

        title = self.info.get('title', 'Unknown Title')
        self.title_text = ft.Text(title, color=AppTheme.TEXT_PRIMARY, weight=ft.FontWeight.W_600, size=14, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
        
        status_str = "Downloading"
        status_color = AppTheme.TEXT_SECONDARY
        
        if self.download_state == "paused":
            status_str = "Paused"
            status_color = AppTheme.ACCENT
        elif self.download_state == "completed":
            status_str = "Download complete"
            status_color = AppTheme.SUCCESS
        elif self.download_state == "cancelled":
            status_str = "Stopped"
            status_color = AppTheme.ERROR
        elif self.download_state == "error":
            status_str = "Error"
            status_color = AppTheme.ERROR
        elif self.download_state == "queued":
            status_str = "Queued (Waiting...)"
            status_color = AppTheme.TEXT_SECONDARY
            
        self.status_text = ft.Text(status_str, color=status_color, size=12)
        self.speed_text = ft.Text("", color=AppTheme.TEXT_SECONDARY, size=12)
        
        progress_val = 0
        if self.download_state == "completed":
            progress_val = 1.0
            
        self.progress_bar = ft.ProgressBar(value=progress_val, color=AppTheme.ACCENT, bgcolor=AppTheme.SURFACE_VARIANT, height=4)
        
        self.actions_row = ft.Row(spacing=0)

        # Layout
        self.content = ft.Row([
            self.thumbnail,
            ft.Column([
                self.title_text,
                ft.Row([self.status_text, self.speed_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.progress_bar,
            ], expand=True, spacing=5),
            self.actions_row
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def did_mount(self):
        if not self.task_id and self.download_state == "active":
            self.start_task()
        elif self.download_state == "queued":
            pass # Wait for MainView to start it
        self.update_actions()

    def start_task(self):
        # Start or resume download task
        url = self.info.get('webpage_url') or self.info.get('url')
        self.task_id = self.backend.start_download(
            url, 
            self.format_id, 
            self.output_path, 
            self.is_audio, 
            video_ext=self.video_ext,
            audio_codec=self.audio_codec,
            audio_quality=self.audio_quality,
            settings=self.settings,
            on_progress=self.handle_progress,
            on_finish=self.handle_finish,
            on_error=self.handle_error,
            embed_thumbnail=self.embed_thumbnail,
            embed_subtitles=self.embed_subtitles,
            subtitle_lang=self.subtitle_lang,
            custom_filename=self.custom_filename,
            info=self.info,
            is_image=self.is_image,
            image_ext=self.image_ext,
            is_thumbnail=self.is_thumbnail,
            on_log=self.handle_log,
        )
        self.save_history()

    def handle_log(self, msg):
        if not hasattr(self, 'log_text'):
            self.log_text = ""
        self.log_text += f"[{time.strftime('%H:%M:%S')}] {msg}\n"
        # Optional: if you want the dialog to update live while open,
        # but typical usage is just accumulating the string.

    def save_history(self):
        if not self.task_id:
            import uuid
            self.task_id = str(uuid.uuid4())
            
        data = {
            'task_id': self.task_id,
            'info': self.info,
            'format_id': self.format_id,
            'is_audio': self.is_audio,
            'output_path': self.output_path,
            'video_ext': self.video_ext,
            'audio_codec': self.audio_codec,
            'audio_quality': self.audio_quality,
            'embed_thumbnail': self.embed_thumbnail,
            'embed_subtitles': self.embed_subtitles,
            'subtitle_lang': self.subtitle_lang,
            'custom_filename': self.custom_filename,
            "is_image": self.is_image,
            "image_ext": self.image_ext,
            "is_thumbnail": self.is_thumbnail,
            'download_state': self.download_state,
            'final_filepath': self.final_filepath,
            'log_text': self.log_text,
            'source_mode': self.source_mode
        }
        self.history_manager.add_or_update(self.task_id, data)

    def update_actions(self):
        self.actions_row.controls.clear()
        
        open_folder_btn = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN_ROUNDED,
            icon_color=AppTheme.TEXT_SECONDARY,
            tooltip="Open Folder",
            on_click=self.open_location
        )
        
        log_btn = ft.IconButton(
            icon=ft.Icons.RECEIPT_LONG_ROUNDED,
            icon_color=AppTheme.TEXT_SECONDARY,
            tooltip="View Logs",
            on_click=self.show_logs
        )

        redownload_btn = ft.IconButton(
            icon=ft.Icons.DOWNLOAD_ROUNDED,
            icon_color=AppTheme.PRIMARY,
            tooltip="Download Again",
            on_click=self.trigger_redownload
        )
        
        if self.download_state == "active":
            controls = []
            if not getattr(self, 'info', {}).get('is_live', False):
                controls.append(ft.IconButton(icon=ft.Icons.PAUSE_ROUNDED, icon_color=AppTheme.ACCENT, tooltip="Pause", on_click=self.pause_download))
            controls.extend([
                ft.IconButton(icon=ft.Icons.STOP_ROUNDED, icon_color=AppTheme.ERROR, tooltip="Stop", on_click=self.stop_download),
                open_folder_btn, log_btn
            ])
            self.actions_row.controls.extend(controls)
        elif self.download_state == "paused":
            self.actions_row.controls.extend([
                ft.IconButton(icon=ft.Icons.PLAY_ARROW_ROUNDED, icon_color=AppTheme.SUCCESS, tooltip="Resume", on_click=self.resume_download),
                ft.IconButton(icon=ft.Icons.STOP_ROUNDED, icon_color=AppTheme.ERROR, tooltip="Stop", on_click=self.stop_download),
                open_folder_btn, log_btn
            ])
        elif self.download_state == "completed":
            delete_btn = ft.IconButton(icon=ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=AppTheme.ERROR, tooltip="Delete", on_click=self.show_delete_dialog)
            self.actions_row.controls.extend([redownload_btn, open_folder_btn, log_btn, delete_btn])
        elif self.download_state in ("cancelled", "error"):
            delete_btn = ft.IconButton(icon=ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=AppTheme.ERROR, tooltip="Delete", on_click=self.show_delete_dialog)
            self.actions_row.controls.extend([
                redownload_btn,
                ft.IconButton(icon=ft.Icons.REFRESH_ROUNDED, icon_color=AppTheme.PRIMARY, tooltip="Retry", on_click=self.retry_download),
                open_folder_btn, log_btn, delete_btn
            ])
        elif self.download_state == "queued":
            delete_btn = ft.IconButton(icon=ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=AppTheme.ERROR, tooltip="Cancel", on_click=self.show_delete_dialog)
            self.actions_row.controls.extend([
                ft.IconButton(icon=ft.Icons.PLAY_ARROW_ROUNDED, icon_color=AppTheme.SUCCESS, tooltip="Start Now", on_click=self.resume_download),
                delete_btn
            ])
            
        self.update()

    def show_snack(self, message, color):
        if getattr(self, 'snack_bar', None) in self._page.overlay:
            self._page.overlay.remove(self.snack_bar)
            
        self.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=AppTheme.TEXT_PRIMARY),
            bgcolor=color,
            duration=3000
        )
        self._page.overlay.append(self.snack_bar)
        self.snack_bar.open = True
        self._page.update()

    def pause_download(self, e):
        if self.task_id:
            self.backend.cancel_download(self.task_id)
        self.status_text.value = "Paused"
        self.status_text.color = AppTheme.ACCENT
        self.download_state = "paused"
        self.log_text += f"[{time.strftime('%H:%M:%S')}] Download paused by user.\n"
        self.update_actions()
        self.save_history()
        if self.on_state_change:
            self.on_state_change(self)
        self.show_snack("Download paused", AppTheme.ACCENT)
        if self.on_state_change:
            self.on_state_change(self)

    def resume_download(self, e):
        self.status_text.value = "Resuming..."
        self.status_text.color = AppTheme.TEXT_SECONDARY
        self.download_state = "active"
        self.log_text += f"[{time.strftime('%H:%M:%S')}] Download resumed.\n"
        self.update_actions()
        self.start_task()
        if self.on_state_change:
            self.on_state_change(self)
        self.save_history()
        self.show_snack("Resuming download...", AppTheme.SUCCESS)
        if self.on_state_change:
            self.on_state_change(self)

    def stop_download(self, e):
        if self.task_id:
            self.backend.cancel_download(self.task_id)
        self.status_text.value = "Stopped"
        self.status_text.color = AppTheme.ERROR
        self.download_state = "cancelled"
        self.log_text += f"[{time.strftime('%H:%M:%S')}] Download stopped by user.\n"
        self.update_actions()
        self.save_history()
        if self.on_state_change:
            self.on_state_change(self)
        self.show_snack("Download stopped", AppTheme.ERROR)
        if self.on_state_change:
            self.on_state_change(self)
        self.safe_update()
            
    def retry_download(self, e):
        self.progress_bar.value = 0
        self.speed_text.value = ""
        self.status_text.value = "Downloading"
        self.status_text.color = AppTheme.TEXT_SECONDARY
        self.download_state = "active"
        self.log_text += f"[{time.strftime('%H:%M:%S')}] Restarting download...\n"
        self.start_task()
        self.update_actions()
        self.save_history()
        self.show_snack("Restarting download...", AppTheme.PRIMARY)
        if self.on_state_change:
            self.on_state_change(self)

    def open_location(self, e):
        if os.path.exists(self.output_path):
            os.startfile(self.output_path)
            self.show_snack("Opening folder...", AppTheme.SUCCESS)
        else:
            self.show_snack("Folder not found", AppTheme.ERROR)

    def show_logs(self, e):
        def close_dlg(ev):
            dlg.open = False
            self._page.update()

        log_content = ft.TextField(
            value=self.log_text if self.log_text else "No logs available.",
            multiline=True,
            read_only=True,
            expand=True,
            border_color=AppTheme.SURFACE_VARIANT,
            text_size=12
        )
        
        dlg = ft.AlertDialog(
            title=ft.Text("Download Logs", color=AppTheme.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            content=ft.Container(content=log_content, width=600, height=400),
            bgcolor=AppTheme.SURFACE,
            shape=ft.RoundedRectangleBorder(radius=10),
            actions=[ft.TextButton("Close", on_click=close_dlg, style=ft.ButtonStyle(color=AppTheme.PRIMARY))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dlg)
        dlg.open = True
        self._page.update()

    def trigger_redownload(self, e):
        if self.on_redownload:
            self.on_redownload(self.info)

    def show_delete_dialog(self, e):
        dlg = ft.AlertDialog(
            title=ft.Text("Delete Download", color=AppTheme.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            content=ft.Text("Do you want to just remove this from the list, or also delete the downloaded file(s) from your storage?", color=AppTheme.TEXT_SECONDARY),
            bgcolor=AppTheme.SURFACE,
            shape=ft.RoundedRectangleBorder(radius=10),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self._close_dialog(dlg)),
                ft.TextButton("Remove from List", on_click=lambda e: self.remove_from_list(dlg)),
                ft.TextButton("Delete from Storage", style=ft.ButtonStyle(color=AppTheme.ERROR), on_click=lambda e: self.delete_from_storage(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dlg)
        dlg.open = True
        self._page.update()

    def _close_dialog(self, dlg):
        dlg.open = False
        self._page.update()

    def remove_from_list(self, dlg=None):
        if dlg:
            self._close_dialog(dlg)
        self.is_deleted = True
        if self.task_id:
            self.history_manager.remove(self.task_id)
        if self.on_state_change:
            self.on_state_change(self)

    def delete_from_storage(self, dlg):
        import glob
        import re
        import os
        if getattr(self, 'final_filepath', None):
            basename = os.path.basename(self.final_filepath)
            base_name_no_ext = os.path.splitext(basename)[0]
            
            # Retroactive fix: if the history saved a temporary format file (e.g. .f137), strip it
            base_name_no_ext = re.sub(r'\.f[a-zA-Z0-9]+$', '', base_name_no_ext)
            
            # Look in the actual output_path instead of the path stored in final_filepath
            target_dir = getattr(self, 'output_path', '')
            if not target_dir or not os.path.exists(target_dir):
                target_dir = os.path.dirname(self.final_filepath)
                
            base_path = os.path.join(target_dir, base_name_no_ext)
            
            # Try to delete files matching the base path (e.g., .mp4, .mp3, .webp, .jpg)
            escaped_path = glob.escape(base_path)
            for f in glob.glob(f"{escaped_path}.*"):
                try:
                    os.remove(f)
                except Exception as ex:
                    print(f"Failed to delete {f}: {ex}")
        self.remove_from_list(dlg)

    def safe_update(self):
        try:
            if hasattr(self, '_page') and self._page:
                if hasattr(self._page, 'run_task'):
                    async def _update():
                        try:
                            self.progress_bar.update()
                            self.status_text.update()
                            self.speed_text.update()
                            self.update()
                        except Exception: pass
                    self._page.run_task(_update)
                else:
                    self._page.update()
        except Exception as e:
            print(f"[DEBUG] safe_update error: {e}")

    def handle_progress(self, d):
        if d.get('filename'):
            fname = d['filename']
            if fname.endswith('.part'): fname = fname[:-5]
            elif fname.endswith('.ytdl'): fname = fname[:-5]
            self.final_filepath = fname

        current_time = time.time()
        if current_time - self.last_update_time < 0.2 and d['percent'] < 100:
            return
        self.last_update_time = current_time

        total = d.get('total_bytes')
        if total is None:
            total = 0
            
        if total > 0:
            self.progress_bar.value = d['percent'] / 100.0
        else:
            self.progress_bar.value = None  # Indeterminate for live streams
        
        status = d.get('status', 'downloading')
        if status == 'downloading':
            if total > 0:
                self.status_text.value = f"Downloading ({d['percent']:.1f}%)"
            else:
                downloaded_mb = d.get('downloaded_bytes', 0) / (1024 * 1024)
                elapsed = d.get('elapsed_secs')
                if elapsed is not None:
                    h, m = divmod(int(elapsed), 3600)
                    m, s = divmod(m, 60)
                    time_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
                    self.status_text.value = f"Downloading ({downloaded_mb:.1f}MB) - {time_str}"
                else:
                    self.status_text.value = f"Downloading ({downloaded_mb:.1f}MB)"
        else:
            self.status_text.value = "Converting" if status == 'processing' else status.capitalize()

        eta_str = d.get('eta', 'N/A')
        self.speed_text.value = f"{d['speed']}" + (f" - ETA: {eta_str}" if eta_str and eta_str != 'N/A' else "")

        # Also add detailed progress to the log text occasionally
        if status == 'downloading':
            if not hasattr(self, '_last_log_time'):
                self._last_log_time = 0
            if current_time - self._last_log_time >= 3.0:
                self._last_log_time = current_time
                mb_downloaded = d.get('downloaded_bytes', 0) / (1024 * 1024)
                if total > 0:
                    total_mb = total / (1024 * 1024)
                    log_msg = f"Progress: {d['percent']:.1f}% ({mb_downloaded:.1f}MB / {total_mb:.1f}MB) at {d.get('speed', 'N/A')}"
                else:
                    log_msg = f"Live Download: {mb_downloaded:.1f}MB at {d.get('speed', 'N/A')}"
                print(f"[DEBUG] UI Update: {log_msg}")
                self.handle_log(log_msg)
                
        self.safe_update()

    def handle_finish(self, final_file=None):
        if final_file:
            self.final_filepath = final_file
        self.status_text.value = "Download complete"
        self.status_text.color = AppTheme.SUCCESS
        self.speed_text.value = ""
        self.progress_bar.value = 1.0
        self.download_state = "completed"
        self.log_text += f"[{time.strftime('%H:%M:%S')}] Download completed successfully.\n"
        self.update_actions()
        self.save_history()
        self.show_snack(f"Download complete: {self.info.get('title', 'Unknown Title')}", AppTheme.SUCCESS)
        if self.on_state_change:
            self.on_state_change(self)
        self.safe_update()

    def handle_error(self, err_msg):
        self.speed_text.value = ""
        if self.download_state != "paused":
            self.progress_bar.value = 0
        if "Cancel" not in err_msg:
            print(f"[DOWNLOAD ERROR] Task {self.task_id} failed: {err_msg}")
            self.log_text += f"[{time.strftime('%H:%M:%S')}] Error: {err_msg}\n"
            self.status_text.value = "Error"
            self.status_text.color = AppTheme.ERROR
            self.download_state = "error"
            self.show_snack("Download failed", AppTheme.ERROR)
        else:
            if self.download_state != "paused":
                self.status_text.value = "Stopped"
                self.status_text.color = AppTheme.ERROR
                self.download_state = "cancelled"
                self.log_text += f"[{time.strftime('%H:%M:%S')}] Download stopped.\n"
                self.show_snack("Download stopped", AppTheme.ERROR)
        self.update_actions()
        self.save_history()
        if self.on_state_change:
            self.on_state_change(self)
        self.safe_update()
