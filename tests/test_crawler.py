import asyncio
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from redis.asyncio import Redis

from src.searchflow import config
from src.searchflow.crawler.manager import CrawlerManager
from src.searchflow.crawler.queue import CrawlQueue
from src.searchflow.crawler.safety import is_allowed_url
from src.searchflow.crawler.scraper import MAX_BYTES, AsyncWebScraper
from src.searchflow.database.connection import SessionLocal
from src.searchflow.database.models import Document

PAGES = {
    "/": '<title>Home</title><a href="/a">a</a> <a href="/a#top">a again</a> <a href="/b">b</a> '
         '<a href="/secret">secret</a> <a href="https://elsewhere.example/">away</a> <a href="/copy">copy</a> home page',
    "/a": '<title>A</title><a href="/">home</a> <a href="/deep">deep</a> page about apples',
    "/b": '<title>B</title><a href="/a">a</a> page about bananas',
    "/deep": "<title>Deep</title>too deep to reach",
    "/secret": "<title>Secret</title>robots says no",
    "/copy": '<title>B</title><a href="/a">a</a> page about bananas',
}


class Site(BaseHTTPRequestHandler):
    hits = []

    def do_GET(self):
        Site.hits.append(self.path)
        if self.path == "/robots.txt":
            return self.reply(200, "text/plain", "User-agent: *\nDisallow: /secret\n")
        if self.path == "/redirect-out":
            self.send_response(302)
            self.send_header("Location", "/internal-only")
            self.end_headers()
            return
        if self.path == "/huge":
            return self.reply(200, "text/html", "x" * (MAX_BYTES + 1))
        if self.path == "/image":
            return self.reply(200, "image/png", "png")
        if self.path in PAGES:
            return self.reply(200, "text/html", PAGES[self.path])
        self.reply(404, "text/html", "missing")

    def reply(self, status, content_type, body):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def site():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Site)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    Site.hits = []
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


async def allow_all(url):
    return True


def test_crawl_follows_links_once_and_respects_robots(site):
    async def crawl():
        redis = Redis.from_url(config.REDIS_URL)
        queue = CrawlQueue(redis, site)
        manager = CrawlerManager(queue, AsyncWebScraper(delay=0, is_allowed=allow_all), max_depth=2, max_pages=20)
        try:
            return await manager.start_crawl(site + "/"), await queue.status()
        finally:
            await queue.clear()
            await redis.aclose()

    crawled, status = asyncio.run(crawl())

    with SessionLocal() as db:
        saved = sorted(url.removeprefix(site) for (url,) in db.query(Document.url).all())
    # /copy has the same text as /b, /deep is past max_depth, /secret is blocked by robots.txt
    assert saved == ["/", "/a", "/b"]
    # every fetched page counts toward max_pages, including the duplicate
    assert crawled == 4
    assert Site.hits.count("/a") == 1
    assert "/secret" not in Site.hits and "/deep" not in Site.hits
    assert status["completed_count"] == 4


def test_scraper_checks_every_redirect_hop(site):
    async def is_allowed(url):
        return "internal-only" not in url

    async def fetch(path, html_only=True):
        async with AsyncWebScraper(delay=0, is_allowed=is_allowed) as scraper:
            return await scraper.fetch(site + path, html_only)

    assert asyncio.run(fetch("/redirect-out")).error == "URL not allowed"
    assert asyncio.run(fetch("/huge")).error == "page too large"
    assert asyncio.run(fetch("/image")).error == "not an HTML page"
    assert asyncio.run(fetch("/missing")).success is False
    assert asyncio.run(fetch("/a")).success is True


@pytest.mark.parametrize("url,allowed", [
    ("http://127.0.0.1/", False),
    ("http://localhost:8000/", False),
    ("http://[::1]/", False),
    ("http://10.1.2.3/", False),
    ("http://192.168.0.1/", False),
    ("http://169.254.169.254/latest/meta-data/", False),
    ("ftp://8.8.8.8/", False),
    ("file:///etc/passwd", False),
    ("http://8.8.8.8/", True),
])
def test_is_allowed_url(url, allowed):
    assert asyncio.run(is_allowed_url(url)) is allowed


def test_extract_content_collapses_whitespace():
    page = AsyncWebScraper.extract_content("<title> T </title><p>one\n\n   two</p><script>x()</script><a href='/b#c'>b</a>", "https://s.example/a")
    assert page.content == "T one two b"
    assert page.links == ["https://s.example/b"]


def test_private_crawl_opt_in(monkeypatch):
    monkeypatch.setattr(config, "ALLOW_PRIVATE_CRAWL", True)
    assert asyncio.run(is_allowed_url("http://127.0.0.1/"))
    assert not asyncio.run(is_allowed_url("ftp://127.0.0.1/"))
