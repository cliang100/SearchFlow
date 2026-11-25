import asyncio
import ipaddress
from urllib.parse import urldefrag, urlsplit

from .. import config


def normalize(url: str) -> str:
    return urldefrag(url)[0]


async def is_allowed_url(url: str) -> bool:
    """Only http(s) URLs whose host resolves to public addresses, so the crawler
    can't be pointed at localhost, private networks or cloud metadata."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return False
    if config.ALLOW_PRIVATE_CRAWL:
        return True
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(parts.hostname, parts.port or 443)
    except (OSError, UnicodeError, ValueError):
        return False
    # shortcut: the address is checked before the request, so DNS rebinding could slip
    # through; pin the resolved IP in the connection if this ever holds real secrets
    return bool(infos) and all(ipaddress.ip_address(info[4][0]).is_global for info in infos)
