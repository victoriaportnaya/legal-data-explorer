import requests
from bs4 import BeautifulSoup
import json
import re
import PyPDF2

# 1. Parse Criminal Code of Ukraine
cc_url = 'https://zakon.rada.gov.ua/laws/show/2341-14#Text'
cc_resp = requests.get(cc_url)
cc_soup = BeautifulSoup(cc_resp.text, 'html.parser')
cc_articles = []
for tag in cc_soup.find_all(['p', 'div']):
    text = tag.get_text(strip=True)
    m = re.match(r'^Стаття\s*(\d+[\-\d]*)\.?\s*(.*)', text)
    if m:
        number = m.group(1)
        title = m.group(2)
        # Collect following siblings as article text
        article_text = ''
        sib = tag.find_next_sibling()
        while sib and not sib.get_text(strip=True).startswith('Стаття'):
            article_text += sib.get_text(strip=True) + '\n'
            sib = sib.find_next_sibling()
        cc_articles.append({
            'source': 'Criminal Code of Ukraine',
            'number': number,
            'title': title,
            'text': article_text.strip()
        })
with open('criminal_code_ukraine.json', 'w', encoding='utf-8') as f:
    json.dump(cc_articles, f, ensure_ascii=False, indent=2)

# 2. Parse Rome Statute
rome_url = 'https://www.ohchr.org/en/instruments-mechanisms/instruments/rome-statute-international-criminal-court'
rome_resp = requests.get(rome_url)
rome_soup = BeautifulSoup(rome_resp.text, 'html.parser')
rome_articles = []
# Try h2/h3 first
for tag in rome_soup.find_all(['h3', 'h2']):
    text = tag.get_text(strip=True)
    m = re.match(r'^Article\s*(\d+[A-Za-z]*)\.?\s*(.*)', text)
    if m:
        number = m.group(1)
        title = m.group(2)
        # Collect following siblings as article text
        article_text = ''
        sib = tag.find_next_sibling()
        while sib and sib.name not in ['h2', 'h3']:
            article_text += sib.get_text(strip=True) + '\n'
            sib = sib.find_next_sibling()
        rome_articles.append({
            'source': 'Rome Statute',
            'number': number,
            'title': title,
            'text': article_text.strip()
        })
# If no articles found, try <p> tags
if not rome_articles:
    for tag in rome_soup.find_all('p'):
        text = tag.get_text(strip=True)
        m = re.match(r'^Article\s*(\d+[A-Za-z]*)\.?\s*(.*)', text)
        if m:
            number = m.group(1)
            title = m.group(2)
            # Collect following siblings as article text
            article_text = ''
            sib = tag.find_next_sibling()
            while sib and sib.name != 'p':
                article_text += sib.get_text(strip=True) + '\n'
                sib = sib.find_next_sibling()
            rome_articles.append({
                'source': 'Rome Statute',
                'number': number,
                'title': title,
                'text': article_text.strip()
            })
print(f"[DEBUG] Parsed {len(rome_articles)} Rome Statute articles.")
for art in rome_articles[:5]:
    print(f"[DEBUG] Article {art['number']}: {art['title']}")
with open('rome_statute.json', 'w', encoding='utf-8') as f:
    json.dump(rome_articles, f, ensure_ascii=False, indent=2)

# 3. Parse Geneva Conventions (PDF) - improved splitting
pdf_url = 'https://www.icrc.org/sites/default/files/external/doc/en/assets/files/publications/icrc-002-0173.pdf'
pdf_resp = requests.get(pdf_url)
with open('geneva_conventions.pdf', 'wb') as f:
    f.write(pdf_resp.content)
geneva_articles = []
with open('geneva_conventions.pdf', 'rb') as f:
    reader = PyPDF2.PdfReader(f)
    text = ''
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + '\n'
    # Improved regex: split by 'Article X' at the start of a line
    article_matches = list(re.finditer(r'(?m)^\s*(Article|ARTICLE)\s*(\d+[A-Za-z]*)\.?\s*(.*?)\n', text))
    for i, m in enumerate(article_matches):
        number = m.group(2)
        title = m.group(3)
        start = m.end()
        end = article_matches[i+1].start() if i+1 < len(article_matches) else len(text)
        article_text = text[start:end].strip()
        geneva_articles.append({
            'source': 'Geneva Conventions',
            'number': number,
            'title': title,
            'text': article_text
        })
with open('geneva_conventions.json', 'w', encoding='utf-8') as f:
    json.dump(geneva_articles, f, ensure_ascii=False, indent=2)

print('Parsed legal documents.') 