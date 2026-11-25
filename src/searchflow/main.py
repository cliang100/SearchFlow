import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .api.crawler import router as crawler_router
from .api.documents import router as documents_router
from .api.search import router as search_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

UI_CSP = (
    "default-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)

app = FastAPI(title="SearchFlow", description="A web search engine built from scratch", version="0.2.0")

if config.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-Admin-Token"],
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    # the API docs page loads scripts from a CDN, so the policy only covers the UI
    if request.url.path == "/ui" or request.url.path.startswith("/static/"):
        response.headers["Content-Security-Policy"] = UI_CSP
    return response


app.include_router(documents_router)
app.include_router(crawler_router)
app.include_router(search_router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/ui", include_in_schema=False)
def serve_ui():
    return FileResponse("static/index.html")


@app.get("/")
def root():
    return {"message": "SearchFlow API is running", "ui": "/ui", "docs": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": app.version}
