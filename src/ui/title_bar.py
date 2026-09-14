import sys
import os
import flet as ft
from src.ui.theme import AppTheme

class WindowControlButton(ft.Container):
    def __init__(self, icon: str, on_click, is_close: bool = False, icon_size: int = 14, tooltip: str = ""):
        super().__init__()
        self.is_close = is_close
        self.on_click = on_click
        self.tooltip = tooltip
        self.width = 44
        self.height = 36
        self.alignment = ft.Alignment.CENTER
        self.bgcolor = ft.Colors.TRANSPARENT
        self.animate = ft.Animation(120, ft.AnimationCurve.EASE_OUT)
        
        self.icon_ctrl = ft.Icon(
            icon=icon,
            size=icon_size,
            color=AppTheme.TEXT_SECONDARY
        )
        self.content = self.icon_ctrl
        self.on_hover = self._handle_hover

    def _handle_hover(self, e):
        is_hovered = (e.data == "true")
        if self.is_close:
            self.bgcolor = "#e81123" if is_hovered else ft.Colors.TRANSPARENT
            self.icon_ctrl.color = ft.Colors.WHITE if is_hovered else AppTheme.TEXT_SECONDARY
        else:
            hover_bg = ft.Colors.with_opacity(0.12, ft.Colors.WHITE if AppTheme.MODE == 'dark' else ft.Colors.BLACK)
            self.bgcolor = hover_bg if is_hovered else ft.Colors.TRANSPARENT
            self.icon_ctrl.color = AppTheme.TEXT_PRIMARY if is_hovered else AppTheme.TEXT_SECONDARY
        try:
            self.update()
        except Exception:
            pass

    def update_icon(self, icon: str, icon_size: int = 14):
        self.icon_ctrl.icon = icon
        self.icon_ctrl.size = icon_size
        self.icon_ctrl.color = AppTheme.TEXT_SECONDARY
        try:
            self.update()
        except Exception:
            pass

    def update_theme(self):
        self.icon_ctrl.color = AppTheme.TEXT_SECONDARY
        self.bgcolor = ft.Colors.TRANSPARENT
        try:
            self.update()
        except Exception:
            pass


class CustomTitleBar(ft.Container):
    """
    Modern custom window title bar matching the app's dark/light theme.
    Supports native dragging, double-click to maximize/restore, and custom window control buttons.
    """
    def __init__(self, page: ft.Page, on_close_click=None, app_title: str = "Any Downloader"):
        super().__init__()
        self._page = page
        self.on_close_click = on_close_click
        self.app_title_text = app_title
        self.height = 36
        self.padding = ft.Padding(left=12, right=0, top=0, bottom=0)
        self.bgcolor = AppTheme.BACKGROUND
        self.border = ft.Border(
            bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.06, ft.Colors.WHITE if AppTheme.MODE == 'dark' else ft.Colors.BLACK))
        )
        
        # Resolve icon path
        if getattr(sys, 'frozen', False):
            assets_dir = os.path.join(sys._MEIPASS, "assets")
        else:
            assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets"))
            
        icon_path = os.path.join(assets_dir, "icon.png")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(assets_dir, "icon.ico")
            
        self.logo = ft.Image(
            src=icon_path if os.path.exists(icon_path) else "assets/icon.png",
            width=16,
            height=16,
            fit=ft.BoxFit.CONTAIN,
        ) if os.path.exists(icon_path) else ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, size=16, color=AppTheme.PRIMARY)

        self.title_label = ft.Text(
            self.app_title_text,
            size=12,
            weight=ft.FontWeight.W_500,
            color=AppTheme.TEXT_SECONDARY,
        )

        # Draggable Header Content (Logo + Title + Empty filler)
        drag_content = ft.Row(
            controls=[
                self.logo,
                ft.Container(width=4),
                self.title_label,
                ft.Container(expand=True),  # fills middle space
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
            expand=True,
        )

        # Flet WindowDragArea allows clicking/dragging anywhere on this row
        self.drag_area = ft.WindowDragArea(
            content=drag_content,
            expand=True,
            maximizable=True,
        )

        # Window Action Buttons
        self.btn_minimize = WindowControlButton(
            icon=ft.Icons.REMOVE_ROUNDED,
            icon_size=14,
            on_click=self._handle_minimize,
            tooltip="Minimize",
        )
        self.btn_maximize = WindowControlButton(
            icon=ft.Icons.CROP_SQUARE_ROUNDED,
            icon_size=13,
            on_click=self._handle_maximize,
            tooltip="Maximize",
        )
        self.btn_close = WindowControlButton(
            icon=ft.Icons.CLOSE_ROUNDED,
            icon_size=15,
            is_close=True,
            on_click=self._handle_close,
            tooltip="Close",
        )

        self.buttons_row = ft.Row(
            controls=[
                self.btn_minimize,
                self.btn_maximize,
                self.btn_close,
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.content = ft.Row(
            controls=[
                self.drag_area,
                self.buttons_row,
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )

    def _handle_minimize(self, e):
        self._page.window.minimized = True
        self._page.update()

    def _handle_maximize(self, e):
        self._page.window.maximized = not getattr(self._page.window, "maximized", False)
        self.update_maximize_state(self._page.window.maximized)
        self._page.update()

    def _handle_close(self, e):
        if self.on_close_click:
            self.on_close_click(e)
        else:
            self._page.window.close()

    def update_maximize_state(self, is_maximized: bool):
        if is_maximized:
            self.btn_maximize.update_icon(ft.Icons.FILTER_NONE_ROUNDED, icon_size=11)
            self.btn_maximize.tooltip = "Restore Down"
        else:
            self.btn_maximize.update_icon(ft.Icons.CROP_SQUARE_ROUNDED, icon_size=13)
            self.btn_maximize.tooltip = "Maximize"

    def update_theme(self):
        self.bgcolor = AppTheme.BACKGROUND
        self.border = ft.Border(
            bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.06, ft.Colors.WHITE if AppTheme.MODE == 'dark' else ft.Colors.BLACK))
        )
        self.title_label.color = AppTheme.TEXT_SECONDARY
        self.btn_minimize.update_theme()
        self.btn_maximize.update_theme()
        self.btn_close.update_theme()
        try:
            self.update()
        except Exception:
            pass
