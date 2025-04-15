# part1_scraper.py
import requests
from bs4 import BeautifulSoup
import csv
import time
import re
import logging
from datetime import datetime
import os
import boto3

# Set up logging configuration
logging.basicConfig(filename='quotes_scraper.log', level=logging.INFO)

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

        # Add timestamp for each quote
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        extract_quotes.append({
            "author": quote_author,
            "tags": ", ".join(tags),
            "text": quote_text,
            "log_status": timestamp  # Timestamp for when the quote was logged
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
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    fieldnames = ["author", "tags", "text", "log_status"]

    try:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            # Write each quote and its log_status (timestamp)
            for quote in author_quotes:
                writer.writerow(quote)

        # Log the successful operation
        logging.info(f"Saved {len(author_quotes)} quotes to {filename}")
    except Exception as e:
        logging.error(f"Error while saving to CSV: {e}")
        print(f"❌ Error while saving to CSV: {e}")

def upload_to_s3(local_file, bucket_name, s3_key):
    """Upload the CSV file to an S3 bucket."""
    s3 = boto3.client('s3')
    try:
        s3.upload_file(local_file, bucket_name, s3_key)
        print(f"✅ Uploaded {local_file} to s3://{bucket_name}/{s3_key}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")

if __name__ == "__main__":
    # Step 1: Scrape all quotes from the website
    quotes = scrape_all_quotes()

    # Step 2: Save the quotes to a CSV file
    save_to_csv(quotes)

    # Step 3: Upload the CSV to an S3 bucket
    upload_to_s3("output/quotes_output.csv", "quotes-scraper-petermacero", "quotes/quotes_output.csv")
