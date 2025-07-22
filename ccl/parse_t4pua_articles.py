import requests
from bs4 import BeautifulSoup
import json
import time

ARTICLE_URLS = [
    "https://t4pua.org/en/25",
    "https://t4pua.org/en/22"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

articles = []

def robust_get(url, retries=3, delay=3):
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            return resp
        except Exception as e:
            print(f"Error fetching {url} (attempt {attempt+1}): {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                return None

for url in ARTICLE_URLS:
    resp = robust_get(url)
    if not resp:
        print(f"Failed to fetch {url} after retries.")
        continue
    soup = BeautifulSoup(resp.text, 'html.parser')
    grid = soup.find('div', id='grid')
    if not grid:
        print(f"No grid found in {url}")
        continue
    for a in grid.find_all('a', class_='listlink'):
        article_url = a.get('href')
        date = a.find('div', class_='sect_date')
        title = a.find('h3')
        summary = a.find('div', class_='list_short')
        articles.append({
            "title": title.get_text(strip=True) if title else None,
            "date": date.get_text(strip=True) if date else None,
            "url": article_url,
            "content": summary.get_text(strip=True) if summary else None
        })

with open('t4pua_articles.json', 'w', encoding='utf-8') as f:
    json.dump(articles, f, ensure_ascii=False, indent=2)

print(f"Parsed {len(articles)} articles.") 