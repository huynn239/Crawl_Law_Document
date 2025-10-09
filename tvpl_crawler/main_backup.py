import argparse
import asyncio
import os
from loguru import logger
from pathlib import Path
from .http import fetch_text
from .parser import (
    parse_title,
    extract_document_info,
    extract_document_links_from_search,
    extract_document_items_from_search,
    extract_luoc_do,
)
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from getpass import getpass
from typing import List
from .http import HttpClient
from .playwright_login import login_with_playwright
from .playwright_extract import extract_luoc_do_with_playwright


def cmd_crawl_url(url: str, out: Path | None):
    async def _run():
        html = await fetch_text(url)
        info = extract_document_info(html)
        title = parse_title(html)
        logger.info(f"Title: {title}")
        if out:
            from .storage import JsonlWriter
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
        from .storage import JsonlWriter
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
                from .storage import JsonlWriter
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
):
    async def _run():
        # Prepare client (with optional cookies)
        client = HttpClient()
        try:
            if cookies_in:
                client.load_cookies(cookies_in)

            def _canonicalize_doc_url(u: str) -> str:
                # Chuẩn hóa: bỏ query/fragment để loại các biến thể ?tab=...
                pu = urlparse(u)
                return urlunparse((pu.scheme, pu.netloc, pu.path, "", "", ""))

            all_items = []
            seen_keys = set()  # use doc_id first, fallback to canonical url
            for page in range(1, max_pages + 1):
                page_url = _set_query_param(url, page_param, str(page)) if max_pages > 1 else url
                logger.debug(f"Fetching search page: {page_url}")
                try:
                    html = await client.get_text(page_url)
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
                # Diagnostics: if no items found, dump HTML to inspect (possible consent/challenge page)
                if not items:
                    try:
                        from .parser import parse_title
                        title = parse_title(html) or "(no title)"
                        logger.warning(f"No items found on page {page}. Title: {title}")
                        dbg_dir = Path("data/debug")
                        dbg_dir.mkdir(parents=True, exist_ok=True)
                        dbg_file = dbg_dir / f"search_page_{page}.html"
                        dbg_file.write_text(html, encoding="utf-8")
                        logger.warning(f"Saved debug HTML to {dbg_file}")
                        snippet = html[:400].replace("\n", " ")
                        logger.debug(f"First 400 chars: {snippet}")
                    except Exception as _e:
                        logger.debug(f"Failed to dump debug HTML: {_e}")
                # Chuẩn hóa URL (bỏ query/fragment) và gán vào canonical_url
                for it in items:
                    pu = urlparse(it["url"])
                    it["canonical_url"] = urlunparse((pu.scheme, pu.netloc, pu.path, "", "", ""))
                # Giới hạn 20 bản ghi mỗi trang (mặc định theo yêu cầu)
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
            logger.info(f"Total unique items: {len(all_items)}")
            for it in all_items:
                print(it.get("canonical_url") or it.get("url"))
            if out:
                # Xác định format (fallback json nếu không có đuôi)
                fmt = (fmt_opt or (out.suffix.lower().lstrip('.') or 'json')).lower()
                # Chuẩn bị dữ liệu theo yêu cầu only-basic
                if only_basic:
                    basic_items = [
                        {
                            "Stt": idx,
                            "Tên văn bản": it.get("title"),
                            "Url": it.get("canonical_url") or it.get("url"),
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
                            # Tiêu đề cột theo yêu cầu: Stt, Tên văn bản, Url
                            writer.writerow(["Stt", "Tên văn bản", "Url"])
                            if only_basic:
                                for row in basic_items:
                                    writer.writerow([row["Stt"], row["Tên văn bản"], row["Url"]])
                            else:
                                for idx, it in enumerate(all_items, start=1):
                                    writer.writerow([idx, it.get("title", ""), it.get("canonical_url") or it.get("url")])
                        logger.info(f"Saved CSV to {out}")
                    else:  # jsonl
                        from .storage import JsonlWriter
                        w = JsonlWriter(out)
                        if only_basic:
                            for row in basic_items:
                                w.write({
                                    "Stt": row["Stt"],
                                    "Tên văn bản": row["Tên văn bản"],
                                    "Url": row["Url"],
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
    # Bảo đảm luôn thực thi _run()
    asyncio.run(_run())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tvpl_crawler")
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("crawl-url", help="Crawl một URL và in thông tin cơ bản")
    p1.add_argument("--url", "-u", required=True)
    p1.add_argument("--out", "-o", type=Path, help="Lưu kết quả vào file JSONL")

    p2 = sub.add_parser("links-from-search", help="Trích xuất link văn bản từ trang kết quả tìm kiếm")
    p2.add_argument(
        "--url",
        "-u",
        default="https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&match=True&area=0",
        help="URL trang tìm kiếm (mặc định là trang tìm văn bản chung)"
    )
    p2.add_argument("--out", "-o", type=Path, help="Đường dẫn file đầu ra")
    p2.add_argument("--max-pages", "-m", type=int, default=1, help="Số trang cần lấy (mặc định 1)")
    p2.add_argument("--page-param", type=str, default="page", help="Tên tham số phân trang, mặc định 'page'")
    # Tùy chọn định dạng xuất: theo phần mở rộng file hoặc --format
    p2.add_argument("--format", "-f", choices=["jsonl", "json", "csv"], help="Định dạng xuất (mặc định dựa trên đuôi file)")
    p2.add_argument("--only-basic", "-b", action="store_true", help="Chỉ xuất 3 trường: Stt, Tên văn bản, Url")
    p2.add_argument("--cookies", type=Path, help="Nạp cookies từ file JSON để truy cập tính năng yêu cầu đăng nhập")

    # Alias nhanh: links-basic (mặc định only-basic, JSON)
    p3 = sub.add_parser("links-basic", help="Nhanh: xuất Stt, Tên văn bản, Url (mặc định JSON)")
    p3.add_argument(
        "--url",
        "-u",
        default="https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&match=True&area=0",
        help="URL trang tìm kiếm (mặc định là trang tìm văn bản chung)"
    )
    p3.add_argument("--out", "-o", type=Path, required=True, help="Đường dẫn file đầu ra (.json, .jsonl hoặc .csv)")
    p3.add_argument("--max-pages", "-m", type=int, default=1, help="Số trang cần lấy (mặc định 1)")
    p3.add_argument("--page-param", type=str, default="page", help="Tên tham số phân trang, mặc định 'page'")
    p3.add_argument("--cookies", type=Path, help="Nạp cookies từ file JSON để truy cập tính năng yêu cầu đăng nhập")

    # Login via Playwright (replaces old HTTP login)
    p4 = sub.add_parser("login-playwright", help="Đăng nhập bằng Playwright và lưu cookies ra file JSON")
    p4.add_argument("--login-url", default="https://thuvienphapluat.vn/", help="URL trang có form đăng nhập (homepage)")
    p4.add_argument("--username", "-U", help="Tên đăng nhập (bỏ qua để được prompt)")
    p4.add_argument("--password", "-P", help="Mật khẩu (bỏ qua để được prompt an toàn)")
    p4.add_argument("--cookies-out", type=Path, default=Path("data/cookies.json"), help="Đường dẫn lưu cookies JSON")
    p4.add_argument("--headed", action="store_true", help="Mở trình duyệt hiển thị (mặc định headless)")
    p4.add_argument("--user-selector", help="CSS selector cho trường username (tuỳ chọn)")
    p4.add_argument("--pass-selector", help="CSS selector cho trường password (tuỳ chọn)")
    p4.add_argument("--submit-selector", help="CSS selector cho nút Đăng nhập (tuỳ chọn)")
    p4.add_argument("--manual", action="store_true", help="Nếu form không bắt được selector, cho phép bạn đăng nhập thủ công rồi lưu cookies")

    # Lược đồ từ file links
    p5 = sub.add_parser("luoc-do-from-file", help="Đọc file links JSON, loại trùng và crawl tab Lược đồ của từng văn bản")
    p5.add_argument("--in", "-i", dest="input", type=Path, required=True, help="File JSON đầu vào (mảng các object có trường Url hoặc mảng chuỗi)")
    p5.add_argument("--out", "-o", type=Path, required=True, help="File kết quả (jsonl hoặc json)")
    p5.add_argument("--format", "-f", dest="fmt", choices=["jsonl", "json"], help="Định dạng output (mặc định dựa vào đuôi file, fallback jsonl)")
    p5.add_argument("--cookies", type=Path, help="File cookies JSON (tùy chọn)")

    # Lược đồ bằng Playwright (nhấp tab #aLuocDo -> #tab4, screenshot)
    p6 = sub.add_parser("luoc-do-playwright-from-file", help="Dùng Playwright mở từng URL, bấm Lược đồ (#aLuocDo) và/hoặc tab Tải về (#tab8); có screenshot")
    p6.add_argument("--in", "-i", dest="input", type=Path, required=True, help="File JSON đầu vào (mảng object có Url hoặc mảng chuỗi)")
    p6.add_argument("--out", "-o", type=Path, required=True, help="File kết quả JSONL")
    p6.add_argument("--cookies", type=Path, help="File cookies JSON (tùy chọn)")
    p6.add_argument("--headed", action="store_true", help="Hiện trình duyệt khi chạy (mặc định headless)")
    p6.add_argument("--shots", type=Path, default=Path("data/screenshots"), help="Thư mục lưu ảnh screenshot")
    p6.add_argument("--only-tab8", action="store_true", help="Chỉ crawl tab Tải về (#tab8), bỏ qua tab Lược đồ (#tab4)")
    p6.add_argument("--relogin-on-fail", action="store_true", help="Nếu phát hiện chưa đăng nhập, tự đăng nhập bằng biến môi trường rồi tiếp tục")
    p6.add_argument("--download-tab8", action="store_true", help="Bấm 'Tải Văn bản tiếng Việt' và lưu file về data/downloads")
    p6.add_argument("--downloads-dir", type=Path, default=Path("data/downloads"), help="Thư mục lưu file tải về")
    p6.add_argument("--login-first", action="store_true", help="Đăng nhập ngay lập tức trước khi mở bất kỳ liên kết nào (sử dụng TVPL_USERNAME/PASSWORD)")
    p6.add_argument("--tab8-minimal-out", action="store_true", help="Ghi JSONL chỉ gồm stt, ten_van_ban, download_url, saved_to cho kết quả tab8")

    # Refresh cookies using env (no prompt)
    p7 = sub.add_parser("refresh-cookies", help="Đăng nhập và làm mới cookies đọc từ biến môi trường TVPL_USERNAME/TVPL_PASSWORD/TVPL_LOGIN_URL")
    p7.add_argument("--headed", action="store_true", help="Mở trình duyệt hiển thị (mặc định headless)")
    p7.add_argument("--cookies-out", type=Path, default=Path("data/cookies.json"), help="Đường dẫn lưu cookies JSON")

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "crawl-url":
        cmd_crawl_url(args.url, args.out)
    elif args.cmd == "links-from-search":
        cmd_links_from_search(args.url, args.out, args.max_pages, args.page_param, args.format, args.only_basic, args.cookies)
    elif args.cmd == "links-basic":
        # Suy ra định dạng từ đuôi file, mặc định json nếu không có
        fmt = (args.out.suffix.lower().lstrip('.') or 'json') if args.out else 'json'
        cmd_links_from_search(args.url, args.out, args.max_pages, args.page_param, fmt, True, args.cookies)
    elif args.cmd == "login-playwright":
        # Ưu tiên lấy từ biến môi trường nếu không truyền tham số
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
