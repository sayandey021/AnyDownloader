import flet as ft
from src.ui.theme import AppTheme

class AboutView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self._page = page
        self.expand = True
        self.alignment = ft.Alignment(0, 0)
        self.padding = 20
        self.setup_ui()

    def setup_ui(self):
        def create_button(text, icon, url, color, bgcolor=AppTheme.SURFACE):
            return ft.ElevatedButton(
                text,
                icon=icon,
                icon_color=color,
                color=AppTheme.TEXT_PRIMARY,
                bgcolor=bgcolor,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=20),
                    padding=ft.padding.Padding(20, 15, 20, 15)
                ),
                url=url
            )

        # Main Logo
        logo = ft.Image(
            src="icon.png",
            width=100,
            height=100,
            fit=ft.BoxFit.CONTAIN
        )

        title = ft.Text("Any Downloader", size=32, weight=ft.FontWeight.BOLD, color=AppTheme.PRIMARY)
        version = ft.Text("Version 1.6.0", size=16, color=AppTheme.TEXT_SECONDARY)
        
        developer = ft.Text("Developed by Sayan Dey", size=18, color=AppTheme.TEXT_PRIMARY)
        
        description = ft.Text(
            "A fast and lightweight media and audio download client.\nBuilt with Python, Flet, and yt-dlp.",
            size=14,
            color=AppTheme.TEXT_SECONDARY,
            text_align=ft.TextAlign.CENTER
        )

        buttons_row_1 = ft.Row([
            create_button("GitHub", ft.Icons.CODE, "https://github.com/sayandey021", ft.Colors.WHITE),
            create_button("LinkedIn", ft.Icons.LINK, "https://www.linkedin.com/in/sayan-dey021/", ft.Colors.BLUE_400)
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=20)

        support_text = ft.Text(
            "Building free software takes time and passion.\nIf Any Downloader has helped you, please consider supporting its development.\nEvery coffee counts! ☕❤️",
            size=14,
            color=AppTheme.TEXT_SECONDARY,
            text_align=ft.TextAlign.CENTER,
            italic=True
        )

        kofi_btn = ft.ElevatedButton(
            "Support me on Ko-fi",
            icon=ft.Icons.COFFEE,
            icon_color=ft.Colors.WHITE,
            color=ft.Colors.WHITE,
            bgcolor="#FF5E5B",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=20),
                padding=ft.padding.Padding(25, 15, 25, 15)
            ),
            url="https://ko-fi.com/sayandey"
        )

        main_content = ft.Column([
            logo,
            title,
            version,
            ft.Container(height=10),
            developer,
            ft.Container(height=10),
            description,
            ft.Container(height=20),
            buttons_row_1,
            ft.Container(height=30),
            support_text,
            kofi_btn
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        def _show_version_history(e):
            changelog_content = ft.Column([
                ft.Text("v1.6.0(Current)", weight=ft.FontWeight.BOLD, color=AppTheme.PRIMARY),
                ft.Text("• Added supported sites list in 'More' button on Search page\n• Added GIF support for Image downloads\n• Added portrait video resolutions (1920p, 1280p, 640p) and improved resolution tags\n• Added 'Lossless' quality option and accurate file size calculations for .wav and .flac downloads\n• UI updates\n• Known bug Fixes", color=AppTheme.TEXT_SECONDARY, size=13),
                ft.Divider(color=AppTheme.SURFACE_VARIANT),
                ft.Text("v1.5.1", weight=ft.FontWeight.BOLD, color=AppTheme.PRIMARY),
                ft.Text("• Improve website support as native audio platforms\n• Added fallback format logic to prevent download crashes when exact resolutions are missing\n• Replaced silent fetch errors with a prominent Error Panel\n• Improved Sidebar navigation icons with proper fill animations\n• Added percentage to background opacity slider\n• Added setting to suppress notifications\n• UI improvements and settings tweaks", color=AppTheme.TEXT_SECONDARY, size=13),
                ft.Divider(color=AppTheme.SURFACE_VARIANT),
                ft.Text("v1.5", weight=ft.FontWeight.BOLD, color=AppTheme.PRIMARY),
                ft.Text("• Completely revamped search interface and centralized History tab\n• Redesigned Settings with modern UI components (Segmented buttons, color chips)\n• Improved playlist thumbnail fallback logic and filename formatting\n• Fixed developer options layout and Troubleshoot visibility\n• Reused download tasks for retries\n• Better setup screen with restart prompt", color=AppTheme.TEXT_SECONDARY, size=13),
                ft.Divider(color=AppTheme.SURFACE_VARIANT),
                ft.Text("v1.4", weight=ft.FontWeight.BOLD, color=AppTheme.PRIMARY),
                ft.Text("• Added automatic missing dependency installer on first startup\n• Significantly improved FFmpeg download speeds by switching to a faster GitHub mirror", color=AppTheme.TEXT_SECONDARY, size=13),
                ft.Divider(color=AppTheme.SURFACE_VARIANT),
                ft.Text("v1.3", weight=ft.FontWeight.BOLD, color=AppTheme.PRIMARY),
                ft.Text("• Complete redesign of Troubleshoot page with advanced system diagnostics\n• Added live 'Loaded System DLLs' viewer for Windows\n• Added smart 'Fix Missing' button that resolves dependencies silently\n• Improved image opacity slider step configuration\n• Improved Windows batch build scripts (CWD fixes)", color=AppTheme.TEXT_SECONDARY, size=13),
                ft.Divider(color=AppTheme.SURFACE_VARIANT),
                ft.Text("v1.2", weight=ft.FontWeight.BOLD, color=AppTheme.PRIMARY),
                ft.Text("• Added Version History in-app dialog\n• UI alignment fixes and Flet API updates\n• Improved background image settings", color=AppTheme.TEXT_SECONDARY, size=13),
                ft.Divider(color=AppTheme.SURFACE_VARIANT),
                ft.Text("v1.1", weight=ft.FontWeight.BOLD, color=AppTheme.PRIMARY),
                ft.Text("• Added Spotify and Apple Music support\n• Improved metadata embedding\n• Dark/Light theme enhancements", color=AppTheme.TEXT_SECONDARY, size=13),
                ft.Divider(color=AppTheme.SURFACE_VARIANT),
                ft.Text("v1.0", weight=ft.FontWeight.BOLD, color=AppTheme.PRIMARY),
                ft.Text("• Initial release\n• Basic YouTube downloading\n• Playlist support", color=AppTheme.TEXT_SECONDARY, size=13),
            ], scroll=ft.ScrollMode.AUTO, height=300, width=450, spacing=5)
            
            def _close_dialog(e):
                dlg.open = False
                self._page.update()
                
            dlg = ft.AlertDialog(
                title=ft.Row([ft.Icon(ft.Icons.HISTORY_ROUNDED, color=AppTheme.PRIMARY), ft.Text("Version History", color=AppTheme.TEXT_PRIMARY, weight=ft.FontWeight.BOLD)]),
                content=changelog_content,
                bgcolor=AppTheme.SURFACE,
                shape=ft.RoundedRectangleBorder(radius=10),
                actions=[
                    ft.TextButton("Close", on_click=_close_dialog)
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self._page.overlay.append(dlg)
            dlg.open = True
            self._page.update()

        version_history_btn = ft.Container(
            content=ft.ElevatedButton(
                "Version History",
                icon=ft.Icons.HISTORY_ROUNDED,
                color=AppTheme.TEXT_PRIMARY,
                bgcolor=AppTheme.SURFACE_VARIANT,
                on_click=_show_version_history
            ),
            alignment=ft.Alignment(1, -1),
            padding=10
        )

        self.content = ft.Stack([
            ft.Container(content=main_content, alignment=ft.Alignment(0, 0), expand=True),
            version_history_btn
        ], expand=True)
