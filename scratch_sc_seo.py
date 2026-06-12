import requests, re
from bs4 import BeautifulSoup

url = 'https://soundcloud.com/soundcloud/sets/the-upload'
r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(r.text, 'html.parser')

tracks = soup.find_all(itemprop='track')
print(f"Found {len(tracks)} tracks")
for t in tracks:
    a = t.find('a', itemprop='url')
    if a:
        print("Track:", a.get('href').encode('ascii', 'ignore').decode())
