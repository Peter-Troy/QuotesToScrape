# install Libraries needed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options  # Firefox options
import json
import time
import boto3
import os

# Set up Firefox options
firefox_options = Options()
firefox_options.add_argument("--headless")  # Run browser in headless mode (no UI)
firefox_options.add_argument("--no-sandbox")  # Use no sandbox mode (important for cloud environments)

# Start Firefox browser
driver = webdriver.Firefox(options=firefox_options)
driver.get("http://quotes.toscrape.com/search.aspx")
wait = WebDriverWait(driver, 10)

# Get all authors from dropdown, skipping the first option (index 0)
author_select = Select(wait.until(EC.presence_of_element_located((By.ID, 'author'))))
authors = [opt.text for opt in author_select.options if opt.text.strip()][1:]  # Skip the first author (index 0)

# Prepare a list to hold all the quotes data
all_quotes = []

for author in authors:
    driver.get("http://quotes.toscrape.com/search.aspx")
    wait.until(EC.presence_of_element_located((By.ID, 'author')))

    # Select the author (skip the first author)
    author_dropdown = Select(driver.find_element(By.ID, 'author'))
    author_dropdown.select_by_visible_text(author)

    # Wait a moment for tags to update
    time.sleep(1)

    # Get tags for the selected author, skipping the first option (index 0)
    tag_dropdown = Select(driver.find_element(By.ID, 'tag'))
    tags = [opt.text for opt in tag_dropdown.options if opt.text.strip()][1:]  # Skip the first tag (index 0)

    for tag in tags:
        # Select tag (skip the first tag)
        tag_dropdown = Select(driver.find_element(By.ID, 'tag'))  # Get the dropdown again to avoid errors
        tag_dropdown.select_by_visible_text(tag)

        # Click Search
        search_button = driver.find_element(By.CSS_SELECTOR, 'input.btn.btn-default')
        search_button.click()

        try:
            # Wait for quote results to appear
            quotes = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "quote"))
            )

            for quote in quotes:
                text = quote.find_element(By.CLASS_NAME, "content").text.strip()
                all_quotes.append({"author": author, "tag": tag, "quote": text})
                print(f"✅ {author} | {tag} | {text[:50]}...")

        except:
            print(f"⚠ No quotes found for {author} - {tag}")

# Save data to JSON
with open("quotes_by_author_and_tag.json", "w", encoding="utf-8") as json_file:
    json.dump(all_quotes, json_file, indent=4, ensure_ascii=False)

driver.quit()
print("All quotes saved to quotes_by_author_and_tag.json")

def upload_to_s3(file_name, bucket_name, object_name=None):
    if object_name is None:
        object_name = file_name

    # Make sure file exists before attempting to upload
    if not os.path.exists(file_name):
        print(f"File {file_name} does not exist.")
        return

    # Create an S3 client
    s3 = boto3.client('s3')

    try:
        # Upload the file to S3
        s3.upload_file(file_name, bucket_name, object_name)
        print(f"Uploaded {file_name} to s3://{bucket_name}/{object_name}")
    except Exception as e:
        print(f"Upload failed: {e}")

# Upload the JSON file to S3
upload_to_s3("quotes_by_author_and_tag.json", "quotes-scraper-petermacero")
