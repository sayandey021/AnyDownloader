import subprocess
import os
import sys

class CookieManager:
    @staticmethod
    def get_anydownloader_cookie_path():
        appdata = os.getenv('APPDATA')
        if not appdata:
            appdata = os.path.expanduser('~')
        path = os.path.join(appdata, 'AnyDownloader', 'anydownloader_cookies.txt')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    @staticmethod
    def open_login_window(url):
        output_file = CookieManager.get_anydownloader_cookie_path()
        script_path = os.path.join(os.path.dirname(__file__), 'cookie_browser.py')
        
        # We run this synchronously or asynchronously depending on caller
        # Because we want to know when it finishes, we can just run it using subprocess
        try:
            subprocess.run([sys.executable, script_path, url, output_file], check=True)
            return output_file
        except Exception as e:
            print(f"[CookieManager] Failed to run cookie browser: {e}")
            return None
