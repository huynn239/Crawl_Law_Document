"""Crawl pending documents directly from database"""
import sys
import subprocess
from pathlib import Path
from tvpl_crawler.fetch_pending_urls import fetch_pending_urls

def crawl_pending(limit=None, concurrency=2, timeout_ms=30000, reuse_session=False, headed=False, save_per_batch=True):
    """Fetch pending URLs from DB and crawl them"""
    
    print(f"Fetching {limit or 'all'} pending URLs from database...")
    
    # Fetch pending URLs to temp file
    tmp_file = Path("data/temp_pending.json")
    links = fetch_pending_urls(limit, str(tmp_file))
    
    if not links:
        print("No pending URLs found")
        return
    
    print(f"\nCrawling {len(links)} documents...")
    
    # Build crawl command
    cmd = [
        "python", "-m", "tvpl_crawler.crawl_data_fast",
        str(tmp_file),
        "data/crawl_result.json",
        str(concurrency),
        str(timeout_ms)
    ]
    
    if reuse_session:
        cmd.append("--reuse-session")
    if headed:
        cmd.append("--headed")
    if save_per_batch:
        cmd.append("--save-per-batch")
    
    # Run crawl
    result = subprocess.run(cmd)
    
    # Cleanup temp file
    tmp_file.unlink(missing_ok=True)
    
    return result.returncode == 0

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Crawl pending documents from database')
    parser.add_argument('--limit', type=int, help='Number of documents to crawl')
    parser.add_argument('--concurrency', type=int, default=2, help='Concurrent crawl workers')
    parser.add_argument('--timeout', type=int, default=30000, help='Timeout in milliseconds')
    parser.add_argument('--reuse-session', action='store_true', help='Reuse browser session')
    parser.add_argument('--headed', action='store_true', help='Show browser')
    parser.add_argument('--save-per-batch', action='store_true', help='Save to database per batch')
    
    args = parser.parse_args()
    
    success = crawl_pending(
        limit=args.limit,
        concurrency=args.concurrency,
        timeout_ms=args.timeout,
        reuse_session=args.reuse_session,
        headed=args.headed,
        save_per_batch=args.save_per_batch
    )
    
    sys.exit(0 if success else 1)
