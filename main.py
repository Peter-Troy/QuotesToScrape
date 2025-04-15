import requests
from bs4 import BeautifulSoup
import json
import boto3
import os

BASE_URL = "http://quotes.toscrape.com/search.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

session = requests.Session()
session.headers.update(HEADERS)

def get_dropdown_options(soup, element_id):
    select = soup.find("select", id=element_id)
    if not select:
        return []
    return [option.text.strip() for option in select.find_all("option") if option.text.strip()][1:]

def get_updated_tag_options(author):
    payload = {"author": author}
    response = session.post(BASE_URL, data=payload)
    soup = BeautifulSoup(response.content, "html.parser")
    return get_dropdown_options(soup, "tag")

def get_quotes(author, tag):
    payload = {"author": author, "tag": tag}
    response = session.post(BASE_URL, data=payload)
    soup = BeautifulSoup(response.content, "html.parser")
    quotes = soup.find_all("div", class_="quote")
    results = []
    for quote in quotes:
        content = quote.find("span", class_="content")
        if content:
            results.append({"author": author, "tag": tag, "quote": content.text.strip()})
    return results

# Step 1: Get initial page to extract authors
response = session.get(BASE_URL)
soup = BeautifulSoup(response.content, "html.parser")

authors = get_dropdown_options(soup, "author")
all_quotes = []

for author in authors:
    tags = get_updated_tag_options(author)
    for tag in tags:
        quotes = get_quotes(author, tag)
        if quotes:
            print(f"✅ {author} | {tag} | {quotes[0]['quote'][:50]}...")
            all_quotes.extend(quotes)
        else:
            print(f"⚠ No quotes found for {author} - {tag}")

# Save to JSON
filename = "quotes_by_author_and_tag.json"
with open(filename, "w", encoding="utf-8") as f:
    json.dump(all_quotes, f, indent=4, ensure_ascii=False)

print(f"All quotes saved to {filename}")

# Upload to S3
def upload_to_s3(file_name, bucket_name, object_name=None):
    if object_name is None:
        object_name = file_name
    if not os.path.exists(file_name):
        print(f"File {file_name} does not exist.")
        return
    s3 = boto3.client("s3")
    try:
        s3.upload_file(file_name, bucket_name, object_name)
        print(f"Uploaded {file_name} to s3://{bucket_name}/{object_name}")
    except Exception as e:
        print(f"Upload failed: {e}")

# Replace with your actual bucket name
upload_to_s3(filename, "quotes-scraper-petermacero")
