import os
import subprocess
import sys
from PySide6.QtCore import QObject, Signal, Slot, Property
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl

from src.backend.history import HistoryManager
from src.backend.search_history import SearchHistoryManager
from src.controllers.models.history_list_model import HistoryListModel


class HistoryController(QObject):
    historyRefreshed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.history_manager = HistoryManager()
        self.search_history_manager = SearchHistoryManager()
        self._model = HistoryListModel(self)
        self.load_history()

    @Property(QObject, constant=True)
    def model(self) -> HistoryListModel:
        return self._model

    @Slot()
    def load_history(self):
        downloads = self.history_manager.get_all()
        searches = self.search_history_manager.get_all()
        self._model.set_items(downloads, searches)
        self.historyRefreshed.emit()

    @Slot(str)
    def setFilter(self, filter_name: str):
        self._model.apply_filter(filter_name)

    @Slot(str)
    def removeDownload(self, task_id: str):
        self.history_manager.remove(task_id)
        self._model.remove_item("download", task_id)

    @Slot(str)
    def removeSearch(self, url: str):
        self.search_history_manager.remove_search(url)
        self._model.remove_item("search", url)

    @Slot()
    def clearAll(self):
        # Clear searches
        self.search_history_manager.clear_all()
        # Clear completed/stopped history items
        all_dls = self.history_manager.get_all()
        for dl in all_dls:
            state = dl.get('download_state')
            if state in ('completed', 'cancelled', 'error'):
                t_id = dl.get('task_id')
                if t_id:
                    self.history_manager.remove(t_id)
        self.load_history()

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
