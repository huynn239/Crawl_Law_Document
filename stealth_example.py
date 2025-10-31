"""Example: How to use playwright-stealth (if manual stealth doesn't work)"""

# 1. Install: pip install playwright-stealth

# 2. Import
from playwright_stealth import stealth_async

# 3. Apply to page (add after page creation)
async def example():
    page = await context.new_page()
    await stealth_async(page)  # <-- Add this line
    await page.goto("https://thuvienphapluat.vn")
    
# That's it! playwright-stealth will automatically:
# - Hide webdriver property
# - Fake plugins, languages, permissions
# - Randomize canvas/webgl fingerprints
# - Mock chrome runtime
# - And 30+ other evasions
