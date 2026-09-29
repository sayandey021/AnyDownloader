import os
import time
from datetime import datetime
from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal, QByteArray


class HistoryEntry:
    def __init__(self, data: dict, item_type: str = "download"):
        self.item_type = item_type  # "download" or "search"
        self.raw_data = data
        self.task_id = str(data.get("task_id", "") or "")
        
        if item_type == "download":
            info = data.get("info", {})
            self.title = info.get("title") or info.get("fulltitle") or "Unknown Media"
            thumb = info.get("thumbnail")
            if not thumb and info.get("thumbnails"):
                thumb = info["thumbnails"][-1].get("url", "")
            self.thumbnail = thumb or ""
            self.url = info.get("webpage_url") or info.get("url") or ""
            self.is_audio = bool(data.get("is_audio", False))
            self.final_filepath = str(data.get("final_filepath", "") or "")
            self.output_path = str(data.get("output_path", "") or "")
            self.download_state = str(data.get("download_state", "completed"))
            self.timestamp = float(data.get("timestamp", 0.0))
            
            # Badges
            if self.is_audio:
                codec = data.get("audio_codec", "mp3").upper()
                self.format_badge = codec
            else:
                ext = (data.get("video_ext") or "MP4").upper()
                self.format_badge = ext
        else:
            # Search entry
            self.title = data.get("title") or data.get("url") or "Search Query"
            self.thumbnail = data.get("thumbnail") or ""
            self.url = data.get("url") or ""
            self.is_audio = False
            self.final_filepath = ""
            self.output_path = ""
            self.download_state = "searched"
            self.timestamp = float(data.get("timestamp", 0.0))
            self.format_badge = "Search"

    @property
    def formatted_date(self) -> str:
        if not self.timestamp:
            return ""
        try:
            dt = datetime.fromtimestamp(self.timestamp)
            now = datetime.now()
            if dt.date() == now.date():
                return f"Today {dt.strftime('%H:%M')}"
            days_diff = (now.date() - dt.date()).days
            if days_diff == 1:
                return f"Yesterday {dt.strftime('%H:%M')}"
            elif days_diff < 7:
                return dt.strftime("%a %H:%M")
            return dt.strftime("%b %d, %Y")
        except Exception:
            return ""

    @property
    def formatted_size(self) -> str:
        if self.final_filepath and os.path.exists(self.final_filepath):
            try:
                sz = os.path.getsize(self.final_filepath)
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if sz < 1024.0:
                        return f"{sz:.1f} {unit}"
                    sz /= 1024.0
                return f"{sz:.1f} TB"
            except Exception:
                pass
        return ""


class HistoryListModel(QAbstractListModel):
    ItemTypeRole = Qt.UserRole + 1
    TaskIdRole = Qt.UserRole + 2
    TitleRole = Qt.UserRole + 3
    ThumbnailRole = Qt.UserRole + 4
    UrlRole = Qt.UserRole + 5
    IsAudioRole = Qt.UserRole + 6
    FinalFilepathRole = Qt.UserRole + 7
    OutputPathRole = Qt.UserRole + 8
    DownloadStateRole = Qt.UserRole + 9
    TimestampRole = Qt.UserRole + 10
    FormattedDateRole = Qt.UserRole + 11
    FormattedSizeRole = Qt.UserRole + 12
    FormatBadgeRole = Qt.UserRole + 13
    RawDataRole = Qt.UserRole + 14

    countChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_items: list[HistoryEntry] = []
        self._filtered_items: list[HistoryEntry] = []
        self._current_filter: str = "all"  # "all", "downloads", "searches"

    def roleNames(self):
        return {
            self.ItemTypeRole: QByteArray(b"itemType"),
            self.TaskIdRole: QByteArray(b"taskId"),
            self.TitleRole: QByteArray(b"title"),
            self.ThumbnailRole: QByteArray(b"thumbnail"),
            self.UrlRole: QByteArray(b"url"),
            self.IsAudioRole: QByteArray(b"isAudio"),
            self.FinalFilepathRole: QByteArray(b"finalFilepath"),
            self.OutputPathRole: QByteArray(b"outputPath"),
            self.DownloadStateRole: QByteArray(b"downloadState"),
            self.TimestampRole: QByteArray(b"timestamp"),
            self.FormattedDateRole: QByteArray(b"formattedDate"),
            self.FormattedSizeRole: QByteArray(b"formattedSize"),
            self.FormatBadgeRole: QByteArray(b"formatBadge"),
            self.RawDataRole: QByteArray(b"rawData"),
        }

    def rowCount(self, parent=QModelIndex()):
        return len(self._filtered_items)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._filtered_items):
            return None

        item = self._filtered_items[index.row()]
        if role == self.ItemTypeRole:
            return item.item_type
        elif role == self.TaskIdRole:
            return item.task_id
        elif role == self.TitleRole:
            return item.title
        elif role == self.ThumbnailRole:
            return item.thumbnail
        elif role == self.UrlRole:
            return item.url
        elif role == self.IsAudioRole:
            return item.is_audio
        elif role == self.FinalFilepathRole:
            return item.final_filepath
        elif role == self.OutputPathRole:
            return item.output_path
        elif role == self.DownloadStateRole:
            return item.download_state
        elif role == self.TimestampRole:
            return item.timestamp
        elif role == self.FormattedDateRole:
            return item.formatted_date
        elif role == self.FormattedSizeRole:
            return item.formatted_size
        elif role == self.FormatBadgeRole:
            return item.format_badge
        elif role == self.RawDataRole:
            return item.raw_data
        return None

    def set_items(self, downloads: list[dict], searches: list[dict]):
        entries = []
        for dl in downloads:
            entries.append(HistoryEntry(dl, item_type="download"))
        for sc in searches:
            entries.append(HistoryEntry(sc, item_type="search"))

        # Sort combined by timestamp descending
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        self._all_items = entries
        self.apply_filter()

    def apply_filter(self, filter_name: str = None):
        if filter_name is not None:
            self._current_filter = filter_name.lower()

        self.beginResetModel()
        if self._current_filter == "all":
            self._filtered_items = list(self._all_items)
        elif self._current_filter == "downloads":
            self._filtered_items = [it for it in self._all_items if it.item_type == "download"]
        elif self._current_filter == "searches":
            self._filtered_items = [it for it in self._all_items if it.item_type == "search"]
        else:
            self._filtered_items = list(self._all_items)
        self.endResetModel()
        self.countChanged.emit()

    def remove_item(self, item_type: str, identifier: str):
        # identifier is task_id for download, or url for search
        if item_type == "download":
            self._all_items = [it for it in self._all_items if not (it.item_type == "download" and it.task_id == identifier)]
        else:
            self._all_items = [it for it in self._all_items if not (it.item_type == "search" and it.url == identifier)]
        self.apply_filter()

    def clear(self):
        self.beginResetModel()
        self._all_items.clear()
        self._filtered_items.clear()
        self.endResetModel()
        self.countChanged.emit()
