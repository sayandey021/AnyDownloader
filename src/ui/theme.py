import flet as ft
from src.backend.settings import SettingsManager


class AppTheme:
    # ── Current palette (mutable at runtime) ──
    PRIMARY = "#6366f1"        # Indigo
    PRIMARY_HOVER = "#4f46e5"
    BACKGROUND = "#0f172a"     # Dark Slate
    SURFACE = "#1e293b"
    SURFACE_VARIANT = "#334155"
    TEXT_PRIMARY = "#f8fafc"
    TEXT_SECONDARY = "#cbd5e1"
    ACCENT = "#38bdf8"         # Sky
    BG_IMAGE = ""
    BG_OPACITY = 0.1
    ERROR = "#ef4444"
    SUCCESS = "#22c55e"

    ACCENT_COLORS = {
        'Indigo': {'PRIMARY': "#6366f1", 'PRIMARY_HOVER': "#4f46e5"},
        'Emerald': {'PRIMARY': "#10b981", 'PRIMARY_HOVER': "#059669"},
        'Rose': {'PRIMARY': "#f43f5e", 'PRIMARY_HOVER': "#e11d48"},
        'Amber': {'PRIMARY': "#f59e0b", 'PRIMARY_HOVER': "#d97706"},
        'Violet': {'PRIMARY': "#8b5cf6", 'PRIMARY_HOVER': "#7c3aed"},
        'Sky': {'PRIMARY': "#0ea5e9", 'PRIMARY_HOVER': "#0284c7"},
    }

    # ── Palettes ──
    _DARK = {
        'PRIMARY': "#6366f1",
        'PRIMARY_HOVER': "#4f46e5",
        'BACKGROUND': "#0f172a",
        'SURFACE': "#1e293b",
        'SURFACE_VARIANT': "#334155",
        'TEXT_PRIMARY': "#f8fafc",
        'TEXT_SECONDARY': "#cbd5e1",
        'ACCENT': "#38bdf8",
        'ERROR': "#ef4444",
        'SUCCESS': "#22c55e",
    }

    _LIGHT = {
        'PRIMARY': "#6366f1",
        'PRIMARY_HOVER': "#4f46e5",
        'BACKGROUND': "#f1f5f9",
        'SURFACE': "#ffffff",
        'SURFACE_VARIANT': "#e2e8f0",
        'TEXT_PRIMARY': "#0f172a",
        'TEXT_SECONDARY': "#475569",
        'ACCENT': "#0284c7",
        'ERROR': "#dc2626",
        'SUCCESS': "#16a34a",
    }

    MODE = "dark"

    @classmethod
    def apply(cls, mode: str = None, accent: str = None, bg_image: str = None, bg_opacity: float = None):
        """Switch the class-level color attributes to the given mode ('dark' or 'light') and accent color.
        If mode or accent is None, reads from saved settings."""
        settings = SettingsManager()
        if mode is None:
            mode = settings.get('theme', 'dark')
        if accent is None:
            accent = settings.get('accent_color', 'Indigo')
        if bg_image is None:
            bg_image = settings.get('bg_image_path', '')
        if bg_opacity is None:
            bg_opacity = settings.get('bg_image_opacity', 0.1)

        cls.MODE = mode
        cls.BG_IMAGE = bg_image
        cls.BG_OPACITY = bg_opacity
        
        palette = cls._LIGHT if mode == 'light' else cls._DARK
        for key, value in palette.items():
            setattr(cls, key, value)
            
        if accent in cls.ACCENT_COLORS:
            cls.PRIMARY = cls.ACCENT_COLORS[accent]['PRIMARY']
            cls.PRIMARY_HOVER = cls.ACCENT_COLORS[accent]['PRIMARY_HOVER']

    @classmethod
    def get_dropdown_menu_style(cls):
        return ft.MenuStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=cls.SURFACE,
            side=ft.BorderSide(1, cls.SURFACE_VARIANT),
            elevation=8,
            shadow_color=ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
            padding=ft.Padding(6, 6, 6, 6),
        )

    @classmethod
    def get_dropdown_option_style(cls):
        return ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(
                radius=8,
                side=ft.BorderSide(width=2.5, color=cls.SURFACE),
            ),
            side=ft.BorderSide(width=2.5, color=cls.SURFACE),
        )

    @classmethod
    def get_theme(cls):
        return ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=cls.PRIMARY,
                surface=cls.SURFACE,
                error=cls.ERROR,
            ),
            font_family="Inter, Roboto, Segoe UI, sans-serif",
            use_material3=True,
            visual_density=ft.VisualDensity.COMFORTABLE,
            tab_bar_theme=ft.TabBarTheme(
                indicator_color=cls.PRIMARY,
                label_color=cls.PRIMARY,
                unselected_label_color=cls.TEXT_SECONDARY,
                splash_border_radius=ft.BorderRadius.all(10),
                indicator=ft.UnderlineTabIndicator(
                    border_side=ft.BorderSide(3, cls.PRIMARY),
                    border_radius=ft.BorderRadius.all(3),
                ),
            ),
            dropdown_theme=ft.DropdownTheme(
                menu_style=cls.get_dropdown_menu_style(),
            ),
            popup_menu_theme=ft.PopupMenuTheme(
                shape=ft.RoundedRectangleBorder(radius=12),
                color=cls.SURFACE,
                elevation=8,
                shadow_color=ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
            ),
        )


# Automatically ensure all dropdown options and menus throughout the app use rounded highlights and styles
def _apply_dropdown_rounded_defaults():
    orig_opt_init = ft.dropdown.Option.__init__
    def _patched_opt_init(self, *args, **kwargs):
        if 'style' not in kwargs or kwargs['style'] is None:
            kwargs['style'] = AppTheme.get_dropdown_option_style()
        orig_opt_init(self, *args, **kwargs)

    ft.dropdown.Option.__init__ = _patched_opt_init
    ft.DropdownOption.__init__ = _patched_opt_init

    orig_dd_init = ft.Dropdown.__init__
    def _patched_dd_init(self, *args, **kwargs):
        if 'menu_style' not in kwargs or kwargs['menu_style'] is None:
            kwargs['menu_style'] = AppTheme.get_dropdown_menu_style()
        if 'border_radius' not in kwargs or kwargs['border_radius'] is None:
            kwargs['border_radius'] = 12
        orig_dd_init(self, *args, **kwargs)
        if self.options:
            for opt in self.options:
                opt.style = AppTheme.get_dropdown_option_style()

    ft.Dropdown.__init__ = _patched_dd_init

_apply_dropdown_rounded_defaults()

