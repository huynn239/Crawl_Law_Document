import argparse
import asyncio
import os
from loguru import logger
from pathlib import Path
from .core.http_client import fetch_text
from .core.parser import (
    parse_title,
    extract_document_info,
    extract_document_links_from_search,
    extract_document_items_from_search,
    extract_luoc_do,
)
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from getpass import getpass
from typing import List
from .core.http_client import HttpClient
from .playwright_login import login_with_playwright
from .playwright_extract import extract_luoc_do_with_playwright


def cmd_crawl_url(url: str, out: Path | None):
    async def _run():
        html = await fetch_text(url)
        info = extract_document_info(html)
        title = parse_title(html)
        logger.info(f"Title: {title}")
        if out:
            from .core.storage import JsonlWriter
            w = JsonlWriter(out)
            w.write({"url": url, **info})
            w.close()
    asyncio.run(_run())


def cmd_luoc_do_playwright_from_file(
    input_path: Path,
    out: Path,
    cookies_in: Path | None = None,
    headed: bool = False,
    screenshots_dir: Path | None = None,
    only_tab8: bool = False,
    relogin_on_fail: bool = False,
    download_tab8: bool = False,
    downloads_dir: Path | None = None,
    login_first: bool = False,
    tab8_minimal_out: bool = False,
    fmt_opt: str | None = None,
):
    """Use Playwright to click #aLuocDo and parse #tab4 for each URL in the input file.
    NOTE: Keep this function synchronous to avoid Playwright Sync API warning inside asyncio.
    """
    import json
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    urls: list[str] = []
    if isinstance(raw, list):
        for it in raw:
            if isinstance(it, str):
                urls.append(it)
            elif isinstance(it, dict):
                u = it.get("Url") or it.get("url") or it.get("canonical_url")
                if u:
                    urls.append(u)
    # Deduplicate canonical
    from urllib.parse import urlparse, urlunparse
    canon, seen = [], set()
    for u in urls:
        pu = urlparse(u)
        cu = urlunparse((pu.scheme, pu.netloc, pu.path, "", "", ""))
        if cu not in seen:
            seen.add(cu); canon.append(cu)
    logger.info(f"Loaded {len(urls)} urls, unique: {len(canon)}")

    # Decide output format (jsonl default; switch to json if --format json or .json suffix)
    fmt = (fmt_opt or (out.suffix.lower().lstrip('.') or 'jsonl')).lower()
    rows: list[dict] = []
    w = None
    if fmt != 'json':
        from .core.storage import JsonlWriter
        out.parent.mkdir(parents=True, exist_ok=True)
        w = JsonlWriter(out)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
    shots = screenshots_dir or Path("data/screenshots")
    # Run Playwright per URL (sync helper inside loop)
    for idx, u in enumerate(canon, start=1):
        try:
            data = extract_luoc_do_with_playwright(
                url=u,
                screenshots_dir=shots,
                cookies_path=cookies_in,
                headed=headed,
                only_tab8=only_tab8,
                relogin_on_fail=relogin_on_fail,
                download_tab8=download_tab8,
                downloads_dir=downloads_dir or Path("data/downloads"),
            )
            data["stt"] = idx
            if tab8_minimal_out and download_tab8:
                # Only keep minimal fields for tab8 download result
                # Robust title fallback: doc_title -> saved_to filename stem -> download filename
                title = (data.get("doc_title") or "").strip()
                if not title:
                    saved_to = data.get("tab8_download_saved_to") or ""
                    try:
                        if saved_to:
                            title = Path(saved_to).stem.replace("_", " ")
                    except Exception:
                        pass
                if not title:
                    fn = (data.get("tab8_download_filename") or "").strip()
                    if fn:
                        from os.path import splitext
                        title = splitext(fn)[0].replace("_", " ")
                minimal = {
                    "stt": idx,
                    "ten_van_ban": title or None,
                    "download_url": data.get("tab8_download_url"),
                    "saved_to": data.get("tab8_download_saved_to"),
                }
                if fmt == 'json':
                    rows.append(minimal)
                else:
                    w.write(minimal)
            else:
                if fmt == 'json':
                    rows.append(data)
                else:
                    w.write(data)
            logger.info(f"Playwright parsed luoc-do #{idx}: {u}")
        except Exception as e:
            logger.warning(f"Playwright failed for {u}: {e}")
    if fmt == 'json':
        import json
        out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
        logger.info(f"Saved JSON array to {out}")
    else:
        w.close()
        logger.info(f"Saved JSONL to {out}")


