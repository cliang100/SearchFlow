from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import Optional

from ..crawler.manager import CrawlerManager

router = APIRouter(prefix="/crawler", tags=["crawler"])

class CrawlRequest(BaseModel):
    start_url: HttpUrl
    max_depth: int = 2
    max_pages: int = 50
    
class CrawlResponse(BaseModel):
    message: str
    start_url: str
    max_pages: int
    status: str = "started"
    
# Global crawler instance (for demo)
active_crawlers = {}

@router.post("/start", response_model=CrawlResponse, status_code=202)
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """Start crawling from a URL"""
    
    # Check if already crawling
    if str(request.start_url) in active_crawlers:
        raise HTTPException(status_code=400, detail="Crawl already in progress for this URL")
    
    # Create crawler manager
    crawler = CrawlerManager(
        max_depth=request.max_depth,
        max_pages=request.max_pages
    )
    
    # Store crawler instance
    active_crawlers[str(request.start_url)] = crawler
    
    # Start crawl in background
    background_tasks.add_task(
        run_crawl_background,
        crawler,
        str(request.start_url)
    )
    
    return CrawlResponse(
        message=f"Crawl started for {request.start_url}",
        start_url=str(request.start_url),
        max_pages=request.max_pages
    )
    
@router.get("/status/{url:path}")
async def get_crawl_status(url: str):
    """Get crawl status for a URL"""
    
    if url not in active_crawlers:
        raise HTTPException(status_code=404, detail="No active crawl for this URL")
    
    crawler = active_crawlers[url]
    queue_size = crawler.queue.get_queue_size()
    processing_count = crawler.queue.get_processing_count()
    completed_count = crawler.queue.get_completed_count()
    
    return {
        "url": url,
        "queue_size": queue_size,
        "processing_count": processing_count,
        "completed_count": completed_count,
        "status": "active"
    }

async def run_crawl_background(crawler: CrawlerManager, start_url: str):
    """Run crawl in background task"""
    try:
        await crawler.start_crawl(start_url)
    finally:
        # Clean up
        if start_url in active_crawlers:
            del active_crawlers[start_url]