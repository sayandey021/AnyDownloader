import requests
from bs4 import BeautifulSoup
url = 'https://www.linkedin.com/posts/polycabindia_quick-service-depot-in-siliguri-activity-7467545779612778496-E2he'
r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(r.text, 'html.parser')
og_image = soup.find('meta', property='og:image')
if og_image:
    print('OG Image:', og_image.get('content'))
else:
    print('No og:image found')
