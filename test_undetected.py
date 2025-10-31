#!/usr/bin/env python3
"""Test undetected-chromedriver bypass Cloudflare"""
import undetected_chromedriver as uc
import time

print("Starting undetected Chrome...")

options = uc.ChromeOptions()
# options.add_argument('--headless=new')  # Uncomment for headless

driver = uc.Chrome(options=options, version_main=141)

print("Navigating to thuvienphapluat.vn...")
driver.get('https://thuvienphapluat.vn')

print("Waiting 10s for Cloudflare check...")
time.sleep(10)

# Check result
page_source = driver.page_source
if "Verify you are human" in page_source:
    print("\n[FAILED] Cloudflare blocked")
else:
    print("\n[SUCCESS] Bypassed Cloudflare!")
    print(f"Title: {driver.title}")

input("\nPress Enter to close browser...")
driver.quit()
