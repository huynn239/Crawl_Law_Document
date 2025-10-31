# Test extract với 1 URL
from tvpl_crawler.crawlers.playwright.extract import extract_luoc_do_with_playwright
from pathlib import Path
import json

url = "https://thuvienphapluat.vn/van-ban/Giao-thong-Van-tai/Van-ban-hop-nhat-17-VBHN-BXD-2025-Nghi-dinh-dang-ky-quoc-tich-va-dang-ky-cac-quyen-doi-voi-tau-bay-676614.aspx"

result = extract_luoc_do_with_playwright(
    url=url,
    screenshots_dir=Path("data/screenshots"),
    cookies_path=Path("data/cookies.json"),
    headed=True,
    timeout_ms=30000,
    storage_state_path=Path("data/storage_state.json")
)

print(json.dumps(result, ensure_ascii=False, indent=2))
