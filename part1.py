# Install Libraries needed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
import json
import time

# Set up Firefox options
firefox_options = Options()
firefox_options.add_argument("--headless")  # Run in headless mode (no UI)
firefox_options.add_argument("--no-sandbox")  # May not apply to Firefox

# Start Firefox browser
driver = webdriver.Firefox(options=firefox_options)
driver.get("http://quotes.toscrape.com/search.aspx")
wait = WebDriverWait(driver, 1)

# Get all authors from dropdown, skipping the first option (index 0)
author_select = Select(wait.until(EC.presence_of_element_located((By.ID, 'author'))))
authors = [opt.text for opt in author_select.options if opt.text.strip()][1:]

# Prepare a list to hold all the quotes data
all_quotes = []

for author in authors:
    driver.get("http://quotes.toscrape.com/search.aspx")
    wait.until(EC.presence_of_element_located((By.ID, 'author')))

    # Select the author
    author_dropdown = Select(driver.find_element(By.ID, 'author'))
    author_dropdown.select_by_visible_text(author)

    # Wait for tags to update
    time.sleep(1)

    # Get tags for selected author
    tag_dropdown = Select(driver.find_element(By.ID, 'tag'))
    tags = [opt.text for opt in tag_dropdown.options if opt.text.strip()][1:]

    for tag in tags:
        tag_dropdown = Select(driver.find_element(By.ID, 'tag'))
        tag_dropdown.select_by_visible_text(tag)

        # Click Search
        search_button = driver.find_element(By.CSS_SELECTOR, 'input.btn.btn-default')
        search_button.click()

        try:
            quotes = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "quote"))
            )

            for quote in quotes:
                text = quote.find_element(By.CLASS_NAME, "content").text.strip()
                all_quotes.append({"author": author, "tag": tag, "quote": text})
                print(f"✅ {author} | {tag} | {text[:50]}...")

        except:
            print(f"⚠ No quotes found for {author} - {tag}")

# Save data to JSON file
json_filename = "quotes_by_author_and_tag.json"
with open(json_filename, "w", encoding="utf-8") as json_file:
    json.dump(all_quotes, json_file, indent=4, ensure_ascii=False)

driver.quit()
print(f"✅ All quotes saved to {json_filename}")
