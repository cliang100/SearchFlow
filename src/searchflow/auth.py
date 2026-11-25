import secrets

from fastapi import Header, HTTPException

from . import config


def require_admin(x_admin_token: str = Header(default="")):
    """Guards endpoints that change data or make the server fetch URLs."""
    if not config.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin endpoints are disabled on this server")
    if not secrets.compare_digest(x_admin_token.encode(), config.ADMIN_TOKEN.encode()):
        raise HTTPException(status_code=401, detail="Invalid admin token")
