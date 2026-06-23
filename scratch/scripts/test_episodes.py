import requests
from bs4 import BeautifulSoup

url = "https://9anime.org.lv/anime/classroom-of-the-elite-iv/"
headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, 'html.parser')

ep_links = []
# Try common Animestream episode list structures
eplist = soup.find('div', class_='eplister')
if eplist:
    for a in eplist.find_all('a'):
        if a.get('href') and 'episode' in a.get('href'):
            ep_links.append(a.get('href'))

# Try episodes-ul
ul = soup.find('ul', class_='episodes-ul') or soup.find('ul', id='episodes')
if ul:
    for a in ul.find_all('a'):
        if a.get('href'):
            ep_links.append(a.get('href'))

if not ep_links:
    # Try just generic anchors with 'episode' in the URL
    for a in soup.find_all('a'):
        href = a.get('href')
        if href and '/classroom-of-the-elite-iv-episode-' in href:
            ep_links.append(href)

print(f"Found {len(ep_links)} episodes")
for ep in ep_links[:5]:
    print(ep)
