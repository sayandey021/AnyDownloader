import requests
from bs4 import BeautifulSoup

url = "https://speakerdeck.com/speakerdeck/welcome-to-speaker-deck"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}
try:
    resp = requests.get(url, headers=headers, timeout=10)
    print("Status:", resp.status_code)
    soup = BeautifulSoup(resp.text, 'html.parser')
    pdf_link = soup.select_one('a[title="Download PDF"]')
    if pdf_link:
        print("Found PDF link:", pdf_link.get('href'))
    else:
        print("PDF link not found. HTML snippet:")
        print(resp.text[:1000])
        # Find any links with PDF or download
        links = soup.find_all('a')
        dl_links = [a for a in links if 'download' in a.get('href', '').lower() or 'pdf' in str(a).lower()]
        print("Possible DL links:", dl_links)
except Exception as e:
    print("Error:", e)