def cmd_luoc_do_from_file(
    input_path: Path,
    out: Path,
    cookies_in: Path | None = None,
    fmt_opt: str | None = None,
):
    async def _run():
        # Read input links (expect JSON array of objects with key 'Url' or plain array of strings)
        import json
        if not input_path.exists():
            logger.error(f"Input file not found: {input_path}")
            return
        raw = json.loads(input_path.read_text(encoding="utf-8"))
        urls: list[str] = []
        if isinstance(raw, list):
            for it in raw:
                if isinstance(it, str):
                    urls.append(it)
                elif isinstance(it, dict):
                    u = it.get("Url") or it.get("url") or it.get("canonical_url")
                    if u:
                        urls.append(u)
        # Deduplicate by canonical URL (strip query/fragment)
        from urllib.parse import urlparse, urlunparse
        canon = []
        seen = set()
        for u in urls:
            pu = urlparse(u)
            cu = urlunparse((pu.scheme, pu.netloc, pu.path, "", "", ""))
            if cu not in seen:
                seen.add(cu)
                canon.append(cu)
        logger.info(f"Loaded {len(urls)} urls, unique after canonicalization: {len(canon)}")

        client = HttpClient()
        try:
            if cookies_in:
                client.load_cookies(cookies_in)
            results = []
            for idx, url in enumerate(canon, start=1):
                try:
                    html = await client.get_text(url)
                    data = extract_luoc_do(html)
                    data["url"] = url
                    data["stt"] = idx
                    results.append(data)
                    logger.info(f"Parsed luoc-do #{idx}: {url}")
                except Exception as e:
                    logger.warning(f"Failed to parse {url}: {e}")
            # Write output
            fmt = (fmt_opt or (out.suffix.lower().lstrip('.') or 'jsonl')).lower()
            out.parent.mkdir(parents=True, exist_ok=True)
            if fmt == 'json':
                import json
                out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
                logger.info(f"Saved JSON array to {out}")
            else:
                from .core.storage import JsonlWriter
                w = JsonlWriter(out)
                for row in results:
                    w.write(row)
                w.close()
                logger.info(f"Saved JSONL to {out}")
        finally:
            await client.close()
    asyncio.run(_run())


