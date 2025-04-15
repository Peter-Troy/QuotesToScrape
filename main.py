from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
import json
import time
import boto3
import os

# Configure Firefox for EC2
def setup_browser():
    firefox_options = Options()
    firefox_options.add_argument("--headless")
    firefox_options.add_argument("--window-size=1280,720")
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument("--disable-dev-shm-usage")  # Critical for EC2
    
      # Initialize Firefox with explicit GeckoDriver path
    return webdriver.Firefox(
        service=Service('/usr/local/bin/geckodriver'),  # <-- THIS GOES HERE
        options=firefox_options
    )

def scrape_quotes():
    driver = webdriver.Firefox(
        service=Service('/usr/local/bin/geckodriver'),
        options=firefox_options
    )
    
    try:
        # Load page
        driver.get("http://quotes.toscrape.com/search.aspx")
        
        # Get authors
        author_select = Select(wait.until(
            EC.presence_of_element_located((By.ID, 'author'))
        ))
        authors = [opt.text for opt in author_select.options if opt.text.strip()][1:]
        
        for author in authors:
            print(f"\n🔍 Processing: {author}")
            driver.get("http://quotes.toscrape.com/search.aspx")
            
            # Select author
            Select(wait.until(
                EC.presence_of_element_located((By.ID, 'author'))
            )).select_by_visible_text(author)
            time.sleep(1)
            
            # Get tags
            tag_dropdown = Select(driver.find_element(By.ID, 'tag'))
            tags = [opt.text for opt in tag_dropdown.options if opt.text.strip()][1:]
            
            for tag in tags:
                print(f"   ⮑ Tag: {tag}")
                Select(driver.find_element(By.ID, 'tag')).select_by_visible_text(tag)
                
                # Click search (with JS fallback)
                button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input.btn.btn-default'))
                )
                driver.execute_script("arguments[0].click();", button)
                time.sleep(1)
                
                # Extract quotes
                try:
                    quotes = wait.until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.quote span.text'))
                    )
                    for quote in quotes:
                        all_quotes.append({
                            "author": author,
                            "tag": tag,
                            "quote": quote.text.strip('"')
                        })
                except:
                    if "No quotes found" not in driver.page_source:
                        print("      ⚠ Unexpected error (screenshot saved)")
                        driver.save_screenshot('error.png')
        
        return all_quotes
    
    finally:
        driver.quit()

# Main execution
if __name__ == "__main__":
    print("🚀 Starting scrape...")
    quotes = scrape_quotes()
    
    # Save to JSON
    filename = "quotes.json"
    with open(filename, "w") as f:
        json.dump(quotes, f, indent=2)
    print(f"✅ Saved {len(quotes)} quotes to {filename}")
    
    # Upload to S3
    s3 = boto3.client('s3')
    try:
        s3.upload_file(filename, "quotes-scraper-petermacero", filename)
        print(f"📤 Uploaded to S3: s3://quotes-scraper-petermacero/{filename}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
