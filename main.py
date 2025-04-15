import requests
from bs4 import BeautifulSoup
import json

BASE_URL = "http://quotes.toscrape.com/search.aspx"

# Start a session to persist cookies and headers
session = requests.Session()

# Step 1: Get initial form values to extract authors and tags
response = session.get(BASE_URL)
soup = BeautifulSoup(response.text, "html.parser")

# Extract authors
author_select = soup.find("select", {"id": "author"})
authors = [option.text.strip() for option in author_select.find_all("option") if option.text.strip()][1:]

# Final data to store
all_quotes = []

# Loop through each author and associated tags
for author in authors:
    print(f"\n🔍 Searching quotes for author: {author}")
    
    # Get updated tags for the selected author (requires submitting form with only author)
    form_data_author = {
        "author": author,
        "tag": "",
        "submit_button": "Search"
    }
    res_author = session.post(BASE_URL, data=form_data_author)
    soup = BeautifulSoup(res_author.text, "html.parser")
    
    # Get updated tag list
    tag_select = soup.find("select", {"id": "tag"})
    if not tag_select:
        continue
    tags = [option.text.strip() for option in tag_select.find_all("option") if option.text.strip()][1:]
    
    for tag in tags:
        print(f"🧠 Trying tag: {tag}")
        form_data = {
            "author": author,
            "tag": tag,
            "submit_button": "Search"
        }

        result = session.post(BASE_URL, data=form_data)
        result_soup = BeautifulSoup(result.text, "html.parser")
        quotes = result_soup.find_all("div", class_="quote")

        if not quotes:
            print(f"⚠ No quotes found for {author} - {tag}")
            continue

        for quote_div in quotes:
            text = quote_div.find("span", class_="content").text.strip()
            all_quotes.append({
                "author": author,
                "tag": tag,
                "quote": text
            })
            print(f"✅ {author} | {tag} | {text[:50]}...")

# Save to JSON
with open("quotes_by_author_and_tag.json", "w", encoding="utf-8") as f:
    json.dump(all_quotes, f, indent=4, ensure_ascii=False)

print("\n🎉 All quotes saved to quotes_by_author_and_tag.json")
