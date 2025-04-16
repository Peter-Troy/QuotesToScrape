from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
import json
import time

def setup_browser():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1280,720")
    options.binary_location = '/usr/bin/firefox'  # Adjust as needed

    return webdriver.Firefox(
        service=Service('/usr/local/bin/geckodriver'),  # Adjust path if needed
        options=options
    )

def scrape_quotes():
    driver = setup_browser()
    wait = WebDriverWait(driver, 5)  # Increased timeout
    all_quotes = []

    try:
        driver.get("http://quotes.toscrape.com/search.aspx")

        author_select = Select(wait.until(
            EC.presence_of_element_located((By.ID, 'author'))
        ))
        authors = [opt.text for opt in author_select.options if opt.text.strip()][1:]

        for author in authors:
            print(f"Processing {author}...")

            # Reload page to reset dropdown state properly
            driver.get("http://quotes.toscrape.com/search.aspx")

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
                    # Re-find tag dropdown (important to avoid stale reference)
                    tag_dropdown = Select(driver.find_element(By.ID, 'tag'))
                    tag_dropdown.select_by_visible_text(tag)

                    # Click Search
                    button = driver.find_element(By.CSS_SELECTOR, 'input.btn.btn-default')
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(0.5)

                    # Wait for quotes to load
                    quotes = wait.until(
                        EC.presence_of_all_elements_located((By.CLASS_NAME, 'quote'))
                    )

                    for quote in quotes:
                        text = quote.find_element(By.CLASS_NAME, 'content').text.strip()
                        all_quotes.append({
                            "author": author,
                            "tag": tag,
                            "quote": text
                        })

                except Exception as e:
                    if "No quotes found!" not in driver.page_source:
                        print(f"    Error processing tag '{tag}' for author '{author}': {e}")
                        driver.save_screenshot(f"error_{author[:3]}_{tag[:3]}.png")

    finally:
        driver.quit()

    return all_quotes

if __name__ == "__main__":
    quotes = scrape_quotes()
    with open("quotes.json", "w", encoding="utf-8") as f:
        json.dump(quotes, f, indent=2, ensure_ascii=False)
    print(f"Success! Saved {len(quotes)} quotes")
