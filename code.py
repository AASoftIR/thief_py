from playwright.sync_api import sync_playwright
import json
import time

def save_cookies(page, filename="cookies.json"):
    cookies = page.context.cookies()
    with open(filename, 'w') as file:
        json.dump(cookies, file)

def load_cookies(page, filename="cookies.json"):
    with open(filename, 'r') as file:
        cookies = json.load(file)
        page.context.add_cookies(cookies)

def wait_for_captcha(page):
    input("Please solve the CAPTCHA and press Enter to continue...")
    save_cookies(page)

def extract_defaces_content(page):
    try:
        defaces_elements = page.locator(".defaces").all()
        defaces_texts = [element.text_content() for element in defaces_elements]
        return "\n".join(defaces_texts)
    except Exception as e:
        print(f"Error extracting .defaces content: {e}")
        return ""

def get_mirror_links(row):
    links = row.query_selector_all("a")
    return [link for link in links if link.text_content().strip().lower() == "mirror"]

def handle_initial_auth(page):
    """Handle initial authentication and CAPTCHA when no cookies exist"""
    print("No cookies found. Going to main page for initial authentication...")
    page.goto('https://www.zone-h.org/archive/published=0', timeout=60000)
    
    # Check for and handle CAPTCHA
    if page.locator("#cryptogram").count() > 0:
        print("Initial CAPTCHA detected. Please solve it manually.")
        wait_for_captcha(page)
        print("Cookies saved successfully. Proceeding with scraping...")
    return True

def scrape_zone_h_pages(playwright, num_pages=5):
    with playwright.chromium.launch(headless=False) as browser:
        context = browser.new_context()
        page = context.new_page()
        
        # Handle cookies and initial authentication
        try:
            load_cookies(page)
            print("Cookies loaded successfully.")
        except FileNotFoundError:
            if not handle_initial_auth(page):
                print("Failed to handle initial authentication")
                return

        for page_number in range(1, num_pages + 1):
            try:
                archive_url = f'https://www.zone-h.org/archive/published=0/page={page_number}'
                print(f'\nScraping page {page_number}: {archive_url}')
                
                # Go to the archive page
                page.goto(archive_url, timeout=60000)
                page.wait_for_selector("#ldeface", timeout=60000)
                
                # Check for CAPTCHA on archive page
                if page.locator("#cryptogram").count() > 0:
                    print("CAPTCHA detected on archive page. Please solve it manually.")
                    wait_for_captcha(page)
                    # Reload the page after CAPTCHA
                    page.goto(archive_url, timeout=60000)
                    page.wait_for_selector("#ldeface", timeout=60000)
                
                # Store all mirror URLs from the page first
                mirror_data = []
                rows = page.query_selector_all("#ldeface tr:not(:first-child)")
                print(f"Found {len(rows)} rows on page {page_number}")
                
                for row_index, row in enumerate(rows, 1):
                    try:
                        mirror_links = get_mirror_links(row)
                        for link in mirror_links:
                            href = link.get_attribute('href')
                            if href:
                                mirror_data.append({
                                    'row': row_index,
                                    'url': f"https://www.zone-h.org{href}"
                                })
                    except Exception as e:
                        print(f"Error collecting mirror URL from row {row_index}: {e}")
                        continue
                
                # Now process all collected mirror URLs
                for index, data in enumerate(mirror_data, 1):
                    try:
                        print(f"\nProcessing mirror {index}/{len(mirror_data)} from row {data['row']}")
                        print(f"URL: {data['url']}")
                        
                        # Visit the mirror page
                        page.goto(data['url'], timeout=60000)
                        
                        # Check for CAPTCHA
                        if page.locator("#cryptogram").count() > 0:
                            print("CAPTCHA detected on mirror page. Please solve it manually.")
                            wait_for_captcha(page)
                            # Reload the mirror page after CAPTCHA
                            page.goto(data['url'], timeout=60000)
                        
                        # Extract content
                        defaces_content = extract_defaces_content(page)
                        if defaces_content:
                            with open("defaces.txt", "a", encoding="utf-8") as f:
                                f.write(f"=== URL: {data['url']} ===\n")
                                f.write(defaces_content + "\n\n")
                            print("Content saved successfully")
                        else:
                            print("No defaces content found")
                        
                        # Add a small delay between requests
                        time.sleep(1)
                        
                    except Exception as e:
                        print(f"Error processing mirror URL: {e}")
                        continue
                
                # Add a delay between pages
                time.sleep(2)
                
            except Exception as e:
                print(f"Error processing page {page_number}: {e}")
                continue
        
        browser.close()

with sync_playwright() as p:
    scrape_zone_h_pages(p, num_pages=2)