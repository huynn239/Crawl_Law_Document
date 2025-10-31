"""Test API imports"""

print("Testing API imports...")

try:
    from tvpl_crawler.core.db import TVPLDatabase
    print("✓ tvpl_crawler.core.db")
except Exception as e:
    print(f"✗ tvpl_crawler.core.db: {e}")

try:
    from tvpl_crawler.main import cmd_links_from_search
    print("✓ tvpl_crawler.main")
except Exception as e:
    print(f"✗ tvpl_crawler.main: {e}")

try:
    from tvpl_crawler.crawlers.playwright.playwright_login import login_with_playwright
    print("✓ tvpl_crawler.crawlers.playwright.playwright_login")
except Exception as e:
    print(f"✗ tvpl_crawler.crawlers.playwright.playwright_login: {e}")

try:
    from tvpl_crawler.crawlers.playwright.playwright_extract import extract_tab8_batch_with_playwright
    print("✓ tvpl_crawler.crawlers.playwright.playwright_extract")
except Exception as e:
    print(f"✗ tvpl_crawler.crawlers.playwright.playwright_extract: {e}")

try:
    from tvpl_crawler.utils.compact_schema import compact_schema
    print("✓ tvpl_crawler.utils.compact_schema")
except Exception as e:
    print(f"✗ tvpl_crawler.utils.compact_schema: {e}")

print("\n✓ Test completed!")
