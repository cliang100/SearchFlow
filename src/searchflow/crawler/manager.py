import asyncio
import hashlib
import logging
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from ..database.connection import SessionLocal
from ..database.models import Document
from .queue import CrawlQueue
from .safety import normalize
from .scraper import USER_AGENT, AsyncWebScraper

log = logging.getLogger(__name__)


class CrawlerManager:
    def __init__(self, queue: CrawlQueue, scraper: AsyncWebScraper, max_depth: int, max_pages: int):
        self.queue = queue
        self.scraper = scraper
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.robots = {}

    async def start_crawl(self, start_url: str) -> int:
        start_url = normalize(start_url)
        self.host = urlsplit(start_url).netloc
        await self.queue.clear()
        await self.queue.add_url(start_url, depth=1)

        crawled = 0
        async with self.scraper:
            while crawled < self.max_pages:
                job = await self.queue.next_job()
                if job is None:
                    break
                if await self._process(job["url"], job["depth"]):
                    crawled += 1
                    await self.queue.mark_done()
        log.info("Crawl of %s finished: %d pages", start_url, crawled)
        return crawled

    async def _process(self, url: str, depth: int) -> bool:
        if not await self._robots_allow(url):
            log.info("robots.txt disallows %s", url)
            return False
        page = await self.scraper.fetch(url)
        if not page.success:
            log.info("Skipped %s: %s", url, page.error)
            return False
        await self.queue.mark_seen(page.final_url)

        extracted = self.scraper.extract_content(page.html, page.final_url)
        if not extracted.success:
            return False
        await asyncio.to_thread(save_document, page.final_url, extracted.title, extracted.content, depth)

        if depth < self.max_depth:
            for link in extracted.links:
                if urlsplit(link).netloc == self.host:
                    await self.queue.add_url(link, depth + 1)
        return True

    async def _robots_allow(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self.robots:
            parser = RobotFileParser()
            result = await self.scraper.fetch(origin + "/robots.txt", html_only=False)
            # a missing robots.txt allows everything
            parser.parse(result.html.splitlines() if result.success else [])
            self.robots[origin] = parser
        return self.robots[origin].can_fetch(USER_AGENT, url)


def save_document(url: str, title: str, content: str, depth: int) -> bool:
    """Store a page unless its URL or exact content is already indexed."""
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    with SessionLocal() as db:
        exists = db.query(Document.id).filter((Document.url == url) | (Document.content_hash == content_hash)).first()
        if exists:
            return False
        db.add(Document(
            url=url[:2048],
            title=title[:500],
            content=content,
            content_hash=content_hash,
            crawl_depth=depth,
            word_count=len(content.split()),
        ))
        db.commit()
        return True
