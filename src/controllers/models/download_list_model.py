from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal, Slot, QByteArray


class DownloadItem:
    def __init__(self, data: dict):
        self.task_id = str(data.get("task_id", ""))
        self.info = data.get("info", {})
        self.title = self.info.get("title") or self.info.get("fulltitle") or "Unknown Title"
        
        # Resolve thumbnail
        thumb = self.info.get("thumbnail")
        if not thumb and self.info.get("thumbnails"):
            thumb = self.info["thumbnails"][-1].get("url", "")
        if not thumb and self.info.get("entries"):
            entries = self.info.get("entries", [])
            if entries:
                first = entries[0]
                thumb = first.get("thumbnail") or (first.get("thumbnails", [{}])[-1].get("url", "") if first.get("thumbnails") else "")
        self.thumbnail = thumb or ""
        
        self.is_audio = bool(data.get("is_audio", False))
        self.is_image = bool(data.get("is_image", False))
        self.format_id = str(data.get("format_id", ""))
        self.output_path = str(data.get("output_path", ""))
        self.video_ext = data.get("video_ext")
        self.audio_codec = data.get("audio_codec")
        self.audio_quality = data.get("audio_quality")
        self.embed_thumbnail = data.get("embed_thumbnail")
        self.embed_subtitles = data.get("embed_subtitles")
        self.subtitle_lang = data.get("subtitle_lang")
        self.custom_filename = data.get("custom_filename")
        self.image_ext = data.get("image_ext")
        self.is_thumbnail = bool(data.get("is_thumbnail", False))
        self.is_manga = bool(data.get("is_manga", False))
        self.selected_entries = data.get("selected_entries")
        self.enable_sponsorblock = data.get("enable_sponsorblock")

        # State & Progress
        self.download_state = data.get("download_state", "active")
        if self.download_state == "active" and not data.get("_is_live_active", False):
            self.download_state = "paused"  # Restored items default to paused
            
        self.progress = 1.0 if self.download_state == "completed" else float(data.get("progress", 0.0))
        self.speed_text = str(data.get("speed_text", ""))
        self.final_filepath = str(data.get("final_filepath", "") or "")
        self.log_text = str(data.get("log_text", "") or "")
        self.is_live = bool(self.info.get("is_live", False))
        self.playlist_id = str(data.get("playlist_id", "") or "")
        self.playlist_title = str(data.get("playlist_title", "") or "")
        self.playlist_url = str(data.get("playlist_url", "") or "")
        self.timestamp = float(data.get("timestamp", 0.0))
        self.source_mode = data.get("source_mode", "audio" if self.is_audio else "video")

    @property
    def status_text(self) -> str:
        if self.download_state == "active":
            return "Downloading..."
        elif self.download_state == "paused":
            return "Paused"
        elif self.download_state == "completed":
            return "Download complete"
        elif self.download_state == "cancelled":
            return "Stopped"
        elif self.download_state == "error":
            return "Error"
        elif self.download_state == "queued":
            return "Queued (Waiting...)"
        return self.download_state.capitalize()

    @property
    def status_color_key(self) -> str:
        if self.download_state == "active":
            return "primary"
        elif self.download_state == "paused":
            return "accent"
        elif self.download_state == "completed":
            return "success"
        elif self.download_state in ("cancelled", "error"):
            return "error"
        return "secondary"

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "info": self.info,
            "format_id": self.format_id,
            "is_audio": self.is_audio,
            "output_path": self.output_path,
            "video_ext": self.video_ext,
            "audio_codec": self.audio_codec,
            "audio_quality": self.audio_quality,
            "embed_thumbnail": self.embed_thumbnail,
            "embed_subtitles": self.embed_subtitles,
            "subtitle_lang": self.subtitle_lang,
            "custom_filename": self.custom_filename,
            "is_image": self.is_image,
            "image_ext": self.image_ext,
            "is_thumbnail": self.is_thumbnail,
            "is_manga": self.is_manga,
            "selected_entries": self.selected_entries,
            "enable_sponsorblock": self.enable_sponsorblock,
            "download_state": self.download_state,
            "final_filepath": self.final_filepath,
            "log_text": self.log_text,
            "source_mode": self.source_mode,
            "playlist_id": self.playlist_id,
            "playlist_title": self.playlist_title,
            "playlist_url": self.playlist_url,
            "timestamp": self.timestamp,
        }


