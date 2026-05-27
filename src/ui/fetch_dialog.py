import flet as ft
from src.ui.theme import AppTheme
import tkinter as tk
from tkinter import filedialog
import os

class FetchDialog(ft.AlertDialog):
    def __init__(self, page: ft.Page, info: dict, settings, on_download, on_close, audio_only_mode=False):
        super().__init__()
        self._page = page
        self.info = info
        self.settings = settings
        self.on_download_callback = on_download
        self.on_close_callback = on_close
        self.audio_only_mode = audio_only_mode
        
        self.bgcolor = AppTheme.SURFACE
        self.shape = ft.RoundedRectangleBorder(radius=14)
        self.modal = True
        self.content_padding = 0
        self.title_padding = 0
        self.inset_padding = ft.Padding(left=20, right=20, top=20, bottom=20)
        
        # Force audio-only for Spotify content
        self.is_audio_platform = self.info.get('_spotify') or self.info.get('extractor_key', '').lower() in ['spotify', 'soundcloud', 'applemusic', 'deezer', 'tidal', 'gaana', 'lastfm']
        if self.is_audio_platform:
            self.audio_only_mode = True

        # Parse available video resolutions
        self.is_playlist = 'entries' in self.info and self.info.get('_type') == 'playlist'
        
        # Detect image
        self.is_image = False
        if self.is_playlist:
            if self.info.get('id') == 'gallery':
                self.is_image = True
            else:
                entries = self.info.get('entries', [])
                if entries:
                    first_formats = entries[0].get('formats', [])
                    if first_formats and all(f.get('vcodec') == 'image' for f in first_formats):
                        self.is_image = True
        else:
            formats = self.info.get('formats', [])
            if formats and all(f.get('vcodec') == 'image' for f in formats):
                self.is_image = True
                
        # Detect livestream
        self.is_live = self.info.get('is_live') or self.info.get('live_status') == 'is_live'
        
        self.available_resolutions = []
        self.playlist_checkboxes = []

        if not self.is_playlist:
            formats = self.info.get('formats', [])
            resolutions = set()
            for f in formats:
                h = f.get('height')
                vcodec = f.get('vcodec')
                if h and vcodec and vcodec != 'none':
                    resolutions.add(h)
            self.available_resolutions = sorted(list(resolutions), reverse=True)
            if not self.available_resolutions:
                self.available_resolutions = [4320, 2160, 1440, 1080, 720, 480, 360]
        else:
            self.available_resolutions = [4320, 2160, 1440, 1080, 720, 480, 360]

        # Pre-compute format size lookup
        self._format_sizes = self._build_format_size_map()

        self._build_ui()
        
        # Populate initial size calculations
        self._update_filesize()
        self._update_embed_options()

    def _build_ui(self):
        # ═══════════════════════════════════════════════════════════
        # LEFT PANEL — Thumbnail + Title + Playlist items
        # ═══════════════════════════════════════════════════════════
        left_panel = self._build_left_panel()
        
        # ═══════════════════════════════════════════════════════════
        # RIGHT PANEL — Download options
        # ═══════════════════════════════════════════════════════════
        right_panel = self._build_right_panel()

        # Vertical divider between panels
        divider = ft.Container(
            width=1,
            bgcolor=AppTheme.SURFACE_VARIANT,
        )

        # Wider dialog for playlists to fit video thumbnails
        if self.is_playlist:
            dialog_w = 920
            dialog_h = 620
        else:
            dialog_w = 780
            dialog_h = 560

        # Two-panel row layout
        self.title = None
        self.content = ft.Container(
            content=ft.Row(
                [left_panel, divider, right_panel],
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            width=dialog_w,
            height=dialog_h,
            padding=0,
        )

        self.actions = [
            ft.TextButton("Cancel", on_click=self._cancel,
                          style=ft.ButtonStyle(color=AppTheme.TEXT_SECONDARY)),
            ft.OutlinedButton(
                "Thumbnail",
                icon=ft.Icons.IMAGE_ROUNDED,
                on_click=self._download_thumbnail,
                style=ft.ButtonStyle(
                    color=AppTheme.TEXT_PRIMARY,
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.Padding(left=16, right=16, top=12, bottom=12),
                ),
            ),
            ft.ElevatedButton(
                "Record Stream" if self.is_live else "Download",
                icon=ft.Icons.FIBER_MANUAL_RECORD if self.is_live else ft.Icons.DOWNLOAD_ROUNDED,
                bgcolor=AppTheme.PRIMARY,
                color="#ffffff",
                on_click=self._start_download,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.Padding(left=24, right=24, top=12, bottom=12),
                ),
            )
        ]
        self.actions_alignment = ft.MainAxisAlignment.END

    # ──────────────────────────────────────────────────────────────
    #  LEFT PANEL
    # ──────────────────────────────────────────────────────────────
    def _build_left_panel(self):
        title_str = self.info.get('title') or self.info.get('fulltitle') or 'Unknown Title'
        uploader = self.info.get('uploader') or self.info.get('creator') or self.info.get('channel') or self.info.get('extractor_key') or 'Unknown uploader'

        # Thumbnail — aspect-ratio aware
        thumb_url = self.info.get('thumbnail')
        if not thumb_url and self.info.get('thumbnails'):
            thumb_url = self.info['thumbnails'][0]['url']
        
        # Fallback for playlists without a top-level thumbnail
        if not thumb_url and self.is_playlist:
            entries = self.info.get('entries', [])
            if entries:
                first = entries[0]
                thumb_url = first.get('thumbnail') or (first.get('thumbnails', [{}])[0].get('url', '') if first.get('thumbnails') else '')

        thumb_display_w = 280
        vid_w = self.info.get('width')
        vid_h = self.info.get('height')
        
        # Audio platforms usually have 1:1 square cover art
        is_audio_platform = self.info.get('_spotify') or self.info.get('extractor_key', '').lower() in ['spotify', 'soundcloud', 'applemusic', 'deezer', 'tidal', 'gaana', 'lastfm']

        if vid_w and vid_h and vid_w > 0 and vid_h > 0:
            aspect = vid_w / vid_h
            thumb_display_h = int(thumb_display_w / aspect)
            # Clamp height to avoid overly tall thumbnails in the panel
            thumb_display_h = min(thumb_display_h, 300)
        elif is_audio_platform:
            thumb_display_h = thumb_display_w  # 1:1 ratio
        else:
            thumb_display_h = 158  # 16:9 default

        thumb_b64 = self.info.get('thumbnail_base64')
        thumb_src = None
        if thumb_b64:
            import base64
            thumb_src = base64.b64decode(thumb_b64)
        elif thumb_url:
            thumb_src = thumb_url
        else:
            thumb_src = "https://via.placeholder.com/280x280" if is_audio_platform else "https://via.placeholder.com/280x158"
        
        thumbnail = ft.Container(
            content=ft.Image(
                src=thumb_src,
                width=thumb_display_w,
                height=thumb_display_h,
                fit=ft.BoxFit.COVER,
                border_radius=10,
                error_content=ft.Container(
                    content=ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED_ROUNDED, color=AppTheme.TEXT_SECONDARY),
                    width=thumb_display_w,
                    height=thumb_display_h,
                    bgcolor=AppTheme.SURFACE_VARIANT,
                    border_radius=10,
                    alignment=ft.Alignment(0, 0)
                )
            ),
            border_radius=10,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )

        # Title & uploader
        title_text = ft.Text(
            title_str, color=AppTheme.TEXT_PRIMARY,
            weight=ft.FontWeight.W_700, size=15,
            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
        )
        uploader_text = ft.Text(
            uploader, color=AppTheme.TEXT_SECONDARY, size=12,
        )

        # Duration / channel info row
        duration = self.info.get('duration')
        duration_str = ""
        if duration:
            mins, secs = divmod(int(duration), 60)
            hrs, mins = divmod(mins, 60)
            duration_str = f"{hrs}:{mins:02d}:{secs:02d}" if hrs else f"{mins}:{secs:02d}"

        info_chips = []
        if self.is_live:
            info_chips.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CIRCLE, color="#ef4444", size=8),
                        ft.Text("LIVE", size=11, color=AppTheme.TEXT_PRIMARY, weight=ft.FontWeight.W_800)
                    ], spacing=4, alignment=ft.MainAxisAlignment.CENTER),
                    bgcolor=AppTheme.SURFACE_VARIANT,
                    padding=ft.Padding(left=8, right=8, top=3, bottom=3),
                    border_radius=4,
                )
            )
        elif duration_str:
            info_chips.append(
                ft.Container(
                    content=ft.Text(duration_str, size=11, color=AppTheme.TEXT_PRIMARY, weight=ft.FontWeight.W_600),
                    bgcolor=AppTheme.SURFACE_VARIANT,
                    padding=ft.Padding(left=8, right=8, top=3, bottom=3),
                    border_radius=4,
                )
            )
        
        view_count = self.info.get('view_count') or self.info.get('concurrent_view_count')
        if view_count:
            if view_count >= 1_000_000:
                views_str = f"{view_count / 1_000_000:.1f}M views"
            elif view_count >= 1_000:
                views_str = f"{view_count / 1_000:.1f}K views"
            else:
                views_str = f"{view_count} views"
            info_chips.append(
                ft.Text(views_str, size=11, color=AppTheme.TEXT_SECONDARY)
            )

        # Approximate file size chip
        self.filesize_text = ft.Text("", size=11, color=AppTheme.ACCENT, weight=ft.FontWeight.W_600)
        approx_size = self._get_approx_size(is_audio=self.audio_only_mode, quality="best")
        if approx_size:
            self.filesize_text.value = f"~{approx_size}"
            
        # Always append so it can become visible later if it changes
        self.filesize_container = ft.Container(
            content=self.filesize_text,
            bgcolor=AppTheme.SURFACE_VARIANT,
            padding=ft.Padding(left=8, right=8, top=3, bottom=3),
            border_radius=4,
            visible=bool(approx_size)
        )
        info_chips.append(self.filesize_container)

        info_row = ft.Row(info_chips, spacing=8, wrap=True) if info_chips else ft.Container()

        # ── PLAYLIST LAYOUT ──
        if self.is_playlist:
            entries = self.info.get('entries', [])
            count = len(entries)

            # Playlist header: thumbnail + info side by side
            header_info = ft.Column([
                title_text,
                uploader_text,
                ft.Container(height=4),
                ft.Container(
                    content=ft.Text(
                        f"📋 {count} tracks" if self.audio_only_mode else f"📋 {count} videos",
                        color=AppTheme.ACCENT, size=13, weight=ft.FontWeight.BOLD,
                    ),
                ),
                info_row,
            ], spacing=4, expand=True)

            # Smaller playlist thumbnail for the header
            ph_w = 120 if is_audio_platform else 160
            ph_h = 120 if is_audio_platform else 90
            ph_placeholder = f"https://via.placeholder.com/{ph_w}x{ph_h}"

            playlist_header = ft.Row(
                [
                    ft.Container(
                        content=ft.Image(
                            src=thumb_url if thumb_url else ph_placeholder,
                            width=ph_w, height=ph_h,
                            fit=ft.BoxFit.COVER, border_radius=8,
                            error_content=ft.Container(
                                content=ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED_ROUNDED, color=AppTheme.TEXT_SECONDARY),
                                width=ph_w, height=ph_h,
                                bgcolor=AppTheme.SURFACE_VARIANT,
                                border_radius=8,
                                alignment=ft.Alignment(0, 0)
                            )
                        ),
                        border_radius=8,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                    header_info,
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )

            # Select All / Select None buttons
            self._all_selected = True
            select_all_btn = ft.OutlinedButton(
                "Select All",
                icon=ft.Icons.SELECT_ALL_ROUNDED,
                on_click=self._select_all,
                style=ft.ButtonStyle(
                    color=AppTheme.ACCENT,
                    side=ft.BorderSide(1, AppTheme.SURFACE_VARIANT),
                    shape=ft.RoundedRectangleBorder(radius=6),
                    padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                ),
            )
            select_none_btn = ft.OutlinedButton(
                "Select None",
                icon=ft.Icons.DESELECT_ROUNDED,
                on_click=self._select_none,
                style=ft.ButtonStyle(
                    color=AppTheme.TEXT_SECONDARY,
                    side=ft.BorderSide(1, AppTheme.SURFACE_VARIANT),
                    shape=ft.RoundedRectangleBorder(radius=6),
                    padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                ),
            )

            self.selection_count_text = ft.Text(
                f"{count}/{count} selected",
                color=AppTheme.TEXT_SECONDARY, size=11,
            )

            selection_bar = ft.Row(
                [select_all_btn, select_none_btn, ft.Container(expand=True), self.selection_count_text],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

            # Build video list with thumbnails
            self.playlist_checkboxes = []
            playlist_items_col = []
            for i, entry in enumerate(entries):
                item_title = entry.get('title', f'Track {i + 1}' if self.audio_only_mode else f'Video {i + 1}')

                # Get video thumbnail
                item_thumb_url = entry.get('thumbnail') or entry.get('thumbnails', [{}])[0].get('url', '') if entry.get('thumbnails') else entry.get('thumbnail', '')

                # Duration
                item_dur = entry.get('duration')
                item_dur_str = ""
                if item_dur:
                    m, s = divmod(int(item_dur), 60)
                    h, m = divmod(m, 60)
                    item_dur_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

                cb = ft.Checkbox(
                    value=True,
                    active_color=AppTheme.PRIMARY,
                    check_color="#ffffff",
                    on_change=self._on_playlist_item_toggle,
                )

                # Dedicated text element for size + duration
                size_dur_text = ft.Text(
                    item_dur_str if item_dur_str else "",
                    size=10, color=AppTheme.TEXT_SECONDARY,
                )
                
                # Keep a reference to the size text in the tuple
                self.playlist_checkboxes.append((cb, entry, size_dur_text))

                # Video thumbnail
                vid_thumb = ft.Container(
                    content=ft.Image(
                        src=item_thumb_url if item_thumb_url else "https://via.placeholder.com/64x36",
                        width=64, height=36,
                        fit=ft.BoxFit.COVER,
                        error_content=ft.Container(
                            content=ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED_ROUNDED, size=20, color=AppTheme.TEXT_SECONDARY),
                            width=64, height=36,
                            bgcolor=AppTheme.SURFACE_VARIANT,
                            alignment=ft.Alignment(0, 0)
                        )
                    ),
                    border_radius=4,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                )

                # Video info (title + duration)
                vid_info = ft.Column([
                    ft.Text(
                        item_title, size=12, color=AppTheme.TEXT_PRIMARY,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                        weight=ft.FontWeight.W_500,
                    ),
                    size_dur_text,
                ], spacing=1, expand=True, alignment=ft.MainAxisAlignment.CENTER)

                # Number badge
                num_badge = ft.Container(
                    content=ft.Text(
                        f"{i + 1}", size=10, color=AppTheme.TEXT_SECONDARY,
                        text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.W_600,
                    ),
                    width=22,
                    alignment=ft.Alignment(0, 0),
                )

                item_row = ft.Container(
                    content=ft.Row(
                        [cb, num_badge, vid_thumb, vid_info],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding(left=4, right=8, top=4, bottom=4),
                    border_radius=6,
                    bgcolor=AppTheme.BACKGROUND if i % 2 == 0 else None,
                )
                playlist_items_col.append(item_row)

            playlist_list = ft.Container(
                content=ft.Column(playlist_items_col, spacing=2, scroll=ft.ScrollMode.AUTO),
                expand=True,
                padding=4,
                border_radius=8,
                border=ft.Border(
                    left=ft.BorderSide(1, AppTheme.SURFACE_VARIANT),
                    right=ft.BorderSide(1, AppTheme.SURFACE_VARIANT),
                    top=ft.BorderSide(1, AppTheme.SURFACE_VARIANT),
                    bottom=ft.BorderSide(1, AppTheme.SURFACE_VARIANT),
                ),
            )

            left_content = ft.Column(
                [
                    playlist_header,
                    ft.Container(height=6),
                    ft.Divider(height=1, color=AppTheme.SURFACE_VARIANT),
                    ft.Container(height=6),
                    selection_bar,
                    playlist_list,
                ],
                spacing=4,
                expand=True,
            )

            return ft.Container(
                content=left_content,
                width=460,
                padding=ft.Padding(left=20, right=12, top=20, bottom=10),
                expand=True,
            )

        # ── SINGLE VIDEO LAYOUT ──
        left_items = [
            thumbnail,
            ft.Container(height=8),
            title_text,
            uploader_text,
            info_row,
        ]

        return ft.Container(
            content=ft.Column(
                left_items,
                spacing=4,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=300,
            padding=ft.Padding(left=20, right=10, top=20, bottom=10),
        )

    # ──────────────────────────────────────────────────────────────
    #  RIGHT PANEL
    # ──────────────────────────────────────────────────────────────
    def _build_right_panel(self):
        # Dropdown styling
        dd_style = dict(
            width=320,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.BACKGROUND,
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            border_radius=8,
            text_size=13,
            content_padding=ft.Padding(left=12, right=8, top=10, bottom=10),
        )

        section_label_style = ft.TextStyle(
            color=AppTheme.ACCENT, size=11,
            weight=ft.FontWeight.BOLD,
        )

        # ── Download Type ──
        if self.is_image:
            dl_type_val = "Image"
            dl_type_opts = [ft.dropdown.Option("Image")]
            dl_type_disabled = True
        elif self.is_audio_platform:
            dl_type_val = "Audio Only"
            dl_type_opts = [ft.dropdown.Option("Audio Only")]
            dl_type_disabled = True
        else:
            dl_type_val = "Audio Only" if self.audio_only_mode else "Video"
            dl_type_opts = [ft.dropdown.Option("Video"), ft.dropdown.Option("Audio Only")]
            dl_type_disabled = False

        self.type_dropdown = ft.Dropdown(
            label="Download Type",
            value=dl_type_val,
            disabled=dl_type_disabled,
            options=dl_type_opts,
            **dd_style,
        )
        self.type_dropdown.on_select = self._on_type_change

        # ── Format & Quality (dynamic) ──
        self.dropdowns_container = ft.Column(controls=[], tight=True, spacing=8)
        self._rebuild_dropdowns(dl_type=dl_type_val)

        # ── Section: Embed Options ──
        embed_thumb_default = self.settings.get('embed_thumbnail', False)
        embed_subs_default = self.settings.get('embed_subtitles', False)
        sub_lang_default = self.settings.get('auto_subtitle_lang', 'en')

        self.embed_thumb_switch = ft.Switch(
            label="Embed Thumbnail",
            value=embed_thumb_default,
            active_color=AppTheme.PRIMARY,
            label_text_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY, size=12),
        )

        self.embed_subs_switch = ft.Switch(
            label="Embed Subtitles",
            value=embed_subs_default,
            active_color=AppTheme.PRIMARY,
            label_text_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY, size=12),
            on_change=self._on_subs_toggle,
        )

        self.sub_lang_field = ft.TextField(
            label="Subtitle Language",
            value=sub_lang_default,
            width=320,
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.BACKGROUND,
            border_radius=8,
            prefix_icon=ft.Icons.SUBTITLES_ROUNDED,
            text_size=13,
            content_padding=ft.Padding(left=12, right=8, top=10, bottom=10),
            visible=embed_subs_default,
            hint_text="e.g. en, hi, es",
        )

        # ── Section: Rename ──
        if self.is_playlist:
            filename_default = self.settings.get('playlist_filename_template', '%(playlist_index)s - %(title)s.%(ext)s')
        else:
            filename_default = self.settings.get('filename_template', '%(title)s.%(ext)s')
        self.filename_field = ft.TextField(
            label="Filename Template",
            value=filename_default,
            width=320,
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.BACKGROUND,
            border_radius=8,
            prefix_icon=ft.Icons.DRIVE_FILE_RENAME_OUTLINE_ROUNDED,
            text_size=13,
            content_padding=ft.Padding(left=12, right=8, top=10, bottom=10),
            tooltip="yt-dlp template, e.g. %(title)s.%(ext)s",
        )

        # ── Build sections ──
        def _section_header(icon, text):
            return ft.Row(
                [
                    ft.Icon(icon, color=AppTheme.ACCENT, size=16),
                    ft.Text(text, style=section_label_style),
                ],
                spacing=6,
            )

        right_content = ft.Column(
            [
                # Header
                ft.Text(
                    "Download Options",
                    color=AppTheme.TEXT_PRIMARY,
                    weight=ft.FontWeight.BOLD,
                    size=17,
                ),
                ft.Divider(height=1, color=AppTheme.SURFACE_VARIANT),
                ft.Container(height=2),

                # Format section
                _section_header(ft.Icons.VIDEO_SETTINGS_ROUNDED, "FORMAT"),
                self.type_dropdown,
                self.dropdowns_container,

                ft.Container(height=4),
                ft.Divider(height=1, color=AppTheme.SURFACE_VARIANT),
                ft.Container(height=4),

                # Embed section
                _section_header(ft.Icons.ATTACH_FILE_ROUNDED, "EMBED OPTIONS"),
                self.embed_thumb_switch,
                self.embed_subs_switch,
                self.sub_lang_field,

                ft.Container(height=4),
                ft.Divider(height=1, color=AppTheme.SURFACE_VARIANT),
                ft.Container(height=4),

                # Rename section
                _section_header(ft.Icons.EDIT_ROUNDED, "FILENAME"),
                self.filename_field,
            ],
            spacing=6,
            scroll=ft.ScrollMode.AUTO,
        )

        return ft.Container(
            content=right_content,
            width=440,
            padding=ft.Padding(left=20, right=20, top=16, bottom=12),
        )

    # ──────────────────────────────────────────────────────────────
    #  FILE SIZE HELPERS
    # ──────────────────────────────────────────────────────────────
    def _build_format_size_map(self):
        """Index yt-dlp formats by height for quick size lookup."""
        size_map = {}  # height -> best filesize estimate
        if self.is_playlist:
            return size_map
        formats = self.info.get('formats', [])
        for f in formats:
            h = f.get('height')
            vcodec = f.get('vcodec')
            if not h or not vcodec or vcodec == 'none':
                continue
            size = f.get('filesize') or f.get('filesize_approx') or 0
            if not size:
                # Estimate from tbr (total bitrate) and duration
                tbr = f.get('tbr')  # kbps
                dur = self.info.get('duration')
                if tbr and dur:
                    size = int(tbr * 1000 / 8 * dur)  # bytes
            if size and (h not in size_map or size > size_map[h]):
                size_map[h] = size
        return size_map

    def _get_approx_size(self, is_audio=False, quality="best"):
        """Return a human-readable approximate file size string."""
        total_size_bytes = 0
        
        if self.is_playlist:
            if not hasattr(self, 'playlist_checkboxes'):
                entries_to_calc = self.info.get('entries', [])
            else:
                entries_to_calc = [entry for cb, entry, _ in self.playlist_checkboxes if cb.value]
            
            for entry in entries_to_calc:
                total_size_bytes += self._calc_single_approx_size(entry, is_audio, quality, use_format_sizes=False)
        else:
            total_size_bytes = self._calc_single_approx_size(self.info, is_audio, quality, use_format_sizes=True)

        if not total_size_bytes:
            return ""
        
        return self._format_bytes(total_size_bytes)

    def _calc_single_approx_size(self, info_dict, is_audio, quality, use_format_sizes=False):
        size_bytes = 0
        duration = info_dict.get('duration', 0)
        
        # Estimate 3 minutes for Spotify scraped tracks without a duration
        if not duration and info_dict.get('_spotify'):
            duration = 180

        if is_audio:
            try:
                bitrate_kbps = int(quality) if quality != "best" else 192
            except (ValueError, TypeError):
                bitrate_kbps = 192
            if duration:
                size_bytes = int(bitrate_kbps * 1000 / 8 * duration)
        else:
            if use_format_sizes and self._format_sizes:
                if quality == "best":
                    size_bytes = max(self._format_sizes.values())
                else:
                    try:
                        target_h = int(quality)
                    except (ValueError, TypeError):
                        target_h = 0
                    if target_h in self._format_sizes:
                        size_bytes = self._format_sizes[target_h]
                    elif self._format_sizes:
                        candidates = {h: s for h, s in self._format_sizes.items() if h <= target_h}
                        if candidates:
                            size_bytes = max(candidates.values())
                        else:
                            size_bytes = min(self._format_sizes.values())
                
                if size_bytes and duration:
                    size_bytes += int(128 * 1000 / 8 * duration)
            
            if not size_bytes:
                size_bytes = info_dict.get('filesize_approx') or info_dict.get('filesize') or 0
                
            if not size_bytes and duration:
                kbps = 3000
                if quality != "best":
                    try:
                        target_h = int(quality)
                        if target_h >= 2160: kbps = 12000
                        elif target_h >= 1440: kbps = 6000
                        elif target_h >= 1080: kbps = 3000
                        elif target_h >= 720: kbps = 1500
                        elif target_h >= 480: kbps = 800
                        else: kbps = 500
                    except (ValueError, TypeError):
                        pass
                size_bytes = int(kbps * 1000 / 8 * duration)

        return size_bytes

    @staticmethod
    def _format_bytes(size_bytes):
        """Format bytes into human-readable string."""
        if size_bytes >= 1_073_741_824:  # 1 GB
            return f"{size_bytes / 1_073_741_824:.1f} GB"
        elif size_bytes >= 1_048_576:  # 1 MB
            return f"{size_bytes / 1_048_576:.0f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.0f} KB"
        return f"{size_bytes} B"

    # ──────────────────────────────────────────────────────────────
    #  EVENT HANDLERS
    # ──────────────────────────────────────────────────────────────
    def _on_type_change(self, e):
        # In Flet 0.85+, on_select passes selected key via e.data
        if hasattr(e, 'data') and e.data:
            self.type_dropdown.value = e.data
        dl_type = self.type_dropdown.value
        self._rebuild_dropdowns(dl_type=dl_type)
        try:
            self.dropdowns_container.controls.clear()
            self.dropdowns_container.controls.append(self.format_dropdown)
            self.dropdowns_container.controls.append(self.quality_dropdown)
            self.dropdowns_container.update()
        except Exception as ex:
            print(f"[DEBUG] container update failed: {ex}")
        self._update_filesize()
        self._update_embed_options()
        self._page.update()

    def _on_format_change(self, e):
        if hasattr(e, 'data') and e.data:
            self.format_dropdown.value = e.data
        self._update_embed_options()
        self._page.update()

    def _update_embed_options(self):
        if not hasattr(self, 'embed_thumb_switch') or not hasattr(self, 'format_dropdown'):
            return
            
        settings_enabled = self.settings.get('embed_thumbnail', False)
        
        if not settings_enabled:
            self.embed_thumb_switch.disabled = True
            self.embed_thumb_switch.value = False
        else:
            current_format = self.format_dropdown.value
            if current_format == "wav":
                self.embed_thumb_switch.disabled = True
                self.embed_thumb_switch.value = False
            else:
                self.embed_thumb_switch.disabled = False
                self.embed_thumb_switch.value = True

    def _rebuild_dropdowns(self, dl_type: str = "Video"):
        """Create fresh Dropdown controls for format and quality based on mode."""
        dd_style = dict(
            width=320,
            color=AppTheme.TEXT_PRIMARY,
            bgcolor=AppTheme.BACKGROUND,
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            border_radius=8,
            text_size=13,
            content_padding=ft.Padding(left=12, right=8, top=10, bottom=10),
        )

        if dl_type == "Audio Only":
            self.format_dropdown = ft.Dropdown(
                label="Audio Format",
                value="mp3",
                options=[
                    ft.dropdown.Option("mp3"),
                    ft.dropdown.Option("m4a"),
                    ft.dropdown.Option("wav"),
                    ft.dropdown.Option("flac"),
                ],
                **dd_style,
            )
            self.format_dropdown.on_select = self._on_format_change
            self.quality_dropdown = ft.Dropdown(
                label="Audio Quality",
                value="192",
                options=[
                    ft.dropdown.Option("320", text="320 kbps (Highest)"),
                    ft.dropdown.Option("256", text="256 kbps (High)"),
                    ft.dropdown.Option("192", text="192 kbps (Standard)"),
                    ft.dropdown.Option("128", text="128 kbps (Low)"),
                    ft.dropdown.Option("96", text="96 kbps (Lowest)"),
                ],
                **dd_style,
            )
            self.quality_dropdown.on_select = self._on_quality_change
        elif dl_type == "Image":
            self.format_dropdown = ft.Dropdown(
                label="Image Format",
                value="jpg",
                options=[
                    ft.dropdown.Option("jpg"),
                    ft.dropdown.Option("png"),
                    ft.dropdown.Option("webp"),
                ],
                **dd_style,
            )
            self.format_dropdown.on_select = self._on_format_change
            self.quality_dropdown = ft.Dropdown(
                label="Quality",
                value="best",
                options=[
                    ft.dropdown.Option("best", text="Best Available (Original)"),
                ],
                **dd_style,
            )
            self.quality_dropdown.on_select = self._on_quality_change
        else:
            self.format_dropdown = ft.Dropdown(
                label="File Format",
                value="mp4",
                options=[
                    ft.dropdown.Option("mp4"),
                    ft.dropdown.Option("mkv"),
                    ft.dropdown.Option("webm"),
                ],
                **dd_style,
            )
            self.format_dropdown.on_select = self._on_format_change
            qual_opts = [ft.dropdown.Option("best", text="Best Available (Max)")]
            for res in self.available_resolutions:
                if res >= 360:
                    text_str = f"{res}p Resolution limit"
                    if res == 2160:
                        text_str = "4K Resolution limit"
                    elif res == 1440:
                        text_str = "1440p (2K) Resolution limit"
                    elif res == 4320:
                        text_str = "8K Resolution limit"
                    qual_opts.append(ft.dropdown.Option(str(res), text=text_str))
            self.quality_dropdown = ft.Dropdown(
                label="Quality",
                value="best",
                options=qual_opts,
                **dd_style,
            )
            self.quality_dropdown.on_select = self._on_quality_change

        self.dropdowns_container.controls = [self.format_dropdown, self.quality_dropdown]

    def _on_quality_change(self, e):
        """Update filesize when quality dropdown changes."""
        self._update_filesize()
        self._page.update()

    def _on_subs_toggle(self, e):
        self.sub_lang_field.visible = self.embed_subs_switch.value
        self._page.update()

    def _update_filesize(self):
        """Refresh the filesize chip based on current dropdown selections."""
        is_audio = (self.type_dropdown.value == "Audio Only") if hasattr(self, 'type_dropdown') else self.audio_only_mode
        qual = self.quality_dropdown.value if hasattr(self, 'quality_dropdown') else "best"
        
        # Update overall size
        if hasattr(self, 'filesize_text'):
            approx = self._get_approx_size(is_audio=is_audio, quality=qual)
            self.filesize_text.value = f"~{approx}" if approx else ""
            if hasattr(self, 'filesize_container'):
                self.filesize_container.visible = bool(approx)
        
        # Update individual track sizes
        if hasattr(self, 'playlist_checkboxes'):
            for _, entry, size_text in self.playlist_checkboxes:
                sz_bytes = self._calc_single_approx_size(entry, is_audio, qual, use_format_sizes=False)
                sz_str = f" • ~{self._format_bytes(sz_bytes)}" if sz_bytes else ""
                
                # Retrieve existing duration string
                dur = entry.get('duration')
                dur_str = ""
                if dur:
                    m, s = divmod(int(dur), 60)
                    h, m = divmod(m, 60)
                    dur_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
                    
                if dur_str and sz_bytes:
                    size_text.value = f"{dur_str} • ~{self._format_bytes(sz_bytes)}"
                elif sz_bytes:
                    size_text.value = f"~{self._format_bytes(sz_bytes)}"
                else:
                    size_text.value = dur_str

    def _select_all(self, e):
        for cb, _, _ in self.playlist_checkboxes:
            cb.value = True
        self._update_selection_text()
        self._update_filesize()
        self._page.update()

    def _select_none(self, e):
        for cb, _, _ in self.playlist_checkboxes:
            cb.value = False
        self._update_selection_text()
        self._update_filesize()
        self._page.update()

    def _on_playlist_item_toggle(self, e):
        self._update_selection_text()
        self._update_filesize()
        self._page.update()

    def _update_selection_text(self):
        if not hasattr(self, 'selection_count_text'):
            return
        selected = sum(1 for cb, _, _ in self.playlist_checkboxes if cb.value)
        total = len(self.playlist_checkboxes)
        self.selection_count_text.value = f"{selected}/{total} selected"

    # ──────────────────────────────────────────────────────────────
    #  ACTIONS
    # ──────────────────────────────────────────────────────────────
    def _cancel(self, e):
        self.open = False
        self._page.update()
        if self.on_close_callback:
            self.on_close_callback()

    def _download_thumbnail(self, e):
        self._start_download(e, is_thumbnail=True)

    def _start_download(self, e, is_thumbnail=False):
        default_path = self.settings.get('default_download_path')
        if default_path and os.path.isdir(default_path):
            output_path = default_path
        else:
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            output_path = filedialog.askdirectory(title="Select Download Folder")
            root.destroy()
            if not output_path:
                return
                
        is_audio = self.type_dropdown.value == "Audio Only"
        is_image = self.type_dropdown.value == "Image"
        f_ext = self.format_dropdown.value
        qual = self.quality_dropdown.value
        
        audio_codec = None
        audio_quality = None
        video_ext = None
        image_ext = None
        format_id = "best"
        
        if is_audio:
            format_id = "bestaudio/best"
            audio_codec = f_ext
            audio_quality = qual
        elif is_image:
            format_id = "best"
            image_ext = f_ext
        else:
            video_ext = f_ext
            if qual == "best":
                format_id = "bestvideo+bestaudio/best"
            else:
                format_id = f"bestvideo[height<={qual}]+bestaudio/best[height<={qual}]"
        
        # Per-download options
        embed_thumbnail = self.embed_thumb_switch.value
        embed_subtitles = self.embed_subs_switch.value
        subtitle_lang = self.sub_lang_field.value.strip() or 'en'
        custom_filename = self.filename_field.value.strip() or None

        # Playlist: gather selected entries
        selected_entries = None
        if self.is_playlist and 'entries' in self.info:
            selected_entries = [entry for cb, entry, _ in self.playlist_checkboxes if cb.value]
            if not selected_entries:
                return  # nothing selected

        self.open = False
        self._page.update()
        
        if self.on_download_callback:
            self.on_download_callback(
                self.info, format_id, is_audio, output_path,
                video_ext=video_ext, audio_codec=audio_codec, audio_quality=audio_quality,
                embed_thumbnail=embed_thumbnail, embed_subtitles=embed_subtitles,
                subtitle_lang=subtitle_lang, custom_filename=custom_filename,
                selected_entries=selected_entries, is_image=is_image, image_ext=image_ext, is_thumbnail=is_thumbnail,
            )
