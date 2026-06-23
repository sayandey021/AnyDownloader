from bs4 import BeautifulSoup

with open('analdin.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

print("ALL IMGs:")
for img in soup.find_all('img'):
    print(img.get('src') or img.get('data-src'))

print("ALL IFRAMEs:")
for iframe in soup.find_all('iframe'):
    print(iframe.get('src'))

print("JSON-LD scripts:")
for s in soup.find_all('script', type='application/ld+json'):
    print(s.string)
