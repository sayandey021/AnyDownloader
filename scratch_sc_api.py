import requests, re

url = 'https://soundcloud.com/soundcloud/sets/the-upload'
r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
scripts = re.findall(r'<script crossorigin src="(https://a-v2\.sndcdn\.com/assets/[^"]+\.js)"></script>', r.text)

client_id = None
for s in scripts:
    js_r = requests.get(s)
    m = re.search(r'client_id:"([a-zA-Z0-9]{32})"', js_r.text)
    if m:
        client_id = m.group(1)
        break

if client_id:
    print("Found Client ID:", client_id)
    api_url = f"https://api-v2.soundcloud.com/resolve?url={url}&client_id={client_id}"
    api_r = requests.get(api_url)
    print("API Response Code:", api_r.status_code)
    if api_r.status_code == 200:
        data = api_r.json()
        print("Title:", data.get('title'))
        print("Tracks count:", len(data.get('tracks', [])))
else:
    print("Client ID not found")
