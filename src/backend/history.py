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
                    cls._instance._load()
        return cls._instance

    def _load(self):
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self._history = json.load(f)
        except Exception:
            self._history = []

    def _save(self):
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save history: {e}")

    def add_or_update(self, task_id, data):
        with self._lock:
            # Check if task_id exists
            for idx, item in enumerate(self._history):
                if item.get('task_id') == task_id:
                    self._history[idx] = data
                    self._save()
                    return
            
            # If not found, add to the front (recent first)
            self._history.insert(0, data)
            self._save()

    def remove(self, task_id):
        with self._lock:
            self._history = [item for item in self._history if item.get('task_id') != task_id]
            self._save()

    def get_all(self):
        with self._lock:
            return list(self._history)
