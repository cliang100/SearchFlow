import asyncio
from typing import Awaitable, Callable, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .models import ExtractedContent, FetchResult
from .safety import is_allowed_url, normalize

MAX_REDIRECTS = 5
MAX_BYTES = 2 * 1024 * 1024
USER_AGENT = "SearchFlowBot/1.0"


class AsyncWebScraper:
    def __init__(self, delay: float = 1.0, is_allowed: Callable[[str], Awaitable[bool]] = is_allowed_url):
        self.delay = delay
        self.is_allowed = is_allowed
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        # redirects are followed by hand so every hop is checked
        self.client = httpx.AsyncClient(timeout=10.0, follow_redirects=False, headers={"User-Agent": USER_AGENT})
        return self

    async def __aexit__(self, *exc):
        await self.client.aclose()

    async def fetch(self, url: str, html_only: bool = True) -> FetchResult:
        await asyncio.sleep(self.delay)
        try:
            for _ in range(MAX_REDIRECTS + 1):
                if not await self.is_allowed(url):
                    return FetchResult.failed(url, "URL not allowed")
                async with self.client.stream("GET", url) as response:
                    if response.is_redirect:
                        url = normalize(urljoin(url, response.headers.get("location", "")))
                        continue
                    response.raise_for_status()
                    if html_only and "text/html" not in response.headers.get("content-type", ""):
                        return FetchResult.failed(url, "not an HTML page")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body += chunk
                        if len(body) > MAX_BYTES:
                            return FetchResult.failed(url, "page too large")
                    text = body.decode(response.encoding or "utf-8", errors="replace")
                    return FetchResult(url=url, html=text, status_code=response.status_code, final_url=url, success=True)
            return FetchResult.failed(url, "too many redirects")
        except httpx.HTTPError as e:
            return FetchResult.failed(url, str(e) or type(e).__name__)

    @staticmethod
    def extract_content(html: str, url: str) -> ExtractedContent:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        if not text:
            return ExtractedContent(url=url, title=title, content="", links=[], word_count=0, success=False, error="no text")
        links = [normalize(urljoin(url, a["href"])) for a in soup.find_all("a", href=True)]
        return ExtractedContent(url=url, title=title, content=text, links=links, word_count=len(text.split()), success=True)
