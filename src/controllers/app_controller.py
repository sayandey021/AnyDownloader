import os
import sys
from PySide6.QtCore import QObject, Signal, Slot, Property
from PySide6.QtGui import QGuiApplication
from src.backend.settings import SettingsManager


class AppController(QObject):
    themeChanged = Signal()
    accentChanged = Signal()
    pageChanged = Signal(int)
    maximizedChanged = Signal(bool)
    toastRequested = Signal(str, str)  # message, type: 'info', 'success', 'warning', 'error'
    closeDialogRequested = Signal()
    windowActivateRequested = Signal()

    ACCENT_COLORS = {
        'Indigo': {'primary': '#6366f1', 'primaryHover': '#4f46e5'},
        'Emerald': {'primary': '#10b981', 'primaryHover': '#059669'},
        'Rose': {'primary': '#f43f5e', 'primaryHover': '#e11d48'},
        'Amber': {'primary': '#f59e0b', 'primaryHover': '#d97706'},
        'Violet': {'primary': '#8b5cf6', 'primaryHover': '#7c3aed'},
        'Sky': {'primary': '#0ea5e9', 'primaryHover': '#0284c7'},
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = SettingsManager()
        self._current_page = 0  # 0: Search, 1: History, 2: Downloads, 3: Settings, 4: About
        self._is_maximized = False
        self._window = None
        self._tray_icon = None

        # Load saved appearance
        self._theme_mode = self.settings.get('theme', 'dark')
        self._accent_name = self.settings.get('accent_color', 'Rose')
        self._bg_image_path = self.settings.get('bg_image_path', '/bg_4.png')
        self._bg_image_opacity = float(self.settings.get('bg_image_opacity', 0.1))

    def set_window(self, window):
        self._window = window

    def set_tray_icon(self, tray_icon):
        self._tray_icon = tray_icon

    # --- Properties ---

    @Property(str, notify=themeChanged)
    def themeMode(self) -> str:
        return self._theme_mode

    @themeMode.setter
    def themeMode(self, val: str):
        if self._theme_mode != val:
            self._theme_mode = val
            self.settings.set('theme', val)
            self.settings.save()
            self.themeChanged.emit()

    @Property(str, notify=accentChanged)
    def accentName(self) -> str:
        return self._accent_name

    @accentName.setter
    def accentName(self, val: str):
        if val in self.ACCENT_COLORS and self._accent_name != val:
            self._accent_name = val
            self.settings.set('accent_color', val)
            self.settings.save()
            self.accentChanged.emit()

    @Property(str, notify=accentChanged)
    def primaryColor(self) -> str:
        return self.ACCENT_COLORS.get(self._accent_name, self.ACCENT_COLORS['Rose'])['primary']

    @Property(str, notify=accentChanged)
    def primaryHoverColor(self) -> str:
        return self.ACCENT_COLORS.get(self._accent_name, self.ACCENT_COLORS['Rose'])['primaryHover']

    @Property(str, notify=themeChanged)
    def backgroundColor(self) -> str:
        return '#0b1120' if self._theme_mode == 'dark' else '#f8fafc'

    @Property(str, notify=themeChanged)
    def surfaceColor(self) -> str:
        return '#131d32' if self._theme_mode == 'dark' else '#ffffff'

    @Property(str, notify=themeChanged)
    def surfaceVariantColor(self) -> str:
        return '#1e293b' if self._theme_mode == 'dark' else '#f1f5f9'

    @Property(str, notify=themeChanged)
    def surfaceCardColor(self) -> str:
        return '#18243c' if self._theme_mode == 'dark' else '#ffffff'

    @Property(str, notify=themeChanged)
    def borderColor(self) -> str:
        return '#24334f' if self._theme_mode == 'dark' else '#e2e8f0'

    @Property(str, notify=themeChanged)
    def textPrimaryColor(self) -> str:
        return '#f8fafc' if self._theme_mode == 'dark' else '#0f172a'

    @Property(str, notify=themeChanged)
    def textSecondaryColor(self) -> str:
        return '#94a3b8' if self._theme_mode == 'dark' else '#64748b'

    @Property(str, notify=themeChanged)
    def accentCyanColor(self) -> str:
        return '#38bdf8' if self._theme_mode == 'dark' else '#0284c7'

    @Property(str, notify=themeChanged)
    def errorColor(self) -> str:
        return '#f43f5e' if self._theme_mode == 'dark' else '#e11d48'

    @Property(str, notify=themeChanged)
    def successColor(self) -> str:
        return '#10b981' if self._theme_mode == 'dark' else '#059669'

    @Property(str, notify=themeChanged)
    def bgImagePath(self) -> str:
        return self._bg_image_path

    @bgImagePath.setter
    def bgImagePath(self, val: str):
        if self._bg_image_path != val:
            self._bg_image_path = val
            self.settings.set('bg_image_path', val)
            self.settings.save()
            self.themeChanged.emit()

    @Property(float, notify=themeChanged)
    def bgImageOpacity(self) -> float:
        return self._bg_image_opacity

    @bgImageOpacity.setter
    def bgImageOpacity(self, val: float):
        if self._bg_image_opacity != val:
            self._bg_image_opacity = val
            self.settings.set('bg_image_opacity', val)
            self.settings.save()
            self.themeChanged.emit()

    @Property(int, notify=pageChanged)
    def currentPage(self) -> int:
        return self._current_page

    @currentPage.setter
    def currentPage(self, val: int):
        if self._current_page != val:
            self._current_page = val
            self.pageChanged.emit(val)

    @Property(bool, notify=maximizedChanged)
    def isMaximized(self) -> bool:
        return self._is_maximized

    # --- Slots ---

    @Slot(int)
    def setPage(self, page_index: int):
        self.currentPage = page_index

    @Slot(str)
    def setTheme(self, mode: str):
        self.themeMode = mode

    @Slot(str)
    def setThemeMode(self, mode: str):
        self.themeMode = mode

    @Slot(str)
    def setAccent(self, accent_name: str):
        self.accentName = accent_name

    @Slot(str)
    def setBgImage(self, path: str):
        self.bgImagePath = path

    @Slot(float)
    def setBgOpacity(self, opacity: float):
        self.bgImageOpacity = opacity

    @Slot()
    def minimizeWindow(self):
        if self._window:
            self._window.showMinimized()

    @Slot()
    def maximizeOrRestoreWindow(self):
        if self._window:
            if self._is_maximized:
                self._window.showNormal()
                self._is_maximized = False
            else:
                self._window.showMaximized()
                self._is_maximized = True
            self.maximizedChanged.emit(self._is_maximized)

    @Slot(bool)
    def updateMaximizedState(self, state: bool):
        if self._is_maximized != state:
            self._is_maximized = state
            self.maximizedChanged.emit(self._is_maximized)

    @Slot()
    def requestCloseWindow(self):
        ask_on_close = self.settings.get('ask_on_close', True)
        close_behavior = self.settings.get('close_behavior', 'prompt')

        if not ask_on_close:
            if close_behavior == 'tray':
                self.minimizeToTray()
            else:
                self.exitApp()
            return

        self.closeDialogRequested.emit()

    @Slot(str, bool)
    def confirmClose(self, action: str, remember: bool):
        if remember:
            self.settings.set('ask_on_close', False)
            self.settings.set('close_behavior', action)
            self.settings.save()

        if action == 'tray':
            self.minimizeToTray()
        else:
            self.exitApp()

    @Slot()
    def minimizeToTray(self):
        if self._window:
            self._window.hide()
            self.showToast("Any Downloader minimized to tray", "info")

    @Slot()
    def restoreFromTray(self):
        if self._window:
            self._window.show()
            self._window.raise_()
            self._window.requestActivate()
            self.windowActivateRequested.emit()

    @Slot()
    def exitApp(self):
        if self._tray_icon:
            self._tray_icon.hide()
        QGuiApplication.quit()

    @Slot(str, str)
    def showToast(self, message: str, toast_type: str = "info"):
        self.toastRequested.emit(message, toast_type)
