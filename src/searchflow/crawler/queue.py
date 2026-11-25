import hashlib
import json
from typing import Optional

from redis.asyncio import Redis

KEY_TTL_SECONDS = 24 * 60 * 60


class CrawlQueue:
    """Redis-backed frontier for one crawl. A URL is queued at most once."""

    def __init__(self, redis: Redis, start_url: str):
        prefix = "crawl:" + hashlib.sha1(start_url.encode()).hexdigest()[:16]
        self.redis = redis
        self.queue_key = prefix + ":queue"
        self.seen_key = prefix + ":seen"
        self.done_key = prefix + ":done"

    async def add_url(self, url: str, depth: int) -> bool:
        # SADD is atomic, so two workers can't queue the same URL
        if not await self.redis.sadd(self.seen_key, url):
            return False
        await self.redis.rpush(self.queue_key, json.dumps({"url": url, "depth": depth}))
        for key in (self.queue_key, self.seen_key):
            await self.redis.expire(key, KEY_TTL_SECONDS)
        return True

    async def mark_seen(self, url: str):
        await self.redis.sadd(self.seen_key, url)

    async def next_job(self) -> Optional[dict]:
        raw = await self.redis.lpop(self.queue_key)
        return json.loads(raw) if raw else None

    async def mark_done(self):
        await self.redis.incr(self.done_key)
        await self.redis.expire(self.done_key, KEY_TTL_SECONDS)

    async def status(self) -> dict:
        return {
            "queue_size": await self.redis.llen(self.queue_key),
            "seen_count": await self.redis.scard(self.seen_key),
            "completed_count": int(await self.redis.get(self.done_key) or 0),
        }

    async def clear(self):
        await self.redis.delete(self.queue_key, self.seen_key, self.done_key)
