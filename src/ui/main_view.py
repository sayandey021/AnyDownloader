import flet as ft
from src.ui.theme import AppTheme
from src.backend.downloader import DownloaderBackend
from src.backend.settings import SettingsManager
from src.backend.history import HistoryManager
from src.backend.search_history import SearchHistoryManager
from src.ui.settings_view import SettingsView
from src.ui.download_card import DownloadCard
from src.ui.fetch_dialog import FetchDialog

class MainView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self._page = page
        self.expand = True
        self.bgcolor = AppTheme.BACKGROUND
        if AppTheme.BG_IMAGE:
            self.image = ft.DecorationImage(
                src=AppTheme.BG_IMAGE,
                fit=ft.BoxFit.COVER,
                opacity=AppTheme.BG_OPACITY
            )
        self.padding = 0  # Changed to 0 so sidebar touches edge
        
        self.backend = DownloaderBackend(run_thread=self._page.run_thread)
        self.settings = SettingsManager()
        self.history_manager = HistoryManager()
        self.search_history_manager = SearchHistoryManager()
        
        self.all_downloads = []
        self.downloads_list_container = ft.Container(expand=True)
        self.current_mode = "search"
        self.setup_ui()
        self.load_history()

    def load_history(self):
        items = self.history_manager.get_all()
        for item in items:
            state = item.get('download_state', 'active')
            if state == 'active':
                state = 'paused'  # Don't auto-start on load
                
            card = DownloadCard(
                page=self._page,
                info=item.get('info', {}),
                backend=self.backend,
                format_id=item.get('format_id'),
                is_audio=item.get('is_audio', False),
                output_path=item.get('output_path'),
                settings=self.settings,
                video_ext=item.get('video_ext'),
                audio_codec=item.get('audio_codec'),
                audio_quality=item.get('audio_quality'),
                embed_thumbnail=item.get('embed_thumbnail'),
                embed_subtitles=item.get('embed_subtitles'),
                subtitle_lang=item.get('subtitle_lang'),
                custom_filename=item.get('custom_filename'),
                is_image=item.get('is_image', False),
                image_ext=item.get('image_ext'),
                on_state_change=self.on_card_state_change,
                restored_task_id=item.get('task_id'),
                restored_state=state,
                final_filepath=item.get('final_filepath'),
                on_redownload=self.open_fetch_dialog,
                restored_log_text=item.get('log_text', ""),
                source_mode=item.get('source_mode', 'audio' if item.get('is_audio') else 'video')
            )
            self.all_downloads.append(card)
        self.refresh_downloads_list()

    def setup_ui(self):
        # Navigation Sidebar
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=90,
            bgcolor=AppTheme.SURFACE,
            group_alignment=-0.85,
            leading=ft.Column([
                ft.Container(height=10),
                ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, color=AppTheme.PRIMARY, size=32),
                ft.Text("Any\nDownloader", size=14, weight=ft.FontWeight.BOLD, color=AppTheme.PRIMARY, text_align=ft.TextAlign.CENTER),
                ft.Container(height=20),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.SEARCH_OUTLINED, 
                    selected_icon=ft.Icons.SEARCH, 
                    label="Search"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.HISTORY_OUTLINED, 
                    selected_icon=ft.Icons.HISTORY, 
                    label="History"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.DOWNLOAD_OUTLINED, 
                    selected_icon=ft.Icons.DOWNLOAD, 
                    label="Downloads"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED, 
                    selected_icon=ft.Icons.SETTINGS, 
                    label="Settings"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.INFO_OUTLINE, 
                    selected_icon=ft.Icons.INFO, 
                    label="About"
                ),
            ],
            on_change=self.on_nav_change,
        )

        # Header
        self.header_text = ft.Text("Media Downloader", size=28, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT_PRIMARY)
        self.clear_all_btn = ft.TextButton(
            "Clear History",
            icon=ft.Icons.DELETE_SWEEP_ROUNDED,
            style=ft.ButtonStyle(color=AppTheme.ERROR),
            visible=False,
            on_click=self.clear_all_history
        )
        header = ft.Row([
            self.header_text,
            ft.Container(expand=True),
            self.clear_all_btn,
        ], alignment=ft.MainAxisAlignment.START)

        # URL Input
        self.url_input = ft.TextField(
            hint_text="Paste YouTube, Spotify, Instagram, or any link here...",
            expand=True,
            border_color=ft.Colors.TRANSPARENT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.SURFACE,
            border_radius=12,
            prefix_icon=ft.Icons.LINK_ROUNDED,
            text_size=16,
            content_padding=20,
            on_submit=self.fetch_info
        )
        
        self.fetch_btn = ft.ElevatedButton(
            "Search",
            icon=ft.Icons.SEARCH_ROUNDED,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=AppTheme.PRIMARY,
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding(left=24, right=24, top=18, bottom=18),
            ),
            on_click=self.fetch_info
        )
        
        self.loading_ring = ft.ProgressRing(color=AppTheme.PRIMARY, width=20, height=20, visible=False)
        self.input_row = ft.Row([self.url_input, self.loading_ring, self.fetch_btn], spacing=15, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        def create_toolbar_btn(btn_text, icon, color, on_click):
            return ft.ElevatedButton(
                btn_text,
                icon=icon,
                on_click=on_click,
                style=ft.ButtonStyle(
                    color={ft.ControlState.DEFAULT: color, ft.ControlState.HOVERED: ft.Colors.WHITE},
                    bgcolor={ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT, ft.ControlState.HOVERED: color},
                    shape=ft.RoundedRectangleBorder(radius=8),
                    elevation=0,
                    padding=ft.padding.Padding(left=16, right=16, top=15, bottom=15),
                )
            )

        self.pause_all_btn = create_toolbar_btn("Pause", ft.Icons.PAUSE_CIRCLE_OUTLINED, AppTheme.ACCENT, self.pause_all_downloads)
        self.resume_all_btn = create_toolbar_btn("Resume", ft.Icons.PLAY_CIRCLE_OUTLINED, AppTheme.SUCCESS, self.resume_all_downloads)
        self.stop_all_btn = create_toolbar_btn("Stop", ft.Icons.STOP_CIRCLE_OUTLINED, AppTheme.ERROR, self.stop_all_downloads)
        self.open_folder_btn = create_toolbar_btn("Folder", ft.Icons.FOLDER_OPEN_ROUNDED, AppTheme.TEXT_SECONDARY, self.open_global_download_folder)
        
        self.filter_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("All"),
                ft.dropdown.Option("Active"),
                ft.dropdown.Option("Paused"),
                ft.dropdown.Option("Queued"),
                ft.dropdown.Option("Completed"),
                ft.dropdown.Option("Stopped"),
                ft.dropdown.Option("Error"),
            ],
            value="All",
            width=150,
            text_size=14,
            border_color=AppTheme.SURFACE_VARIANT,
            bgcolor=AppTheme.SURFACE,
            color=AppTheme.TEXT_PRIMARY,
            on_select=self.on_filter_change,
            border_radius=8,
            content_padding=ft.padding.Padding(left=15, right=15, top=5, bottom=5),
        )
        
        self.history_toolbar = ft.Container(
            content=ft.Row([
                self.filter_dropdown,
                ft.Container(expand=True),
                self.pause_all_btn,
                self.resume_all_btn,
                self.stop_all_btn,
                self.open_folder_btn
            ], spacing=10),
            padding=10,
            bgcolor=ft.Colors.TRANSPARENT,
            border_radius=10,
            visible=False
        )

        # Main Layout Content Area
        
        # Search View
        search_icon = ft.Icon(ft.Icons.CLOUD_DOWNLOAD_OUTLINED, size=64, color=AppTheme.PRIMARY)
        search_title = ft.Text("Download Anything", size=42, weight=ft.FontWeight.W_900, color=AppTheme.TEXT_PRIMARY, text_align=ft.TextAlign.CENTER)
        search_subtitle = ft.Text("Paste a link below to instantly download video or audio in high quality.", size=16, color=AppTheme.TEXT_SECONDARY, text_align=ft.TextAlign.CENTER)
        
        # Supported platforms chips
        def platform_chip(text, icon, on_click=None):
            return ft.Container(
                content=ft.Row([ft.Icon(icon, size=16, color=AppTheme.TEXT_SECONDARY), ft.Text(text, size=13, color=AppTheme.TEXT_SECONDARY)], spacing=4),
                padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                bgcolor=AppTheme.SURFACE,
                border_radius=20,
                on_click=on_click,
                tooltip="Show all supported sites" if text == "More..." else None,
            )

        def _show_supported_sites(e):
            supported_list = [
                ("YouTube", ft.Icons.SMART_DISPLAY_ROUNDED, ft.Colors.RED),
                ("YT Music", ft.Icons.PLAY_CIRCLE_ROUNDED, ft.Colors.RED_600),
                ("Spotify", ft.Icons.LIBRARY_MUSIC_ROUNDED, ft.Colors.GREEN),
                ("Apple Music", ft.Icons.APPLE, ft.Colors.RED_ACCENT),
                ("Instagram", ft.Icons.CAMERA_ALT_ROUNDED, ft.Colors.PINK),
                ("Twitter / X", ft.Icons.ALTERNATE_EMAIL_ROUNDED, ft.Colors.BLUE),
                ("Facebook", ft.Icons.FACEBOOK_ROUNDED, ft.Colors.BLUE_700),
                ("TikTok", ft.Icons.MUSIC_NOTE_ROUNDED, ft.Colors.BLACK87),
                ("SoundCloud", ft.Icons.CLOUD_ROUNDED, ft.Colors.ORANGE),
                ("Twitch", ft.Icons.LIVE_TV_ROUNDED, ft.Colors.PURPLE),
                ("Vimeo", ft.Icons.ONDEMAND_VIDEO_ROUNDED, ft.Colors.BLUE_400),
                ("Reddit", ft.Icons.FORUM_ROUNDED, ft.Colors.ORANGE_900),
                ("Tidal", ft.Icons.WAVES_ROUNDED, ft.Colors.CYAN),
                ("Deezer", ft.Icons.EQUALIZER_ROUNDED, ft.Colors.PURPLE_ACCENT),
                ("JioSaavn", ft.Icons.LIBRARY_MUSIC_ROUNDED, ft.Colors.GREEN_600),
                ("Gaana", ft.Icons.MUSIC_NOTE_ROUNDED, ft.Colors.RED_400),
                ("Last.fm", ft.Icons.RADIO_ROUNDED, ft.Colors.RED_600),
                ("Pinterest", ft.Icons.PIN_DROP_ROUNDED, ft.Colors.RED_800),
                ("LinkedIn", ft.Icons.WORK_ROUNDED, ft.Colors.BLUE_800),
                ("Bandcamp", ft.Icons.ALBUM_ROUNDED, ft.Colors.TEAL),
                ("Dailymotion", ft.Icons.VIDEO_LIBRARY_ROUNDED, ft.Colors.BLUE_600),
                ("Tumblr", ft.Icons.ARTICLE_ROUNDED, ft.Colors.INDIGO_400),
                ("Rumble", ft.Icons.PLAY_ARROW_ROUNDED, ft.Colors.GREEN_400),
                ("Bilibili", ft.Icons.TV_ROUNDED, ft.Colors.LIGHT_BLUE),
                ("Snapchat", ft.Icons.CHAT_BUBBLE_ROUNDED, ft.Colors.YELLOW_700),
                ("VK", ft.Icons.GROUPS_ROUNDED, ft.Colors.BLUE_ACCENT),
                ("Mixcloud", ft.Icons.CLOUD_CIRCLE_ROUNDED, ft.Colors.BLUE_200),
                ("Audiomack", ft.Icons.HEADSET_ROUNDED, ft.Colors.ORANGE_600),
            ]
            
            grid = ft.GridView(
                expand=True,
                runs_count=4,
                max_extent=150,
                child_aspect_ratio=1.0,
                spacing=10,
                run_spacing=10,
                padding=ft.Padding(left=0, top=0, right=15, bottom=0),
            )
            
            for site, icon, color in supported_list:
                grid.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(icon, size=40, color=color),
                            ft.Text(site, weight=ft.FontWeight.W_600, color=AppTheme.TEXT_PRIMARY, text_align=ft.TextAlign.CENTER)
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor=AppTheme.SURFACE_VARIANT,
                        border_radius=10,
                        padding=10
                    )
                )
            
            def close_dlg(e):
                dlg.open = False
                self._page.update()
                
            dlg = ft.AlertDialog(
                title=ft.Row([ft.Icon(ft.Icons.PUBLIC_ROUNDED, color=AppTheme.PRIMARY), ft.Text("Supported Sites", weight=ft.FontWeight.BOLD, color=AppTheme.TEXT_PRIMARY)]),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Any Downloader natively supports fetching from 1000+ websites. Here are some popular ones:", color=AppTheme.TEXT_SECONDARY),
                        ft.Container(content=grid, height=350, width=500),
                        ft.TextButton(
                            "View all 1000+ supported sites", 
                            icon=ft.Icons.OPEN_IN_NEW_ROUNDED,
                            url="https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md"
                        )
                    ], tight=True, spacing=15),
                    width=500,
                ),
                bgcolor=AppTheme.SURFACE,
                shape=ft.RoundedRectangleBorder(radius=10),
                actions=[
                    ft.TextButton("Close", on_click=close_dlg)
                ],
            )
            self._page.overlay.append(dlg)
            dlg.open = True
            self._page.update()
            
        platforms_row = ft.Row([
            platform_chip("YouTube", ft.Icons.SMART_DISPLAY_ROUNDED),
            platform_chip("Spotify", ft.Icons.AUDIOTRACK_OUTLINED),
            platform_chip("Instagram", ft.Icons.CAMERA_ALT_OUTLINED),
            platform_chip("Twitter", ft.Icons.CHAT_BUBBLE_OUTLINE),
            platform_chip("More...", ft.Icons.MORE_HORIZ, on_click=_show_supported_sites),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)
        
        # Create a container around the input row to constrain its width
        search_box_container = ft.Container(
            content=self.input_row,
            width=700,
            padding=ft.Padding(left=0, right=0, top=10, bottom=10)
        )
        
        self.search_view = ft.Column([
            ft.Container(expand=True),  # Spacer
            ft.Column([
                search_icon,
                ft.Container(height=10),
                search_title,
                search_subtitle,
                ft.Container(height=30),
                search_box_container,
                ft.Container(height=20),
                platforms_row
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(expand=True)   # Spacer
        ], expand=True)

        # Search History View
        self.clear_search_history_btn = ft.TextButton(
            "Clear All",
            icon=ft.Icons.DELETE_SWEEP_ROUNDED,
            style=ft.ButtonStyle(color=AppTheme.ERROR),
            on_click=self.clear_all_search_history
        )
        self.search_history_list = ft.ListView(expand=True, spacing=10)
        self.search_history_view = ft.Column([
            ft.Row([
                ft.Text("Search History", size=28, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT_PRIMARY),
                ft.Container(expand=True),
                self.clear_search_history_btn
            ], alignment=ft.MainAxisAlignment.START),
            ft.Divider(height=20, color=AppTheme.SURFACE_VARIANT),
            self.search_history_list
        ], expand=True)

        # Downloads View
        self.history_view = ft.Column([
            header,
            self.history_toolbar,
            ft.Divider(height=20, color=AppTheme.SURFACE_VARIANT),
            self.downloads_list_container
        ], expand=True)

        self.main_area = ft.Container(
            content=self.search_view,
            expand=True,
            padding=30
        )

        # Combine sidebar and main area
        self.content = ft.Row([
            self.nav_rail,
            ft.VerticalDivider(width=1, color=AppTheme.SURFACE_VARIANT),
            self.main_area
        ], expand=True, spacing=0)

        self.snack_bar = ft.SnackBar(
            content=ft.Text("", color=AppTheme.TEXT_PRIMARY),
            bgcolor=AppTheme.PRIMARY,
            duration=3000
        )
        self._page.overlay.append(self.snack_bar)

        self.fetch_cancel_btn = ft.TextButton("Cancel", on_click=self.cancel_fetch, style=ft.ButtonStyle(color=AppTheme.TEXT_SECONDARY))
        self.fetching_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Fetching Metadata", color=AppTheme.TEXT_PRIMARY, size=18, weight=ft.FontWeight.BOLD),
            content=ft.Row([
                ft.ProgressRing(width=20, height=20, color=AppTheme.PRIMARY),
                ft.Text(" Please wait...", color=AppTheme.TEXT_SECONDARY)
            ], spacing=20),
            actions=[self.fetch_cancel_btn],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=AppTheme.SURFACE,
            shape=ft.RoundedRectangleBorder(radius=10)
        )

    def cancel_fetch(self, e):
        self._cancel_fetch = True
        self.set_loading(False)
        self._page.update()
        self.show_snack("Fetching cancelled.", ft.Colors.ORANGE)

    def clear_all_history(self, e):
        def on_confirm(e):
            dlg.open = False
            self._page.update()
            
            for card in list(self.all_downloads):
                if card.download_state not in ("active", "paused"):
                    card.is_deleted = True
                    if card.task_id:
                        self.history_manager.remove(card.task_id)
            self.refresh_downloads_list()
            self.show_snack("History cleared", AppTheme.SUCCESS)
            
        def on_cancel(e):
            dlg.open = False
            self._page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Clear History", color=AppTheme.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            content=ft.Text("Are you sure you want to clear all history? Active downloads will not be affected.", color=AppTheme.TEXT_SECONDARY),
            bgcolor=AppTheme.SURFACE,
            shape=ft.RoundedRectangleBorder(radius=10),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel, style=ft.ButtonStyle(color=AppTheme.TEXT_SECONDARY)),
                ft.TextButton("Clear", style=ft.ButtonStyle(color=AppTheme.ERROR), on_click=on_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dlg)
        dlg.open = True
        self._page.update()

    def clear_all_search_history(self, e):
        def on_confirm(e):
            dlg.open = False
            self._page.update()
            
            self.search_history_manager.clear_all()
            self.refresh_search_history()
            self.show_snack("Search history cleared", AppTheme.SUCCESS)
            
        def on_cancel(e):
            dlg.open = False
            self._page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Clear Search History", color=AppTheme.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            content=ft.Text("Are you sure you want to clear all your search history?", color=AppTheme.TEXT_SECONDARY),
            bgcolor=AppTheme.SURFACE,
            shape=ft.RoundedRectangleBorder(radius=10),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel, style=ft.ButtonStyle(color=AppTheme.TEXT_SECONDARY)),
                ft.TextButton("Clear", style=ft.ButtonStyle(color=AppTheme.ERROR), on_click=on_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dlg)
        dlg.open = True
        self._page.update()

    def on_nav_change(self, e):
        idx = e.control.selected_index
        if idx == 0:
            self.current_mode = "search"
            self.header_text.value = "Search"
            self.url_input.label = "Media or Playlist URL"
            self.url_input.hint_text = "Paste YouTube, Spotify, Instagram, or other supported URL here"
            self.input_row.visible = True
            self.history_toolbar.visible = False
            self.clear_all_btn.visible = False
            self.main_area.content = self.search_view
        elif idx == 1:
            self.current_mode = "search_history"
            self.refresh_search_history()
            self.main_area.content = self.search_history_view
        elif idx == 2:
            self.current_mode = "downloads"
            self.header_text.value = "Downloads"
            self.input_row.visible = False
            self.history_toolbar.visible = True
            self.clear_all_btn.visible = True
            self.main_area.content = self.history_view
        elif idx == 3:
            self.current_mode = "settings"
            self.header_text.value = "Settings"
            if not hasattr(self, 'settings_view'):
                self.settings_view = SettingsView(self._page, show_back_button=False, on_theme_changed=self.rebuild_app)
            self.settings_view.sync_from_settings()
            self.main_area.content = self.settings_view
            self.input_row.visible = False
            self.clear_all_btn.visible = False
            self.history_toolbar.visible = False
        elif idx == 4:
            self.current_mode = "about"
            self.header_text.value = "About Any Downloader"
            if not hasattr(self, 'about_view'):
                from src.ui.about_view import AboutView
                self.about_view = AboutView(self._page)
            self.main_area.content = self.about_view
            self.input_row.visible = False
            self.clear_all_btn.visible = False
            self.history_toolbar.visible = False
            
        self.refresh_downloads_list()
        self.safe_update()

    def rebuild_app(self, show_notification=True):
        # Hot-swap the entire MainView on the page to instantly apply the new theme globally
        self._page.controls.clear()
        
        # Create a completely new instance of MainView which will evaluate the newly updated AppTheme colors
        new_view = MainView(self._page)
        
        # Restore the user's position back to the Settings tab visually
        new_view.nav_rail.selected_index = 3
        
        class DummyEvent:
            class DummyControl:
                def __init__(self):
                    self.selected_index = 3
            def __init__(self):
                self.control = self.DummyControl()
                
        new_view.on_nav_change(DummyEvent())
        
        self._page.add(new_view)
        if show_notification:
            new_view.show_snack("Theme applied!", AppTheme.SUCCESS)

    def safe_update(self):
        try:
            _ = self.page
            self.update()
            self._page.update()
        except RuntimeError:
            pass

    def fetch_info(self, e):
        url = self.url_input.value.strip()
        if not url:
            self.show_snack("Please enter a valid URL", AppTheme.ERROR)
            return

        self._cancel_fetch = False
        self.set_loading(True)
        self.url_input.value = ""
        self.update()
        self._page.update()

        self._page.run_thread(self._fetch_thread, url)

    def _fetch_thread(self, url):
        try:
            info = self.backend.get_video_info(url, getattr(self, 'settings', None))
            
            # If the user clicked Cancel, simply ignore the result
            if getattr(self, '_cancel_fetch', False):
                return

            self.set_loading(False)
            import time
            time.sleep(0.1) # Allow the fetching dialog to close properly
            
            if info:
                title = info.get('title') or info.get('fulltitle') or 'Unknown Title'
                thumb_url = info.get('thumbnail')
                if not thumb_url and info.get('thumbnails'):
                    thumb_url = info['thumbnails'][0]['url']
                
                # Fallback for playlists without a top-level thumbnail
                if not thumb_url and info.get('entries'):
                    entries = info.get('entries', [])
                    if entries:
                        first = entries[0]
                        thumb_url = first.get('thumbnail') or (first.get('thumbnails', [{}])[0].get('url', '') if first.get('thumbnails') else '')

                self.search_history_manager.add_search(url, title, thumb_url)

                self.show_snack("Video info fetched!", AppTheme.SUCCESS)
                self.open_fetch_dialog(info)
            else:
                self.show_snack("Failed to fetch info.", AppTheme.ERROR)
                
            self.safe_update()
        except Exception as e:
            if getattr(self, '_cancel_fetch', False):
                return
            import traceback
            print(f"[ERROR] Fetching video info failed: {url}")
            traceback.print_exc()
            self.set_loading(False)
            self.show_snack(f"Error processing video info: {str(e)}", AppTheme.ERROR)
            self.safe_update()

    def open_fetch_dialog(self, info):
        self._current_dialog = FetchDialog(
            self._page, 
            info, 
            self.settings, 
            on_download=self.add_download,
            on_close=self.clear_dialog,
            audio_only_mode=False
        )
        self._page.show_dialog(self._current_dialog)

    def refresh_search_history(self):
        items = self.search_history_manager.get_all()
        self.search_history_list.controls.clear()
        
        if not items:
            self.clear_search_history_btn.visible = False
            self.search_history_list.controls.append(
                ft.Container(
                    content=ft.Text("No search history yet.", color=AppTheme.TEXT_SECONDARY, text_align=ft.TextAlign.CENTER),
                    padding=40,
                    alignment=ft.Alignment(0, 0)
                )
            )
        else:
            self.clear_search_history_btn.visible = True
            for item in items:
                url = item['url']
                title = item.get('title', url)
                thumb = item.get('thumbnail')
                
                def create_click_handler(u):
                    def handler(e):
                        self.url_input.value = u
                        self.nav_rail.selected_index = 0
                        class DummyControl:
                            def __init__(self):
                                self.selected_index = 0
                        class DummyEvent:
                            def __init__(self):
                                self.control = DummyControl()
                        self.on_nav_change(DummyEvent())
                        self.fetch_info(None)
                    return handler
                    
                def create_delete_handler(u):
                    def handler(e):
                        self.search_history_manager.remove_search(u)
                        self.refresh_search_history()
                    return handler
                
                tile = ft.Container(
                    content=ft.Row([
                        ft.Image(src=thumb, width=80, height=45, fit=ft.BoxFit.COVER, border_radius=4) if thumb else ft.Container(content=ft.Icon(ft.Icons.LINK, size=24, color=AppTheme.TEXT_SECONDARY), width=80, height=45, bgcolor=AppTheme.SURFACE_VARIANT, border_radius=4, alignment=ft.Alignment(0, 0)),
                        ft.Column([
                            ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=AppTheme.TEXT_PRIMARY, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(url, size=12, color=AppTheme.TEXT_SECONDARY, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
                        ], expand=True, spacing=2),
                        ft.Row([
                            ft.IconButton(ft.Icons.SEARCH, icon_color=AppTheme.PRIMARY, on_click=create_click_handler(url), tooltip="Search Again"),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=AppTheme.ERROR, on_click=create_delete_handler(url), tooltip="Remove from History")
                        ], spacing=0)
                    ], spacing=15),
                    padding=10,
                    bgcolor=AppTheme.BACKGROUND,
                    border_radius=8,
                    on_click=create_click_handler(url),
                    ink=True
                )
                self.search_history_list.controls.append(tile)
        
        try:
            self.search_history_list.update()
        except Exception:
            pass

    def clear_dialog(self):
        if hasattr(self, '_current_dialog') and getattr(self._current_dialog, 'open', False):
            self._page.pop_dialog()

    def add_download(self, info, format_id, is_audio, output_path, 
                     video_ext=None, audio_codec=None, audio_quality=None,
                     embed_thumbnail=None, embed_subtitles=None, subtitle_lang=None,
                     custom_filename=None, selected_entries=None, is_image=False, image_ext=None, is_thumbnail=False):
        self.clear_dialog()
        
        # For playlists with selected entries, create a card per selected video
        if selected_entries:
            import os
            import re
            
            create_folder = self.settings.get('create_playlist_folder', True)
            playlist_title = info.get('title', 'Playlist')
            
            playlist_output_path = output_path
            if create_folder:
                safe_title = re.sub(r'[\\/*?:"<>|]', "", playlist_title)
                playlist_output_path = os.path.join(output_path, safe_title)
                
            playlist_template = self.settings.get('playlist_filename_template', '%(playlist_index)s - %(title)s.%(ext)s')
            
            for i, entry in enumerate(selected_entries, start=1):
                idx = entry.get('playlist_index')
                if idx is None:
                    idx = i
                
                # Pre-format playlist variables since yt-dlp won't know the playlist context during individual downloads
                resolved_template = playlist_template
                resolved_template = re.sub(r'%\(playlist\)s', str(playlist_title), resolved_template)
                resolved_template = re.sub(r'%\(playlist_index\)s', str(idx), resolved_template)
                resolved_template = re.sub(r'%\(playlist_index\)([0-9]+)d', lambda m: format(int(idx), m.group(1)), resolved_template)

                card = DownloadCard(
                    page=self._page,
                    info=entry,
                    backend=self.backend,
                    format_id=format_id,
                    is_audio=is_audio,
                    output_path=playlist_output_path,
                    settings=self.settings,
                    video_ext=video_ext,
                    audio_codec=audio_codec,
                    audio_quality=audio_quality,
                    embed_thumbnail=embed_thumbnail,
                    embed_subtitles=embed_subtitles,
                    subtitle_lang=subtitle_lang,
                    custom_filename=resolved_template,
                    is_image=is_image,
                    image_ext=image_ext,
                    is_thumbnail=is_thumbnail,
                    on_state_change=self.on_card_state_change,
                    on_redownload=self.open_fetch_dialog,
                    restored_state="queued",
                    source_mode=self.current_mode
                )
                self.all_downloads.insert(0, card)
        else:
            card = DownloadCard(
                page=self._page,
                info=info,
                backend=self.backend,
                format_id=format_id,
                is_audio=is_audio,
                output_path=output_path,
                settings=self.settings,
                video_ext=video_ext,
                audio_codec=audio_codec,
                audio_quality=audio_quality,
                embed_thumbnail=embed_thumbnail,
                embed_subtitles=embed_subtitles,
                subtitle_lang=subtitle_lang,
                custom_filename=custom_filename,
                is_image=is_image,
                image_ext=image_ext,
                is_thumbnail=is_thumbnail,
                on_state_change=self.on_card_state_change,
                on_redownload=self.open_fetch_dialog,
                source_mode=self.current_mode
            )
            self.all_downloads.insert(0, card)
            
        self.refresh_downloads_list()
        self.process_queue()
        
        # Navigate to Downloads tab
        if getattr(self, 'nav_rail', None):
            self.nav_rail.selected_index = 2
            class DummyControl:
                def __init__(self):
                    self.selected_index = 2
            class DummyEvent:
                def __init__(self):
                    self.control = DummyControl()
            self.on_nav_change(DummyEvent())
        
    def process_queue(self):
        max_concurrent = int(self.settings.get('max_concurrent_downloads', 3))
        
        # Count currently active downloads
        active_count = sum(1 for card in self.all_downloads if getattr(card, 'download_state', '') == 'active')
        
        # Find queued downloads
        queued_cards = [card for card in self.all_downloads if getattr(card, 'download_state', '') == 'queued']
        
        # Start queued downloads if we have capacity
        while active_count < max_concurrent and queued_cards:
            next_card = queued_cards.pop(-1)
            
            next_card.download_state = "active"
            next_card.status_text.value = "Starting..."
            next_card.update_actions()
            next_card.start_task()
            active_count += 1
            
        self.safe_update()
        
    def on_card_state_change(self, card):
        self.refresh_downloads_list()
        self.process_queue()
        
    def on_filter_change(self, e):
        print(f"[DEBUG] on_filter_change triggered with value: {e.control.value}")
        if getattr(self, 'filter_dropdown', None):
            self.filter_dropdown.value = e.control.value
        self.refresh_downloads_list(filter_val_override=e.control.value)

    def pause_all_downloads(self, e):
        for card in list(self.all_downloads):
            if card.download_state == "active":
                card.pause_download(e)

    def resume_all_downloads(self, e):
        for card in list(self.all_downloads):
            if card.download_state == "paused":
                card.resume_download(e)

    def stop_all_downloads(self, e):
        for card in list(self.all_downloads):
            if card.download_state in ("active", "paused", "queued"):
                card.stop_download(e)

    def open_global_download_folder(self, e):
        import os
        default_folder = self.settings.get('download_path', '')
        if not default_folder or not os.path.exists(default_folder):
            default_folder = os.path.join(os.path.expanduser('~'), 'Downloads')
        if os.path.exists(default_folder):
            os.startfile(default_folder)
            self.show_snack("Opening folder...", AppTheme.SUCCESS)
        else:
            self.show_snack("Default folder not found", AppTheme.ERROR)

    def refresh_downloads_list(self, filter_val_override=None):
        # Remove deleted cards safely
        to_remove = [c for c in self.all_downloads if getattr(c, 'is_deleted', False)]
        for c in to_remove:
            self.all_downloads.remove(c)
            
        # Sort so running/active downloads are at the top, followed by queued, then others.
        def get_state_priority(card):
            state = getattr(card, 'download_state', '')
            if state == 'active': return 0
            if state == 'queued': return 1
            if state == 'paused': return 2
            return 3
            
        self.all_downloads.sort(key=get_state_priority)
        
        filter_val = getattr(self, 'filter_dropdown', None)
        if filter_val_override is not None:
            f_val = filter_val_override.lower()
        else:
            f_val = filter_val.value.lower() if filter_val and filter_val.value else "all"
        
        print(f"[DEBUG] refresh_downloads_list called. current_mode={self.current_mode}, f_val={f_val}, total_cards={len(self.all_downloads)}")
        
        # Create a completely new list to bypass Flet caching
        new_list = ft.ListView(expand=True, spacing=0, item_extent=96, auto_scroll=False)
        
        visible_count = 0
        for card in self.all_downloads:
            should_show = False
            if self.current_mode == "downloads":
                if f_val == "all":
                    should_show = True
                elif f_val == "active" and card.download_state == "active":
                    should_show = True
                elif f_val == "paused" and card.download_state == "paused":
                    should_show = True
                elif f_val == "queued" and card.download_state == "queued":
                    should_show = True
                elif f_val == "completed" and card.download_state == "completed":
                    should_show = True
                elif f_val == "stopped" and card.download_state == "cancelled":
                    should_show = True
                elif f_val == "error" and card.download_state == "error":
                    should_show = True
            else:
                should_show = False
                
            if should_show:
                card.visible = True
                new_list.controls.append(card)
                visible_count += 1
                
        print(f"[DEBUG] refresh_downloads_list matched {visible_count} cards out of {len(self.all_downloads)}")
                
        self.downloads_list = new_list
        if hasattr(self, 'downloads_list_container'):
            self.downloads_list_container.content = self.downloads_list
            try:
                self.downloads_list_container.update()
            except Exception:
                pass

        self.safe_update()

    def set_loading(self, is_loading):
        self.loading_ring.visible = is_loading
        self.url_input.disabled = is_loading
        self.fetch_btn.disabled = is_loading
        if is_loading:
            self._page.show_dialog(self.fetching_dialog)
        else:
            if getattr(self.fetching_dialog, 'open', False):
                self._page.pop_dialog()
        self._page.update()

    def show_snack(self, message, color):
        if getattr(self, 'snack_bar', None) in self._page.overlay:
            self._page.overlay.remove(self.snack_bar)
            
        self.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=AppTheme.TEXT_PRIMARY),
            bgcolor=color,
            duration=3000
        )
        self._page.overlay.append(self.snack_bar)
        self.snack_bar.open = True
        self._page.update()
