import requests
from bs4 import BeautifulSoup
import re

url = "https://megaplay.buzz/stream/s-2/142018/sub"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://9anime.blue/"
}
try:
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {resp.status_code}")
    html = resp.text
    
    print("\n--- M3U8 Links ---")
    for m in re.finditer(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', html):
        print(m.group(1))
        
    print("\n--- MP4 Links ---")
    for m in re.finditer(r'(https?://[^\s\'"]+\.mp4[^\s\'"]*)', html):
        print(m.group(1))
        
    print("\n--- Javascript Sources ---")
    soup = BeautifulSoup(html, 'html.parser')
    for s in soup.find_all('script'):
        if s.get('src'):
            print(s.get('src'))
        if s.string and ('m3u8' in s.string or 'mp4' in s.string or 'sources' in s.string or 'file' in s.string):
            print("Found interesting inline script")
            print(s.string[:200])

except Exception as e:
    print(f"Error: {e}")
