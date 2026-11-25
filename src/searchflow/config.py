import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://searchflow:password@localhost:5433/searchflow")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

# Empty disables crawling and document changes, which is the safe default for a public demo.
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# Only for local development: lets the crawler fetch localhost and private networks.
ALLOW_PRIVATE_CRAWL = os.getenv("ALLOW_PRIVATE_CRAWL", "false").lower() == "true"
CRAWL_DELAY = float(os.getenv("CRAWL_DELAY", "1.0"))
MAX_CRAWL_PAGES = 200
MAX_CRAWL_DEPTH = 3
