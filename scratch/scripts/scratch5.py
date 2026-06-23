import requests
import re

url = "https://www.analdin.xxx/videos/781532/gorgeous-milf-mind-boggling-xxx-story/"
resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)

m = re.search(r"preview_url:\s*'([^']+)'", resp.text)
if m:
    print("Found preview_url:", m.group(1))
else:
    print("Not found")

m2 = re.search(r"preview_url1?:\s*'([^']+)'", resp.text)
if m2:
    print("Found preview_url (regex 2):", m2.group(1))
