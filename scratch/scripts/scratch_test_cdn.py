import urllib.request

url = "https://i1.r2d2storage.com/manga_69e989c90b8cd/5c685d39f8ef9f137cd61a97bd8348d3/001.webp"
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://hiperdex.com/'
})
try:
    with urllib.request.urlopen(req) as response:
        data = response.read()
        print("Success! Downloaded bytes:", len(data))
except Exception as e:
    print("Error:", e)

import requests
try:
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://hiperdex.com/'})
    r.raise_for_status()
    print("Requests success! Bytes:", len(r.content))
except Exception as e:
    print("Requests error:", e)
