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
    options.binary_location = '/usr/bin/firefox'  # Explicit path
    
    return webdriver.Firefox(
        service=Service('/usr/local/bin/geckodriver'),
        options=options
    )

def scrape_quotes():
    driver = setup_browser()
    wait = WebDriverWait(driver, 15)
    all_quotes = []
    
    try:
        driver.get("http://quotes.toscrape.com/search.aspx")
        
        # Get authors
        authors = [opt.text for opt in 
                  Select(wait.until(
                      EC.presence_of_element_located((By.ID, 'author'))
                  ).options if opt.text.strip()][1:]
        
        for author in authors:
            print(f"Processing {author}...")
            driver.refresh()  # More reliable than get()
            
            # Select author
            author_dropdown = Select(wait.until(
                EC.presence_of_element_located((By.ID, 'author'))
            )
            author_dropdown.select_by_visible_text(author)
            time.sleep(0.5)
            
            # Get tags
            tags = [opt.text for opt in 
                   Select(driver.find_element(By.ID, 'tag')).options 
                   if opt.text.strip()][1:]
            
            for tag in tags:
                # Select tag
                Select(driver.find_element(By.ID, 'tag')).select_by_visible_text(tag)
                
                # Click search with JS fallback
                button = driver.find_element(By.CSS_SELECTOR, 'input.btn.btn-default')
                driver.execute_script("arguments[0].click();", button)
                time.sleep(0.5)
                
                # Get quotes
                try:
                    quotes = wait.until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.quote span.text'))
                    )
                    all_quotes.extend({
                        "author": author,
                        "tag": tag,
                        "quote": q.text.strip('"')
                    } for q in quotes)
                except:
                    if "No quotes found" not in driver.page_source:
                        driver.save_screenshot(f'error_{author[:3]}_{tag[:3]}.png')
        
        return all_quotes
    
    finally:
        driver.quit()

if __name__ == "__main__":
    quotes = scrape_quotes()
    with open("quotes.json", "w") as f:
        json.dump(quotes, f, indent=2)
    print(f"Success! Saved {len(quotes)} quotes")
