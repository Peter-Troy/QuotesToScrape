from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import json
import boto3
import os

# Set up Chrome options for headless operation
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# ChromeDriver setup
chromedriver_path = '/usr/local/bin/chromedriver'
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.get("http://quotes.toscrape.com/search.aspx")
wait = WebDriverWait(driver, 10)

def wait_for_element(locator, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.visibility_of_element_located(locator))

# Get all authors (skip the first placeholder)
author_select = Select(wait_for_element((By.ID, 'author')))
authors = [opt.text for opt in author_select.options if opt.text.strip()][1:]

all_quotes = []

for author in authors:
    print(f"\n🔍 Searching quotes by: {author}")
    driver.get("http://quotes.toscrape.com/search.aspx")
    wait_for_element((By.ID, 'author'))

    author_dropdown = Select(driver.find_element(By.ID, 'author'))
    author_dropdown.select_by_visible_text(author)
    time.sleep(1)  # Let tags load

    tag_dropdown = Select(driver.find_element(By.ID, 'tag'))
    tags = [opt.text for opt in tag_dropdown.options if opt.text.strip()][1:]

    for tag in tags:
        print(f"➡ Selecting tag: {tag}")
        tag_dropdown = Select(driver.find_element(By.ID, 'tag'))  # Re-locate each loop
        tag_dropdown.select_by_visible_text(tag)
        time.sleep(1)

        # Click Search button
        try:
            search_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input.btn.btn-default')))
            try:
                ActionChains(driver).move_to_element(search_button).click().perform()
            except:
                search_button.click()
        except Exception as e:
            print(f"⚠ Could not click search button: {e}")
            continue

        # Extract quotes
        try:
            quotes = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "quote"))
            )

            for quote in quotes:
                text = quote.find_element(By.CLASS_NAME, "content").text.strip()
                all_quotes.append({"author": author, "tag": tag, "quote": text})
                print(f"✅ {author} | {tag} | {text[:50]}...")
        except Exception as e:
            print(f"⚠ No quotes found for {author} - {tag}. Error: {e}")

# Save to JSON
json_file_path = "quotes_by_author_and_tag.json"
with open(json_file_path, "w", encoding="utf-8") as json_file:
    json.dump(all_quotes, json_file, indent=4, ensure_ascii=False)

driver.quit()
print(f"\n📁 All quotes saved to {json_file_path}")

# Upload to S3
def upload_to_s3(file_name, bucket_name, object_name=None):
    if object_name is None:
        object_name = file_name

    if not os.path.exists(file_name):
        print(f"File {file_name} does not exist.")
        return

    s3 = boto3.client('s3')
    try:
        s3.upload_file(file_name, bucket_name, object_name)
        print(f"☁ Uploaded {file_name} to s3://{bucket_name}/{object_name}")
    except Exception as e:
        print(f"Upload failed: {e}")

upload_to_s3(json_file_path, "quotes-scraper-petermacero")
