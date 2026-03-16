import asyncio
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from .models import FetchResult, ExtractedContent
from .scraper import AsyncWebScraper
from .queue import CrawlQueue
from ..database.connection import SessionLocal
from ..database.models import Document
import hashlib

class CrawlerManager:
    def __init__(self, max_depth: int = 3, max_pages: int = 1000):
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.queue = CrawlQueue()
        self.scraper = AsyncWebScraper(delay=1.0)
        
    async def start_crawl(self, start_url: str):
        """Start crawling from a seed URL"""
        # Add seed URL to queue
        self.queue.add_url(start_url, depth=1)
        
        crawled_count = 0
        
        while crawled_count < self.max_pages:
            # Get next job from queue
            job = self.queue.get_next_job()
            if not job:
                print("No more jobs in queue")
                break
            
            # Process the job
            success = await self._process_job(job)
            if success:
                crawled_count += 1
                print(f"Crawled {crawled_count}/{self.max_pages}: {job['url']}")
            else:
                self.queue.mark_failed(job['url'])
        
        print(f"Crawling complete! Processed {crawled_count} pages")
    
    async def _process_job(self, job: dict) -> bool:
        """Process a single crawl job"""
        url = job['url']
        depth = job['depth']
        
        try:
            async with self.scraper:
                fetch_result = await self.scraper.fetch_page(url)
                if not fetch_result.success:
                    print(f"Failed to fetch {url}: {fetch_result.error}")
                    return False
            
            extracted = self.scraper.extract_content(fetch_result.html, fetch_result.final_url)
            if not extracted.success:
                print(f"Failed to extract content from {fetch_result.final_url}: {extracted.error}")
                return False
            
            await self._save_document(fetch_result.final_url, extracted, depth)
            
            if depth < self.max_depth:
                await self._add_links_to_queue(extracted.links, depth + 1, fetch_result.final_url)
            
            return True
        except Exception as e:
            print(f"Error processing job {url}: {e}")
            return False
    
    async def _save_document(self, url: str, extracted: ExtractedContent, depth: int):
        """Save extracted content to database"""
        db = SessionLocal()
        try:
            content_hash = hashlib.sha256(extracted.content.encode()).hexdigest()
            existing = db.query(Document).filter(Document.content_hash == content_hash).first()
            
            if existing:
                return
            
            document = Document(
                url=url,
                title=extracted.title,
                content=extracted.content,
                content_hash=content_hash,
                crawl_depth=depth,
                word_count=extracted.word_count
            )
            db.add(document)
            db.commit()
        except Exception as e:
            print(f"Error saving document {url}: {e}")
            db.rollback()
        finally:
            db.close()
    async def _add_links_to_queue(self, links: List[str], depth: int, parent_url: str):
        """Add new links to crawl queue"""
        for link in links:
            # Only add same domain links
            if urlparse(link).netloc == urlparse(parent_url).netloc:
                self.queue.add_url(link, depth=depth, parent_url=parent_url)