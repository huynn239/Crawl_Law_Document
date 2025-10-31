# -*- coding: utf-8 -*-
"""Crawler using undetected-chromedriver (Selenium)"""
import json
import sys
import os
import time
import random
from pathlib import Path
from dotenv import load_dotenv
import undetected_chromedriver as uc
from tvpl_crawler.selenium_extract import extract_document
from tvpl_crawler.compact_schema import compact_schema

load_dotenv()

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

if len(sys.argv) < 2:
    print("Usage: python crawl_selenium.py <input_file> [output_file] [--headless]")
    sys.exit(1)

HEADLESS = "--headless" in sys.argv
args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]

input_file = Path(args[0])
output_file = Path(args[1]) if len(args) >= 2 else input_file.parent / f"{input_file.stem}_Result.json"

links = json.loads(input_file.read_text(encoding="utf-8"))
BATCH_SIZE = 5  # Giảm xuống 5 để tránh Cloudflare
print(f"Crawl {len(links)} documents (batch_size={BATCH_SIZE})\n")

def login_driver(driver):
    """Login to website"""
    print("Logging in...")
    driver.get("https://thuvienphapluat.vn")
    time.sleep(3)
    
    try:
        username_field = driver.find_element("id", "usernameTextBox")
        password_field = driver.find_element("id", "passwordTextBox")
        login_button = driver.find_element("id", "loginButton")
        
        username_field.send_keys(os.getenv("TVPL_USERNAME", ""))
        time.sleep(random.uniform(0.5, 1.5))
        password_field.send_keys(os.getenv("TVPL_PASSWORD", ""))
        time.sleep(random.uniform(0.3, 0.8))
        login_button.click()
        time.sleep(3)
        
        # Xử lý popup "Tài khoản đã có người sử dụng"
        time.sleep(2)  # Đợi popup xuất hiện
        
        try:
            # Thử nhiều selector khác nhau cho nút popup
            selectors = [
                "div.ui-dialog[style*='display: block'] button",  # Dialog đang hiển thị
                ".ui-dialog-buttonset button",
                "button[type='button']",
            ]
            
            for selector in selectors:
                buttons = driver.find_elements("css selector", selector)
                visible_buttons = [b for b in buttons if b.is_displayed()]
                
                if len(visible_buttons) > 0:
                    print(f"  Found {len(visible_buttons)} visible button(s) in popup")
                    # Click nút đầu tiên hiển thị
                    driver.execute_script("arguments[0].click();", visible_buttons[0])
                    print("  Clicked popup button")
                    time.sleep(3)
                    break
        except Exception as e:
            print(f"  Could not handle popup: {e}")
        
        # Verify login thành công
        time.sleep(3)
        try:
            # Check xem form login còn hiển thị không
            login_form = driver.find_elements("id", "usernameTextBox")
            if len(login_form) > 0:
                try:
                    if login_form[0].is_displayed():
                        print("  Login failed: still see login form\n")
                        return False
                except:
                    pass
            
            print("  Login successful\n")
            return True
        except:
            print("  Login successful\n")
            return True
    except Exception as e:
        print(f"Login failed: {e}\n")
        return False

# Crawl documents in batches
results = []
for batch_idx in range(0, len(links), BATCH_SIZE):
    batch = links[batch_idx:batch_idx + BATCH_SIZE]
    batch_num = batch_idx // BATCH_SIZE + 1
    total_batches = (len(links) - 1) // BATCH_SIZE + 1
    
    print(f"\n{'='*60}")
    print(f"Batch {batch_num}/{total_batches} - {len(batch)} documents")
    print(f"{'='*60}\n")
    
    # Setup Chrome for this batch
    options = uc.ChromeOptions()
    if HEADLESS:
        options.add_argument('--headless=new')
    
    driver = uc.Chrome(options=options, version_main=141)
    
    # Login
    if not login_driver(driver):
        print("  Login failed, skip batch")
        driver.quit()
        continue
    
    # Crawl batch
    for item in batch:
        idx = batch_idx + batch.index(item) + 1
        url = item.get("Url") or item.get("url") or ""
        title = item.get("Ten van ban") or item.get("ten_van_ban") or ""
        
        if not url:
            results.append({"stt": idx, "error": "Missing URL"})
            continue
        
        print(f"[{idx}/{len(links)}] {title[:60]}...")
        print(f"  URL: {url}")
        
        # Random delay (tăng lên để tránh Cloudflare)
        delay = random.uniform(5, 8)
        print(f"  Delay {delay:.1f}s...")
        time.sleep(delay)
        
        # Extract
        data = extract_document(driver, url)
        data["stt"] = idx
        data["title"] = title
        
        if "error" in data:
            print(f"  Error: {data['error']}")
        else:
            total = data.get("tab4_total_relations", 0)
            print(f"  OK: {total} relations")
        
        results.append(data)
    
    # Close driver after batch
    driver.quit()
    
    # Delay between batches (tăng lên để tránh Cloudflare)
    if batch_idx + BATCH_SIZE < len(links):
        delay = random.uniform(30, 45)
        print(f"\nWaiting {delay:.1f}s before next batch...\n")  
        time.sleep(delay)

# Save results
compact_results = compact_schema(results)
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(compact_results, f, ensure_ascii=False, indent=2)

print(f"\nDone: {len(results)}/{len(links)} documents")
print(f"Output: {output_file}")
