import requests
from curl_cffi import requests as crequests

try:
    r = requests.get('https://httpbin.org/status/403')
    r.raise_for_status()
except Exception as e:
    print("requests error:", str(e))

try:
    r = crequests.get('https://httpbin.org/status/403')
    r.raise_for_status()
except Exception as e:
    print("curl_cffi error:", str(e))
