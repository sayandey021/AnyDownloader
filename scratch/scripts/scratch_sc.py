import requests, re, json
from bs4 import BeautifulSoup

url = 'https://soundcloud.com/soundcloud/sets/the-upload'
r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(r.text, 'html.parser')

scripts = soup.find_all('script')
hydration_data = None
for s in scripts:
    if s.string and 'window.__sc_hydration' in s.string:
        m = re.search(r'window\.__sc_hydration = (\[.*\]);', s.string)
        if m:
            try:
                hydration_data = json.loads(m.group(1))
            except:
                pass
        break

if hydration_data:
    for item in hydration_data:
        print("Hydratable type:", item.get('hydratable'))
