import json
import os
import sys
import argparse
from pathlib import Path
from loguru import logger

# Reuse project extractors
from tvpl_crawler.playwright_extract import extract_luoc_do_with_playwright
from tvpl_crawler.playwright_login import login_with_playwright


def main():
    ap = argparse.ArgumentParser(description="Run Tab4 extractor locally (Playwright)")
    ap.add_argument("--url", required=True, help="Document URL to crawl")
    ap.add_argument("--cookies", default="data/cookies.json", help="Path to cookies.json")
    ap.add_argument("--screenshots", default="data/screenshots", help="Dir to save screenshots")
    ap.add_argument("--out", default="data/Result_Tab4_local.json", help="Output JSON file")
    ap.add_argument("--headed", action="store_true", help="Run browser headed (visible)")
    ap.add_argument("--relogin", action="store_true", help="Try login with env TVPL_USERNAME/TVPL_PASSWORD before crawl")
    ap.add_argument("--timeout_ms", type=int, default=45000)
    args = ap.parse_args()

    screenshots_dir = Path(args.screenshots)
    cookies_path = Path(args.cookies)
    out_path = Path(args.out)

    # Optional: login first to refresh cookies/storage_state using env
    if args.relogin:
        username = os.getenv("TVPL_USERNAME", "")
        password = os.getenv("TVPL_PASSWORD", "")
        login_url = os.getenv("TVPL_LOGIN_URL", "https://thuvienphapluat.vn/")
        if not username or not password:
            logger.warning("TVPL_USERNAME/TVPL_PASSWORD not found in environment; skipping pre-login.")
        else:
            ok = login_with_playwright(
                login_url=login_url,
                username=username,
                password=password,
                cookies_out=cookies_path,
                storage_state_out=Path("data/storage_state.json"),
                headed=args.headed,
                manual=False,
            )
            if not ok:
                logger.warning("Pre-login may have failed; continuing with existing cookies/storage state.")

    # Extract Tab4 with deep relation attempts implemented in project code
    data = extract_luoc_do_with_playwright(
        url=args.url,
        screenshots_dir=screenshots_dir,
        cookies_path=cookies_path,
        headed=args.headed,
        timeout_ms=args.timeout_ms,
        only_tab8=False,
        relogin_on_fail=args.relogin,
        download_tab8=False,
        downloads_dir=Path("data/downloads"),
    )

    # Save pretty UTF-8 JSON
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    sys.exit(main())
