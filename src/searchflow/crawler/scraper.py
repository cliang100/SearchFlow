import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
import time
from urllib.parse import urljoin, urlparse

from .models import FetchResult, ExtractedContent

class AsyncWebScraper:
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = None
        
    async def __aenter__(self):
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            follow_redirects=True,
            max_redirects=5,
            headers={
                'User-Agent': 'SearchFlow Bot 1.0'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
            
    async def fetch_page(self, url: str, max_redirects: int = 5) -> Optional[str]:
        try:
            await asyncio.sleep(self.delay)
            response = await self.session.get(url)
            response.raise_for_status()
            
            final_url = str(response.url)
            if response.history:
                print(f"Redirected: {url} → {final_url}")
            
            return FetchResult(
                url=url,
                html=response.text,
                status_code=response.status_code,
                final_url=final_url,
                success=True
            )
        except Exception as e:
            return FetchResult(
                url=url,
                html="",
                status_code=0,
                final_url="",
                success=False,
                error=str(e)
            )
    
    def extract_content(self, html: str, url: str) -> Dict[str, Any]:
        try:
            if not html:
                return ExtractedContent(
                    url=url,
                    title="",
                    content="",
                    links=[],
                    word_count=0,
                    success=False,
                    error="Empty HTML content"
                )
            
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.title.string.strip() if soup.title else ""
            
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text(separator=' ', strip=True)
            links = []
            for link in soup.find_all('a', href=True):
                absolute_url = urljoin(url, link['href'])
                links.append(absolute_url)
            
            return ExtractedContent(
                url=url,
                title=title,
                content=text,
                links=links,
                word_count=len(text.split()),
                success=True
            )
        except Exception as e:
            return ExtractedContent(
                url=url,
                title="",
                content="",
                links=[],
                word_count=0,
                success=False,
                error=str(e)
            )