import requests
import re
import json

url = "https://www.behance.net/gallery/241795869/Porsche-The-Coded-Love-Letter"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
response = requests.get(url, headers=headers)
html = response.text

print(f"HTML Length: {len(html)}")

videos = []

# Approach 1: Look for .mp4 in the HTML
mp4_links = re.findall(r'https?://[^"\'\s]+\.mp4', html)
print(f"Found {len(mp4_links)} mp4 links: {set(mp4_links)}")

# Approach 2: Look for m3u8
m3u8_links = re.findall(r'https?://[^"\'\s]+\.m3u8', html)
print(f"Found {len(m3u8_links)} m3u8 links: {set(m3u8_links)}")

# Approach 3: Look for behance video player JSON data
# Sometimes it's in window.__INITIAL_STATE__
state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', html)
if state_match:
    print("Found window.__INITIAL_STATE__")
    try:
        state = json.loads(state_match.group(1))
        # Save to file to inspect
        with open("scratch_behance_state.json", "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except:
        pass

