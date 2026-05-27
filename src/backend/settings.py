import json
import os
import tempfile

import sys

if getattr(sys, 'frozen', False):
    # If packaged, store settings in a persistent user directory
    _app_data_dir = os.path.join(os.path.expanduser('~'), '.AnyDownloader')
    os.makedirs(_app_data_dir, exist_ok=True)
    SETTINGS_FILE = os.path.join(_app_data_dir, 'settings.json')
else:
    SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'settings.json')
DEFAULTS = {
    'default_download_path': os.path.join(os.path.expanduser('~'), 'Downloads'),
    'temp_download_path': tempfile.gettempdir(),
    'preferred_format': 'best',
    'audio_codec': 'mp3',
    'audio_quality': '192',
    'filename_template': '%(title)s.%(ext)s',
    'speed_limit': 0,  # 0 = no limit, otherwise bytes/sec
    'embed_thumbnail': True,
    'embed_subtitles': False,
    'embed_metadata': True,
    'auto_subtitle_lang': 'en',
    'browser_cookies': 'none',
    'theme': 'dark',  # 'dark' or 'light'
    'accent_color': 'Rose',
    'bg_image_path': '/bg_4.png',
    'bg_image_opacity': 0.1,
    'max_concurrent_downloads': 3,
    'playlist_filename_template': '%(playlist_index)s - %(title)s.%(ext)s',
    'create_playlist_folder': True,
    'close_behavior': 'prompt',  # 'prompt', 'tray', 'exit'
    'ask_on_close': True,
}


class SettingsManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = {}
            cls._instance._load()
        return cls._instance

    def _load(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    self._settings = json.load(f)
        except Exception:
            self._settings = {}
        # Fill in any missing keys with defaults
        for key, value in DEFAULTS.items():
            if key not in self._settings:
                self._settings[key] = value
                
        # Enforce temp_download_path is not empty since it's no longer optional
        if not self._settings.get('temp_download_path'):
            self._settings['temp_download_path'] = DEFAULTS['temp_download_path']

    def save(self):
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def get(self, key, default=None):
        return self._settings.get(key, default if default is not None else DEFAULTS.get(key))

    def set(self, key, value):
        self._settings[key] = value

    def all(self):
        return dict(self._settings)

    def reset(self):
        self._settings = dict(DEFAULTS)
        self.save()
