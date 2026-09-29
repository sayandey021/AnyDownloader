import os
import sys
import time
import uuid
import threading
import subprocess
from PySide6.QtCore import QObject, Signal, Slot, Property
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl

from src.backend.downloader import DownloaderBackend
from src.backend.settings import SettingsManager
from src.backend.history import HistoryManager
from src.backend.search_history import SearchHistoryManager
from src.controllers.models.download_list_model import DownloadListModel


class DownloaderController(QObject):
    fetchStarted = Signal()
    fetchFinished = Signal(dict)
    fetchError = Signal(str)
    
    downloadStarted = Signal(str)
    downloadProgress = Signal(str, float, str, str)  # taskId, percent, speedText, statusText
    downloadFinished = Signal(str, str)             # taskId, filePath
    downloadError = Signal(str, str)                # taskId, errorMsg
    downloadLog = Signal(str, str)                  # taskId, logMsg
    activeCountChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.backend = DownloaderBackend(run_thread=None)
        self.settings = SettingsManager()
        self.history_manager = HistoryManager()
        self.search_history_manager = SearchHistoryManager()
        self._model = DownloadListModel(self)
        self._cancel_fetch_event = threading.Event()
        self._queue_lock = threading.Lock()
        
        # Load existing history into download model
        self.load_history()

    @Property(QObject, constant=True)
    def model(self) -> DownloadListModel:
        return self._model

    def load_history(self):
        items = self.history_manager.get_all()
        for item in items:
            state = item.get('download_state', 'active')
            if state == 'active':
                state = 'paused'
            item['download_state'] = state
            self._model.add_item(item, prepend=False)

    # --- Fetch / Search ---

    @Slot(str)
    def fetchInfo(self, url: str):
        url = url.strip()
        if not url:
            self.fetchError.emit("Please enter a valid URL.")
            return

        self._cancel_fetch_event.clear()
        self.fetchStarted.emit()

        def _worker():
            try:
                info = self.backend.get_video_info(
                    url,
                    cancel_event=self._cancel_fetch_event
                )
                if self._cancel_fetch_event.is_set():
                    return

                if not info:
                    self.fetchError.emit("Could not fetch metadata for this link. Please check the URL and try again.")
                    return

                # Record in search history
                title = info.get('title') or info.get('fulltitle') or url
                thumb = info.get('thumbnail')
                if not thumb and info.get('thumbnails'):
                    thumb = info['thumbnails'][-1].get('url', '')
                self.search_history_manager.add_search(url, title, thumb or "")

                self.fetchFinished.emit(info)
            except Exception as e:
                if not self._cancel_fetch_event.is_set():
                    err_msg = str(e)
                    if "Private video" in err_msg or "Sign in" in err_msg:
                        err_msg += "\nTip: Set up browser cookies in Settings > Advanced to bypass sign-in walls."
                    self.fetchError.emit(err_msg)

        threading.Thread(target=_worker, daemon=True).start()

    @Slot()
    def cancelFetch(self):
        self._cancel_fetch_event.set()

    # --- Start Download ---

    @Slot(dict)
    def startDownload(self, opts: dict):
        info = opts.get("info", {})
        is_playlist = 'entries' in info and info.get('_type') == 'playlist'
        selected_entries = opts.get("selected_entries")
        
        # If playlist, start/queue each selected item
        if is_playlist and selected_entries is not None:
            entries = info.get('entries', [])
            create_folder = self.settings.get('create_playlist_folder', True)
            pl_title = info.get('title', 'Playlist')
            base_output = opts.get("output_path") or self.settings.get('default_download_path')
            
            if create_folder:
                import re
                clean_name = re.sub(r'[\\/*?:"<>|]', "", pl_title).strip()
                target_output = os.path.join(base_output, clean_name)
            else:
                target_output = base_output

            playlist_id = str(uuid.uuid4())
            playlist_url = info.get('webpage_url') or info.get('url') or ''

            for idx in selected_entries:
                if idx < len(entries):
                    entry = entries[idx]
                    single_opts = dict(opts)
                    single_opts["info"] = entry
                    single_opts["output_path"] = target_output
                    single_opts["playlist_id"] = playlist_id
                    single_opts["playlist_title"] = pl_title
                    single_opts["playlist_url"] = playlist_url
                    single_opts["is_playlist"] = False
                    
                    template = self.settings.get('playlist_filename_template', '%(playlist_index)s - %(title)s.%(ext)s')
                    single_opts["custom_filename"] = template.replace('%(playlist_index)s', str(idx + 1))
                    self._start_single_download(single_opts)
            return

        self._start_single_download(opts)

    def _start_single_download(self, opts: dict):
        task_id = str(uuid.uuid4())
        opts["task_id"] = task_id
        opts["download_state"] = "active"
        opts["_is_live_active"] = True
        opts["timestamp"] = time.time()
        
        # Check active count vs max concurrency
        active_count = len([it for it in self._model.get_all_items() if it.download_state == "active"])
        max_concurrent = int(self.settings.get('max_concurrent_downloads', 3))
        
        if active_count >= max_concurrent:
            opts["download_state"] = "queued"

        self._model.add_item(opts, prepend=True)
        self.history_manager.add_or_update(task_id, opts)

        if opts["download_state"] == "active":
            self._execute_download_task(task_id, opts)

        self._update_active_count()

    def _execute_download_task(self, task_id: str, opts: dict):
        url = opts.get("info", {}).get('webpage_url') or opts.get("info", {}).get('url')
        format_id = opts.get("format_id", "best")
        output_path = opts.get("output_path") or self.settings.get('default_download_path')
        is_audio = opts.get("is_audio", False)
        
        def _progress(percent, speed_str, status_str):
            prog = percent / 100.0 if percent > 0 else 0.0
            self._model.update_item_field(task_id, progress=prog, speed_text=speed_str)
            self.downloadProgress.emit(task_id, prog, speed_str, status_str)

        def _finish(final_filepath):
            self._model.update_item_field(task_id, download_state="completed", progress=1.0, speed_text="", final_filepath=final_filepath)
            it = self._model.get_item(task_id)
            if it:
                self.history_manager.add_or_update(task_id, it.to_dict())
            self.downloadFinished.emit(task_id, final_filepath)
            self._check_queue()
            self._update_active_count()

        def _error(err_str):
            self._model.update_item_field(task_id, download_state="error", speed_text="")
            it = self._model.get_item(task_id)
            if it:
                self.history_manager.add_or_update(task_id, it.to_dict())
            self.downloadError.emit(task_id, err_str)
            self._check_queue()
            self._update_active_count()

        def _log(msg):
            timestamped = f"[{time.strftime('%H:%M:%S')}] {msg}\n"
            it = self._model.get_item(task_id)
            if it:
                new_log = it.log_text + timestamped
                self._model.update_item_field(task_id, log_text=new_log)
            self.downloadLog.emit(task_id, timestamped)

        self.backend.start_download(
            url=url,
            format_id=format_id,
            output_path=output_path,
            is_audio=is_audio,
            video_ext=opts.get("video_ext"),
            audio_codec=opts.get("audio_codec"),
            audio_quality=opts.get("audio_quality"),
            settings=self.settings,
            on_progress=_progress,
            on_finish=_finish,
            on_error=_error,
            embed_thumbnail=opts.get("embed_thumbnail"),
            embed_subtitles=opts.get("embed_subtitles"),
            subtitle_lang=opts.get("subtitle_lang"),
            custom_filename=opts.get("custom_filename"),
            info=opts.get("info"),
            is_image=opts.get("is_image", False),
            image_ext=opts.get("image_ext"),
            is_thumbnail=opts.get("is_thumbnail", False),
            is_manga=opts.get("is_manga", False),
            selected_entries=opts.get("selected_entries"),
            on_log=_log,
            task_id=task_id,
            enable_sponsorblock=opts.get("enable_sponsorblock")
        )
        self.downloadStarted.emit(task_id)

    def _check_queue(self):
        with self._queue_lock:
            max_concurrent = int(self.settings.get('max_concurrent_downloads', 3))
            active_count = len([it for it in self._model.get_all_items() if it.download_state == "active"])
            
            if active_count < max_concurrent:
                queued = [it for it in self._model.get_all_items() if it.download_state == "queued"]
                if queued:
                    next_item = queued[0]
                    self._model.update_item_field(next_item.task_id, download_state="active")
                    self._execute_download_task(next_item.task_id, next_item.to_dict())

    def _update_active_count(self):
        active_count = len([it for it in self._model.get_all_items() if it.download_state == "active"])
        self.activeCountChanged.emit(active_count)

    # --- Item Actions ---

    @Slot(str)
    def pauseDownload(self, task_id: str):
        self.backend.cancel_download(task_id)
        self._model.update_item_field(task_id, download_state="paused", speed_text="")
        it = self._model.get_item(task_id)
        if it:
            self.history_manager.add_or_update(task_id, it.to_dict())
        self._check_queue()
        self._update_active_count()

    @Slot(str)
    def resumeDownload(self, task_id: str):
        it = self._model.get_item(task_id)
        if not it:
            return
        self._model.update_item_field(task_id, download_state="active")
        self._execute_download_task(task_id, it.to_dict())
        self._update_active_count()

    @Slot(str)
    def stopDownload(self, task_id: str):
        self.backend.cancel_download(task_id)
        self._model.update_item_field(task_id, download_state="cancelled", speed_text="")
        it = self._model.get_item(task_id)
        if it:
            self.history_manager.add_or_update(task_id, it.to_dict())
        self._check_queue()
        self._update_active_count()

    @Slot(str)
    def retryDownload(self, task_id: str):
        it = self._model.get_item(task_id)
        if not it:
            return
        self._model.update_item_field(task_id, download_state="active", progress=0.0, speed_text="")
        self._execute_download_task(task_id, it.to_dict())
        self._update_active_count()

    @Slot(str, bool)
    def deleteDownload(self, task_id: str, delete_file: bool = False):
        it = self._model.get_item(task_id)
        if it:
            if it.download_state == "active":
                self.backend.cancel_download(task_id)
            if delete_file and it.final_filepath and os.path.exists(it.final_filepath):
                try:
                    os.remove(it.final_filepath)
                except Exception as e:
                    print(f"Error removing file {it.final_filepath}: {e}")

        self.history_manager.remove(task_id)
        self._model.remove_item(task_id)
        self._check_queue()
        self._update_active_count()

    @Slot()
    def pauseAll(self):
        for it in self._model.get_all_items():
            if it.download_state == "active":
                self.pauseDownload(it.task_id)

    @Slot()
    def resumeAll(self):
        for it in self._model.get_all_items():
            if it.download_state in ("paused", "cancelled"):
                self.resumeDownload(it.task_id)

    @Slot()
    def stopAll(self):
        for it in self._model.get_all_items():
            if it.download_state in ("active", "queued"):
                self.stopDownload(it.task_id)

    @Slot()
    def clearFinishedHistory(self):
        for it in list(self._model.get_all_items()):
            if it.download_state in ("completed", "cancelled", "error"):
                self.history_manager.remove(it.task_id)
                self._model.remove_item(it.task_id)

    @Slot(str)
    def setFilter(self, filter_name: str):
        self._model.apply_filter(filter_name)

    # --- File & Folder opening ---

    @Slot(str)
    def openFile(self, filepath: str):
        if not filepath or not os.path.exists(filepath):
            return
        try:
            if sys.platform == "win32":
                os.startfile(filepath)
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(filepath))
        except Exception as e:
            print(f"Error opening file: {e}")

    @Slot(str)
    def openFolder(self, filepath: str):
        if not filepath:
            return
        target_dir = filepath if os.path.isdir(filepath) else os.path.dirname(filepath)
        if not os.path.exists(target_dir):
            return
        try:
            if sys.platform == "win32":
                subprocess.Popen(f'explorer /select,"{os.path.normpath(filepath)}"' if os.path.isfile(filepath) else f'explorer "{os.path.normpath(target_dir)}"')
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(target_dir))
        except Exception as e:
            print(f"Error opening folder: {e}")

    @Slot()
    def openGlobalDownloadFolder(self):
        path = self.settings.get('default_download_path') or os.path.join(os.path.expanduser('~'), 'Downloads')
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        self.openFolder(path)
