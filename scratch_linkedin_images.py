import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO

r = requests.get('https://www.linkedin.com/posts/polycabindia_quick-service-depot-in-siliguri-activity-7467545779612778496-E2he', headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(r.text, 'html.parser')
imgs = [img.get('src') for img in soup.find_all('img') if img.get('src') and 'media.licdn.com' in img.get('src')]

for url in imgs:
    try:
        ir = requests.get(url)
        sz = Image.open(BytesIO(ir.content)).size
        print(sz, url)
    except:
        pass
