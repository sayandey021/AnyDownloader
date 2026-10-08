import threading
import webbrowser
import flet as ft

from src.backend.bug_report import (
    APP_VERSION,
    DEVELOPER_EMAIL,
    build_full_report_markdown,
    build_mailto_url,
    get_recent_debug_logs,
    get_system_diagnostics,
    send_bug_report,
    set_clipboard_text,
)
from src.ui.theme import AppTheme


class BugReportDialog:
    """A sleek, wide, professional Fluent UI modal dialog for submitting bug reports."""

    CATEGORIES = [
        "Download Failed / Extraction Error",
        "Audio / Video Quality Issue",
        "User Interface / Visual Glitch",
        "Application Crash or Freeze",
        "Feature Suggestion",
        "Other Issue",
    ]

    DIALOG_WIDTH = 680

    def __init__(self, page: ft.Page):
        self.page = page
        self.dialog = None
        self.is_submitting = False
        self._cached_diagnostics = None
        self._cached_logs = None
        self._is_preview_expanded = False

        self._build_ui()

    def _build_ui(self):
        # ── 1. INPUT CONTROLS (Edge-to-edge, clean external labels) ──

        # Category Dropdown
        self.category_dd = ft.Dropdown(
            value=self.CATEGORIES[0],
            options=[ft.dropdown.Option(cat) for cat in self.CATEGORIES],
            bgcolor=AppTheme.BACKGROUND,
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            border_radius=8,
            content_padding=ft.Padding(12, 10, 12, 10),
            text_size=13,
            color=AppTheme.TEXT_PRIMARY,
            height=44,
        )

        # Title Field
        self.title_field = ft.TextField(
            hint_text="e.g. YouTube 1080p download fails with 403 Forbidden",
            hint_style=ft.TextStyle(color="#64748b", size=13),
            bgcolor=AppTheme.BACKGROUND,
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            border_radius=8,
            content_padding=ft.Padding(12, 10, 12, 10),
            text_size=13,
            color=AppTheme.TEXT_PRIMARY,
            cursor_color=AppTheme.PRIMARY,
            height=44,
        )

        # Contact Email Field (Optional)
        self.email_field = ft.TextField(
            hint_text="name@example.com (optional, for follow-up notifications)",
            hint_style=ft.TextStyle(color="#64748b", size=13),
            prefix_icon=ft.Icons.ALTERNATE_EMAIL_ROUNDED,
            bgcolor=AppTheme.BACKGROUND,
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            border_radius=8,
            content_padding=ft.Padding(12, 10, 12, 10),
            text_size=13,
            color=AppTheme.TEXT_PRIMARY,
            cursor_color=AppTheme.PRIMARY,
            height=44,
        )

        # Description Field
        self.desc_field = ft.TextField(
            hint_text="What happened? Paste any link you tried to download, what went wrong, and any error message displayed.",
            hint_style=ft.TextStyle(color="#64748b", size=13),
            multiline=True,
            min_lines=3,
            max_lines=5,
            bgcolor=AppTheme.BACKGROUND,
            border_color=AppTheme.SURFACE_VARIANT,
            focused_border_color=AppTheme.PRIMARY,
            border_radius=8,
            content_padding=ft.Padding(12, 12, 12, 12),
            text_size=13,
            color=AppTheme.TEXT_PRIMARY,
            cursor_color=AppTheme.PRIMARY,
        )

        # ── 2. DIAGNOSTICS & LOGS SECTION (Edge-to-edge card with scroll safety) ──
        self.include_diag_cb = ft.Checkbox(
            label="Attach system info & last 50 debug logs",
            value=True,
            active_color=AppTheme.PRIMARY,
            check_color=ft.Colors.WHITE,
            label_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY, size=13, weight=ft.FontWeight.W_500),
            on_change=self._on_diag_toggle,
        )

        self.preview_btn = ft.TextButton(
            "View Details",
            icon=ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
            icon_color=AppTheme.ACCENT,
            style=ft.ButtonStyle(color=AppTheme.ACCENT, padding=ft.Padding(8, 4, 8, 4)),
            on_click=self._toggle_preview,
        )

        # Badges row for quick glance summary
        self.diag_badges_row = ft.Row(
            [
                self._make_badge(ft.Icons.WINDOW_ROUNDED, "Windows"),
                self._make_badge(ft.Icons.TERMINAL_ROUNDED, "Python"),
                self._make_badge(ft.Icons.BOLT_ROUNDED, "yt-dlp"),
                self._make_badge(ft.Icons.MOVIE_FILTER_ROUNDED, "FFmpeg"),
                self._make_badge(ft.Icons.ARTICLE_ROUNDED, "50 Logs"),
            ],
            spacing=8,
            wrap=True,
        )

        # Expandable terminal/details container
        self.preview_text = ft.Text(
            "",
            font_family="Consolas, monospace",
            size=11,
            color="#34d399",
            selectable=True,
        )

        self.preview_expandable = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Bundled Diagnostics Preview", size=11, color=AppTheme.TEXT_SECONDARY, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            ft.TextButton(
                                "Copy Preview",
                                icon=ft.Icons.CONTENT_COPY_ROUNDED,
                                icon_color=AppTheme.ACCENT,
                                style=ft.ButtonStyle(color=AppTheme.ACCENT, padding=ft.Padding(4, 2, 4, 2)),
                                on_click=self._copy_diagnostics_only,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(
                        content=ft.Column([self.preview_text], scroll=ft.ScrollMode.AUTO),
                        height=140,
                        bgcolor="#070b14",
                        border_radius=8,
                        padding=10,
                        border=ft.Border.all(1, "#1e293b"),
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            visible=False,
        )

        self.diag_card = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [self.include_diag_cb, ft.Container(expand=True), self.preview_btn],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.diag_badges_row,
                    self.preview_expandable,
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            bgcolor=AppTheme.BACKGROUND,
            border=ft.Border.all(1, AppTheme.SURFACE_VARIANT),
            border_radius=10,
            padding=ft.Padding(14, 10, 14, 10),
        )

        # ── 3. STATUS & FALLBACK BANNER ──
        self.status_icon = ft.Icon(ft.Icons.INFO_ROUNDED, size=18, color=AppTheme.PRIMARY)
        self.status_text = ft.Text("", size=12, color=AppTheme.TEXT_PRIMARY, expand=True)
        self.status_banner = ft.Container(
            content=ft.Row([self.status_icon, self.status_text], spacing=8),
            bgcolor=AppTheme.BACKGROUND,
            border=ft.Border.all(1, AppTheme.SURFACE_VARIANT),
            border_radius=8,
            padding=ft.Padding(10, 8, 10, 8),
            visible=False,
        )

        self.fallback_row = ft.Row(
            [
                ft.OutlinedButton(
                    "Copy Report",
                    icon=ft.Icons.CONTENT_COPY_ROUNDED,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                    on_click=self._copy_full_report,
                ),
                ft.OutlinedButton(
                    "Send via Email",
                    icon=ft.Icons.EMAIL_ROUNDED,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                    on_click=self._open_email_client,
                ),
                ft.OutlinedButton(
                    "GitHub Issues",
                    icon=ft.Icons.OPEN_IN_NEW_ROUNDED,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                    on_click=lambda _: webbrowser.open("https://github.com/sayandey021/AnyDownloader/issues"),
                ),
            ],
            spacing=8,
            visible=False,
            wrap=True,
        )

        # ── 4. HEADER (Wide, balanced) ──
        header = ft.Container(
            content=ft.Row(
                [
                    # Glowing bug badge
                    ft.Container(
                        content=ft.Icon(ft.Icons.BUG_REPORT_ROUNDED, color="#f43f5e", size=22),
                        bgcolor=ft.Colors.with_opacity(0.12, "#f43f5e"),
                        border=ft.Border.all(1, ft.Colors.with_opacity(0.25, "#f43f5e")),
                        border_radius=10,
                        padding=8,
                    ),
                    ft.Column(
                        [
                            ft.Text("Report an Issue", size=18, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT_PRIMARY),
                            ft.Row(
                                [
                                    ft.Icon(ft.Icons.VERIFIED_ROUNDED, size=13, color=AppTheme.ACCENT),
                                    ft.Text(f"Direct Developer Dispatch • {DEVELOPER_EMAIL}", size=11, color=AppTheme.TEXT_SECONDARY),
                                ],
                                spacing=4,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE_ROUNDED,
                        icon_color=AppTheme.TEXT_SECONDARY,
                        tooltip="Close",
                        on_click=self._close_dialog,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(28, 20, 24, 16),
        )

        # ── 5. FORM BODY (With dedicated right gutter so scrollbar NEVER overlaps) ──
        inner_form_items = ft.Column(
            [
                self._form_row("Issue Category", self.category_dd, required=True),
                self._form_row("Summary / Title", self.title_field, required=True),
                self._form_row("Your Email", self.email_field, required=False, hint="For direct reply"),
                self._form_row("What Happened?", self.desc_field, required=True),
                self.diag_card,
                self.status_banner,
                self.fallback_row,
            ],
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        # Inner container provides 28px left margin and 20px right gutter for the scrollbar
        inner_content_container = ft.Container(
            content=inner_form_items,
            padding=ft.Padding(left=28, right=20, top=16, bottom=16),
        )

        # Scrollable column with dedicated space for the scrollbar
        scrollable_form = ft.Column(
            [inner_content_container],
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            spacing=0,
        )

        form_body = ft.Container(
            content=scrollable_form,
            height=435,
        )

        # ── 6. ACTIONS FOOTER (Compact, sleek Windows 11 style) ──
        self.progress_ring = ft.ProgressRing(width=16, height=16, stroke_width=2, color=ft.Colors.WHITE, visible=False)
        self.submit_btn = ft.FilledButton(
            "Submit Bug Report",
            icon=ft.Icons.SEND_ROUNDED,
            icon_color=ft.Colors.WHITE,
            bgcolor=AppTheme.PRIMARY,
            color=ft.Colors.WHITE,
            height=36,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding(16, 0, 16, 0),
            ),
            on_click=self._on_submit_clicked,
        )

        self.copy_btn = ft.TextButton(
            "Copy Report",
            icon=ft.Icons.CONTENT_COPY_ROUNDED,
            icon_color=AppTheme.TEXT_SECONDARY,
            height=36,
            style=ft.ButtonStyle(
                color=AppTheme.TEXT_SECONDARY,
                padding=ft.Padding(10, 0, 10, 0),
            ),
            tooltip="Copy markdown bug report to clipboard",
            on_click=self._copy_full_report,
        )

        self.cancel_btn = ft.TextButton(
            "Cancel",
            height=36,
            style=ft.ButtonStyle(
                color=AppTheme.TEXT_SECONDARY,
                padding=ft.Padding(12, 0, 12, 0),
            ),
            on_click=self._close_dialog,
        )

        footer = ft.Container(
            content=ft.Row(
                [
                    self.copy_btn,
                    ft.Container(expand=True),
                    self.cancel_btn,
                    self.progress_ring,
                    self.submit_btn,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(20, 6, 20, 8),
        )

        # Complete Modal Container with 680px width
        modal_content = ft.Container(
            content=ft.Column(
                [
                    header,
                    ft.Divider(height=1, thickness=1, color=AppTheme.SURFACE_VARIANT),
                    form_body,
                    ft.Divider(height=1, thickness=1, color=AppTheme.SURFACE_VARIANT),
                    footer,
                ],
                spacing=0,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            width=self.DIALOG_WIDTH,
            bgcolor=AppTheme.SURFACE,
            border_radius=16,
        )

        self.dialog = ft.AlertDialog(
            content=modal_content,
            content_padding=0,
            bgcolor=AppTheme.SURFACE,
            shape=ft.RoundedRectangleBorder(radius=16),
        )

    def _form_row(self, label: str, control: ft.Control, required: bool = False, hint: str = None) -> ft.Column:
        """Builds a clean input group stretching edge-to-edge with external labels."""
        header_items = [
            ft.Text(label, size=12, weight=ft.FontWeight.W_600, color=AppTheme.TEXT_SECONDARY)
        ]
        if required:
            header_items.append(ft.Text("*", size=12, weight=ft.FontWeight.BOLD, color=AppTheme.ERROR))
        if hint:
            header_items.append(ft.Container(expand=True))
            header_items.append(ft.Text(hint, size=11, color="#64748b", italic=True))

        return ft.Column(
            [
                ft.Row(header_items, spacing=3),
                control,
            ],
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def _make_badge(self, icon, text: str) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, size=12, color=AppTheme.ACCENT),
                    ft.Text(text, size=11, color=AppTheme.TEXT_SECONDARY, weight=ft.FontWeight.W_500),
                ],
                spacing=4,
                tight=True,
            ),
            bgcolor=AppTheme.SURFACE,
            border=ft.Border.all(1, AppTheme.SURFACE_VARIANT),
            border_radius=6,
            padding=ft.Padding(7, 3, 9, 3),
        )

    def show(self):
        """Displays the Bug Report modal dialog on the page."""
        threading.Thread(target=self._precompute_diagnostics, daemon=True).start()

        if self.dialog not in self.page.overlay:
            self.page.overlay.append(self.dialog)
        self.dialog.open = True
        self.page.update()

    def _precompute_diagnostics(self):
        try:
            self._cached_diagnostics = get_system_diagnostics()
            self._cached_logs = get_recent_debug_logs(50)
            self._update_preview_content()
        except Exception:
            pass

    def _update_preview_content(self):
        diag = self._cached_diagnostics or get_system_diagnostics()
        logs = self._cached_logs or get_recent_debug_logs(50)

        diag_lines = [f"{k}: {v}" for k, v in diag.items()]
        preview = "=== SYSTEM DIAGNOSTICS ===\n" + "\n".join(diag_lines) + "\n\n=== RECENT DEBUG LOGS (LAST 50 LINES) ===\n" + logs
        self.preview_text.value = preview
        try:
            self.preview_expandable.update()
        except Exception:
            pass

    def _toggle_preview(self, e):
        self._is_preview_expanded = not self._is_preview_expanded
        self.preview_expandable.visible = self._is_preview_expanded
        self.preview_btn.text = "Hide Details" if self._is_preview_expanded else "View Details"
        self.preview_btn.icon = ft.Icons.KEYBOARD_ARROW_UP_ROUNDED if self._is_preview_expanded else ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED
        if self._is_preview_expanded:
            self._update_preview_content()
        self.page.update()

    def _on_diag_toggle(self, e):
        is_checked = self.include_diag_cb.value
        self.diag_badges_row.visible = is_checked
        self.preview_btn.visible = is_checked
        if not is_checked:
            self.preview_expandable.visible = False
            self._is_preview_expanded = False
            self.preview_btn.text = "View Details"
        self.page.update()

    def _copy_diagnostics_only(self, e=None):
        diag = self._cached_diagnostics or get_system_diagnostics()
        logs = self._cached_logs or get_recent_debug_logs(50)
        lines = [f"{k}: {v}" for k, v in diag.items()]
        content = "=== SYSTEM DIAGNOSTICS ===\n" + "\n".join(lines) + "\n\n=== RECENT DEBUG LOGS ===\n" + logs
        set_clipboard_text(content, self.page)
        self._show_status("Diagnostics copied to clipboard!", is_error=False)

    def _copy_full_report(self, e=None):
        markdown = build_full_report_markdown(
            category=self.category_dd.value or "General",
            title=self.title_field.value or "Bug Report",
            description=self.desc_field.value or "No description provided.",
            user_email=self.email_field.value or "",
            include_diagnostics=self.include_diag_cb.value,
            system_info=self._cached_diagnostics,
            logs=self._cached_logs,
        )
        set_clipboard_text(markdown, self.page)
        self._show_status("Full bug report copied to clipboard!", is_error=False)

    def _open_email_client(self, e=None):
        mailto_url = build_mailto_url(
            category=self.category_dd.value or "General",
            title=self.title_field.value or "Bug Report",
            description=self.desc_field.value or "",
            system_info=self._cached_diagnostics if self.include_diag_cb.value else None,
        )
        webbrowser.open(mailto_url)

    def _show_status(self, message: str, is_error: bool = False):
        self.status_banner.visible = True
        self.status_text.value = message
        if is_error:
            self.status_banner.bgcolor = "#450a0a"
            self.status_icon.name = ft.Icons.ERROR_OUTLINE_ROUNDED
            self.status_icon.color = AppTheme.ERROR
            self.fallback_row.visible = True
        else:
            self.status_banner.bgcolor = "#064e3b"
            self.status_icon.name = ft.Icons.CHECK_CIRCLE_ROUNDED
            self.status_icon.color = AppTheme.SUCCESS
        try:
            self.page.update()
        except Exception:
            pass

    def _close_dialog(self, e=None):
        if self.dialog:
            self.dialog.open = False
            self.page.update()

    def _on_submit_clicked(self, e):
        if self.is_submitting:
            return

        title = (self.title_field.value or "").strip()
        description = (self.desc_field.value or "").strip()

        has_error = False
        if not title:
            self.title_field.error_text = "Please enter a brief summary of the issue"
            has_error = True
        else:
            self.title_field.error_text = None

        if not description:
            self.desc_field.error_text = "Please provide some details on what went wrong"
            has_error = True
        else:
            self.desc_field.error_text = None

        if has_error:
            self.page.update()
            return

        self.is_submitting = True
        self.submit_btn.disabled = True
        self.progress_ring.visible = True
        self.status_banner.visible = False
        self.fallback_row.visible = False
        self.page.update()

        category = self.category_dd.value
        user_email = (self.email_field.value or "").strip()
        include_diag = self.include_diag_cb.value

        def submit_worker():
            success, msg, full_report = send_bug_report(
                category=category,
                title=title,
                description=description,
                user_email=user_email,
                include_diagnostics=include_diag,
            )

            def update_ui():
                self.is_submitting = False
                self.progress_ring.visible = False
                self.submit_btn.disabled = False

                if success:
                    self._close_dialog()
                    self._show_success_snackbar()
                else:
                    if msg == "NO_WEBHOOK_URL":
                        error_msg = (
                            "Webhook endpoint not configured yet. You can 1-click copy "
                            f"the full report or send directly to {DEVELOPER_EMAIL}."
                        )
                    else:
                        error_msg = f"Submission error: {msg}. You can copy the full report below."

                    self._show_status(error_msg, is_error=True)

            if hasattr(self.page, "run_thread"):
                self.page.run_thread(update_ui)
            else:
                update_ui()

        threading.Thread(target=submit_worker, daemon=True).start()

    def _show_success_snackbar(self):
        snack = ft.SnackBar(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=AppTheme.SUCCESS, size=24),
                    ft.Column(
                        [
                            ft.Text("Bug Report Delivered!", weight=ft.FontWeight.BOLD, color=AppTheme.TEXT_PRIMARY),
                            ft.Text(f"Successfully sent to {DEVELOPER_EMAIL}. Thank you!", size=12, color=AppTheme.TEXT_SECONDARY),
                        ],
                        spacing=2,
                    ),
                ],
                spacing=12,
            ),
            bgcolor=AppTheme.SURFACE,
            duration=6000,
        )
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()


def open_bug_report_dialog(page: ft.Page):
    """Convenience helper to create and display BugReportDialog."""
    dialog = BugReportDialog(page)
    dialog.show()
    return dialog
