from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
import json
import time
import boto3
import os

def setup_browser():
    """Configure Firefox for headless scraping on EC2"""
    firefox_options = Options()
    firefox_options.add_argument("--headless")
    firefox_options.add_argument("--window-size=1280,720")
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument("--disable-dev-shm-usage")  # Critical for EC2
    
    return webdriver.Firefox(
        service=Service('/usr/local/bin/geckodriver'),
        options=firefox_options
    )

def scrape_quotes():
    """Main scraping function"""
    driver = setup_browser()
    wait = WebDriverWait(driver, 15)
    all_quotes = []
    
    try:
        # Initial page load
        print("🚀 Launching browser...")
        driver.get("http://quotes.toscrape.com/search.aspx")
        
        # Get all authors
        print("🔍 Fetching authors list...")
        author_select = Select(wait.until(
            EC.presence_of_element_located((By.ID, 'author'))
        ))
        authors = [opt.text for opt in author_select.options if opt.text.strip()][1:]
        print(f"📝 Found {len(authors)} authors")
        
        for author in authors:
            print(f"\n🧑 Processing author: {author}")
            driver.get("http://quotes.toscrape.com/search.aspx")  # Fresh page load
            
            # Select author
            Select(wait.until(
                EC.presence_of_element_located((By.ID, 'author'))
            )).select_by_visible_text(author)
            time.sleep(1)  # Wait for tag dropdown
            
            # Get all tags
            tag_dropdown = Select(driver.find_element(By.ID, 'tag'))
            tags = [opt.text for opt in tag_dropdown.options if opt.text.strip()][1:]
            print(f"   🏷️ Found {len(tags)} tags")
            
            for tag in tags:
                print(f"   ⮑ Processing tag: {tag}")
                
                # Select tag
                Select(driver.find_element(By.ID, 'tag')).select_by_visible_text(tag)
                time.sleep(0.5)
                
                # Click search (JavaScript click for reliability)
                button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input.btn.btn-default'))
                )
                driver.execute_script("arguments[0].click();", button)
                time.sleep(1)  # Wait for results
                
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
                    print(f"      ✅ Found {len(quotes)} quotes")
                except Exception as e:
                    if "No quotes found" not in driver.page_source:
                        print(f"      ❌ Error: {str(e)[:100]}")
                        driver.save_screenshot(f'error_{author[:3]}_{tag[:3]}.png')
        
        return all_quotes
    
    finally:
        driver.quit()
        print("🛑 Browser closed")

def upload_to_s3(file_path, bucket_name):
    """Upload file to S3"""
    try:
        s3 = boto3.client('s3')
        s3.upload_file(file_path, bucket_name, os.path.basename(file_path))
        return True
    except Exception as e:
        print(f"📤 Upload failed: {e}")
        return False

if __name__ == "__main__":
    # Run scraper
    print("🕒 Starting scrape...")
    quotes_data = scrape_quotes()
    
    # Save results
    output_file = "quotes.json"
    with open(output_file, "w", encoding='utf-8') as f:
        json.dump(quotes_data, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved {len(quotes_data)} quotes to {output_file}")
    
    # Upload to S3 (optional)
    if upload_to_s3(output_file, "quotes-scraper-petermacero"):
        print("☁️ Uploaded to S3 successfully")