def _set_query_param(url: str, key: str, value: str) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    qs[key] = [value]
    new_query = urlencode(qs, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


def cmd_links_from_search(
    url: str,
    out: Path | None,
    max_pages: int,
    page_param: str,
    fmt_opt: str | None = None,
    only_basic: bool = False,
    cookies_in: Path | None = None,
    start_page: int = 1,
    end_page: int | None = None,
):
    async def _run():
        # Prepare client (with optional cookies)
        client = HttpClient()
        try:
            if cookies_in:
                client.load_cookies(cookies_in)

            def _canonicalize_doc_url(u: str) -> str:
                pu = urlparse(u)
                return urlunparse((pu.scheme, pu.netloc, pu.path, "", "", ""))

            all_items = []
            seen_keys = set()  # use doc_id first, fallback to canonical url
            # Use start_page and end_page if provided, otherwise use max_pages
            page_start = start_page
            page_end = end_page if end_page else (start_page + max_pages - 1)
            for page in range(page_start, page_end + 1):
                page_url = _set_query_param(url, page_param, str(page))
                logger.debug(f"Fetching search page: {page_url}")
                try:
                    html = await client.get_text(page_url)
                    # Check for CAPTCHA
                    if "Bạn đã tìm kiếm với tốc độ của Robot" in html or "txtSecCode" in html:
                        logger.error(f"CAPTCHA detected on page {page}! Stopping crawl.")
                        logger.error("Please increase delay or use Playwright with CAPTCHA solver.")
                        break
                except Exception as e:
                    logger.error(f"Fetch failed for {page_url}: {e}")
                    continue
                parsed = urlparse(page_url)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
                try:
                    items = extract_document_items_from_search(html, base_url)
                except Exception as e:
                    logger.error(f"Parse failed for {page_url}: {e}")
                    items = []
                # Debug: always save HTML to inspect structure
                try:
                    dbg_dir = Path("data/debug")
                    dbg_dir.mkdir(parents=True, exist_ok=True)
                    dbg_file = dbg_dir / f"search_page_{page}.html"
                    dbg_file.write_text(html, encoding="utf-8")
                    logger.info(f"Saved HTML to {dbg_file} for inspection")
                except Exception as _e:
                    logger.debug(f"Failed to dump HTML: {_e}")
                # Canonicalize URL and assign to canonical_url
                for it in items:
                    pu = urlparse(it["url"])
                    it["canonical_url"] = urlunparse((pu.scheme, pu.netloc, pu.path, "", "", ""))
                # Limit 20 records per page (default requirement)
                per_page_limit = 20
                page_added = 0
                page_seen = 0
                for it in items:
                    key = it.get("doc_id") or it.get("canonical_url")
                    if key and key not in seen_keys:
                        page_seen += 1
                        if page_added < per_page_limit:
                            seen_keys.add(key)
                            all_items.append(it)
                            page_added += 1
                logger.info(
                    f"Page {page}: added {page_added} (unique candidates on page: {page_seen}, raw items: {len(items)})"
                )
                # Add delay between pages to avoid CAPTCHA (5-10s)
                if page < page_end:
                    import random
                    delay = random.uniform(5.0, 10.0)
                    logger.info(f"Waiting {delay:.1f}s before next page...")
                    await asyncio.sleep(delay)
            logger.info(f"Total unique items: {len(all_items)}")
            for it in all_items:
                print(it.get("canonical_url") or it.get("url"))
            if out:
                # Determine format (fallback json if no extension)
                fmt = (fmt_opt or (out.suffix.lower().lstrip('.') or 'json')).lower()
                # Prepare data according to only-basic requirement
                if only_basic:
                    basic_items = [
                        {
                            "Stt": idx,
                            "Ten van ban": it.get("title"),
                            "Url": it.get("canonical_url") or it.get("url"),
                            "Ngay cap nhat": it.get("ngay_cap_nhat"),
                        }
                        for idx, it in enumerate(all_items, start=1)
                    ]
                else:
                    basic_items = None

                out.parent.mkdir(parents=True, exist_ok=True)
                try:
                    if fmt == "json":
                        import json
                        with out.open("w", encoding="utf-8") as f:
                            json.dump(basic_items if only_basic else all_items, f, ensure_ascii=False, indent=2)
                        logger.info(f"Saved JSON array to {out}")
                    elif fmt == "csv":
                        import csv
                        with out.open("w", encoding="utf-8", newline="") as f:
                            writer = csv.writer(f)
                            # Column headers: Stt, Ten van ban, Url, Ngay cap nhat
                            writer.writerow(["Stt", "Ten van ban", "Url", "Ngay cap nhat"])
                            if only_basic:
                                for row in basic_items:
                                    writer.writerow([row["Stt"], row["Ten van ban"], row["Url"], row.get("Ngay cap nhat", "")])
                            else:
                                for idx, it in enumerate(all_items, start=1):
                                    writer.writerow([idx, it.get("title", ""), it.get("canonical_url") or it.get("url"), it.get("ngay_cap_nhat", "")])
                        logger.info(f"Saved CSV to {out}")
                    else:  # jsonl
                        from .core.storage import JsonlWriter
                        w = JsonlWriter(out)
                        if only_basic:
                            for row in basic_items:
                                w.write({
                                    "Stt": row["Stt"],
                                    "Ten van ban": row["Ten van ban"],
                                    "Url": row["Url"],
                                    "Ngay cap nhat": row.get("Ngay cap nhat"),
                                })
                        else:
                            for idx, it in enumerate(all_items, start=1):
                                w.write({
                                    "stt": idx,
                                    "title": it.get("title"),
                                    "url": it.get("canonical_url") or it.get("url"),
                                    **it,
                                })
                        w.close()
                        logger.info(f"Saved JSONL to {out}")
                except Exception as e:
                    logger.error(f"Write output failed: {e}")
        finally:
            await client.close()
    # Ensure _run() is always executed
    asyncio.run(_run())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tvpl_crawler")
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("crawl-url", help="Crawl mot URL va in thong tin co ban")
    p1.add_argument("--url", "-u", required=True)
    p1.add_argument("--out", "-o", type=Path, help="Luu ket qua vao file JSONL")

    p2 = sub.add_parser("links-from-search", help="Trich xuat link van ban tu trang ket qua tim kiem")
    p2.add_argument(
        "--url",
        "-u",
        default="https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&match=True&area=0",
        help="URL trang tim kiem (mac dinh la trang tim van ban chung)"
    )
    p2.add_argument("--out", "-o", type=Path, help="Duong dan file dau ra")
    p2.add_argument("--max-pages", "-m", type=int, default=1, help="So trang can lay (mac dinh 1, bo qua neu dung --start-page/--end-page)")
    p2.add_argument("--start-page", type=int, help="Trang bat dau (mac dinh 1)")
    p2.add_argument("--end-page", type=int, help="Trang ket thuc (dung voi --start-page)")
    p2.add_argument("--page-param", type=str, default="page", help="Ten tham so phan trang, mac dinh 'page'")
    # Format option: by file extension or --format
    p2.add_argument("--format", "-f", choices=["jsonl", "json", "csv"], help="Dinh dang xuat (mac dinh dua tren duoi file)")
    p2.add_argument("--only-basic", "-b", action="store_true", help="Chi xuat 3 truong: Stt, Ten van ban, Url")
    p2.add_argument("--cookies", type=Path, help="Nap cookies tu file JSON de truy cap tinh nang yeu cau dang nhap")

    # Quick alias: links-basic (default only-basic, JSON)
    p3 = sub.add_parser("links-basic", help="Nhanh: xuat Stt, Ten van ban, Url (mac dinh JSON)")
    p3.add_argument(
        "--url",
        "-u",
        default="https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&match=True&area=0",
        help="URL trang tim kiem (mac dinh la trang tim van ban chung)"
    )
    p3.add_argument("--out", "-o", type=Path, required=True, help="Duong dan file dau ra (.json, .jsonl hoac .csv)")
    p3.add_argument("--max-pages", "-m", type=int, default=1, help="So trang can lay (mac dinh 1, bo qua neu dung --start-page/--end-page)")
    p3.add_argument("--start-page", type=int, help="Trang bat dau (mac dinh 1)")
    p3.add_argument("--end-page", type=int, help="Trang ket thuc (dung voi --start-page)")
    p3.add_argument("--page-param", type=str, default="page", help="Ten tham so phan trang, mac dinh 'page'")
    p3.add_argument("--cookies", type=Path, help="Nap cookies tu file JSON de truy cap tinh nang yeu cau dang nhap")

    # Login via Playwright (replaces old HTTP login)
    p4 = sub.add_parser("login-playwright", help="Dang nhap bang Playwright va luu cookies ra file JSON")
    p4.add_argument("--login-url", default="https://thuvienphapluat.vn/", help="URL trang co form dang nhap (homepage)")
    p4.add_argument("--username", "-U", help="Ten dang nhap (bo qua de duoc prompt)")
    p4.add_argument("--password", "-P", help="Mat khau (bo qua de duoc prompt an toan)")
    p4.add_argument("--cookies-out", type=Path, default=Path("data/cookies.json"), help="Duong dan luu cookies JSON")
    p4.add_argument("--headed", action="store_true", help="Mo trinh duyet hien thi (mac dinh headless)")
    p4.add_argument("--user-selector", help="CSS selector cho truong username (tuy chon)")
    p4.add_argument("--pass-selector", help="CSS selector cho truong password (tuy chon)")
    p4.add_argument("--submit-selector", help="CSS selector cho nut Dang nhap (tuy chon)")
    p4.add_argument("--manual", action="store_true", help="Neu form khong bat duoc selector, cho phep ban dang nhap thu cong roi luu cookies")

    # Luoc do from file links
    p5 = sub.add_parser("luoc-do-from-file", help="Doc file links JSON, loai trung va crawl tab Luoc do cua tung van ban")
    p5.add_argument("--in", "-i", dest="input", type=Path, required=True, help="File JSON dau vao (mang cac object co truong Url hoac mang chuoi)")
    p5.add_argument("--out", "-o", type=Path, required=True, help="File ket qua (jsonl hoac json)")
    p5.add_argument("--format", "-f", dest="fmt", choices=["jsonl", "json"], help="Dinh dang output (mac dinh dua vao duoi file, fallback jsonl)")
    p5.add_argument("--cookies", type=Path, help="File cookies JSON (tuy chon)")

    # Luoc do using Playwright (click tab #aLuocDo -> #tab4, screenshot)
    p6 = sub.add_parser("luoc-do-playwright-from-file", help="Dung Playwright mo tung URL, bam Luoc do (#aLuocDo) va/hoac tab Tai ve (#tab8); co screenshot")
    p6.add_argument("--in", "-i", dest="input", type=Path, required=True, help="File JSON dau vao (mang object co Url hoac mang chuoi)")
    p6.add_argument("--out", "-o", type=Path, required=True, help="File ket qua JSONL")
    p6.add_argument("--cookies", type=Path, help="File cookies JSON (tuy chon)")
    p6.add_argument("--headed", action="store_true", help="Hien trinh duyet khi chay (mac dinh headless)")
    p6.add_argument("--shots", type=Path, default=Path("data/screenshots"), help="Thu muc luu anh screenshot")
    p6.add_argument("--only-tab8", action="store_true", help="Chi crawl tab Tai ve (#tab8), bo qua tab Luoc do (#tab4)")
    p6.add_argument("--relogin-on-fail", action="store_true", help="Neu phat hien chua dang nhap, tu dang nhap bang bien moi truong roi tiep tuc")
    p6.add_argument("--download-tab8", action="store_true", help="Bam 'Tai Van ban tieng Viet' va luu file ve data/downloads")
    p6.add_argument("--downloads-dir", type=Path, default=Path("data/downloads"), help="Thu muc luu file tai ve")
    p6.add_argument("--login-first", action="store_true", help="Dang nhap ngay lap tuc truoc khi mo bat ky lien ket nao (su dung TVPL_USERNAME/PASSWORD)")
    p6.add_argument("--tab8-minimal-out", action="store_true", help="Ghi JSONL chi gom stt, ten_van_ban, download_url, saved_to cho ket qua tab8")

    # Refresh cookies using env (no prompt)
    p7 = sub.add_parser("refresh-cookies", help="Dang nhap va lam moi cookies doc tu bien moi truong TVPL_USERNAME/TVPL_PASSWORD/TVPL_LOGIN_URL")
    p7.add_argument("--headed", action="store_true", help="Mo trinh duyet hien thi (mac dinh headless)")
    p7.add_argument("--cookies-out", type=Path, default=Path("data/cookies.json"), help="Duong dan luu cookies JSON")

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "crawl-url":
        cmd_crawl_url(args.url, args.out)
    elif args.cmd == "links-from-search":
        cmd_links_from_search(args.url, args.out, args.max_pages, args.page_param, args.format, args.only_basic, args.cookies, 
                            args.start_page or 1, args.end_page)
    elif args.cmd == "links-basic":
        # Infer format from file extension, default json if none
        fmt = (args.out.suffix.lower().lstrip('.') or 'json') if args.out else 'json'
        cmd_links_from_search(args.url, args.out, args.max_pages, args.page_param, fmt, True, args.cookies,
                            args.start_page or 1, args.end_page)
    elif args.cmd == "login-playwright":
        # Prioritize environment variables if not passed as parameters
        username = args.username or os.getenv("TVPL_USERNAME") or input("Username: ")
        password = args.password or os.getenv("TVPL_PASSWORD") or getpass("Password: ")
        login_url = args.login_url or os.getenv("TVPL_LOGIN_URL", "https://thuvienphapluat.vn/")
        ok = login_with_playwright(
            login_url=login_url,
            username=username,
            password=password,
            cookies_out=args.cookies_out,
            headed=args.headed,
            user_selector=args.user_selector,
            pass_selector=args.pass_selector,
            submit_selector=args.submit_selector,
            manual=args.manual,
        )
        if ok:
            logger.info("Login OK and cookies saved by Playwright.")
        else:
            logger.warning("Playwright login may have failed. Check cookies.json or adjust selectors.")
    elif args.cmd == "refresh-cookies":
        username = os.getenv("TVPL_USERNAME")
        password = os.getenv("TVPL_PASSWORD")
        login_url = os.getenv("TVPL_LOGIN_URL", "https://thuvienphapluat.vn/")
        if not username or not password:
            logger.error("Missing TVPL_USERNAME or TVPL_PASSWORD in environment. Please set them or use login-playwright with -U/-P.")
            return
        ok = login_with_playwright(
            login_url=login_url,
            username=username,
            password=password,
            cookies_out=args.cookies_out,
            headed=args.headed,
            user_selector=None,
            pass_selector=None,
            submit_selector=None,
            manual=False,
        )
        if ok:
            logger.info("Refreshed cookies using environment variables.")
        else:
            logger.warning("Failed to refresh cookies with environment variables.")
    elif args.cmd == "luoc-do-playwright-from-file":
        cmd_luoc_do_playwright_from_file(
            input_path=args.input,
            out=args.out,
            cookies_in=args.cookies,
            headed=args.headed,
            screenshots_dir=args.shots,
            only_tab8=args.only_tab8,
            relogin_on_fail=args.relogin_on_fail,
            download_tab8=args.download_tab8,
            downloads_dir=args.downloads_dir,
            login_first=args.login_first,
            tab8_minimal_out=args.tab8_minimal_out,
        )
    elif args.cmd == "luoc-do-from-file":
        cmd_luoc_do_from_file(
            input_path=args.input,
            out=args.out,
            cookies_in=args.cookies,
            fmt_opt=args.fmt,
        )


if __name__ == "__main__":
    main()