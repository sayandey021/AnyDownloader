import flet as ft
import os
from src.ui.theme import AppTheme
from src.backend.settings import SettingsManager
from src.backend.ffmpeg_manager import is_ffmpeg_available
from src.backend.engine_manager import (
    get_installed_engine_versions,
    check_for_engine_updates,
    update_engines,
)
import importlib.util


class SettingsView(ft.Container):
    """Full settings page overlayed on the main view."""

    def __init__(self, page: ft.Page, on_close=None, show_back_button=True, on_theme_changed=None):
        super().__init__()
        self._page = page
        self._on_close = on_close
        self.show_back_button = show_back_button
        self.on_theme_changed = on_theme_changed
        self.settings = SettingsManager()
        self.expand = True
        self.bgcolor = ft.Colors.TRANSPARENT
        self.padding = 0

        self.snack_bar = ft.SnackBar(
            content=ft.Text("", color=AppTheme.TEXT_PRIMARY),
            bgcolor=AppTheme.PRIMARY,
            duration=3000,
        )
        self._page.overlay.append(self.snack_bar)

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        # ── Header ──
        header_elements = []
        if self.show_back_button:
            header_elements.append(
                ft.IconButton(
                    ft.Icons.ARROW_BACK_ROUNDED,
                    icon_color=AppTheme.TEXT_PRIMARY,
                    icon_size=24,
                    tooltip="Back",
                    on_click=self._close,
                )
            )
        
        header_elements.extend([
            ft.Icon(ft.Icons.SETTINGS_ROUNDED, color=AppTheme.PRIMARY, size=30),
            ft.Text("Settings", size=26, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT_PRIMARY),
        ])
        
        header = ft.Container(
            content=ft.Row([
                *header_elements,
                ft.Container(expand=True),
                ft.TextButton(
                    "Reset to Defaults",
                    icon=ft.Icons.RESTORE_ROUNDED,
                    style=ft.ButtonStyle(color=AppTheme.ERROR),
                    on_click=self._reset_defaults,
                ),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding(left=20, right=20, top=10, bottom=10),
        )

        # ── Download Settings ──
        self.path_field = ft.TextField(
            label="Default Download Folder",
            value=self.settings.get('default_download_path'),
            expand=True,
            read_only=True,
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=10,
            prefix_icon=ft.Icons.FOLDER_ROUNDED,
        )
        browse_btn = ft.IconButton(
            ft.Icons.FOLDER_OPEN_ROUNDED,
            icon_color=AppTheme.ACCENT,
            tooltip="Browse…",
            on_click=lambda e: self._browse_folder('default_download_path', self.path_field),
        )

        self.temp_path_field = ft.TextField(
            label="Temporary Download Folder",
            value=self.settings.get('temp_download_path'),
            expand=True,
            read_only=True,
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=10,
            prefix_icon=ft.Icons.FOLDER_SPECIAL_ROUNDED,
        )
        temp_browse_btn = ft.IconButton(
            ft.Icons.FOLDER_OPEN_ROUNDED,
            icon_color=AppTheme.ACCENT,
            tooltip="Browse Temp Folder…",
            on_click=lambda e: self._browse_folder('temp_download_path', self.temp_path_field),
        )

        self.format_dropdown = ft.Dropdown(
            label="Preferred Quality",
            width=350,
            value=self.settings.get('preferred_format'),
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=12,
            menu_style=AppTheme.get_dropdown_menu_style(),
            options=[
                ft.dropdown.Option(key="best", text="Best Quality (Video + Audio)"),
                ft.dropdown.Option(key="bestvideo[height<=1920]+bestaudio/best", text="1920p"),
                ft.dropdown.Option(key="bestvideo[height<=1800]+bestaudio/best", text="1800p"),
                ft.dropdown.Option(key="bestvideo[height<=1280]+bestaudio/best", text="1280p"),
                ft.dropdown.Option(key="bestvideo[height<=1080]+bestaudio/best", text="1080p"),
                ft.dropdown.Option(key="bestvideo[height<=720]+bestaudio/best", text="720p"),
                ft.dropdown.Option(key="bestvideo[height<=640]+bestaudio/best", text="640p"),
                ft.dropdown.Option(key="bestvideo[height<=540]+bestaudio/best", text="540p"),
                ft.dropdown.Option(key="bestvideo[height<=480]+bestaudio/best", text="480p"),
                ft.dropdown.Option(key="bestaudio/best", text="Audio Only"),
            ],
        )

        self.filename_field = ft.TextField(
            label="Filename Template",
            value=self.settings.get('filename_template'),
            width=450,
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=10,
            prefix_icon=ft.Icons.EDIT_ROUNDED,
            tooltip="yt-dlp output template, e.g. %(title)s.%(ext)s",
        )
        
        template_info_btn = ft.IconButton(
            ft.Icons.INFO_OUTLINED,
            icon_color=AppTheme.ACCENT,
            tooltip="View useful templates",
            on_click=self._show_templates_info,
        )
        filename_row = ft.Row([self.filename_field, template_info_btn], spacing=5)

        # ── Audio Settings ──
        self.audio_codec_dropdown = ft.Dropdown(
            label="Audio Codec",
            width=200,
            value=self.settings.get('audio_codec'),
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=12,
            menu_style=AppTheme.get_dropdown_menu_style(),
            options=[
                ft.dropdown.Option(key="mp3", text="MP3"),
                ft.dropdown.Option(key="aac", text="AAC"),
                ft.dropdown.Option(key="opus", text="Opus"),
                ft.dropdown.Option(key="flac", text="FLAC"),
                ft.dropdown.Option(key="wav", text="WAV"),
            ],
        )

        self.audio_quality_dropdown = ft.Dropdown(
            label="Audio Bitrate (kbps)",
            width=200,
            value=self.settings.get('audio_quality'),
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=12,
            menu_style=AppTheme.get_dropdown_menu_style(),
            options=[
                ft.dropdown.Option(key="320", text="320 kbps"),
                ft.dropdown.Option(key="256", text="256 kbps"),
                ft.dropdown.Option(key="192", text="192 kbps"),
                ft.dropdown.Option(key="128", text="128 kbps"),
                ft.dropdown.Option(key="96", text="96 kbps"),
            ],
        )

        download_section = self._section(
            "Download Settings",
            ft.Icons.DOWNLOAD_ROUNDED,
            [
                ft.Row([self.path_field, browse_btn], spacing=10),
                ft.Row([self.temp_path_field, temp_browse_btn], spacing=10),
                ft.Row([self.format_dropdown, filename_row], spacing=20, wrap=True),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.Text("Audio Extraction Default Settings", size=14, weight=ft.FontWeight.W_600, color=AppTheme.TEXT_PRIMARY),
                ft.Row([self.audio_codec_dropdown, self.audio_quality_dropdown], spacing=20, wrap=True),
            ],
        )

        # ── Playlist & Queue Settings ──
        self.max_concurrent_dropdown = ft.Dropdown(
            label="Max Concurrent Downloads",
            width=200,
            value=str(self.settings.get('max_concurrent_downloads', 3)),
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=12,
            menu_style=AppTheme.get_dropdown_menu_style(),
            options=[
                ft.dropdown.Option(key=str(i), text=str(i)) for i in range(1, 11)
            ],
            tooltip="How many items from a playlist download at once"
        )
        
        self.playlist_filename_field = ft.TextField(
            label="Playlist Filename Format",
            value=self.settings.get('playlist_filename_template', '%(playlist_index)s - %(title)s.%(ext)s'),
            width=450,
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=10,
            prefix_icon=ft.Icons.EDIT_ROUNDED,
        )
        
        playlist_template_info_btn = ft.IconButton(
            ft.Icons.INFO_OUTLINED,
            icon_color=AppTheme.ACCENT,
            tooltip="View playlist templates",
            on_click=self._show_playlist_templates_info,
        )
        playlist_filename_row = ft.Row([self.playlist_filename_field, playlist_template_info_btn], spacing=5)

        self.playlist_folder_switch = ft.Switch(
            label="Create subfolder for Playlist",
            value=self.settings.get('create_playlist_folder', True),
            active_color=AppTheme.PRIMARY,
            label_text_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY),
        )

        playlist_section = self._section(
            "Playlist & Queue",
            ft.Icons.QUEUE_MUSIC_ROUNDED,
            [
                ft.Row([self.max_concurrent_dropdown, playlist_filename_row], spacing=20, wrap=True),
                self.playlist_folder_switch,
            ],
        )

        # Audio Settings moved under Download Settings

        # ── Advanced Settings ──
        self.ask_on_close_switch = ft.Switch(
            label="Ask before closing (Minimize to Tray / Exit)",
            value=self.settings.get('ask_on_close', True),
            active_color=AppTheme.PRIMARY,
            label_text_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY),
            tooltip="If disabled, uses your saved close behavior",
        )

        self.speed_limit_field = ft.TextField(
            label="Speed Limit (0 = Unlimited)",
            value=str(int(self.settings.get('speed_limit', 0) / 1024)) if self.settings.get('speed_limit', 0) else "0",
            width=300,
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=12,
            prefix_icon=ft.Icons.SPEED_ROUNDED,
            suffix=ft.Text("KB/s", color=AppTheme.TEXT_SECONDARY, size=12),
            input_filter=ft.NumbersOnlyInputFilter(),
            tooltip="Download speed limit in KB/s (set 0 for unlimited)",
        )

        self.auto_delete_history_dropdown = ft.Dropdown(
            label="Auto Delete History",
            width=300,
            value=str(self.settings.get('auto_delete_history_days', 0)),
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=12,
            menu_style=AppTheme.get_dropdown_menu_style(),
            options=[
                ft.dropdown.Option(key="0", text="Never"),
                ft.dropdown.Option(key="1", text="Older than 1 day"),
                ft.dropdown.Option(key="3", text="Older than 3 days"),
                ft.dropdown.Option(key="7", text="Older than 7 days"),
                ft.dropdown.Option(key="30", text="Older than 30 days"),
            ],
            tooltip="Automatically delete download and search history older than the selected time"
        )

        self.embed_thumbnail_switch = ft.Switch(
            label="Embed Thumbnail in File",
            value=self.settings.get('embed_thumbnail', True),
            active_color=AppTheme.PRIMARY,
            label_text_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY),
        )

        self.embed_metadata_switch = ft.Switch(
            label="Embed Metadata (Title, Artist, Track #)",
            value=self.settings.get('embed_metadata', True),
            active_color=AppTheme.PRIMARY,
            label_text_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY),
        )

        self.embed_chapters_switch = ft.Switch(
            label="Save with Chapters",
            value=self.settings.get('embed_chapters', True),
            active_color=AppTheme.PRIMARY,
            label_text_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY),
            tooltip="Embed video/audio chapters and timestamps into the file",
        )

        self.embed_subs_switch = ft.Switch(
            label="Embed Subtitles",
            value=self.settings.get('embed_subtitles'),
            active_color=AppTheme.PRIMARY,
            label_text_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY),
        )

        self.sub_lang_field = ft.TextField(
            label="Subtitle Language(s)",
            value=self.settings.get('auto_subtitle_lang'),
            width=320,
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=10,
            prefix_icon=ft.Icons.SUBTITLES_ROUNDED,
            hint_text="e.g. en, es, hi or all",
            tooltip="Comma-separated language codes (e.g. en, es, ja, hi) or 'all' to embed multiple subtitle tracks",
        )
        sub_lang_info_btn = ft.IconButton(
            ft.Icons.INFO_OUTLINED,
            icon_color=AppTheme.ACCENT,
            tooltip="View Subtitle Language guide & presets",
            on_click=self._show_subtitles_info,
        )
        self.sub_lang_row = ft.Row([self.sub_lang_field, sub_lang_info_btn], spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        self.hw_accel_dropdown = ft.Dropdown(
            label="Hardware Acceleration (FFmpeg)",
            width=280,
            value=self.settings.get('hw_accel', 'auto'),
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=12,
            menu_style=AppTheme.get_dropdown_menu_style(),
            options=[
                ft.dropdown.Option(key="none", text="Disabled"),
                ft.dropdown.Option(key="auto", text="Auto"),
                ft.dropdown.Option(key="cuda", text="NVIDIA (CUDA)"),
                ft.dropdown.Option(key="qsv", text="Intel (QSV)"),
                ft.dropdown.Option(key="d3d11va", text="AMD/Generic (D3D11VA)"),
            ],
            tooltip="Use GPU for faster video processing when FFmpeg is used."
        )

        self.browser_cookies_dropdown = ft.Dropdown(
            label="Use Cookies from Browser",
            width=280,
            value=self.settings.get('browser_cookies', 'none'),
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=12,
            menu_style=AppTheme.get_dropdown_menu_style(),
            options=[
                ft.dropdown.Option(key="none", text="None"),
                ft.dropdown.Option(key="chrome", text="Google Chrome"),
                ft.dropdown.Option(key="edge", text="Microsoft Edge"),
                ft.dropdown.Option(key="firefox", text="Mozilla Firefox"),
                ft.dropdown.Option(key="brave", text="Brave"),
                ft.dropdown.Option(key="opera", text="Opera"),
                ft.dropdown.Option(key="vivaldi", text="Vivaldi"),
                ft.dropdown.Option(key="safari", text="Safari"),
            ],
            tooltip="Automatically extract cookies from your local browser"
        )

        self.cookies_path_field = ft.TextField(
            label="Cookies File (Optional)",
            value=self.settings.get('cookies_path'),
            expand=True,
            read_only=True,
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=10,
            prefix_icon=ft.Icons.COOKIE_ROUNDED,
            tooltip="Netscape cookies.txt file to bypass login walls (Instagram, Facebook)",
        )
        cookies_browse_btn = ft.IconButton(
            ft.Icons.FILE_OPEN_ROUNDED,
            icon_color=AppTheme.ACCENT,
            tooltip="Browse Cookies File...",
            on_click=lambda e: self._browse_file('cookies_path', self.cookies_path_field),
        )

        login_insta_btn = ft.ElevatedButton(
            "Login to Instagram",
            icon=ft.Icons.CAMERA_ALT_ROUNDED,
            on_click=lambda e: self._login_browser('https://www.instagram.com/'),
            bgcolor=AppTheme.SURFACE_VARIANT,
            color=AppTheme.TEXT_PRIMARY
        )
        login_fb_btn = ft.ElevatedButton(
            "Login to Facebook",
            icon=ft.Icons.FACEBOOK_ROUNDED,
            on_click=lambda e: self._login_browser('https://www.facebook.com/'),
            bgcolor=AppTheme.SURFACE_VARIANT,
            color=AppTheme.TEXT_PRIMARY
        )
        login_x_btn = ft.ElevatedButton(
            "Login to X (Twitter)",
            icon=ft.Icons.ALTERNATE_EMAIL_ROUNDED,
            on_click=lambda e: self._login_browser('https://x.com/'),
            bgcolor=AppTheme.SURFACE_VARIANT,
            color=AppTheme.TEXT_PRIMARY
        )
        login_yt_btn = ft.ElevatedButton(
            "Login to YouTube",
            icon=ft.Icons.PLAY_CIRCLE_FILL_ROUNDED,
            on_click=lambda e: self._login_browser('https://www.youtube.com/'),
            bgcolor=AppTheme.SURFACE_VARIANT,
            color=AppTheme.TEXT_PRIMARY
        )

        def _on_dev_mode_change(e):
            self.settings.set('developer_mode', self.dev_mode_switch.value)
            self.settings.save()
            self._page.bgcolor = AppTheme.BACKGROUND
            self.bgcolor = ft.Colors.TRANSPARENT
            self.content = None
            self._build_ui()
            self.update()

        self.dev_mode_switch = ft.Switch(
            label="Developer Mode",
            value=self.settings.get('developer_mode', False),
            active_color=AppTheme.PRIMARY,
            label_text_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY),
            on_change=_on_dev_mode_change
        )

        # ── Backend Engines & Updates Controls ──
        self.engine_interval_dropdown = ft.Dropdown(
            label="Auto-Check Frequency",
            width=240,
            value=self.settings.get('engine_update_interval', 'weekly'),
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=12,
            menu_style=AppTheme.get_dropdown_menu_style(),
            options=[
                ft.dropdown.Option(key="daily", text="Daily"),
                ft.dropdown.Option(key="weekly", text="Weekly"),
                ft.dropdown.Option(key="monthly", text="Monthly"),
                ft.dropdown.Option(key="never", text="Never (Manual Only)"),
            ],
            tooltip="Choose how often Any Downloader checks for updates to yt-dlp and spotdl"
        )

        self.check_engines_btn = ft.OutlinedButton(
            "Check for Updates",
            icon=ft.Icons.REFRESH_ROUNDED,
            style=ft.ButtonStyle(
                color=AppTheme.TEXT_PRIMARY,
                side=ft.BorderSide(1, AppTheme.SURFACE_VARIANT),
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding(16, 12, 16, 12),
            ),
            on_click=self._on_check_engines_click,
            tooltip="Query PyPI for newer versions of yt-dlp, spotdl, and curl_cffi"
        )

        self.update_engines_btn = ft.ElevatedButton(
            "Update Engines Now",
            icon=ft.Icons.UPGRADE_ROUNDED,
            style=ft.ButtonStyle(
                bgcolor=AppTheme.PRIMARY,
                color=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding(16, 12, 16, 12),
            ),
            on_click=self._on_update_engines_click,
            tooltip="Download and install the latest versions of all backend engines"
        )

        self.engine_status_container = ft.Container(
            content=self._build_engine_status_content(),
            padding=ft.Padding(0, 5, 0, 5),
        )

        # ── SponsorBlock (YouTube) Controls ──
        def _on_sb_toggle(e):
            is_enabled = self.sponsorblock_switch.value
            self.sponsorblock_action_dropdown.disabled = not is_enabled
            for cb in self.sponsorblock_cat_checkboxes.values():
                cb.disabled = not is_enabled
            self.sponsorblock_options_container.opacity = 1.0 if is_enabled else 0.4
            self.sponsorblock_options_container.update()
            self._save(e)

        self.sponsorblock_switch = ft.Switch(
            label="Enable SponsorBlock (YouTube)",
            value=self.settings.get('enable_sponsorblock', False),
            active_color=AppTheme.PRIMARY,
            label_text_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY),
            tooltip="Automatically skip or cut out sponsors, promos, and intros in downloaded YouTube videos",
            on_change=_on_sb_toggle,
        )

        self.sponsorblock_action_dropdown = ft.Dropdown(
            label="Action Mode",
            width=320,
            value=self.settings.get('sponsorblock_action', 'remove'),
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=12,
            menu_style=AppTheme.get_dropdown_menu_style(),
            disabled=not self.settings.get('enable_sponsorblock', False),
            options=[
                ft.dropdown.Option(key="remove", text="Remove Segments (Cut from file)"),
                ft.dropdown.Option(key="mark", text="Mark as Chapters (Tag segments)"),
                ft.dropdown.Option(key="remove_and_mark", text="Remove & Save with Chapters (Cut sponsors, tag remaining)"),
            ],
            tooltip="Choose whether to cut sponsor segments or embed them as named chapters"
        )

        SPONSORBLOCK_CATEGORY_DEFS = [
            ("sponsor", "Sponsors", "Paid promotion, sponsored products, and referral links"),
            ("selfpromo", "Self-Promotion", "Unpaid promotion, merch, second channels, and personal projects"),
            ("interaction", "Interaction Reminders", "Subscribe, like, notification bell, or social media reminders"),
            ("intro", "Intermission / Intro", "Intro animations, channel idents, pause screens, and intermission cards"),
            ("outro", "Endcards / Outro", "End credits, outro music, and closing title cards"),
            ("preview", "Preview / Recap", "Recap of previous episodes or preview of upcoming content"),
            ("filler", "Filler Tangent", "Tangents, non-contextual banter, and superfluous jokes"),
            ("music_offtopic", "Non-Music Section", "Only applies to music videos: skits, dialogue, or non-song portions"),
        ]

        saved_sb_cats = self.settings.get('sponsorblock_categories', ['sponsor', 'selfpromo', 'interaction', 'intro', 'outro'])
        self.sponsorblock_cat_checkboxes = {}
        sb_checkbox_controls = []

        is_sb_on = self.settings.get('enable_sponsorblock', False)
        for cat_id, cat_title, cat_desc in SPONSORBLOCK_CATEGORY_DEFS:
            cb = ft.Checkbox(
                label=cat_title,
                value=(cat_id in saved_sb_cats),
                active_color=AppTheme.PRIMARY,
                label_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY, size=13),
                tooltip=cat_desc,
                disabled=not is_sb_on,
                on_change=self._save
            )
            self.sponsorblock_cat_checkboxes[cat_id] = cb
            sb_checkbox_controls.append(cb)

        def _set_sb_preset(cats):
            for cid, cbox in self.sponsorblock_cat_checkboxes.items():
                cbox.value = (cid in cats)
                try:
                    cbox.update()
                except Exception:
                    pass
            self._save(None)

        def _sb_select_recommended(e):
            _set_sb_preset({'sponsor', 'selfpromo', 'interaction', 'intro', 'outro'})

        def _sb_select_all(e):
            _set_sb_preset({c[0] for c in SPONSORBLOCK_CATEGORY_DEFS})

        def _sb_clear_all(e):
            _set_sb_preset(set())

        sb_preset_row = ft.Row([
            ft.Text("Quick Presets:", size=12, color=AppTheme.TEXT_SECONDARY),
            ft.TextButton("Recommended", style=ft.ButtonStyle(color=AppTheme.PRIMARY), on_click=_sb_select_recommended),
            ft.TextButton("Select All", style=ft.ButtonStyle(color=AppTheme.TEXT_SECONDARY), on_click=_sb_select_all),
            ft.TextButton("Clear", style=ft.ButtonStyle(color=AppTheme.TEXT_SECONDARY), on_click=_sb_clear_all),
        ], spacing=5)

        sb_cats_grid = ft.ResponsiveRow(
            columns=12,
            controls=[
                ft.Container(content=cb, col={"sm": 12, "md": 6, "lg": 6})
                for cb in sb_checkbox_controls
            ],
            spacing=5,
            run_spacing=5
        )

        self.sponsorblock_options_container = ft.Container(
            content=ft.Column([
                ft.Row([self.sponsorblock_action_dropdown], spacing=10),
                ft.Container(height=5),
                ft.Row([
                    ft.Text("Categories to Block:", size=13, weight=ft.FontWeight.W_600, color=AppTheme.TEXT_PRIMARY),
                    ft.Container(expand=True),
                    sb_preset_row
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                sb_cats_grid
            ], spacing=8),
            opacity=1.0 if is_sb_on else 0.4,
            animate_opacity=ft.Animation(250, ft.AnimationCurve.EASE_OUT)
        )

        def _sub_header(title_text, icon_name=None):
            return ft.Text(title_text, size=14, weight=ft.FontWeight.W_600, color=AppTheme.TEXT_PRIMARY)

        general_section = self._section(
            "General",
            ft.Icons.SETTINGS_ROUNDED,
            [
                _sub_header("General Behavior"),
                ft.Row([self.ask_on_close_switch], spacing=20, wrap=True),
                ft.Row([self.speed_limit_field, self.auto_delete_history_dropdown], spacing=20, wrap=True),
                
                ft.Divider(height=20, color=AppTheme.SURFACE_VARIANT),
                
                _sub_header("Media & Processing"),
                ft.Row([self.embed_thumbnail_switch, self.embed_subs_switch, self.embed_metadata_switch, self.embed_chapters_switch], spacing=30, wrap=True),
                self.sub_lang_row,

                ft.Divider(height=20, color=AppTheme.SURFACE_VARIANT),
                
                _sub_header("SponsorBlock (YouTube)"),
                ft.Row([self.sponsorblock_switch]),
                self.sponsorblock_options_container,
            ],
        )

        advanced_section = self._section(
            "Advanced",
            ft.Icons.TUNE_ROUNDED,
            [
                _sub_header("Hardware Acceleration"),
                ft.Text("Use GPU for faster video processing and transcoding when FFmpeg is used.", size=13, color=AppTheme.TEXT_SECONDARY),
                ft.Row([self.hw_accel_dropdown], spacing=10, wrap=True),

                ft.Divider(height=20, color=AppTheme.SURFACE_VARIANT),
                
                _sub_header("Authentication & Bypassing"),
                ft.Row([self.browser_cookies_dropdown], spacing=10),
                ft.Row([self.cookies_path_field, cookies_browse_btn], spacing=10),
                ft.Container(height=4),
                ft.Text("Or login directly via embedded browser:", color=AppTheme.TEXT_SECONDARY, size=13),
                ft.Row([login_yt_btn, login_insta_btn, login_fb_btn, login_x_btn], spacing=10, wrap=True),
                
                ft.Divider(height=20, color=AppTheme.SURFACE_VARIANT),
                
                _sub_header("Backend Engines & Updates"),
                ft.Text("Manage core media download and extraction engines (yt-dlp, spotdl, curl_cffi).", size=13, color=AppTheme.TEXT_SECONDARY),
                ft.Row([
                    self.engine_interval_dropdown,
                    self.check_engines_btn,
                    self.update_engines_btn,
                ], spacing=12, wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                self.engine_status_container,

                ft.Divider(height=20, color=AppTheme.SURFACE_VARIANT),
                _sub_header("Developer"),
                ft.Row([self.dev_mode_switch], spacing=20, wrap=True),
            ],
        )

        # ── Theme ──
        self.theme_segmented = ft.SegmentedButton(
            selected=[self.settings.get('theme', 'dark')],
            on_change=self._on_theme_change,
            segments=[
                ft.Segment(value="dark", label=ft.Text("Dark"), icon=ft.Icons.DARK_MODE_ROUNDED),
                ft.Segment(value="light", label=ft.Text("Light"), icon=ft.Icons.LIGHT_MODE_ROUNDED),
            ],
            selected_icon=ft.Icons.CHECK_CIRCLE_ROUNDED,
        )

        def _on_accent_change(color_name):
            self.settings.set('accent_color', color_name)
            self._on_theme_change(None)

        def create_color_chip(color_name, hex_color):
            is_selected = self.settings.get('accent_color', 'Indigo') == color_name
            selected_side = ft.border.BorderSide(3, AppTheme.TEXT_PRIMARY)
            unselected_side = ft.border.BorderSide(1, AppTheme.SURFACE_VARIANT)
            
            b_side = selected_side if is_selected else unselected_side
            
            return ft.Container(
                width=40, height=40,
                border_radius=20,
                bgcolor=hex_color,
                border=ft.border.Border(top=b_side, right=b_side, bottom=b_side, left=b_side),
                tooltip=color_name,
                on_click=lambda e, c=color_name: _on_accent_change(c),
                animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT)
            )

        self.color_chips_row = ft.Row(
            controls=[
                create_color_chip("Indigo", "#6366f1"),
                create_color_chip("Emerald", "#10b981"),
                create_color_chip("Rose", "#f43f5e"),
                create_color_chip("Amber", "#f59e0b"),
                create_color_chip("Violet", "#8b5cf6"),
                create_color_chip("Sky", "#0ea5e9"),
            ],
            wrap=True, spacing=10
        )

        # ── Background Image Overlay ──
        self.bg_image_path = self.settings.get('bg_image_path', '')
        
        def _set_bg_image(path):
            self.bg_image_path = path if path else ''
            self._on_theme_change(None)

        def _browse_bg_image(e):
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            path = filedialog.askopenfilename(
                title="Select Background Image",
                filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp")]
            )
            root.destroy()
            if path:
                _set_bg_image(path)

        def _build_thumb(img_path, label):
            is_active = self.bg_image_path.endswith(img_path)
            border_color = AppTheme.PRIMARY if is_active else ft.Colors.TRANSPARENT
            b_side = ft.border.BorderSide(2, border_color)
            return ft.Container(
                content=ft.Stack([
                    ft.Image(src=img_path, fit="cover", width=120, height=68, border_radius=6),
                    ft.Container(
                        content=ft.Text(label, size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.BLACK54,
                        padding=ft.Padding(4, 2, 4, 2),
                        border_radius=4,
                        bottom=4, right=4
                    )
                ]),
                border=ft.border.Border(top=b_side, right=b_side, bottom=b_side, left=b_side),
                border_radius=8,
                on_click=lambda e: _set_bg_image(img_path)
            )

        demo_thumbs = ft.Row([
            _build_thumb("/bg_1.png", "Neon Grid"),
            _build_thumb("/bg_2.png", "Ethereal"),
            _build_thumb("/bg_3.png", "Circuit"),
            _build_thumb("/bg_4.png", "Minimal"),
        ], scroll=ft.ScrollMode.AUTO, spacing=10)

        self.bg_opacity_slider = ft.Slider(
            min=0, max=100, divisions=10,
            value=int(self.settings.get('bg_image_opacity', 0.1) * 100),
            label="{value}%",
            on_change_end=self._on_theme_change,
            active_color=AppTheme.PRIMARY,
        )

        bg_overlay_controls = ft.Column([
            ft.Text("Background Image", size=14, weight=ft.FontWeight.W_600, color=AppTheme.TEXT_PRIMARY),
            demo_thumbs,
            ft.Row([
                ft.ElevatedButton("Browse Local Image...", icon=ft.Icons.FOLDER_OPEN_ROUNDED, 
                                  on_click=_browse_bg_image),
                ft.TextButton("Clear Background", icon=ft.Icons.CLEAR_ROUNDED, on_click=lambda _: _set_bg_image(''), style=ft.ButtonStyle(color=AppTheme.ERROR))
            ]),
            ft.Text("Image Opacity", size=14, weight=ft.FontWeight.W_600, color=AppTheme.TEXT_PRIMARY),
            self.bg_opacity_slider
        ], spacing=10)

        theme_section = self._section("Appearance", ft.Icons.PALETTE_ROUNDED, [
            ft.Row([ft.Text("Theme:", color=AppTheme.TEXT_PRIMARY), self.theme_segmented], spacing=20),
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            ft.Column([
                ft.Text("Accent Color:", color=AppTheme.TEXT_PRIMARY),
                self.color_chips_row
            ], spacing=10),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            bg_overlay_controls
        ])

        # ── Troubleshoot Settings ──
        b_side = ft.border.BorderSide(1, AppTheme.SURFACE_VARIANT)
        
        def _build_dependency_row(name, is_installed):
            icon = ft.Icons.CHECK_CIRCLE_ROUNDED if is_installed else ft.Icons.ERROR_ROUNDED
            color = AppTheme.SUCCESS if is_installed else AppTheme.ERROR
            return ft.Row([
                ft.Icon(icon, color=color, size=20),
                ft.Text(name, color=AppTheme.TEXT_PRIMARY, size=16),
            ], spacing=10)

        def _get_dependencies_status():
            return [
                ("yt-dlp (YouTube Download)", importlib.util.find_spec("yt_dlp") is not None),
                ("spotdl (Spotify Download)", importlib.util.find_spec("spotdl") is not None),
                ("requests (HTTP Client)", importlib.util.find_spec("requests") is not None),
                ("beautifulsoup4 (HTML Parser)", importlib.util.find_spec("bs4") is not None),
                ("AppleMusicMP3 (Apple Music)", importlib.util.find_spec("AppleMusicMP3") is not None),
                ("curl_cffi (Bypass Protection)", importlib.util.find_spec("curl_cffi") is not None),
                ("flet (UI Framework)", importlib.util.find_spec("flet") is not None),
                ("Pillow (Image Processing)", importlib.util.find_spec("PIL") is not None),
                ("FFmpeg (Audio/Video Processing)", is_ffmpeg_available()),
            ]

        health_icon = ft.Icon(ft.Icons.HELP_OUTLINE, size=40)
        health_text = ft.Text(size=20, weight=ft.FontWeight.BOLD)
        self.troubleshoot_column = ft.Column(spacing=10)

        def _fix_dependencies(e):
            if getattr(self, 'snack_bar', None) in self._page.overlay:
                self._page.overlay.remove(self.snack_bar)
            self.snack_bar = ft.SnackBar(
                content=ft.Text("Fixing missing dependencies in background...", color=AppTheme.TEXT_PRIMARY),
                bgcolor=AppTheme.PRIMARY,
                duration=4000
            )
            self._page.overlay.append(self.snack_bar)
            self.snack_bar.open = True
            self._page.update()

            def fix_task():
                import sys, subprocess, os
                from src.backend.ffmpeg_manager import download_ffmpeg, is_ffmpeg_available
                
                if not getattr(sys, 'frozen', False):
                    req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'requirements.txt')
                    if os.path.exists(req_file):
                        try:
                            subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_file], check=False, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                        except Exception:
                            pass

                if not is_ffmpeg_available():
                    try:
                        download_ffmpeg()
                    except Exception:
                        pass

                _update_troubleshoot_ui()
                if getattr(self, 'snack_bar', None) in self._page.overlay:
                    self._page.overlay.remove(self.snack_bar)
                self.snack_bar = ft.SnackBar(
                    content=ft.Text("Dependency fix attempt complete!", color=AppTheme.TEXT_PRIMARY),
                    bgcolor=AppTheme.SUCCESS,
                    duration=3000
                )
                self._page.overlay.append(self.snack_bar)
                self.snack_bar.open = True
                self._page.update()

            import threading
            threading.Thread(target=fix_task, daemon=True).start()

        fix_btn = ft.ElevatedButton(
            "Fix Missing",
            icon=ft.Icons.AUTO_FIX_HIGH_ROUNDED,
            on_click=_fix_dependencies,
            bgcolor=AppTheme.PRIMARY,
            color=ft.Colors.WHITE
        )

        def _update_troubleshoot_ui(e=None):
            deps = _get_dependencies_status()
            all_ok = all(installed for name, installed in deps)
            
            health_icon.name = ft.Icons.CHECK_CIRCLE_ROUNDED if all_ok else ft.Icons.ERROR_ROUNDED
            health_icon.color = AppTheme.SUCCESS if all_ok else AppTheme.ERROR
            health_text.value = "System Status: All Systems Normal" if all_ok else "System Status: Missing Dependencies"
            health_text.color = AppTheme.SUCCESS if all_ok else AppTheme.ERROR
            
            fix_btn.visible = not all_ok
            
            content_list = []
            for name, installed in deps:
                content_list.append(_build_dependency_row(name, installed))
            self.troubleshoot_column.controls = content_list
            
            try:
                self.troubleshoot_column.update()
                health_icon.update()
                health_text.update()
                fix_btn.update()
            except:
                pass

        _update_troubleshoot_ui()

        dll_text = ft.Text("Click 'Load DLLs' to view loaded modules for the current process.", size=12, color=AppTheme.TEXT_SECONDARY, selectable=True)
        dll_container = ft.Container(
            content=ft.Column([dll_text], scroll=ft.ScrollMode.AUTO),
            height=150, padding=10, border=ft.border.Border(top=b_side, right=b_side, bottom=b_side, left=b_side),
            bgcolor=AppTheme.SURFACE_VARIANT, border_radius=10
        )
        
        def _load_dlls(e):
            import subprocess, os
            try:
                pid = os.getpid()
                output = subprocess.check_output(
                    f'tasklist /m /fi "pid eq {pid}"',
                    shell=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                dll_text.value = output
            except Exception as ex:
                dll_text.value = f"Error fetching DLLs: {ex}"
            dll_text.update()

        load_dlls_btn = ft.ElevatedButton("Load System DLLs", icon=ft.Icons.DATA_OBJECT_ROUNDED, on_click=_load_dlls, bgcolor=AppTheme.SURFACE_VARIANT, color=AppTheme.TEXT_PRIMARY)

        advanced_expansion = ft.ExpansionTile(
            title=ft.Text("Advanced Diagnostics & DLLs", weight=ft.FontWeight.W_600, color=AppTheme.TEXT_PRIMARY),
            subtitle=ft.Text("View detailed dependency list and loaded modules", color=AppTheme.TEXT_SECONDARY),
            controls=[
                ft.Container(
                    content=self.troubleshoot_column,
                    padding=10,
                    border=ft.border.Border(top=b_side, right=b_side, bottom=b_side, left=b_side),
                    border_radius=10,
                    bgcolor=AppTheme.SURFACE
                ),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.Row([load_dlls_btn]),
                dll_container
            ]
        )

        refresh_btn = ft.ElevatedButton(
            "Refresh Status",
            icon=ft.Icons.REFRESH_ROUNDED,
            on_click=_update_troubleshoot_ui,
            bgcolor=AppTheme.SURFACE_VARIANT,
            color=AppTheme.TEXT_PRIMARY
        )

        troubleshoot_section = self._section("Troubleshoot", ft.Icons.BUILD_ROUNDED, [
            ft.Row([health_icon, health_text], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([refresh_btn, fix_btn], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
            ft.Divider(height=20, color=AppTheme.SURFACE_VARIANT),
            advanced_expansion
        ])

        # Bind auto-save to controls
        auto_save_controls_change = [
            self.format_dropdown, self.max_concurrent_dropdown,
            self.playlist_folder_switch, self.audio_codec_dropdown,
            self.audio_quality_dropdown, self.ask_on_close_switch,
            self.embed_thumbnail_switch, self.embed_metadata_switch,
            self.embed_subs_switch, self.embed_chapters_switch, self.browser_cookies_dropdown,
            self.auto_delete_history_dropdown, self.hw_accel_dropdown,
            self.sponsorblock_action_dropdown, self.engine_interval_dropdown
        ]
        for control in auto_save_controls_change:
            if isinstance(control, ft.Dropdown):
                if control.options:
                    for opt in control.options:
                        opt.style = AppTheme.get_dropdown_option_style()
                orig_on_select = getattr(control, 'on_select', None)
                def make_handler(orig):
                    def handler(e):
                        if orig: orig(e)
                        self._save(e)
                    return handler
                control.on_select = make_handler(orig_on_select)
            else:
                orig_on_change = getattr(control, 'on_change', None)
                def make_handler(orig):
                    def handler(e):
                        if orig: orig(e)
                        self._save(e)
                    return handler
                control.on_change = make_handler(orig_on_change)

        auto_save_controls_blur = [
            self.filename_field, self.playlist_filename_field,
            self.speed_limit_field, self.sub_lang_field
        ]
        for control in auto_save_controls_blur:
            control.on_blur = self._save

        tabs = [
            ft.Tab(label="General", icon=ft.Icons.SETTINGS_ROUNDED),
            ft.Tab(label="Appearance", icon=ft.Icons.PALETTE_ROUNDED),
            ft.Tab(label="Download", icon=ft.Icons.DOWNLOAD_ROUNDED),
            ft.Tab(label="Playlist & Queue", icon=ft.Icons.QUEUE_MUSIC_ROUNDED),
            ft.Tab(label="Advanced", icon=ft.Icons.TUNE_ROUNDED),
        ]
        views = [
            general_section,
            theme_section,
            download_section,
            playlist_section,
            advanced_section,
        ]

        if self.settings.get('developer_mode', False):
            tabs.append(ft.Tab(label="Troubleshoot", icon=ft.Icons.BUILD_ROUNDED))
            views.append(troubleshoot_section)

        tab_bar = ft.TabBar(
            tabs=tabs,
            scrollable=True,
            splash_border_radius=ft.BorderRadius.all(10),
            indicator_color=AppTheme.PRIMARY,
            label_color=AppTheme.PRIMARY,
            unselected_label_color=AppTheme.TEXT_SECONDARY,
            indicator=ft.UnderlineTabIndicator(
                border_side=ft.BorderSide(3, AppTheme.PRIMARY),
                border_radius=ft.BorderRadius.all(3),
            ),
        )

        tab_view = ft.TabBarView(
            controls=views,
            expand=True
        )

        tabs_controller = ft.Tabs(
            length=len(tabs),
            selected_index=0,
            content=ft.Column([
                tab_bar,
                tab_view
            ], expand=True),
            expand=True
        )

        self.content = ft.Column(
            [
                header,
                ft.Divider(height=1, color=AppTheme.SURFACE_VARIANT),
                ft.Container(
                    content=tabs_controller,
                    padding=ft.Padding(left=10, right=10, top=10, bottom=0),
                    expand=True,
                )
            ],
            spacing=0,
        )

    # ------------------------------------------------------------------ helpers
    def _section(self, title: str, icon, children: list) -> ft.Container:
        inner_content = ft.Container(
            content=ft.Column(
                children,
                spacing=15,
            ),
            padding=ft.Padding(left=10, right=28, top=10, bottom=20),
        )
        return ft.Container(
            content=ft.Column(
                [inner_content],
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=ft.Padding(left=10, right=4, top=10, bottom=10),
            expand=True,
        )

    # ------------------------------------------------------------------ actions
    def _browse_folder(self, setting_key, field):
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        title = "Select Temporary Folder" if "temp" in setting_key else "Select Default Download Folder"
        path = filedialog.askdirectory(title=title)
        root.destroy()
        if path:
            field.value = path
            self._save(None)
            self.update()
            self._page.update()

    def _browse_file(self, setting_key, field):
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        title = "Select Cookies File"
        path = filedialog.askopenfilename(title=title, filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        root.destroy()
        if path:
            field.value = path
            self._save(None)
            self.update()
            self._page.update()

    def _login_browser(self, url):
        def run():
            from src.backend.cookie_manager import CookieManager
            out_file = CookieManager.open_login_window(url)
            if out_file and os.path.exists(out_file) and os.path.getsize(out_file) > 0:
                self.cookies_path_field.value = out_file
                self.settings.set('cookies_path', out_file)
                self.settings.save()
                self.update()
                
                # Show confirmation
                if getattr(self, 'snack_bar', None) in self._page.overlay:
                    self._page.overlay.remove(self.snack_bar)
                self.snack_bar = ft.SnackBar(
                    content=ft.Text("Cookies saved successfully ✓", color=AppTheme.TEXT_PRIMARY),
                    bgcolor=AppTheme.SUCCESS,
                    duration=3000
                )
                self._page.overlay.append(self.snack_bar)
                self.snack_bar.open = True
                self._page.update()
                
        if hasattr(self._page, 'run_thread') and self._page.run_thread:
            self._page.run_thread(run)
        else:
            import threading
            threading.Thread(target=run, daemon=True).start()

    def _build_engine_status_content(self, check_results=None):
        installed = get_installed_engine_versions()
        last_check_time = float(self.settings.get('engine_last_check_time', 0))
        if last_check_time > 0:
            import datetime
            dt = datetime.datetime.fromtimestamp(last_check_time)
            last_checked_str = dt.strftime("%b %d, %Y at %I:%M %p")
        else:
            last_checked_str = "Never"

        chips = []
        engine_display = [
            ("yt-dlp", "yt-dlp (Core Engine)", ft.Icons.PLAY_CIRCLE_ROUNDED),
            ("spotdl", "spotdl (Spotify)", ft.Icons.MUSIC_NOTE_ROUNDED),
            ("curl_cffi", "curl_cffi (Bypass)", ft.Icons.SHIELD_ROUNDED),
        ]

        for key, label, icon in engine_display:
            curr_v = installed.get(key, 'Unknown')
            latest_v = None
            is_newer = False
            if check_results and 'engines' in check_results:
                info = check_results['engines'].get(key, {})
                latest_v = info.get('latest')
                is_newer = info.get('update_available', False)

            status_badges = []
            if is_newer and latest_v:
                status_badges.append(
                    ft.Container(
                        content=ft.Text(f"Update: v{latest_v}", size=11, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                        bgcolor=ft.Colors.AMBER_800,
                        padding=ft.Padding(6, 2, 6, 2),
                        border_radius=6,
                    )
                )
            elif curr_v not in ('Not Installed', 'Unknown'):
                status_badges.append(
                    ft.Container(
                        content=ft.Text("Up to date", size=11, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                        bgcolor=AppTheme.SUCCESS,
                        padding=ft.Padding(6, 2, 6, 2),
                        border_radius=6,
                    )
                )

            chip = ft.Container(
                content=ft.Row([
                    ft.Icon(icon, size=18, color=AppTheme.PRIMARY),
                    ft.Column([
                        ft.Text(label, size=12, weight=ft.FontWeight.W_600, color=AppTheme.TEXT_PRIMARY),
                        ft.Text(f"Installed: v{curr_v}", size=11, color=AppTheme.TEXT_SECONDARY),
                    ], spacing=1, expand=True),
                    *status_badges
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=AppTheme.SURFACE,
                padding=ft.Padding(12, 8, 12, 8),
                border_radius=10,
                border=ft.Border(
                    top=ft.BorderSide(1, AppTheme.SURFACE_VARIANT),
                    bottom=ft.BorderSide(1, AppTheme.SURFACE_VARIANT),
                    left=ft.BorderSide(1, AppTheme.SURFACE_VARIANT),
                    right=ft.BorderSide(1, AppTheme.SURFACE_VARIANT),
                ),
                expand=True,
            )
            chips.append(chip)

        return ft.Column([
            ft.ResponsiveRow([
                ft.Column([c], col={"sm": 12, "md": 4}) for c in chips
            ], spacing=10, run_spacing=10),
            ft.Row([
                ft.Icon(ft.Icons.SCHEDULE_ROUNDED, size=14, color=AppTheme.TEXT_SECONDARY),
                ft.Text(f"Last checked: {last_checked_str}", size=11, color=AppTheme.TEXT_SECONDARY),
            ], spacing=5)
        ], spacing=8)

    def _on_check_engines_click(self, e):
        self.check_engines_btn.disabled = True
        self.check_engines_btn.icon = ft.Icons.HOURGLASS_TOP_ROUNDED
        self.check_engines_btn.text = "Checking..."
        self.update()

        def run_check():
            results = check_for_engine_updates()
            def update_ui():
                self.check_engines_btn.disabled = False
                self.check_engines_btn.icon = ft.Icons.REFRESH_ROUNDED
                self.check_engines_btn.text = "Check for Updates"
                self.engine_status_container.content = self._build_engine_status_content(results)
                self.update()

                if getattr(self, 'snack_bar', None) in self._page.overlay:
                    self._page.overlay.remove(self.snack_bar)

                if results.get('has_updates'):
                    self.snack_bar = ft.SnackBar(
                        content=ft.Text("Engine updates available! Click 'Update Engines Now' to install.", color=AppTheme.TEXT_PRIMARY),
                        bgcolor=AppTheme.PRIMARY,
                        duration=3500
                    )
                else:
                    self.snack_bar = ft.SnackBar(
                        content=ft.Text("All backend engines are up to date!", color=AppTheme.TEXT_PRIMARY),
                        bgcolor=AppTheme.SUCCESS,
                        duration=3000
                    )
                self._page.overlay.append(self.snack_bar)
                self.snack_bar.open = True
                self._page.update()

            if hasattr(self._page, 'run_thread') and self._page.run_thread:
                self._page.run_thread(update_ui)
            else:
                update_ui()

        import threading
        threading.Thread(target=run_check, daemon=True).start()

    def _on_update_engines_click(self, e):
        self.update_engines_btn.disabled = True
        self.update_engines_btn.icon = ft.Icons.HOURGLASS_TOP_ROUNDED
        self.update_engines_btn.text = "Updating..."
        self.update()

        if getattr(self, 'snack_bar', None) in self._page.overlay:
            self._page.overlay.remove(self.snack_bar)
        self.snack_bar = ft.SnackBar(
            content=ft.Text("Updating backend engines in background... Please wait.", color=AppTheme.TEXT_PRIMARY),
            bgcolor=AppTheme.PRIMARY,
            duration=4000
        )
        self._page.overlay.append(self.snack_bar)
        self.snack_bar.open = True
        self._page.update()

        def run_update():
            success, msg = update_engines()
            def update_ui():
                self.update_engines_btn.disabled = False
                self.update_engines_btn.icon = ft.Icons.UPGRADE_ROUNDED
                self.update_engines_btn.text = "Update Engines Now"
                self.engine_status_container.content = self._build_engine_status_content()
                self.update()

                if getattr(self, 'snack_bar', None) in self._page.overlay:
                    self._page.overlay.remove(self.snack_bar)
                self.snack_bar = ft.SnackBar(
                    content=ft.Text(msg, color=AppTheme.TEXT_PRIMARY),
                    bgcolor=AppTheme.SUCCESS if success else AppTheme.ERROR,
                    duration=3500
                )
                self._page.overlay.append(self.snack_bar)
                self.snack_bar.open = True
                self._page.update()

            if hasattr(self._page, 'run_thread') and self._page.run_thread:
                self._page.run_thread(update_ui)
            else:
                update_ui()

        import threading
        threading.Thread(target=run_update, daemon=True).start()

    def _show_templates_info(self, e):
        templates = [
            ("%(title)s.%(ext)s", "Default (Title Only)", "Never Gonna Give You Up.mp4"),
            ("%(uploader)s - %(title)s.%(ext)s", "Channel Name - Title", "Rick Astley - Never Gonna Give You Up.mp4"),
            ("%(uploader)s - %(title)s [%(resolution)s].%(ext)s", "Channel - Title [Resolution]", "Rick Astley - Video Title [1080p].mp4"),
            ("%(title)s [%(resolution)s].%(ext)s", "Title with Resolution", "Never Gonna Give You Up [1080p].mp4"),
            ("%(upload_date)s - %(title)s.%(ext)s", "Date - Title", "20091025 - Never Gonna Give You Up.mp4"),
            ("%(upload_date)s - %(uploader)s - %(title)s.%(ext)s", "Date - Channel - Title", "20091025 - Rick Astley - Never Gonna Give You Up.mp4"),
            ("%(title)s [%(id)s].%(ext)s", "Title with Video ID", "Never Gonna Give You Up [dQw4w9WgXcQ].mp4"),
            ("%(uploader)s - %(title)s [%(id)s].%(ext)s", "Channel - Title with Video ID", "Rick Astley - Never Gonna Give You Up [dQw4w9WgXcQ].mp4"),
            ("%(uploader)s - %(title)s [%(resolution)s] [%(id)s].%(ext)s", "Channel - Title [Resolution] [ID]", "Rick Astley - Video Title [1080p] [dQw4w9WgXcQ].mp4"),
        ]
        self._show_templates_dialog(
            templates=templates,
            title_str="Filename Template Guide",
            icon=ft.Icons.DESCRIPTION_ROUNDED,
            target_field=self.filename_field,
            is_playlist=False,
        )

    def _show_playlist_templates_info(self, e):
        templates = [
            ("%(playlist_index)s - %(title)s.%(ext)s", "Default (Index - Title)", "1 - Song Title.mp3"),
            ("%(playlist_index)02d - %(title)s.%(ext)s", "2-Digit Padded Index (01 - Title)", "01 - Song Title.mp3"),
            ("%(playlist_index)03d - %(title)s.%(ext)s", "3-Digit Padded Index (001 - Title)", "001 - Song Title.mp3"),
            ("%(playlist_index)02d - %(uploader)s - %(title)s.%(ext)s", "Padded Index - Artist - Title", "01 - Rick Astley - Song Title.mp3"),
            ("%(playlist)s - %(playlist_index)02d - %(title)s.%(ext)s", "Playlist - Index - Title", "Greatest Hits - 01 - Song Title.mp3"),
            ("%(uploader)s - %(playlist)s - %(playlist_index)02d - %(title)s.%(ext)s", "Channel - Playlist - Index - Title", "Rick Astley - Greatest Hits - 01 - Song Title.mp3"),
            ("%(playlist_index)s. %(title)s.%(ext)s", "Dot Numbered (1. Title)", "1. Song Title.mp3"),
            ("[%(playlist_index)02d] %(title)s.%(ext)s", "Bracketed Index ([01] Title)", "[01] Song Title.mp3"),
        ]
        self._show_templates_dialog(
            templates=templates,
            title_str="Playlist Template Guide",
            icon=ft.Icons.PLAYLIST_PLAY_ROUNDED,
            target_field=self.playlist_filename_field,
            is_playlist=True,
        )

    def _show_subtitles_info(self, e):
        def apply_lang(val):
            self.sub_lang_field.value = val
            self._save(None)
            self.update()
            if getattr(self, 'snack_bar', None) in self._page.overlay:
                self._page.overlay.remove(self.snack_bar)
            self.snack_bar = ft.SnackBar(
                content=ft.Text(f"Applied subtitle language: {val}", color=AppTheme.TEXT_PRIMARY),
                bgcolor=AppTheme.SUCCESS,
                duration=2000
            )
            self._page.overlay.append(self.snack_bar)
            self.snack_bar.open = True
            self._close_dialog(dlg)

        presets = [
            ("en", "English", "Default single language track"),
            ("en, es", "English & Spanish", "Embed both English and Spanish tracks"),
            ("en, hi", "English & Hindi", "Embed English and Hindi tracks"),
            ("en, ja", "English & Japanese", "Embed English and Japanese tracks"),
            ("en, fr, de", "English, French & German", "Embed multiple European language tracks"),
            ("all", "All Available Subtitles", "Embed every subtitle language available for the video"),
        ]

        preset_controls = [
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.SUBTITLES_ROUNDED, color=AppTheme.PRIMARY, size=20),
                    ft.Column([
                        ft.Text(p[1], color=AppTheme.TEXT_PRIMARY, weight=ft.FontWeight.W_600, size=13),
                        ft.Text(f"Code: {p[0]} — {p[2]}", color=AppTheme.TEXT_SECONDARY, size=11),
                    ], spacing=2, expand=True),
                    ft.ElevatedButton(
                        "Apply",
                        icon=ft.Icons.CHECK_ROUNDED,
                        style=ft.ButtonStyle(
                            bgcolor=AppTheme.PRIMARY,
                            color=AppTheme.TEXT_PRIMARY,
                            padding=ft.Padding(12, 6, 12, 6),
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                        on_click=lambda e, val=p[0]: apply_lang(val)
                    )
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
                padding=ft.Padding(left=12, right=14, top=8, bottom=8),
                margin=ft.Margin(left=0, right=16, top=0, bottom=0),
                bgcolor=AppTheme.SURFACE_VARIANT,
                border_radius=10,
            )
            for p in presets
        ]

        info_box = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.TIPS_AND_UPDATES_ROUNDED, color=AppTheme.ACCENT, size=18),
                    ft.Text("How Subtitle Embedding Works", weight=ft.FontWeight.BOLD, color=AppTheme.TEXT_PRIMARY, size=13),
                ], spacing=6),
                ft.Text(
                    "• Multiple Languages: Enter multiple 2-letter codes separated by commas (e.g. en, es, hi). All selected tracks will be embedded into the single video.\n"
                    "• Download All: Type 'all' to automatically download and embed every available subtitle.\n"
                    "• Soft Subtitles: Tracks are muxed inside the video container (MKV, MP4) with proper language labels so you can switch languages or turn them off anytime in your video player (VLC, TV, etc.).\n"
                    "• Common codes: en (English), es (Spanish), hi (Hindi), ja (Japanese), fr (French), de (German), ko (Korean), zh-Hans (Chinese), pt (Portuguese), ru (Russian), ar (Arabic).",
                    color=AppTheme.TEXT_SECONDARY,
                    size=12,
                )
            ], spacing=6),
            bgcolor=AppTheme.SURFACE_VARIANT,
            padding=14,
            border_radius=10,
            margin=ft.Margin(left=0, right=16, top=0, bottom=0),
        )

        presets_title = ft.Container(
            content=ft.Text("Quick Presets (Click Apply):", weight=ft.FontWeight.W_600, color=AppTheme.TEXT_PRIMARY, size=13),
            margin=ft.Margin(left=2, right=16, top=4, bottom=2),
        )

        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.SUBTITLES_ROUNDED, color=AppTheme.PRIMARY, size=24),
                ft.Text("Subtitle Language Guide", color=AppTheme.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            ], spacing=8),
            content=ft.Container(
                content=ft.Column([
                    info_box,
                    presets_title,
                    *preset_controls
                ], spacing=8, scroll=ft.ScrollMode.AUTO),
                width=540,
                height=440,
            ),
            bgcolor=AppTheme.SURFACE,
            shape=ft.RoundedRectangleBorder(radius=12),
            actions=[
                ft.TextButton("Close", on_click=lambda e: self._close_dialog(dlg))
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dlg)
        dlg.open = True
        self._page.update()

    def _show_templates_dialog(self, templates, title_str, icon, target_field, is_playlist=False):
        def apply_template(tmpl):
            target_field.value = tmpl
            self._save(None)
            self.update()
            
            if getattr(self, 'snack_bar', None) in self._page.overlay:
                self._page.overlay.remove(self.snack_bar)
                
            self.snack_bar = ft.SnackBar(
                content=ft.Text(f"Applied template: {tmpl}", color=AppTheme.TEXT_PRIMARY),
                bgcolor=AppTheme.SUCCESS,
                duration=2000
            )
            self._page.overlay.append(self.snack_bar)
            self.snack_bar.open = True
            self._close_dialog(dlg)

        preset_controls = [
            ft.Container(
                content=ft.Row([
                    ft.Icon(icon, color=AppTheme.PRIMARY, size=20),
                    ft.Column([
                        ft.Text(t[1], color=AppTheme.TEXT_PRIMARY, weight=ft.FontWeight.W_600, size=13),
                        ft.Text(f"Format: {t[0]}", color=AppTheme.ACCENT, size=11, weight=ft.FontWeight.W_500),
                        ft.Text(f"Example: {t[2]}", color=AppTheme.TEXT_SECONDARY, size=11),
                    ], spacing=2, expand=True),
                    ft.ElevatedButton(
                        "Apply",
                        icon=ft.Icons.CHECK_ROUNDED,
                        style=ft.ButtonStyle(
                            bgcolor=AppTheme.PRIMARY,
                            color=AppTheme.TEXT_PRIMARY,
                            padding=ft.Padding(12, 6, 12, 6),
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                        on_click=lambda e, tmpl=t[0]: apply_template(tmpl)
                    )
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
                padding=ft.Padding(left=12, right=14, top=8, bottom=8),
                margin=ft.Margin(left=0, right=16, top=0, bottom=0),
                bgcolor=AppTheme.SURFACE_VARIANT,
                border_radius=10,
            )
            for t in templates
        ]

        if is_playlist:
            info_text = (
                "• How Playlist Templates Work: Customize how files in playlists, albums, and series are named automatically.\n"
                "• Essential Playlist Tags:\n"
                "  - %(playlist_index)s : Track position / order (e.g. 1, 2, 3...)\n"
                "  - %(playlist_index)02d : Padded 2-digit number (e.g. 01, 02, 03...)\n"
                "  - %(playlist_index)03d : Padded 3-digit number (e.g. 001, 002...)\n"
                "  - %(playlist)s : Name of the playlist, album, or series\n"
                "  - %(title)s : Video or track title\n"
                "  - %(uploader)s : Channel or artist name\n"
                "  - %(ext)s : Output extension (mp4, mkv, mp3)\n"
                "• Tip: Padded numbers like %(playlist_index)02d keep your tracks in exact chronological order in Windows File Explorer!"
            )
        else:
            info_text = (
                "• How Filename Templates Work: Templates let you automatically name downloaded files using dynamic tags enclosed in %(tag)s.\n"
                "• Supported Tags:\n"
                "  - %(title)s : Video or audio title\n"
                "  - %(uploader)s : Channel, creator, or artist name\n"
                "  - %(upload_date)s : Published date in YYYYMMDD format (e.g. 20240115)\n"
                "  - %(resolution)s : Video resolution (e.g. 1080p, 720p, 4k)\n"
                "  - %(id)s : Unique platform video ID (e.g. dQw4w9WgXcQ)\n"
                "  - %(ext)s : Media file extension (mp4, mkv, mp3, flac)\n"
                "• Tip: You can type custom text, separators (e.g. hyphens, underscores, brackets), or any combination directly in the filename field!"
            )

        info_box = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.TIPS_AND_UPDATES_ROUNDED, color=AppTheme.ACCENT, size=18),
                    ft.Text("How Filename Templates Work", weight=ft.FontWeight.BOLD, color=AppTheme.TEXT_PRIMARY, size=13),
                ], spacing=6),
                ft.Text(
                    info_text,
                    color=AppTheme.TEXT_SECONDARY,
                    size=12,
                )
            ], spacing=6),
            bgcolor=AppTheme.SURFACE_VARIANT,
            padding=14,
            border_radius=10,
            margin=ft.Margin(left=0, right=16, top=0, bottom=0),
        )

        presets_title = ft.Container(
            content=ft.Text("Popular Presets (Click Apply):", weight=ft.FontWeight.W_600, color=AppTheme.TEXT_PRIMARY, size=13),
            margin=ft.Margin(left=2, right=16, top=4, bottom=2),
        )

        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(icon, color=AppTheme.PRIMARY, size=24),
                ft.Text(title_str, color=AppTheme.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            ], spacing=8),
            content=ft.Container(
                content=ft.Column([
                    info_box,
                    presets_title,
                    *preset_controls
                ], spacing=8, scroll=ft.ScrollMode.AUTO),
                width=560,
                height=460,
            ),
            bgcolor=AppTheme.SURFACE,
            shape=ft.RoundedRectangleBorder(radius=12),
            actions=[
                ft.TextButton("Close", on_click=lambda e: self._close_dialog(dlg))
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dlg)
        dlg.open = True
        self._page.update()
        
    def _close_dialog(self, dlg):
        dlg.open = False
        self._page.update()

    def _save(self, e):
        self.settings.set('default_download_path', self.path_field.value)
        self.settings.set('temp_download_path', self.temp_path_field.value)
        self.settings.set('preferred_format', self.format_dropdown.value)
        self.settings.set('filename_template', self.filename_field.value)
        self.settings.set('audio_codec', self.audio_codec_dropdown.value)
        self.settings.set('audio_quality', self.audio_quality_dropdown.value)
        self.settings.set('max_concurrent_downloads', int(self.max_concurrent_dropdown.value))
        self.settings.set('playlist_filename_template', self.playlist_filename_field.value)
        self.settings.set('create_playlist_folder', self.playlist_folder_switch.value)
        
        self.settings.set('ask_on_close', self.ask_on_close_switch.value)
        if self.ask_on_close_switch.value:
            self.settings.set('close_behavior', 'prompt')

        try:
            speed_kb = int(self.speed_limit_field.value or 0)
            self.settings.set('speed_limit', speed_kb * 1024)  # store in bytes/sec
        except ValueError:
            self.settings.set('speed_limit', 0)

        self.settings.set('embed_thumbnail', self.embed_thumbnail_switch.value)
        self.settings.set('embed_metadata', self.embed_metadata_switch.value)
        self.settings.set('embed_chapters', self.embed_chapters_switch.value)
        self.settings.set('embed_subtitles', self.embed_subs_switch.value)
        self.settings.set('auto_subtitle_lang', self.sub_lang_field.value.strip() or 'en')
        self.settings.set('browser_cookies', self.browser_cookies_dropdown.value)
        self.settings.set('cookies_path', self.cookies_path_field.value)
        
        self.settings.set('enable_sponsorblock', self.sponsorblock_switch.value)
        self.settings.set('sponsorblock_action', self.sponsorblock_action_dropdown.value)
        selected_sb_cats = [cid for cid, cb in self.sponsorblock_cat_checkboxes.items() if cb.value]
        self.settings.set('sponsorblock_categories', selected_sb_cats)
        
        if hasattr(self, 'engine_interval_dropdown') and self.engine_interval_dropdown.value:
            self.settings.set('engine_update_interval', self.engine_interval_dropdown.value)
        
        self.settings.save()

    def sync_from_settings(self):
        self.path_field.value = self.settings.get('default_download_path')
        self.temp_path_field.value = self.settings.get('temp_download_path')
        self.format_dropdown.value = self.settings.get('preferred_format')
        self.filename_field.value = self.settings.get('filename_template')
        self.audio_codec_dropdown.value = self.settings.get('audio_codec')
        self.audio_quality_dropdown.value = self.settings.get('audio_quality')
        self.max_concurrent_dropdown.value = str(self.settings.get('max_concurrent_downloads', 3))
        self.playlist_filename_field.value = self.settings.get('playlist_filename_template')
        self.playlist_folder_switch.value = self.settings.get('create_playlist_folder')
        self.ask_on_close_switch.value = self.settings.get('ask_on_close')
        if hasattr(self, 'close_behavior_dropdown'):
            self.close_behavior_dropdown.value = self.settings.get('close_behavior')
        speed = self.settings.get('speed_limit', 0)
        self.speed_limit_field.value = str(int(speed / 1024)) if speed else "0"
        self.embed_thumbnail_switch.value = self.settings.get('embed_thumbnail')
        self.embed_metadata_switch.value = self.settings.get('embed_metadata', True)
        if hasattr(self, 'embed_chapters_switch'):
            self.embed_chapters_switch.value = self.settings.get('embed_chapters', True)
        self.embed_subs_switch.value = self.settings.get('embed_subtitles')
        self.sub_lang_field.value = self.settings.get('auto_subtitle_lang')
        self.browser_cookies_dropdown.value = self.settings.get('browser_cookies')
        self.cookies_path_field.value = self.settings.get('cookies_path')
        self.theme_segmented.selected = [self.settings.get('theme', 'dark')]
        if hasattr(self, 'dev_mode_switch'):
            self.dev_mode_switch.value = self.settings.get('developer_mode', False)
        if hasattr(self, 'sponsorblock_switch'):
            is_sb = self.settings.get('enable_sponsorblock', False)
            self.sponsorblock_switch.value = is_sb
            self.sponsorblock_action_dropdown.value = self.settings.get('sponsorblock_action', 'remove')
            self.sponsorblock_action_dropdown.disabled = not is_sb
            saved_cats = self.settings.get('sponsorblock_categories', ['sponsor', 'selfpromo', 'interaction', 'intro', 'outro'])
            for cid, cb in self.sponsorblock_cat_checkboxes.items():
                cb.value = (cid in saved_cats)
                cb.disabled = not is_sb
            self.sponsorblock_options_container.opacity = 1.0 if is_sb else 0.4
        if hasattr(self, 'engine_interval_dropdown'):
            self.engine_interval_dropdown.value = self.settings.get('engine_update_interval', 'weekly')
        try:
            self.update()
        except:
            pass

    def _reset_defaults(self, e):
        self.settings.reset()
        self.sync_from_settings()
        self._page.update()

    def _on_theme_change(self, e):
        """Apply theme instantly when the settings change."""
        new_theme = self.theme_segmented.selected[0] if self.theme_segmented.selected else "dark"
        new_accent = self.settings.get('accent_color', 'Indigo')
        new_bg = self.bg_image_path
        new_opacity = self.bg_opacity_slider.value / 100.0
        
        self.settings.set('theme', new_theme)
        self.settings.set('accent_color', new_accent)
        self.settings.set('bg_image_path', new_bg)
        self.settings.set('bg_image_opacity', new_opacity)
        self.settings.save()
        AppTheme.apply(new_theme, new_accent, new_bg, new_opacity)
        
        # Update UI colors immediately
        self._page.bgcolor = AppTheme.BACKGROUND
        self._page.theme = AppTheme.get_theme()
        self._page.theme_mode = ft.ThemeMode.LIGHT if AppTheme.MODE == 'light' else ft.ThemeMode.DARK
        self._page.window.brightness = ft.Brightness.LIGHT if AppTheme.MODE == 'light' else ft.Brightness.DARK
        try:
            import main
            if hasattr(main, 'apply_native_window_styling'):
                icon_path = getattr(self._page.window, 'icon', None)
                main.apply_native_window_styling("Any Downloader", icon_path, dark=(AppTheme.MODE == 'dark'))
        except Exception:
            pass

        if hasattr(self._page, 'custom_title_bar') and self._page.custom_title_bar:
            try:
                self._page.custom_title_bar.update_theme()
            except Exception:
                pass
        # Update the container's own background color
        self.bgcolor = ft.Colors.TRANSPARENT
        # Rebuild the settings UI with new colors
        self._build_ui()
        self.update()
        self._page.update()
        
        if self.on_theme_changed:
            import inspect
            sig = inspect.signature(self.on_theme_changed)
            if 'show_notification' in sig.parameters:
                is_slider = e is not None and getattr(e, 'control', None) == getattr(self, 'bg_opacity_slider', None)
                self.on_theme_changed(show_notification=not is_slider)
            else:
                self.on_theme_changed()

    def _close(self, e):
        if self._on_close:
            self._on_close()
