import urllib.request
import json
import os

url = "https://api.github.com/repos/Neelfrost/slideshare-dl/contents/slideshare_dl"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode('utf-8'))
    for item in data:
        print(item['name'], item['download_url'])
