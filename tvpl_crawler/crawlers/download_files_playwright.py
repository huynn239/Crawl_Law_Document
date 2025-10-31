"""Download files using Playwright with login session"""
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

async def download_file_with_playwright(url: str, output_path: Path, storage_state: str = "data/storage_state.json"):
    """Download single file with Playwright"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Load session
        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()
        
        # Navigate and download
        async with page.expect_download() as download_info:
            await page.goto(url)
        
        download = await download_info.value
        await download.save_as(output_path)
        
        await browser.close()
        return True

async def download_files_batch(files: list, storage_state: str = "data/storage_state.json"):
    """Download multiple files"""
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=storage_state)
        
        for file_info in files:
            try:
                page = await context.new_page()
                
                # Download
                async with page.expect_download(timeout=60000) as download_info:
                    await page.goto(file_info['url'])
                
                download = await download_info.value
                
                # Save to temp
                temp_path = Path(f"/tmp/{file_info['file_name']}")
                await download.save_as(temp_path)
                
                await page.close()
                
                results.append({
                    "id": file_info['id'],
                    "status": "success",
                    "path": str(temp_path),
                    "size": temp_path.stat().st_size
                })
                
            except Exception as e:
                results.append({
                    "id": file_info['id'],
                    "status": "failed",
                    "error": str(e)
                })
        
        await browser.close()
    
    return results
