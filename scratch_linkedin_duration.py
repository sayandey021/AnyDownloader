import requests, re
r = requests.get('https://www.linkedin.com/posts/polycabindia_quick-service-depot-in-siliguri-activity-7467545779612778496-E2he', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
print('duration:', re.findall(r'"duration":(\d+)', r.text))
print('durationMs:', re.findall(r'"durationMs":(\d+)', r.text))
print('duration_seconds:', re.findall(r'duration=(\d+)', r.text))
print('duration:', re.findall(r'"duration":([0-9.]+)', r.text))
