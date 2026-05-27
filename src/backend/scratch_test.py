import flet as ft
import time

def main(page: ft.Page):
    page.window.prevent_close = True
    def window_event(e):
        with open("event_log.txt", "a") as f:
            f.write(f"type={e.type}, name={e.name}, data={e.data}\n")
        if e.data == "close" or getattr(e, 'type', '') == "close":
            page.window.destroy()
    page.window.on_event = window_event
    page.add(ft.Text("Test"))

ft.app(target=main)
