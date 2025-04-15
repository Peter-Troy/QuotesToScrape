# part1_scraper.py
import requests
from bs4 import BeautifulSoup
import csv
import time
import re


def get_page(url):
    """Fetch the content of a page with error handling."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None


def parse_quotes(html):
    """Extract quotes, authors, and tags from page HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    extract_quotes = []

    quote_elements = soup.find_all("div", class_="quote")

    for quote in quote_elements:
        author = quote.find("small", class_="author")
        tag_elements = quote.find_all("a", class_="tag")
        text = quote.find("span", class_="text")

        # Handle potential missing elements
        quote_author = author.get_text(strip=True) if author else "Unknown"
        tags = [tag.get_text(strip=True) for tag in tag_elements]
        quote_text = text.get_text(strip=True) if text else "N/A"
        quote_text = re.sub(r'[“”]', '"', quote_text)  # Replace smart quotes with plain double quotes
        quote_text = re.sub(r"[‘’]", "'", quote_text)  # Replace smart apostrophes with straight apostrophes
        quote_text = re.sub(r'[^\x00-\x7F]+', '', quote_text)  # Remove any remaining non-ASCII chars

        extract_quotes.append({
            "author": quote_author,
            "tags": ", ".join(tags),
            "text": quote_text
        })

    return extract_quotes


def scrape_all_quotes(base_url="http://quotes.toscrape.com"):
    """Scrape all quotes from all pages."""
    all_quotes = []
    page = 1

    while True:
        url = f"{base_url}/page/{page}/"
        print(f"Scraping {url}...")
        html = get_page(url)
        if not html:
            break

        page_quotes = parse_quotes(html)
        if not page_quotes:
            print("No more quotes found. Stopping.")
            break

        all_quotes.extend(page_quotes)
        page += 1
        time.sleep(1)  # Be nice to the server

    return all_quotes


def save_to_csv(author_quotes, filename="output/quotes_output.csv"):
    """Save the list of quotes to a CSV file."""
    import os
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["author", "tags", "text"])
        writer.writeheader()
        writer.writerows(author_quotes)

    print(f"Saved {len(author_quotes)} quotes to {filename}")


if __name__ == "__main__":
    quotes = scrape_all_quotes()
    save_to_csv(quotes)