class DownloadListModel(QAbstractListModel):
    TaskIdRole = Qt.UserRole + 1
    TitleRole = Qt.UserRole + 2
    ThumbnailRole = Qt.UserRole + 3
    IsAudioRole = Qt.UserRole + 4
    IsImageRole = Qt.UserRole + 5
    FormatIdRole = Qt.UserRole + 6
    OutputPathRole = Qt.UserRole + 7
    StatusTextRole = Qt.UserRole + 8
    StatusColorKeyRole = Qt.UserRole + 9
    DownloadStateRole = Qt.UserRole + 10
    ProgressRole = Qt.UserRole + 11
    SpeedTextRole = Qt.UserRole + 12
    FinalFilepathRole = Qt.UserRole + 13
    LogTextRole = Qt.UserRole + 14
    IsLiveRole = Qt.UserRole + 15
    PlaylistIdRole = Qt.UserRole + 16
    PlaylistTitleRole = Qt.UserRole + 17
    PlaylistUrlRole = Qt.UserRole + 18
    TimestampRole = Qt.UserRole + 19
    InfoMapRole = Qt.UserRole + 20

    countChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_items: list[DownloadItem] = []
        self._filtered_items: list[DownloadItem] = []
        self._current_filter: str = "All"

    def roleNames(self):
        return {
            self.TaskIdRole: QByteArray(b"taskId"),
            self.TitleRole: QByteArray(b"title"),
            self.ThumbnailRole: QByteArray(b"thumbnail"),
            self.IsAudioRole: QByteArray(b"isAudio"),
            self.IsImageRole: QByteArray(b"isImage"),
            self.FormatIdRole: QByteArray(b"formatId"),
            self.OutputPathRole: QByteArray(b"outputPath"),
            self.StatusTextRole: QByteArray(b"statusText"),
            self.StatusColorKeyRole: QByteArray(b"statusColorKey"),
            self.DownloadStateRole: QByteArray(b"downloadState"),
            self.ProgressRole: QByteArray(b"progress"),
            self.SpeedTextRole: QByteArray(b"speedText"),
            self.FinalFilepathRole: QByteArray(b"finalFilepath"),
            self.LogTextRole: QByteArray(b"logText"),
            self.IsLiveRole: QByteArray(b"isLive"),
            self.PlaylistIdRole: QByteArray(b"playlistId"),
            self.PlaylistTitleRole: QByteArray(b"playlistTitle"),
            self.PlaylistUrlRole: QByteArray(b"playlistUrl"),
            self.TimestampRole: QByteArray(b"timestamp"),
            self.InfoMapRole: QByteArray(b"infoMap"),
        }

    def rowCount(self, parent=QModelIndex()):
        return len(self._filtered_items)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._filtered_items):
            return None

        item = self._filtered_items[index.row()]
        if role == self.TaskIdRole:
            return item.task_id
        elif role == self.TitleRole:
            return item.title
        elif role == self.ThumbnailRole:
            return item.thumbnail
        elif role == self.IsAudioRole:
            return item.is_audio
        elif role == self.IsImageRole:
            return item.is_image
        elif role == self.FormatIdRole:
            return item.format_id
        elif role == self.OutputPathRole:
            return item.output_path
        elif role == self.StatusTextRole:
            return item.status_text
        elif role == self.StatusColorKeyRole:
            return item.status_color_key
        elif role == self.DownloadStateRole:
            return item.download_state
        elif role == self.ProgressRole:
            return item.progress
        elif role == self.SpeedTextRole:
            return item.speed_text
        elif role == self.FinalFilepathRole:
            return item.final_filepath
        elif role == self.LogTextRole:
            return item.log_text
        elif role == self.IsLiveRole:
            return item.is_live
        elif role == self.PlaylistIdRole:
            return item.playlist_id
        elif role == self.PlaylistTitleRole:
            return item.playlist_title
        elif role == self.PlaylistUrlRole:
            return item.playlist_url
        elif role == self.TimestampRole:
            return item.timestamp
        elif role == self.InfoMapRole:
            return item.info
        return None

    def apply_filter(self, filter_name: str = None):
        if filter_name is not None:
            self._current_filter = filter_name

        flt = self._current_filter.lower()
        self.beginResetModel()
        if flt == "all":
            self._filtered_items = list(self._all_items)
        elif flt == "active":
            self._filtered_items = [it for it in self._all_items if it.download_state == "active"]
        elif flt == "paused":
            self._filtered_items = [it for it in self._all_items if it.download_state == "paused"]
        elif flt == "queued":
            self._filtered_items = [it for it in self._all_items if it.download_state == "queued"]
        elif flt == "completed":
            self._filtered_items = [it for it in self._all_items if it.download_state == "completed"]
        elif flt == "stopped":
            self._filtered_items = [it for it in self._all_items if it.download_state == "cancelled"]
        elif flt == "error":
            self._filtered_items = [it for it in self._all_items if it.download_state == "error"]
        else:
            self._filtered_items = list(self._all_items)
        self.endResetModel()
        self.countChanged.emit()

    def add_item(self, item_data: dict, prepend: bool = True):
        item = DownloadItem(item_data)
        # Check if already exists
        for idx, existing in enumerate(self._all_items):
            if existing.task_id == item.task_id:
                self._all_items[idx] = item
                self.apply_filter()
                return idx

        if prepend:
            self._all_items.insert(0, item)
        else:
            self._all_items.append(item)
        self.apply_filter()
        return 0

    def update_item_field(self, task_id: str, **kwargs):
        found_item = None
        for item in self._all_items:
            if item.task_id == task_id:
                found_item = item
                for k, v in kwargs.items():
                    if hasattr(item, k):
                        setattr(item, k, v)
                break

        if not found_item:
            return

        # Check if visible in filtered
        for row, f_item in enumerate(self._filtered_items):
            if f_item.task_id == task_id:
                idx = self.index(row, 0)
                roles = []
                for k in kwargs.keys():
                    if k == "progress":
                        roles.append(self.ProgressRole)
                    elif k == "speed_text":
                        roles.append(self.SpeedTextRole)
                    elif k == "download_state":
                        roles.extend([self.DownloadStateRole, self.StatusTextRole, self.StatusColorKeyRole])
                    elif k == "final_filepath":
                        roles.append(self.FinalFilepathRole)
                    elif k == "log_text":
                        roles.append(self.LogTextRole)
                if not roles:
                    roles = [Qt.DisplayRole]
                self.dataChanged.emit(idx, idx, roles)
                break

    def remove_item(self, task_id: str):
        self._all_items = [it for it in self._all_items if it.task_id != task_id]
        self.apply_filter()

    def get_item(self, task_id: str) -> DownloadItem | None:
        for it in self._all_items:
            if it.task_id == task_id:
                return it
        return None

    def get_all_items(self) -> list[DownloadItem]:
        return list(self._all_items)

    def clear(self):
        self.beginResetModel()
        self._all_items.clear()
        self._filtered_items.clear()
        self.endResetModel()
        self.countChanged.emit()
