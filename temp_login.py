from tvpl_crawler.playwright_login import login_with_playwright
from pathlib import Path
ok = login_with_playwright(
    login_url="https://thuvienphapluat.vn/",
    username="thienhoang2024",
    password="Ab@12345678",
    cookies_out=Path("data/cookies.json"),
    storage_state_out=Path("data/storage_state.json"),
    headed=True,
    manual=False,
)
print("LOGIN_OK=", ok)
