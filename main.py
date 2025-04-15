from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import datetime
import json
import boto3
import os

# === Chrome Options ===
chrome_options = Options()
# Comment out headless mode for debugging (re-enable later)
# chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# === Chrome Driver Path ===
chromedriver_path = '/usr/local/bin/chromedriver'
service = Service(chromedriver_path)

# === Start the browser ===
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.implicitly_wait(1)
driver.get("http://quotes.toscrape.com/search.aspx")
wait = WebDriverWait(driver, 10)

# === Helper Functions ===
def wait_for_element(locator, timeout=5):
    return WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located(locator)
    )

def wait_and_click(element_locator, timeout=5):
    element = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable(element_locator)
    )
    element.click()

# === Collect Authors ===
author_select = Select(wait_for_element((By.ID, 'author')))
authors = [opt.text for opt in author_select.options if opt.text.strip()][1:]

all_quotes = []

# === Main Loop ===
for author in authors:
    driver.get("http://quotes.toscrape.com/search.aspx")
    wait_for_element((By.ID, 'author'))

    author_dropdown = Select(driver.find_element(By.ID, 'author'))
    author_dropdown.select_by_visible_text(author)

    time.sleep(1)  # Let tags update

    tag_dropdown = Select(driver.find_element(By.ID, 'tag'))
    tags = [opt.text for opt in tag_dropdown.options if opt.text.strip()][1:]

    for tag in tags:
        tag_dropdown = Select(driver.find_element(By.ID, 'tag'))
        tag_dropdown.select_by_visible_text(tag)

        # Click search using ActionChains to simulate interaction
        search_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input.btn.btn-default')))
        ActionChains(driver).move_to_element(search_button).click().perform()

        # Wait manually up to 10 seconds for quotes to appear
        start_time = datetime.datetime.now()
        quotes = []
        while True:
            quotes = driver.find_elements(By.CLASS_NAME, "quote")
            if quotes or (datetime.datetime.now() - start_time).seconds > 10:
                break
            time.sleep(1)

        if quotes:
            for quote in quotes:
                text = quote.find_element(By.CLASS_NAME, "content").text.strip()
                all_quotes.append({"author": author, "tag": tag, "quote": text})
                print(f"✅ {author} | {tag} | {text[:50]}...")
        else:
            print(f"⚠ No quotes found for {author} - {tag}. Saving debug HTML...")
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)

# === Save to JSON ===
with open("quotes_by_author_and_tag.json", "w", encoding="utf-8") as json_file:
    json.dump(all_quotes, json_file, indent=4, ensure_ascii=False)

print("✅ All quotes saved to quotes_by_author_and_tag.json")

driver.quit()

# === Upload to S3 ===
def upload_to_s3(file_name, bucket_name, object_name=None):
    if object_name is None:
        object_name = file_name

    if not os.path.exists(file_name):
        print(f"File {file_name} does not exist.")
        return

    s3 = boto3.client('s3')

    try:
        s3.upload_file(file_name, bucket_name, object_name)
        print(f"✅ Uploaded {file_name} to s3://{bucket_name}/{object_name}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")

upload_to_s3("quotes_by_author_and_tag.json", "quotes-scraper-petermacero")
