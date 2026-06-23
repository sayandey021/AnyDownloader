import re, json
from curl_cffi import requests

url = 'https://soundcloud.com/soundcloud/sets/the-upload'
r = requests.get(url, impersonate="chrome")
m = re.search(r'window\.__sc_hydration = (\[.*\]);', r.text)
if m:
    with open('sc_hydration.json', 'w') as f:
        f.write(m.group(1))
    print("Saved sc_hydration.json")
