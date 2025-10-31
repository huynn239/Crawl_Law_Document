#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple API wrapper for crawl_data_fast"""
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List
import subprocess
import json
import uuid
from pathlib import Path

app = FastAPI(title="TVPL Crawler API")

class CrawlRequest(BaseModel):
    urls: List[str]
    concurrency: int = 2
    timeout_ms: int = 30000

class CrawlResponse(BaseModel):
    job_id: str
    status: str
    message: str

# In-memory job storage (dùng Redis cho production)
jobs = {}

@app.post("/crawl", response_model=CrawlResponse)
async def crawl_urls(request: CrawlRequest, background_tasks: BackgroundTasks):
    """Start crawl job"""
    job_id = str(uuid.uuid4())
    
    # Tạo file input
    input_file = Path(f"data/jobs/{job_id}_input.json")
    input_file.parent.mkdir(exist_ok=True)
    
    links = [{"Stt": i+1, "Url": url, "Ten van ban": ""} 
             for i, url in enumerate(request.urls)]
    
    input_file.write_text(json.dumps(links, ensure_ascii=False, indent=2))
    
    # Start background job
    jobs[job_id] = {"status": "running", "result": None}
    background_tasks.add_task(run_crawler, job_id, input_file, request.concurrency, request.timeout_ms)
    
    return CrawlResponse(
        job_id=job_id,
        status="running",
        message=f"Started crawling {len(request.urls)} URLs"
    )

@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Get job status and result"""
    if job_id not in jobs:
        return {"error": "Job not found"}
    
    return jobs[job_id]

def run_crawler(job_id: str, input_file: Path, concurrency: int, timeout_ms: int):
    """Run crawler in background"""
    output_file = Path(f"data/jobs/{job_id}_result.json")
    
    try:
        cmd = [
            "python", "crawl_data_fast.py",
            str(input_file),
            str(output_file),
            str(concurrency),
            str(timeout_ms),
            "--reuse-session"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        if result.returncode == 0 and output_file.exists():
            data = json.loads(output_file.read_text(encoding='utf-8'))
            jobs[job_id] = {
                "status": "completed",
                "result": data,
                "total": len(data)
            }
        else:
            jobs[job_id] = {
                "status": "error",
                "error": result.stderr
            }
    except Exception as e:
        jobs[job_id] = {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
