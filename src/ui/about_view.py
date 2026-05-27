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
        version = ft.Text("Version 1.1", size=16, color=AppTheme.TEXT_SECONDARY)
        
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

        self.content = ft.Column([
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
