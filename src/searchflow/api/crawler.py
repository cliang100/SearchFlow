import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from redis.asyncio import Redis

from .. import config
from ..auth import require_admin
from ..crawler.manager import CrawlerManager
from ..crawler.queue import CrawlQueue
from ..crawler.safety import is_allowed_url, normalize
from ..crawler.scraper import AsyncWebScraper
from ..search import search

log = logging.getLogger(__name__)
router = APIRouter(prefix="/crawler", tags=["crawler"])

# shortcut: in-process registry, so it assumes a single API worker
active_crawls = {}


class CrawlRequest(BaseModel):
    start_url: HttpUrl
    max_depth: int = Field(default=2, ge=1, le=config.MAX_CRAWL_DEPTH)
    max_pages: int = Field(default=50, ge=1, le=config.MAX_CRAWL_PAGES)


class CrawlResponse(BaseModel):
    message: str
    start_url: str
    max_pages: int
    status: str = "started"


@router.post("/start", response_model=CrawlResponse, status_code=202, dependencies=[Depends(require_admin)])
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    start_url = normalize(str(request.start_url))
    if start_url in active_crawls:
        raise HTTPException(status_code=409, detail="Crawl already in progress for this URL")
    if not await is_allowed_url(start_url):
        raise HTTPException(status_code=400, detail="URL must be http(s) and resolve to a public address")

    redis = Redis.from_url(config.REDIS_URL)
    queue = CrawlQueue(redis, start_url)
    manager = CrawlerManager(queue, AsyncWebScraper(delay=config.CRAWL_DELAY), request.max_depth, request.max_pages)
    active_crawls[start_url] = queue
    background_tasks.add_task(run_crawl, manager, redis, start_url)
    return CrawlResponse(message=f"Crawl started for {start_url}", start_url=start_url, max_pages=request.max_pages)


@router.get("/status/{url:path}")
async def get_crawl_status(url: str):
    queue = active_crawls.get(normalize(url))
    if queue is None:
        raise HTTPException(status_code=404, detail="No active crawl for this URL")
    return {"url": url, "status": "active", **await queue.status()}


async def run_crawl(manager: CrawlerManager, redis: Redis, start_url: str):
    try:
        await manager.start_crawl(start_url)
        await asyncio.to_thread(search.rebuild)
    except Exception:
        log.exception("Crawl of %s failed", start_url)
    finally:
        active_crawls.pop(start_url, None)
        await redis.aclose()
