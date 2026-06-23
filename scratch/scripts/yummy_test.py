import json
import re
from bs4 import BeautifulSoup
from curl_cffi import requests

url = "https://old.yummyani.me/catalog/item/mech-i-zhezl-vistorii-2"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print(f"Fetching {url}...")
try:
    response = requests.get(url, headers=headers, impersonate="chrome120")
    print(f"Status Code: {response.status_code}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract page_id
    page_id_meta = soup.find('meta', {'id': 'page_id'})
    if page_id_meta:
        print(f"Page ID: {page_id_meta.get('content')}")
        
    # Look for scripts
    scripts = soup.find_all('script')
    for i, script in enumerate(scripts):
        if script.string:
            if 'episodes' in script.string or 'player' in script.string or 'video' in script.string:
                print(f"\n--- Found interesting script #{i} ---")
                print(script.string[:500])
                
    # Look for specific div
    video_div = soup.find('div', id='video')
    if video_div:
        print(f"\n--- Found Video Div ---")
        print(video_div.prettify())
        
    # Find list of episodes if it exists in DOM
    print("\n--- Looking for episodes list ---")
    episodes = soup.find_all(class_=re.compile("episode|ep-list|player-list"))
    if episodes:
        print(f"Found {len(episodes)} episode elements.")
    else:
        print("No episode elements found using class regex.")
        
    # Dump all elements that have data-id or data-episode
    items = soup.find_all(attrs={"data-id": True})
    print(f"\n--- Found {len(items)} items with data-id ---")
    for item in items[:10]:
        print(f"{item.name} class={item.get('class')} data-id={item.get('data-id')}")
        
except Exception as e:
    print(f"Error: {e}")
