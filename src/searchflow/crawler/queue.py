import redis
import json
import time
from typing import List, Optional
from urllib.parse import urlparse

class CrawlQueue:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url)
        self.queue_name = "crawl_queue"
        self.processing_name = "processing_queue"
        self.completed_name = "completed_urls"
        
    def add_url(self, url: str, depth: int = 1, parent_url: str = None) -> bool:
        """Add URL to crawl queue"""
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # Check if already processed
        if self.redis_client.sismember(self.completed_name, url):
            return False
    
        # Check if already in queue
        if self.redis_client.lpos(self.queue_name, url) is not None:
            return False
        
        # Add to queue
        job_data = {
            'url': url,
            'depth': depth,
            'parent_url': parent_url,
            'added_at': str(time.time())
        }
        
        self.redis_client.rpush(self.queue_name, json.dumps(job_data))
        return True

    def get_next_job(self) -> Optional[dict]:
        """Get next URL to crawl"""
        job_json = self.redis_client.lpop(self.queue_name)
        if job_json:
            job_data = json.loads(job_json)
            # Add to processing queue
            self.redis_client.rpush(self.processing_name, job_json)
            return job_data
        return None
    
    def mark_completed(self, url: str):
        """Mark URL as completed"""
        # Remove from processing
        self.redis_client.lrem(self.processing_name, 0, json.dumps({'url': url}))
        # Add to completed set
        self.redis_client.sadd(self.completed_name, url)
    
    def mark_failed(self, url: str):
        """Mark URL as failed (remove from processing)"""
        self.redis_client.lrem(self.processing_name, 0, json.dumps({'url': url}))
        
    def get_queue_size(self) -> int:
        """Get number of URLs in queue"""
        return self.redis_client.llen(self.queue_name)
    
    def get_processing_count(self) -> int:
        """Get number of URLs currently processing"""
        return self.redis_client.llen(self.processing_name)

    def get_completed_count(self) -> int:
        """Get number of completed URLs"""
        return self.redis_client.scard(self.completed_name)
    
    def clear(self):
        self.redis_client.delete(self.queue_name)
        self.redis_client.delete(self.processing_name)
        self.redis_client.delete(self.completed_name)