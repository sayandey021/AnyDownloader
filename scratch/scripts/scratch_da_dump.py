import os, json
from src.backend.downloader import DownloaderBackend
from src.backend.settings import SettingsManager
import subprocess

url = "https://www.deviantart.com/horrorguy23/art/Horror-OC-James-Mitchel-929740410"

# run gallery-dl --dump-json
try:
    print("Running gallery-dl dump-json")
    gallery_dl_exe = 'gallery-dl'
    process = subprocess.Popen(
        [gallery_dl_exe, '--dump-json', url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        universal_newlines=True
    )
    stdout, stderr = process.communicate(timeout=15)
    print("=== STDOUT ===")
    print(stdout)
except Exception as e:
    print("Error:", e)
