#import necessary libraries
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

# Set up the AWS S3 client
s3 = boto3.client('s3')

# Define function to upload to S3
def upload_to_s3(file_name, bucket_name, object_name=None):
    if object_name is None:
        object_name = file_name

    # Make sure file exists before attempting to upload
    if not os.path.exists(file_name):
        print(f"File {file_name} does not exist.")
        return

    try:
        # Upload the file to S3
        s3.upload_file(file_name, bucket_name, object_name)
        print(f"Uploaded {file_name} to s3://{bucket_name}/{object_name}")
    except Exception as e:
        print(f"Upload failed: {e}")

def setup_browser():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1280,720")
    options.binary_location = '/usr/bin/firefox'  # path for firefox browser

    return webdriver.Firefox(
        service=Service('/usr/local/bin/geckodriver'),  # path for geckodriver
        options=options
    )

def scrape_quotes():
    driver = setup_browser() # Set up the browser and the wait time for elements to load
    wait = WebDriverWait(driver, 5)  # Increased timeout
    all_quotes = []

    try:
        driver.get("http://quotes.toscrape.com/search.aspx") # Open the website for scraping quotes

        author_select = Select(wait.until(
            EC.presence_of_element_located((By.ID, 'author'))
        ))
        authors = [opt.text for opt in author_select.options if opt.text.strip()][1:]  # Extract all the authors from the dropdown, skipping the first option

        for author in authors:
            print(f"Processing {author}...")

            # Reload page to reset dropdown state properly
            driver.get("http://quotes.toscrape.com/search.aspx")
            
            Select(driver.find_element(By.ID, "author")).select_by_visible_text("Albert Einstein")
            time.sleep(1)
            Select(driver.find_element(By.ID, "tag")).select_by_visible_text("inspirational")
            driver.find_element(By.CSS_SELECTOR, 'input.btn.btn-default').click()
            
            quotes = driver.find_elements(By.CLASS_NAME, "quote")
            print([q.find_element(By.CLASS_NAME, "content").text for q in quotes])  # Updated to fetch text from <span class="content">

            # Select author
            author_dropdown = Select(wait.until(
                EC.presence_of_element_located((By.ID, 'author'))
            ))
            author_dropdown.select_by_visible_text(author)
            time.sleep(0.5)

            # Get tags after author is selected
            tag_dropdown = Select(wait.until(
                EC.presence_of_element_located((By.ID, 'tag'))
            ))
            tags = [opt.text for opt in tag_dropdown.options if opt.text.strip()][1:]

            for tag in tags:
                print(f"  Processing tag: {tag}")
                try:
                    Select(driver.find_element(By.ID, 'tag')).select_by_visible_text(tag)# Select the tag

                    button = driver.find_element(By.CSS_SELECTOR, 'input.btn.btn-default')# Click the Search button
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(0.5)

                    # Wait until quotes appear
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_all_elements_located((By.CLASS_NAME, "quote"))
                    )

                    #  Get all quotes
                    quotes = driver.find_elements(By.CLASS_NAME, "quote")

                    for quote in quotes:
                        text = quote.find_element(By.CLASS_NAME, "content").text.strip('“”')  # Updated to fetch text from <span class="content">
                        all_quotes.append({
                            "author": author,
                            "tag": tag,
                            "quote": text
                        })
                        print(f"✅ {author} | {tag} | {text[:50]}...")

                except Exception as e:
                    if "No quotes found" not in driver.page_source:
                        print(f"    Error processing tag '{tag}' for author '{author}': {e}")
                        driver.save_screenshot(f"error_{author[:3]}_{tag[:3]}.png")

    except Exception as e:
        print(f"Error in scraping: {e}")

    finally:
        driver.quit()

    return all_quotes

if __name__ == "__main__":
    quotes = scrape_quotes()
    with open("quotes.json", "w", encoding="utf-8") as f:
        json.dump(quotes, f, indent=2, ensure_ascii=False)
    print(f"Success! Saved {len(quotes)} quotes")

    # Upload the JSON file to S3
    upload_to_s3(file_name, "quotes-scraper-petermacero")  # Replace with your S3 bucket name
