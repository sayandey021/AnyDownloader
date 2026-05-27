import flet as ft
def main(page: ft.Page):
    page.window.prevent_close = True
    def close_dlg(e):
        dlg.open = False
        page.update()
        page.window.prevent_close = False
        page.window.destroy()

    dlg = ft.AlertDialog(title=ft.Text("Close?"), actions=[ft.TextButton("Yes", on_click=close_dlg)])

    def window_event(e):
        if getattr(e, 'type', getattr(e, 'data', '')) == 'close' or e.data == 'close':
            print("Trying to show dialog")
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

    page.window.on_event = window_event
    page.add(ft.Text("Close me!"))

ft.app(target=main)
