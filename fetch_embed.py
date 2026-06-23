import sys
import os
from curl_cffi import requests

try:
    url = "https://www.scribd.com/embeds/587149423/content"
    resp = requests.get(url, impersonate="chrome")
    
    with open("scribd_embed.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("Success")
except Exception as e:
    print("Error:", e)
