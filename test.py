from bs4 import BeautifulSoup
import requests
from datetime import datetime

url = "https://www.studierendenwerk-kaiserslautern.de/de/essen/speiseplaene"
print(f"Fetching URL: {url}")

# Add headers to mimic a browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0'
}

response = requests.get(url, headers=headers)

soup = BeautifulSoup(response.text, 'html.parser')

# Safe to html
with open('output.html', 'w', encoding='utf-8') as file:
    file.write(response.text)
