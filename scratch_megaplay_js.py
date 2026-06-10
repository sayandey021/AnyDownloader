import requests
url = "https://megaplay.buzz/lib/e1-player.min.js?v=2.0"
headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(url, headers=headers)
with open('megaplay_js.txt', 'w', encoding='utf-8') as f:
    f.write(resp.text)
