import subprocess
import json
import sys

url = "https://tapas.io/event/9uwRGV"

print("--- yt-dlp ---")
try:
    res = subprocess.run(["yt-dlp", "-j", url], capture_output=True, text=True)
    if res.stdout:
        print("yt-dlp success. Output snippet:")
        print(res.stdout[:500])
    else:
        print("yt-dlp failed:")
        print(res.stderr)
except Exception as e:
    print(f"yt-dlp execution error: {e}")

print("\n--- gallery-dl ---")
try:
    res = subprocess.run(["gallery-dl", "-j", url], capture_output=True, text=True)
    if res.stdout:
        print("gallery-dl success. Output snippet:")
        print(res.stdout[:500])
    else:
        print("gallery-dl failed:")
        print(res.stderr)
except Exception as e:
    print(f"gallery-dl execution error: {e}")
