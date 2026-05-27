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
        )
