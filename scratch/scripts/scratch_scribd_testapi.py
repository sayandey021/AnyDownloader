import requests
from bs4 import BeautifulSoup
import json

def test_downscribd(url):
    print("Testing downscribd.com")
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    })
    try:
        res = session.get('https://downscribd.com/')
        print("GET downscribd:", res.status_code)
    except Exception as e:
        print("Error:", e)

def test_scribdvdownloaders(url):
    print("\nTesting scribd.vdownloaders.com")
    try:
        res = requests.post('https://scribd.vdownloaders.com/api/generate', json={'url': url})
        print("POST response:", res.status_code, res.text)
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    test_url = 'https://www.scribd.com/document/55949937/33-Strategies-of-War'
    test_downscribd(test_url)
    test_scribdvdownloaders(test_url)
