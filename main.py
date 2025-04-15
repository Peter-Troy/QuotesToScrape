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
import psutil

def kill_chrome_processes():
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] in ('chrome', 'chromedriver'):
            try:
                proc.kill()
            except psutil.NoSuchProcess:
                pass

# Kill any existing Chrome processes
kill_chrome_processes()

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--user-data-dir=/tmp/chrome-user-data")
chrome_options.add_argument("--window-size=1920,1080")  # Added window size
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--remote-debugging-port=9222")
chrome_options.add_argument("--disable-application-cache")
chrome_options.add_argument("--disable-setuid-sandbox")

# ChromeDriver setup
chromedriver_path = '/usr/local/bin/chromedriver'
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 15)

def safe_click(element):
    """Helper function to click elements reliably"""
    try:
        # Try regular click first
        element.click()
    except:
        try:
            # Try ActionChains if regular click fails
            ActionChains(driver).move_to_element(element).click().perform()
        except:
            # Fall back to JavaScript click
            driver.execute_script("arguments[0].click();", element)

def wait_for_element(locator, timeout=15):
    return wait.until(EC.visibility_of_element_located(locator))

# Get all authors (skip the first placeholder)
driver.get("http://quotes.toscrape.com/search.aspx")
author_select = Select(wait_for_element((By.ID, 'author')))
authors = [opt.text for opt in author_select.options if opt.text.strip()][1:]

all_quotes = []

for author in authors[:3]:  # Test with first 3 authors
    print(f"\n🔍 Searching quotes by: {author}")
    driver.get("http://quotes.toscrape.com/search.aspx")
    wait_for_element((By.ID, 'author'))

    # Select author
    author_dropdown = Select(driver.find_element(By.ID, 'author'))
    author_dropdown.select_by_visible_text(author)

    # Wait for tag dropdown
    wait.until(lambda d: len(Select(d.find_element(By.ID, "tag")).options) > 1)

    # Search quotes by author only
    try:
        search_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input.btn.btn-default')))
        
        # Scroll to button and click using reliable method
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_button)
        time.sleep(0.5)
        safe_click(search_button)
        
        # Wait for results
        wait.until(EC.presence_of_element_located((By.ID, 'results')))
        time.sleep(1)
        
        # Find quotes - try multiple selectors
        quotes = []
        for selector in [
            '//div[@class="quote"]/span[@class="text"]',  # XPath
            'div.quote span.text'  # CSS
        ]:
            quotes = driver.find_elements(By.XPATH if '//' in selector else By.CSS_SELECTOR, selector)
            if quotes:
                break
                
        if quotes:
            for quote in quotes:
                text = quote.text.strip('"')
                all_quotes.append({"author": author, "tag": None, "quote": text})
                print(f"✅ {author} | No tag | {text[:50]}...")
        else:
            print(f"⚠ No quotes found for {author} (no tag)")
            print("Page content:", driver.find_element(By.TAG_NAME, 'body').text[:500])
            
    except Exception as e:
        print(f"⚠ Search failed for {author}. Error: {str(e)}")
        driver.save_screenshot(f'error_{author.replace(" ", "_")}.png')

# Save and upload results (same as before)
json_file_path = "quotes_by_author_and_tag.json"
with open(json_file_path, "w", encoding="utf-8") as json_file:
    json.dump(all_quotes, json_file, indent=4, ensure_ascii=False)

driver.quit()
print(f"\n📁 All quotes saved to {json_file_path}")

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
