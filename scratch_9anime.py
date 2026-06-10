import requests
from bs4 import BeautifulSoup
import re
import json

url = "https://9anime.blue/anime/demon-slayer-kimetsu-no-yaiba-infinity-castle/episode-1/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
try:
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {resp.status_code}")
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    print("\n--- IFRAMES ---")
    for iframe in soup.find_all('iframe'):
        print(iframe.get('src'))
        
    print("\n--- VIDEO TAGS ---")
    for video in soup.find_all('video'):
        print(video.get('src'))
        for source in video.find_all('source'):
            print(source.get('src'))

    print("\n--- SERVERS ---")
    servers = soup.select('div.server-item a, a.server-link, li.server a')
    for s in servers:
        print(s.get('data-video') or s.get('href') or s.get('data-id'))
        
    print("\n--- JS VARIABLES ---")
    scripts = soup.find_all('script')
    for s in scripts:
        if s.string and ('player' in s.string.lower() or 'video' in s.string.lower() or 'file' in s.string.lower()):
            print("Found interesting script...")
            # print(s.string[:500])
except Exception as e:
    print(f"Error: {e}")
