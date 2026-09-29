import os
import sys
import threading
import subprocess
import importlib.util
from PySide6.QtCore import QObject, Signal, Slot, Property
from PySide6.QtWidgets import QFileDialog, QApplication

from src.backend.settings import SettingsManager, DEFAULTS
from src.backend.ffmpeg_manager import is_ffmpeg_available, download_ffmpeg
from src.backend.cookie_manager import CookieManager
from src.backend.engine_manager import (
    get_installed_engine_versions,
    check_for_engine_updates,
    update_engines,
)


class SettingsController(QObject):
    settingsChanged = Signal()
    engineStatusUpdated = Signal(dict)
    engineUpdateProgress = Signal(str)
    engineUpdateFinished = Signal(bool, str)
    troubleshootStatusUpdated = Signal(dict)
    loadedDllsUpdated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = SettingsManager()

    # --- Generic settings access ---

    @Slot(str, result="QVariant")
    def get(self, key: str):
        return self.settings.get(key)

    @Slot(str, "QVariant")
    def set(self, key: str, value):
        self.settings.set(key, value)
        self.settings.save()
        self.settingsChanged.emit()

    @Slot()
    def save(self):
        self.settings.save()
        self.settingsChanged.emit()

    @Slot()
    def resetDefaults(self):
        self.settings.reset()
        self.settingsChanged.emit()

    # --- Folder & File Dialogs ---

    @Slot(str, result=str)
    def browseFolder(self, current_path: str = "") -> str:
        start_dir = current_path if current_path and os.path.isdir(current_path) else os.path.expanduser("~")
        chosen = QFileDialog.getExistingDirectory(
            None,
            "Select Download Directory",
            start_dir,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        return chosen or ""

    @Slot(str, str, result=str)
    def browseFile(self, title: str = "Select File", filter_str: str = "All Files (*.*)") -> str:
        chosen, _ = QFileDialog.getOpenFileName(
            None,
            title,
            os.path.expanduser("~"),
            filter_str
        )
        return chosen or ""

    @Slot(result=str)
    def browseBgImage(self) -> str:
        chosen, _ = QFileDialog.getOpenFileName(
            None,
            "Select Background Image",
            os.path.expanduser("~"),
            "Images (*.png *.jpg *.jpeg *.webp)"
        )
        return chosen or ""

    # --- Backend Engines & Updates ---

    @Slot()
    def loadEngineVersionsAsync(self):
        def _worker():
            versions = get_installed_engine_versions(force_refresh=False)
            self.engineStatusUpdated.emit({
                'engines': {
                    k: {'current': v, 'latest': v, 'update_available': False}
                    for k, v in versions.items()
                },
                'has_updates': False,
                'checking': False
            })

        threading.Thread(target=_worker, daemon=True).start()

    @Slot()
    def checkForEngineUpdates(self):
        def _worker():
            try:
                results = check_for_engine_updates(force_refresh=True)
                results['checking'] = False
                self.engineStatusUpdated.emit(results)
            except Exception as e:
                self.engineStatusUpdated.emit({'error': str(e), 'checking': False})

        threading.Thread(target=_worker, daemon=True).start()

    @Slot(list)
    def updateEnginesNow(self, packages: list = None):
        if not packages:
            packages = ['yt-dlp', 'spotdl', 'curl_cffi']

        def _worker():
            def _progress(msg):
                self.engineUpdateProgress.emit(msg)

            success, msg = update_engines(packages=packages, progress_callback=_progress)
            self.engineUpdateFinished.emit(success, msg)
            # Refresh versions
            self.checkForEngineUpdates()

        threading.Thread(target=_worker, daemon=True).start()

    # --- System Diagnostics & Troubleshoot ---

    @Slot()
    def runTroubleshoot(self):
        def _worker():
            deps = [
                ("yt-dlp (YouTube & 1000+ sites)", importlib.util.find_spec("yt_dlp") is not None),
                ("spotdl (Spotify Download)", importlib.util.find_spec("spotdl") is not None),
                ("requests (HTTP Client)", importlib.util.find_spec("requests") is not None),
                ("beautifulsoup4 (HTML Parser)", importlib.util.find_spec("bs4") is not None),
                ("curl_cffi (Bypass Protection)", importlib.util.find_spec("curl_cffi") is not None),
                ("Pillow (Image Processing)", importlib.util.find_spec("PIL") is not None),
                ("FFmpeg (Audio/Video Processing)", is_ffmpeg_available()),
            ]
            all_ok = all(installed for _, installed in deps)
            status_data = {
                'all_ok': all_ok,
                'items': [{'name': name, 'installed': installed} for name, installed in deps]
            }
            self.troubleshootStatusUpdated.emit(status_data)

        threading.Thread(target=_worker, daemon=True).start()

    @Slot()
    def fixDependencies(self):
        def _worker():
            if not getattr(sys, 'frozen', False):
                req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'requirements.txt')
                if os.path.exists(req_file):
                    try:
                        c_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                        si = None
                        if os.name == 'nt':
                            si = subprocess.STARTUPINFO()
                            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                            si.wShowWindow = 0
                        subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_file], check=False, creationflags=c_flags, startupinfo=si)
                    except Exception:
                        pass

            if not is_ffmpeg_available():
                try:
                    download_ffmpeg()
                except Exception:
                    pass

            self.runTroubleshoot()

        threading.Thread(target=_worker, daemon=True).start()

    @Slot()
    def loadSystemDlls(self):
        def _worker():
            try:
                pid = os.getpid()
                c_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                si = None
                if os.name == 'nt':
                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    si.wShowWindow = 0
                output = subprocess.check_output(
                    f'tasklist /m /fi "pid eq {pid}"',
                    shell=True,
                    text=True,
                    creationflags=c_flags,
                    startupinfo=si
                )
                self.loadedDllsUpdated.emit(output)
            except Exception as ex:
                self.loadedDllsUpdated.emit(f"Error fetching DLLs: {ex}")

        threading.Thread(target=_worker, daemon=True).start()

    # --- Embedded Browser Login ---

    @Slot(str)
    def openBrowserLogin(self, url: str):
        def _worker():
            CookieManager.open_login_window(url)
            # Auto set cookies path if successfully extracted
            p = CookieManager.get_anydownloader_cookie_path()
            if os.path.exists(p):
                self.set('cookies_path', p)

        threading.Thread(target=_worker, daemon=True).start()
