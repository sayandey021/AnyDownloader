import json
import os
import threading

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'history.json')

class HistoryManager:
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
            print(f"Error cleaning history: {e}")

    def _save_immediately(self):
        with self._lock:
            self._save_timer = None
            try:
                with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self._history, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Failed to save history: {e}")

    def _save(self):
        # Debounce the actual save by 1 second to prevent massive disk writes when stopping/pausing many at once
        if self._save_timer is not None:
            self._save_timer.cancel()
        self._save_timer = threading.Timer(1.0, self._save_immediately)
        self._save_timer.daemon = True
        self._save_timer.start()

    def add_or_update(self, task_id, data):
        import time
        if 'timestamp' not in data:
            data['timestamp'] = time.time()
            
        with self._lock:
            for idx, item in enumerate(self._history):
                if item.get('task_id') == task_id:
                    self._history[idx] = data
                    self._save()
                    return
            self._history.insert(0, data)
            self._save()

    def remove(self, task_id):
        with self._lock:
            self._history = [item for item in self._history if item.get('task_id') != task_id]
            self._save()

    def get_all(self):
        with self._lock:
            return list(self._history)

