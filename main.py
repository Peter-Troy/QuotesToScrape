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
driver.get("http://quotes.toscrape.com/search.aspx")
wait = WebDriverWait(driver, 15)  # Increased timeout to 15 seconds

def wait_for_element(locator, timeout=15):
    return WebDriverWait(driver, timeout).until(EC.visibility_of_element_located(locator))

# Get all authors (skip the first placeholder)
author_select = Select(wait_for_element((By.ID, 'author')))
authors = [opt.text for opt in author_select.options if opt.text.strip()][1:]

all_quotes = []

for author in authors[:3]:  # Just process first 3 authors for testing
    print(f"\n🔍 Searching quotes by: {author}")
    driver.get("http://quotes.toscrape.com/search.aspx")
    wait_for_element((By.ID, 'author'))

    # Take screenshot before search
    driver.save_screenshot(f'before_search_{author.replace(" ", "_")}.png')

    author_dropdown = Select(driver.find_element(By.ID, 'author'))
    author_dropdown.select_by_visible_text(author)

    # Wait for tag dropdown to be populated
    wait.until(lambda d: len(Select(d.find_element(By.ID, "tag")).options) > 1)

    # Search quotes by author only (no tag selected)
    try:
        search_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//input[@value="Search"]')))
        search_button.click()
        
        # Wait for results to load completely
        wait.until(EC.presence_of_element_located((By.ID, 'results')))
        time.sleep(1)  # Small delay to ensure content is loaded
        
        # Take screenshot after search
        driver.save_screenshot(f'after_search_{author.replace(" ", "_")}.png')
        
        # Try multiple ways to locate quotes
        try:
            quotes = driver.find_elements(By.XPATH, '//div[@class="quote"]/span[@class="text"]')
            if not quotes:
                quotes = driver.find_elements(By.CSS_SELECTOR, 'div.quote span.text')
            
            for quote in quotes:
                text = quote.text.strip('"')  # Remove quotation marks
                all_quotes.append({"author": author, "tag": None, "quote": text})
                print(f"✅ {author} | No tag | {text[:50]}...")
                
        except Exception as e:
            print(f"⚠ Could not locate quotes for {author}. Error: {str(e)}")
            print("Trying alternative quote location method...")
            results_div = driver.find_element(By.ID, 'results')
            print("Results div content:", results_div.text[:200])  # Print first 200 chars
            
    except Exception as e:
        print(f"⚠ Search failed for {author}. Error: {str(e)}")
        driver.save_screenshot(f'error_{author.replace(" ", "_")}.png')

    # Now search quotes by each tag (for first author only for testing)
    if author == authors[0]:
        tag_dropdown = Select(driver.find_element(By.ID, 'tag'))
        tags = [opt.text for opt in tag_dropdown.options if opt.text.strip()][1:3]  # Just first 2 tags for testing
        
        for tag in tags:
            print(f"\n➡ Selecting tag: {tag} for author: {author}")
            driver.get("http://quotes.toscrape.com/search.aspx")
            wait_for_element((By.ID, 'author'))
            
            # Select author again
            author_dropdown = Select(driver.find_element(By.ID, 'author'))
            author_dropdown.select_by_visible_text(author)
            
            # Select tag
            tag_dropdown = Select(driver.find_element(By.ID, 'tag'))
            tag_dropdown.select_by_visible_text(tag)
            
            try:
                search_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//input[@value="Search"]')))
                search_button.click()
                
                wait.until(EC.presence_of_element_located((By.ID, 'results')))
                time.sleep(1)
                
                try:
                    quotes = driver.find_elements(By.XPATH, '//div[@class="quote"]/span[@class="text"]')
                    if not quotes:
                        quotes = driver.find_elements(By.CSS_SELECTOR, 'div.quote span.text')
                    
                    for quote in quotes:
                        text = quote.text.strip('"')
                        all_quotes.append({"author": author, "tag": tag, "quote": text})
                        print(f"✅ {author} | {tag} | {text[:50]}...")
                        
                except Exception as e:
                    print(f"⚠ Could not locate quotes for {author} with tag {tag}. Error: {str(e)}")
                    
            except Exception as e:
                print(f"⚠ Search failed for {author} with tag {tag}. Error: {str(e)}")

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
