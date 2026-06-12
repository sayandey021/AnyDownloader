import json
import os
import threading

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'search_history.json')

class SearchHistoryManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._history = []
                    cls._instance._save_timer = None
                    cls._instance._load()
        return cls._instance

    def _load(self):
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self._history = json.load(f)
        except Exception:
            self._history = []
            
        self._clean_old()

    def _clean_old(self):
        try:
            from src.backend.settings import SettingsManager
            days = int(SettingsManager().get('auto_delete_history_days', 0))
            if days <= 0:
                return
            
            import time
            cutoff = time.time() - (days * 86400)
            original_len = len(self._history)
            
            self._history = [item for item in self._history if item.get('timestamp', time.time()) >= cutoff]
            
            if len(self._history) < original_len:
                self._save_immediately()
        except Exception as e:
            print(f"Error cleaning search history: {e}")

    def _save_immediately(self):
        with self._lock:
            self._save_timer = None
            try:
                with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self._history, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Failed to save search history: {e}")

    def _save(self):
        if self._save_timer is not None:
            self._save_timer.cancel()
        self._save_timer = threading.Timer(1.0, self._save_immediately)
        self._save_timer.daemon = True
        self._save_timer.start()

    def add_search(self, url, title, thumbnail):
        import time
        with self._lock:
            # Check if it already exists, if so move to top and update
            for idx, item in enumerate(self._history):
                if item.get('url') == url:
                    self._history.pop(idx)
                    break
            
            self._history.insert(0, {
                'url': url,
                'title': title,
                'thumbnail': thumbnail,
                'timestamp': time.time()
            })
            
            # Keep only the last 100 searches
            if len(self._history) > 100:
                self._history = self._history[:100]
                
            self._save()

    def remove_search(self, url):
        with self._lock:
            for idx, item in enumerate(self._history):
                if item.get('url') == url:
                    self._history.pop(idx)
                    self._save()
                    break

    def clear_all(self):
        with self._lock:
            self._history = []
            self._save()

    def get_all(self):
        with self._lock:
            return list(self._history)
