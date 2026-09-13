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
        
        # Sanitize top-level title to prevent double extensions during download
        import re
        t = self.info.get('title', '').strip()
        if t:
            for ext in ['.mp3', '.ogg', '.flac', '.wav', '.m4a', '.mp4', '.mkv', '.webm', '.avi', '.mov']:
                if t.lower().endswith(ext):
                    t = t[:-len(ext)].strip()
            t = re.sub(r'_(512kb|archive|spectrogram|1080p|720p|480p|360p|240p|vbr|hq)$', '', t, flags=re.IGNORECASE).strip()
            if t:
                self.info['title'] = t
        
        # Force audio-only for Spotify content
        extractor_key = self.info.get('extractor_key', '').lower()
        self.is_audio_platform = self.info.get('_spotify') or extractor_key in ['spotify', 'soundcloud', 'applemusic', 'applepodcasts', 'audioboom', 'deezer', 'tidal', 'gaana', 'lastfm', 'mixcloud'] or 'bandcamp' in extractor_key or 'jiosaavn' in extractor_key or 'podcasts.apple.com' in (self.info.get('original_url') or self.info.get('webpage_url') or '').lower()
        if self.is_audio_platform:
            self.audio_only_mode = True

        # Parse available video resolutions
        self.is_playlist = 'entries' in self.info and self.info.get('_type') == 'playlist'
        
        # Detect image & mixed media
        self.is_image = False
        self.is_mixed = False
        
        url_lower = (self.info.get('original_url') or self.info.get('webpage_url') or '').lower()
        self.is_manga_platform = any(domain in url_lower for domain in [
            'fanfox.net', 'mangafire.to', 'mangafreak.me', 'mangaread.org', 
            'mangataro.org', 'hiperdex.com', 'mangadex.org', 'bato.to', 
            'dynasty-scans.com', 'tapas.io', 'danbooru.donmai.us', 'pinterest.com',
            'myhentaigallery.com', 'hentaihere.com', 'nhentai', 'rawkuma.net', 'simply-hentai.com', 'weebcentral.com', '8muses.com'
        ])
        
        self.is_document_platform = any(domain in url_lower for domain in ['slideshare.net', 'scribd.com', 'issuu.com', 'docdroid.net', 'speakerdeck.com'])
        
        if self.is_manga_platform or self.is_document_platform:
            self.is_image = True
        if self.is_audio_platform:
            pass
        elif self.is_playlist:
            entries = self.info.get('entries', [])
            if entries:
                # Deduplicate entries by title and merge formats (fixes archive.org exposing formats as separate entries)
                seen_titles = {}
                unique_entries = []
                import re
                for e in entries:
                    t = e.get('title', '').strip()
                    # Remove common extensions from title for deduplication
                    for ext in ['.mp3', '.ogg', '.flac', '.wav', '.m4a', '.mp4', '.mkv', '.webm', '.avi', '.mov']:
                        if t.lower().endswith(ext):
                            t = t[:-len(ext)].strip()
                            
                    # Aggressively strip archive.org derivative suffixes
                    t = re.sub(r'_(512kb|archive|spectrogram|1080p|720p|480p|360p|240p|vbr|hq)$', '', t, flags=re.IGNORECASE).strip()
                    
                    if t:
                        # Save the cleaned title back to prevent double extensions during download
                        e['title'] = t
                        
                    if t and t in seen_titles:
                        # Group formats into the original entry so they can be selected in the quality dropdown
                        orig_e = seen_titles[t]
                        if e.get('formats'):
                            if not orig_e.get('formats'):
                                orig_e['formats'] = []
                            orig_e['formats'].extend(e.get('formats', []))
                        continue
                        
                    if t:
                        seen_titles[t] = e
                    unique_entries.append(e)
                entries = unique_entries
                self.info['entries'] = entries
                
                has_video = False
                has_image = False
                has_audio = False
                for entry in entries:
                    entry_formats = entry.get('formats', [])
                    ext = entry.get('ext', '').lower()
                    vcodec = entry.get('vcodec')
                    acodec = entry.get('acodec')
                    if '?' in ext: ext = ext.split('?')[0]
                    if not ext and entry.get('url'):
                        ext = entry['url'].split('?')[0].split('.')[-1][:4].lower()
                        
                    is_img = False
                    is_aud = False
                    is_vid = False
                    
                    if ext in ['jpg', 'jpeg', 'png', 'webp', 'gif', 'pdf'] or vcodec == 'image':
                        is_img = True
                        
                    if entry_formats:
                        all_images = True
                        all_audio = True
                        for f in entry_formats:
                            f_ext = f.get('ext', '').lower()
                            f_vcodec = f.get('vcodec')
                            f_acodec = f.get('acodec')
                            
                            if f_ext in ['mp4', 'webm', 'mkv', 'mov', 'avi', 'm4v', 'flv', 'mp3', 'wav', 'flac', 'm4a', 'ogg', 'aac', 'm3u8']:
                                all_images = False
                            if (f_vcodec and f_vcodec not in ['image', 'none']) or (f_acodec and f_acodec not in ['none']):
                                all_images = False
                            if f_vcodec and f_vcodec not in ['none', 'image']:
                                all_audio = False
                            if f.get('width') or f.get('height') or f_ext in ['mp4', 'webm', 'mkv', 'mov', 'avi', 'm4v', 'flv', 'm3u8', 'ts']:
                                all_audio = False
                                
                        if all_images:
                            is_img = True
                        elif all_audio and entry_formats:
                            is_aud = True
                        else:
                            is_vid = True
                    else:
                        if ext in ['mp3', 'wav', 'flac', 'm4a', 'ogg', 'aac'] or (acodec and acodec != 'none' and vcodec in ['none', 'image']):
                            is_aud = True
                        elif ext in ['mp4', 'webm', 'mkv', 'mov', 'avi', 'm4v', 'flv', 'm3u8', 'ts'] or (vcodec and vcodec not in ['none', 'image']):
                            is_vid = True
                        elif is_img:
                            pass
                        else:
                            is_vid = True
                            
                    if is_img and not is_vid and not is_aud:
                        has_image = True
                    elif is_aud and not is_vid:
                        has_audio = True
                    else:
                        has_video = True
                        
                if has_image and not has_video and not has_audio:
                    self.is_image = True
                elif has_audio and not has_video and not has_image:
                    self.audio_only_mode = True
                elif has_image and (has_video or has_audio):
                    self.is_mixed = True
        else:
            formats = self.info.get('formats', [])
            if formats:
                all_images = True
                all_audio = True
                for f in formats:
                    # yt-dlp sometimes mislabels tumblr mp4 videos as vcodec='image'
                    ext = f.get('ext', '').lower()
                    if ext in ['mp4', 'webm', 'mkv', 'mov', 'avi', 'm4v', 'flv', 'mp3', 'wav', 'flac', 'm4a', 'ogg', 'aac', 'm3u8']:
                        all_images = False
                    
                    vcodec = f.get('vcodec')
                    acodec = f.get('acodec')
                    
                    # If the codec is explicitly a video or audio codec, it's not an image
                    if (vcodec and vcodec not in ['image', 'none']) or (acodec and acodec not in ['none']):
                        all_images = False
                        
                    if vcodec and vcodec not in ['none', 'image']:
                        all_audio = False
                        
                    # If it has video-specific properties or extensions, it's not purely audio
                    if f.get('width') or f.get('height') or ext in ['mp4', 'webm', 'mkv', 'mov', 'avi', 'm4v', 'flv', 'm3u8', 'ts']:
                        all_audio = False
                        
                if all_images:
                    self.is_image = True
                elif all_audio and formats:
                    self.audio_only_mode = True
        
        # Detect livestream
        self.is_live = self.info.get('is_live') or self.info.get('live_status') == 'is_live'
        
        self.available_resolutions = []
        self.playlist_checkboxes = []

        self.available_resolutions = []
        self.playlist_checkboxes = []

        formats = self.info.get('formats', [])
        if not formats and self.is_playlist and self.info.get('entries'):
            for entry in self.info.get('entries'):
                if entry.get('formats'):
                    formats = entry.get('formats')
                    break

        if formats:
            resolutions = set()
            for f in formats:
                h = f.get('height')
                if not h and f.get('resolution') and 'x' in str(f.get('resolution')):
                    try:
                        h = int(str(f.get('resolution')).split('x')[1])
                    except:
                        pass
                if not h and f.get('width'):
                    try:
                        h = int(f.get('width')) * 9 // 16
                    except:
                        pass
                
                vcodec = f.get('vcodec')
                if h and (vcodec != 'none' or 'video' in f.get('format', '').lower()):
                    resolutions.add(h)
            self.available_resolutions = sorted(list(resolutions), reverse=True)
            
        if not self.available_resolutions:
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
            thumb_url = self.info['thumbnails'][-1]['url']
        
        # Fallback for playlists without a top-level thumbnail
        if not thumb_url and self.is_playlist:
            entries = self.info.get('entries', [])
            if entries:
                first = entries[0]
                thumb_url = first.get('thumbnail') or (first.get('thumbnails', [{}])[-1].get('url', '') if first.get('thumbnails') else '')

        # Fallback for archive.org cover photos if yt-dlp missed them
        if not thumb_url and self.info.get('original_url') and 'archive.org/details/' in self.info.get('original_url'):
            import re
            m = re.search(r'archive\.org/details/([^/?#&]+)', self.info.get('original_url'))
            if m:
                thumb_url = f"https://archive.org/services/img/{m.group(1)}"
                
        if thumb_url:
            if thumb_url.startswith('//'):
                thumb_url = 'https:' + thumb_url
            elif thumb_url.startswith('/'):
                domain = self.info.get('webpage_url', 'https://archive.org').split('/')[2]
                thumb_url = f"https://{domain}{thumb_url}"

        thumb_display_w = 280
        vid_w = self.info.get('width')
        vid_h = self.info.get('height')
        
        # Audio platforms usually have 1:1 square cover art
        extractor_key = self.info.get('extractor_key', '').lower()
        is_audio_platform = self.info.get('_spotify') or extractor_key in ['spotify', 'soundcloud', 'applemusic', 'applepodcasts', 'audioboom', 'deezer', 'tidal', 'gaana', 'lastfm', 'mixcloud'] or 'bandcamp' in extractor_key or 'jiosaavn' in extractor_key or 'podcasts.apple.com' in (self.info.get('original_url') or self.info.get('webpage_url') or '').lower()

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
                        f"📋 {count} images" if self.is_image else (f"📋 {count} media items" if getattr(self, 'is_mixed', False) else (f"📋 {count} tracks" if self.audio_only_mode else f"📋 {count} videos")),
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
                item_thumb_url = entry.get('thumbnail') or (entry.get('thumbnails', [{}])[0].get('url', '') if entry.get('thumbnails') else '')
                if not item_thumb_url and thumb_url:
                    item_thumb_url = thumb_url

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
                content=ft.ListView(controls=playlist_items_col, spacing=0, item_extent=46, auto_scroll=False),
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
            border_radius=12,
            menu_style=AppTheme.get_dropdown_menu_style(),
            text_size=13,
            content_padding=ft.Padding(left=12, right=8, top=10, bottom=10),
        )

        section_label_style = ft.TextStyle(
            color=AppTheme.ACCENT, size=11,
            weight=ft.FontWeight.BOLD,
        )

        # ── Download Type ──
        url_str = self.info.get('original_url', '') or self.info.get('webpage_url', '') or self.info.get('url', '') or getattr(self, 'url', '')
        is_manga_site = getattr(self, 'is_manga_platform', False)
        is_document_site = getattr(self, 'is_document_platform', False)
        if is_manga_site:
            dl_type_val = "Manga"
            dl_type_opts = [ft.dropdown.Option("Manga")]
            dl_type_disabled = True
        elif is_document_site:
            dl_type_val = "Document"
            dl_type_opts = [ft.dropdown.Option("Document")]
            dl_type_disabled = True
        elif self.is_image:
            dl_type_val = "Image"
            dl_type_opts = [ft.dropdown.Option("Image")]
            dl_type_disabled = True
        elif getattr(self, 'is_mixed', False):
            dl_type_val = "Mixed Media"
            dl_type_opts = [ft.dropdown.Option("Mixed Media")]
            dl_type_disabled = True
        elif self.is_audio_platform or getattr(self, 'audio_only_mode', False):
            dl_type_val = "Audio Only"
            dl_type_opts = [ft.dropdown.Option("Audio Only")]
            dl_type_disabled = True
        else:
            dl_type_val = "Video"
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
        
        # Disable embed thumbnail switch automatically for 9anime/anime8 downloads
        if self.info.get('_is_9anime') or self.info.get('_is_anime8') or self.info.get('_is_animeflv'):
            embed_thumb_default = False
            
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

        is_youtube = 'youtube' in (self.info.get('extractor', '') or self.info.get('extractor_key', '') or '').lower() or 'youtube' in (self.info.get('webpage_url', '') or '').lower() or 'youtu.be' in (self.info.get('webpage_url', '') or '').lower()
        self.sponsorblock_switch = ft.Switch(
            label="SponsorBlock",
            value=self.settings.get('enable_sponsorblock', False),
            active_color=AppTheme.PRIMARY,
            label_text_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY, size=12),
            tooltip="Skip or cut out sponsored segments in YouTube videos",
            visible=is_youtube,
        )

        self.sub_lang_field = ft.TextField(
            label="Subtitle Language(s)",
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
            hint_text="e.g. en, es, hi or all",
            tooltip="Comma-separated language codes (e.g. en, es, ja, hi) or 'all' to embed multiple subtitle tracks",
        )

        sub_lang_info_btn = ft.IconButton(
            ft.Icons.INFO_OUTLINED,
            icon_color=AppTheme.ACCENT,
            tooltip="View Subtitle Language guide & presets",
            on_click=self._show_subtitles_info,
        )

        self.sub_lang_row = ft.Row(
            [self.sub_lang_field, sub_lang_info_btn],
            spacing=5,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            visible=embed_subs_default,
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
                self.sponsorblock_switch,
                self.sub_lang_row,

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
        formats = self.info.get('formats', [])
        if not formats and getattr(self, 'is_playlist', False) and self.info.get('entries'):
            for entry in self.info.get('entries'):
                if entry.get('formats'):
                    formats = entry.get('formats')
                    break
                    
        for f in formats:
            h = f.get('height')
            if not h and f.get('resolution') and 'x' in str(f.get('resolution')):
                try:
                    h = int(str(f.get('resolution')).split('x')[1])
                except:
                    pass
            if not h and f.get('width'):
                try:
                    h = int(f.get('width')) * 9 // 16
                except:
                    pass
                    
            vcodec = f.get('vcodec')
            if not h or (vcodec == 'none' and 'video' not in f.get('format', '').lower()):
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

    def _get_approx_size(self, is_audio=False, quality="best", audio_format="mp3"):
        """Return a human-readable approximate file size string."""
        total_size_bytes = 0
        
        if self.is_playlist:
            if not hasattr(self, 'playlist_checkboxes'):
                entries_to_calc = self.info.get('entries', [])
            else:
                entries_to_calc = [entry for cb, entry, _ in self.playlist_checkboxes if cb.value]
            
            for entry in entries_to_calc:
                total_size_bytes += self._calc_single_approx_size(entry, is_audio, quality, use_format_sizes=False, audio_format=audio_format)
        else:
            total_size_bytes = self._calc_single_approx_size(self.info, is_audio, quality, use_format_sizes=True, audio_format=audio_format)

        if not total_size_bytes:
            return ""
        
        return self._format_bytes(total_size_bytes)

    def _calc_single_approx_size(self, info_dict, is_audio, quality, use_format_sizes=False, audio_format="mp3"):
        size_bytes = 0
        duration = info_dict.get('duration', 0)
        
        # Estimate 3 minutes for Spotify scraped tracks without a duration
        if not duration and info_dict.get('_spotify'):
            duration = 180

        if is_audio:
            if audio_format == "wav":
                bitrate_kbps = 1411
            elif audio_format == "flac":
                bitrate_kbps = 900
            else:
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
        fmt = self.format_dropdown.value
        
        is_audio = (self.type_dropdown.value == "Audio Only") if hasattr(self, 'type_dropdown') else self.audio_only_mode
        
        if is_audio and hasattr(self, 'quality_dropdown'):
            if fmt in ("wav", "flac"):
                self.quality_dropdown.options = [
                    ft.dropdown.Option("best", text="Lossless"),
                ]
                self.quality_dropdown.value = "best"
                self.quality_dropdown.disabled = True
            else:
                self.quality_dropdown.options = [
                    ft.dropdown.Option("320", text="320 kbps (Highest)"),
                    ft.dropdown.Option("256", text="256 kbps (High)"),
                    ft.dropdown.Option("192", text="192 kbps (Standard)"),
                    ft.dropdown.Option("128", text="128 kbps (Low)"),
                    ft.dropdown.Option("96", text="96 kbps (Lowest)"),
                ]
                if self.quality_dropdown.value == "best":
                    self.quality_dropdown.value = "192"
                self.quality_dropdown.disabled = False
                
        self._update_embed_options()
        self._update_filesize()
        self._page.update()

    def _update_embed_options(self):
        if not hasattr(self, 'embed_thumb_switch') or not hasattr(self, 'format_dropdown'):
            return
            
        settings_enabled = self.settings.get('embed_thumbnail', False)
        is_9anime = self.info.get('_is_9anime', False)
        is_anime8 = self.info.get('_is_anime8', False)
        is_animeflv = self.info.get('_is_animeflv', False)
        
        if not settings_enabled:
            self.embed_thumb_switch.disabled = True
            self.embed_thumb_switch.value = False
        else:
            current_format = self.format_dropdown.value
            if current_format == "wav" or is_9anime or is_anime8 or is_animeflv:
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
            border_radius=12,
            menu_style=AppTheme.get_dropdown_menu_style(),
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
                value="0",
                options=[
                    ft.dropdown.Option("0", text="Best Available (Original)"),
                    ft.dropdown.Option("320", text="320 kbps (Highest)"),
                    ft.dropdown.Option("256", text="256 kbps (High)"),
                    ft.dropdown.Option("192", text="192 kbps (Standard)"),
                    ft.dropdown.Option("128", text="128 kbps (Low)"),
                    ft.dropdown.Option("96", text="96 kbps (Lowest)"),
                ],
                **dd_style,
            )
            self.quality_dropdown.on_select = self._on_quality_change
        elif dl_type == "Mixed Media":
            self.format_dropdown = ft.Dropdown(
                label="Format",
                value="original",
                options=[ft.dropdown.Option("original", "Original Formats")],
                disabled=True,
                **dd_style,
            )
            self.format_dropdown.on_select = self._on_format_change
            self.quality_dropdown = ft.Dropdown(
                label="Quality",
                value="best",
                options=[ft.dropdown.Option("best", text="Best Available (Original)")],
                disabled=True,
                **dd_style,
            )
            self.quality_dropdown.on_select = self._on_quality_change
        elif dl_type == "Document":
            self.format_dropdown = ft.Dropdown(
                label="Format",
                value="pdf",
                options=[
                    ft.dropdown.Option("pdf", text="PDF (Batch)"),
                    ft.dropdown.Option("jpg", text="JPG (Individual)"),
                    ft.dropdown.Option("png", text="PNG (Individual)"),
                    ft.dropdown.Option("webp", text="WEBP (Individual)"),
                ],
                disabled=False,
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
        elif dl_type == "Manga":
            self.format_dropdown = ft.Dropdown(
                label="Format",
                value="pdf",
                options=[
                    ft.dropdown.Option("pdf", text="PDF (Batch)"),
                    ft.dropdown.Option("epub", text="EPUB (Batch)"),
                    ft.dropdown.Option("jpg", text="JPG (Individual)"),
                    ft.dropdown.Option("png", text="PNG (Individual)"),
                    ft.dropdown.Option("webp", text="WEBP (Individual)"),
                    ft.dropdown.Option("gif", text="GIF (Individual)"),
                ],
                disabled=False,
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
        elif dl_type == "Image":
            default_val = "jpg"
            url_str = self.info.get('original_url', '') or self.info.get('webpage_url', '') or self.info.get('url', '') or getattr(self, 'url', '')
            if any(domain in url_str.lower() for domain in ['mangadex.org', 'dynasty-scans.com', 'webtoons.com', 'tapas.io']):
                default_val = "pdf"
                
            self.format_dropdown = ft.Dropdown(
                label="Image Format",
                value=default_val,
                options=[
                    ft.dropdown.Option("jpg"),
                    ft.dropdown.Option("png"),
                    ft.dropdown.Option("webp"),
                    ft.dropdown.Option("gif"),
                    ft.dropdown.Option("pdf"),
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
                    ft.dropdown.Option("mov"),
                ],
                **dd_style,
            )
            self.format_dropdown.on_select = self._on_format_change
            qual_opts = [ft.dropdown.Option("best", text="Best Available (Max)")]
            for res in self.available_resolutions:
                if res >= 360:
                    if res == 4320:
                        text_str = "4320p (7680 x 4320) [8K]"
                    elif res == 2160:
                        text_str = "2160p (3840 x 2160) [4K]"
                    elif res == 1920:
                        text_str = "1920p (1080 x 1920) [FHD]"
                    elif res == 1800:
                        text_str = "1800p (3200 x 1800) [QHD+]"
                    elif res == 1440:
                        text_str = "1440p (2560 x 1440) [2K]"
                    elif res == 1280:
                        text_str = "1280p (720 x 1280) [HD]"
                    elif res == 1080:
                        text_str = "1080p (1920 x 1080) [FHD]"
                    elif res == 720:
                        text_str = "720p (1280 x 720) [HD]"
                    elif res == 640:
                        text_str = "640p (480 x 640) [SD]"
                    elif res == 540:
                        text_str = "540p (960 x 540) [qHD]"
                    elif res == 480:
                        text_str = "480p (854 x 480) [SD]"
                    elif res == 360:
                        text_str = "360p (640 x 360) [SD]"
                    else:
                        text_str = f"{res}p"
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
        self.sub_lang_row.visible = self.embed_subs_switch.value
        self._page.update()

    def _show_subtitles_info(self, e):
        def _close_info(evt=None):
            info_dlg.open = False
            self._page.update()
            if info_dlg in self._page.overlay:
                self._page.overlay.remove(info_dlg)

        def apply_lang(val):
            self.sub_lang_field.value = val
            try:
                self.sub_lang_field.update()
            except:
                pass
            _close_info()

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
                        on_click=lambda evt, val=p[0]: apply_lang(val)
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

        info_dlg = ft.AlertDialog(
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
                ft.TextButton("Close", on_click=_close_info)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(info_dlg)
        info_dlg.open = True
        self._page.update()

    def _update_filesize(self):
        """Refresh the filesize chip based on current dropdown selections."""
        is_audio = (self.type_dropdown.value == "Audio Only") if hasattr(self, 'type_dropdown') else self.audio_only_mode
        qual = self.quality_dropdown.value if hasattr(self, 'quality_dropdown') else "best"
        fmt = self.format_dropdown.value if hasattr(self, 'format_dropdown') else "mp3"
        
        # Update overall size
        if hasattr(self, 'filesize_text'):
            approx = self._get_approx_size(is_audio=is_audio, quality=qual, audio_format=fmt)
            self.filesize_text.value = f"~{approx}" if approx else ""
            if hasattr(self, 'filesize_container'):
                self.filesize_container.visible = bool(approx)
        
        # Update individual track sizes
        if hasattr(self, 'playlist_checkboxes'):
            for _, entry, size_text in self.playlist_checkboxes:
                sz_bytes = self._calc_single_approx_size(entry, is_audio, qual, use_format_sizes=False, audio_format=fmt)
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
        if e and e.control:
            e.control.disabled = True
            e.control.text = "Starting..."
            self._page.update()

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
                if e and e.control:
                    e.control.disabled = False
                    e.control.text = "Record Stream" if getattr(self, 'is_live', False) else ("Thumbnail" if is_thumbnail else "Download")
                    self._page.update()
                return
                
        is_audio = self.type_dropdown.value == "Audio Only"
        is_image = self.type_dropdown.value == "Image"
        is_mixed = self.type_dropdown.value == "Mixed Media"
        is_manga = self.type_dropdown.value == "Manga"
        is_document = self.type_dropdown.value == "Document"
        f_ext = self.format_dropdown.value if self.format_dropdown else None
        qual = self.quality_dropdown.value if self.quality_dropdown else None
        
        audio_codec = None
        audio_quality = None
        video_ext = None
        image_ext = None
        format_id = "best"
        
        if is_audio:
            format_id = "bestaudio/best"
            audio_codec = f_ext
            audio_quality = qual
        elif is_image or is_manga or is_document:
            format_id = "best"
            image_ext = f_ext
        elif is_mixed:
            format_id = "bestvideo+bestaudio/best"
        else:
            video_ext = f_ext
            if qual == "best":
                format_id = "bestvideo+bestaudio/best"
            else:
                format_id = f"bestvideo[height<={qual}]+bestaudio/best[height<={qual}]/best"
        
        # Per-download options
        embed_thumbnail = self.embed_thumb_switch.value
        embed_subtitles = self.embed_subs_switch.value
        subtitle_lang = self.sub_lang_field.value.strip() or 'en'
        custom_filename = self.filename_field.value.strip() or None
        
        if is_thumbnail and self.is_playlist and custom_filename:
            custom_filename = custom_filename.replace('%(playlist_index)s - ', '').replace('%(playlist_index)s ', '').replace('%(playlist_index)s', '')

        # Playlist: gather selected entries
        selected_entries = None
        if self.is_playlist and 'entries' in self.info and not is_thumbnail:
            selected_entries = [entry for cb, entry, _ in self.playlist_checkboxes if cb.value]
            if not selected_entries:
                if e and e.control:
                    e.control.disabled = False
                    e.control.text = "Record Stream" if getattr(self, 'is_live', False) else ("Thumbnail" if is_thumbnail else "Download")
                    self._page.update()
                return  # nothing selected

        self.open = False
        self._page.update()
        
        if self.on_download_callback:
            self.on_download_callback(
                self.info, format_id, is_audio, output_path,
                video_ext=video_ext, audio_codec=audio_codec, audio_quality=audio_quality,
                embed_thumbnail=embed_thumbnail, embed_subtitles=embed_subtitles,
                subtitle_lang=subtitle_lang, custom_filename=custom_filename,
                selected_entries=selected_entries, is_image=(is_image or is_document), image_ext=image_ext, is_thumbnail=is_thumbnail,
                is_manga=(is_manga or is_document),
                enable_sponsorblock=self.sponsorblock_switch.value if getattr(self, 'sponsorblock_switch', None) else None,
            )
