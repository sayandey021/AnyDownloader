import re
from curl_cffi import requests

url = 'https://soundcloud.com/soundcloud/sets/the-upload'
r = requests.get(url, impersonate="chrome")
scripts = re.findall(r'<script crossorigin src="(https://a-v2\.sndcdn\.com/assets/[^"]+\.js)"></script>', r.text)

print("Hydration:", "window.__sc_hydration" in r.text)
