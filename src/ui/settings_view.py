import flet as ft
import os
from src.ui.theme import AppTheme
from src.backend.settings import SettingsManager


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
            border_radius=10,
            options=[
                ft.dropdown.Option(key="best", text="Best Quality (Video + Audio)"),
                ft.dropdown.Option(key="bestvideo[height<=1080]+bestaudio/best", text="1080p"),
                ft.dropdown.Option(key="bestvideo[height<=720]+bestaudio/best", text="720p"),
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

        download_section = self._section(
            "Download Settings",
            ft.Icons.DOWNLOAD_ROUNDED,
            [
                ft.Row([self.path_field, browse_btn], spacing=10),
                ft.Row([self.temp_path_field, temp_browse_btn], spacing=10),
                ft.Row([self.format_dropdown, filename_row], spacing=20, wrap=True),
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
            border_radius=10,
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

        # ── Audio Settings ──
        self.audio_codec_dropdown = ft.Dropdown(
            label="Audio Codec",
            width=200,
            value=self.settings.get('audio_codec'),
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=10,
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
            border_radius=10,
            options=[
                ft.dropdown.Option(key="320", text="320 kbps"),
                ft.dropdown.Option(key="256", text="256 kbps"),
                ft.dropdown.Option(key="192", text="192 kbps"),
                ft.dropdown.Option(key="128", text="128 kbps"),
                ft.dropdown.Option(key="96", text="96 kbps"),
            ],
        )

        audio_section = self._section(
            "Audio Settings",
            ft.Icons.MUSIC_NOTE_ROUNDED,
            [ft.Row([self.audio_codec_dropdown, self.audio_quality_dropdown], spacing=20, wrap=True)],
        )

        # ── Advanced Settings ──
        self.ask_on_close_switch = ft.Switch(
            label="Ask before closing (Minimize to Tray / Exit)",
            value=self.settings.get('ask_on_close', True),
            active_color=AppTheme.PRIMARY,
            label_text_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY),
            tooltip="If disabled, uses your saved close behavior",
        )

        self.speed_limit_field = ft.TextField(
            label="Download Speed Limit (KB/s, 0 = unlimited)",
            value=str(int(self.settings.get('speed_limit', 0) / 1024)) if self.settings.get('speed_limit', 0) else "0",
            width=280,
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=10,
            prefix_icon=ft.Icons.SPEED_ROUNDED,
            input_filter=ft.NumbersOnlyInputFilter(),
        )

        self.embed_thumbnail_switch = ft.Switch(
            label="Embed Thumbnail in File",
            value=self.settings.get('embed_thumbnail'),
            active_color=AppTheme.PRIMARY,
            label_text_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY),
        )

        self.embed_metadata_switch = ft.Switch(
            label="Embed Metadata (Title, Artist, Track #)",
            value=self.settings.get('embed_metadata', True),
            active_color=AppTheme.PRIMARY,
            label_text_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY),
        )

        self.embed_subs_switch = ft.Switch(
            label="Embed Subtitles",
            value=self.settings.get('embed_subtitles'),
            active_color=AppTheme.PRIMARY,
            label_text_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY),
        )

        self.sub_lang_field = ft.TextField(
            label="Subtitle Language (e.g. en, es, hi)",
            value=self.settings.get('auto_subtitle_lang'),
            width=280,
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=10,
            prefix_icon=ft.Icons.SUBTITLES_ROUNDED,
        )

        self.browser_cookies_dropdown = ft.Dropdown(
            label="Use Cookies from Browser",
            width=280,
            value=self.settings.get('browser_cookies', 'none'),
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=10,
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

        advanced_section = self._section(
            "Advanced",
            ft.Icons.TUNE_ROUNDED,
            [
                ft.Row([self.ask_on_close_switch], spacing=20, wrap=True),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                self.speed_limit_field,
                ft.Row([self.embed_thumbnail_switch, self.embed_subs_switch, self.embed_metadata_switch], spacing=30, wrap=True),
                self.sub_lang_field,
                ft.Row([self.browser_cookies_dropdown], spacing=10),
                ft.Row([self.cookies_path_field, cookies_browse_btn], spacing=10),
                ft.Text("Or login directly via embedded browser:", color=AppTheme.TEXT_SECONDARY, size=13),
                ft.Row([login_yt_btn, login_insta_btn, login_fb_btn, login_x_btn], spacing=10, wrap=True),
            ],
        )

        # ── Theme ──
        self.theme_dropdown = ft.Dropdown(
            label="Theme",
            width=200,
            value=self.settings.get('theme'),
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=10,
            on_select=self._on_theme_change,
            options=[
                ft.dropdown.Option(key="dark", text="Dark"),
                ft.dropdown.Option(key="light", text="Light"),
            ],
        )

        self.accent_dropdown = ft.Dropdown(
            label="Accent Color",
            width=200,
            value=self.settings.get('accent_color', 'Indigo'),
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=10,
            on_select=self._on_theme_change,
            options=[
                ft.dropdown.Option(key="Indigo", text="Indigo"),
                ft.dropdown.Option(key="Emerald", text="Emerald"),
                ft.dropdown.Option(key="Rose", text="Rose"),
                ft.dropdown.Option(key="Amber", text="Amber"),
                ft.dropdown.Option(key="Violet", text="Violet"),
                ft.dropdown.Option(key="Sky", text="Sky"),
            ],
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
            min=0.0, max=1.0, divisions=20,
            value=self.settings.get('bg_image_opacity', 0.1),
            label="{value}",
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
            ft.Row([self.theme_dropdown, self.accent_dropdown], spacing=20),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            bg_overlay_controls
        ])

        # Bind auto-save to controls
        auto_save_controls_change = [
            self.format_dropdown, self.max_concurrent_dropdown,
            self.playlist_folder_switch, self.audio_codec_dropdown,
            self.audio_quality_dropdown, self.ask_on_close_switch,
            self.embed_thumbnail_switch, self.embed_metadata_switch,
            self.embed_subs_switch, self.browser_cookies_dropdown
        ]
        for control in auto_save_controls_change:
            if isinstance(control, ft.Dropdown):
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

        tab_bar = ft.TabBar(
            tabs=[
                ft.Tab(label="Appearance", icon=ft.Icons.PALETTE_ROUNDED),
                ft.Tab(label="Download", icon=ft.Icons.DOWNLOAD_ROUNDED),
                ft.Tab(label="Playlist & Queue", icon=ft.Icons.QUEUE_MUSIC_ROUNDED),
                ft.Tab(label="Audio", icon=ft.Icons.MUSIC_NOTE_ROUNDED),
                ft.Tab(label="Advanced", icon=ft.Icons.TUNE_ROUNDED),
            ],
            scrollable=True,
        )

        tab_view = ft.TabBarView(
            controls=[
                theme_section,
                download_section,
                playlist_section,
                audio_section,
                advanced_section,
            ],
            expand=True
        )

        tabs_controller = ft.Tabs(
            length=5,
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
        return ft.Container(
            content=ft.Column(
                children,
                spacing=15,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
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

    def _show_templates_info(self, e):
        templates = [
            ("%(title)s.%(ext)s", "Default (Title Only)"),
            ("%(uploader)s - %(title)s.%(ext)s", "Channel Name - Title"),
            ("%(title)s [%(id)s].%(ext)s", "Title with Video ID"),
            ("%(upload_date)s - %(title)s.%(ext)s", "Date - Title"),
        ]
        self._show_templates_dialog(templates, "Filename Templates", self.filename_field)

    def _show_playlist_templates_info(self, e):
        templates = [
            ("%(playlist_index)s - %(title)s.%(ext)s", "Default (Index - Title)"),
            ("%(playlist_index)03d - %(title)s.%(ext)s", "Padded Index (001 - Title)"),
            ("%(playlist)s - %(playlist_index)s - %(title)s.%(ext)s", "Playlist - Index - Title"),
            ("%(uploader)s - %(playlist_index)s - %(title)s.%(ext)s", "Channel - Index - Title"),
            ("%(playlist_index)s. %(title)s.%(ext)s", "1. Title"),
        ]
        self._show_templates_dialog(templates, "Playlist Templates", self.playlist_filename_field)

    def _show_templates_dialog(self, templates, title_str, target_field):
        def apply_template(tmpl):
            target_field.value = tmpl
            self.update()
            
            if getattr(self, 'snack_bar', None) in self._page.overlay:
                self._page.overlay.remove(self.snack_bar)
                
            self.snack_bar = ft.SnackBar(
                content=ft.Text(f"Applied format: {tmpl}", color=AppTheme.TEXT_PRIMARY),
                bgcolor=AppTheme.SUCCESS,
                duration=2000
            )
            self._page.overlay.append(self.snack_bar)
            self.snack_bar.open = True
            self._close_dialog(dlg)

        content = ft.Column([
            ft.ListTile(
                title=ft.Text(t[1], color=AppTheme.TEXT_PRIMARY, weight=ft.FontWeight.W_600),
                subtitle=ft.Text(t[0], color=AppTheme.TEXT_SECONDARY),
                trailing=ft.IconButton(
                    ft.Icons.CHECK_CIRCLE_ROUNDED, 
                    icon_color=AppTheme.PRIMARY,
                    tooltip="Apply", 
                    on_click=lambda e, tmpl=t[0]: apply_template(tmpl)
                )
            ) for t in templates
        ], tight=True, spacing=0)
        
        dlg = ft.AlertDialog(
            title=ft.Text(title_str, color=AppTheme.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            content=content,
            bgcolor=AppTheme.SURFACE,
            shape=ft.RoundedRectangleBorder(radius=10),
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
        self.settings.set('embed_subtitles', self.embed_subs_switch.value)
        self.settings.set('auto_subtitle_lang', self.sub_lang_field.value.strip() or 'en')
        self.settings.set('browser_cookies', self.browser_cookies_dropdown.value)
        self.settings.set('cookies_path', self.cookies_path_field.value)
        
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
        self.embed_subs_switch.value = self.settings.get('embed_subtitles')
        self.sub_lang_field.value = self.settings.get('auto_subtitle_lang')
        self.browser_cookies_dropdown.value = self.settings.get('browser_cookies')
        self.cookies_path_field.value = self.settings.get('cookies_path')
        self.theme_dropdown.value = self.settings.get('theme')
        self.accent_dropdown.value = self.settings.get('accent_color', 'Indigo')
        try:
            self.update()
        except:
            pass

    def _reset_defaults(self, e):
        self.settings.reset()
        self.sync_from_settings()
        self._page.update()

    def _on_theme_change(self, e):
        """Apply theme instantly when the dropdown changes."""
        new_theme = self.theme_dropdown.value
        new_accent = self.accent_dropdown.value
        new_bg = self.bg_image_path
        new_opacity = self.bg_opacity_slider.value
        
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
        # Update the container's own background color
        self.bgcolor = ft.Colors.TRANSPARENT
        # Rebuild the settings UI with new colors
        self._build_ui()
        self.update()
        self._page.update()
        
        if self.on_theme_changed:
            self.on_theme_changed()

    def _close(self, e):
        if self._on_close:
            self._on_close()
