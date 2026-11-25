# SearchFlow

A search engine built from scratch. It crawls web pages, builds its own inverted index with TF-IDF ranking, and serves results through a REST API and a browser UI. No Elasticsearch, no Solr.

## How it works

1. **Crawl:** an admin seeds a URL. The async crawler follows links on the same site up to a depth and page limit, respects `robots.txt`, and stores each page's text in PostgreSQL.
2. **Index:** after each crawl, and after any document change, an in-memory inverted index is rebuilt. Each word maps to the set of documents containing it.
3. **Search:** queries are tokenized, every document containing any query word is scored with TF-IDF, and results come back best first.
4. **Autocomplete:** a trie built from the indexed words suggests completions, most common words first.

## Tech stack

| Layer | Technology |
|---|---|
| API | Python, FastAPI, asyncio |
| Database | PostgreSQL, SQLAlchemy, Alembic migrations |
| Crawl queue | Redis |
| Crawler | httpx, BeautifulSoup |
| Search | Inverted index and TF-IDF in plain Python |
| Autocomplete | Trie |
| Frontend | Vanilla HTML, CSS and JavaScript |
| Tooling | pytest, GitHub Actions, Docker Compose |

## Running locally

**With Docker** (needs Docker and Docker Compose):

```bash
docker compose up --build
```

The UI is at http://localhost:8000/ui and the interactive API docs at http://localhost:8000/docs. Compose sets the admin token to `change-me`; set `ADMIN_TOKEN` in your shell to choose another.

To index something, click **crawl url** in the UI, enter the admin token, and give it a site, for example `https://gobyexample.com` with 50 pages.

**Without Docker** (needs PostgreSQL and Redis running):

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env            # then edit it
alembic upgrade head
uvicorn src.searchflow.main:app --reload
```

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql://searchflow:password@localhost:5433/searchflow` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379` | Redis, only used while crawling |
| `ADMIN_TOKEN` | empty | Enables crawling, document changes and index rebuilds. Empty makes the API read-only. |
| `CORS_ORIGINS` | empty | Comma-separated sites allowed to call the API from a browser |
| `CRAWL_DELAY` | `1.0` | Seconds between page fetches |
| `ALLOW_PRIVATE_CRAWL` | `false` | Lets the crawler reach localhost and private networks. Local development only. |

## API

Endpoints marked **admin** need an `X-Admin-Token` header matching `ADMIN_TOKEN`. They return 403 when no token is configured and 401 when it is wrong.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/search/?q={query}&limit={n}` | Search indexed documents |
| `GET` | `/search/autocomplete?q={prefix}&limit={n}` | Autocomplete suggestions |
| `POST` | `/search/rebuild-index` | Rebuild the index from the database (**admin**) |
| `POST` | `/crawler/start` | Start a crawl from a seed URL (**admin**) |
| `GET` | `/crawler/status/{url}` | Progress of a running crawl |
| `GET` | `/documents/` | List documents, paginated |
| `GET` | `/documents/{id}` | Get one document |
| `POST` | `/documents/` | Add a document (**admin**) |
| `PUT` | `/documents/{id}` | Edit a document (**admin**) |
| `DELETE` | `/documents/{id}` | Delete a document (**admin**) |
| `GET` | `/health` | Health check |

Start a crawl:

```bash
curl -X POST http://localhost:8000/crawler/start \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: change-me" \
  -d '{"start_url": "https://gobyexample.com", "max_pages": 50}'
```

Search:

```bash
curl "http://localhost:8000/search/?q=goroutines&limit=10"
```

## Tests

The tests need PostgreSQL and Redis. These match the defaults in `tests/conftest.py`:

```bash
docker run -d --rm -p 55432:5432 -e POSTGRES_USER=searchflow -e POSTGRES_PASSWORD=test -e POSTGRES_DB=searchflow_test postgres:15
docker run -d --rm -p 56379:6379 redis:7
python -m pytest
```

Point `TEST_DATABASE_URL` and `TEST_REDIS_URL` elsewhere if you prefer. The tests cover ranking, autocomplete, the document API, admin auth, input validation, and the crawler running against a local test site (link following, duplicate pages, `robots.txt`, depth limits, redirects, size limits, and blocked addresses). The test setup runs the Alembic migrations, so they're tested too.

CI runs the tests against real PostgreSQL and Redis, audits dependencies with `pip-audit`, checks the JavaScript, and builds the Docker image.

## Technical notes

**TF-IDF scoring:** term frequency times inverse document frequency. Words that are rare across the corpus score higher. A word in every document scores zero, so searching only for "python" across python.org pages ranks everything equally. That's how TF-IDF works, not a bug.

**Inverted index:** maps each word to the set of document IDs containing it. Search takes the union of documents for the query words and scores each one. The index is built from PostgreSQL on first use, and rebuilds happen off to the side and are swapped in under a lock, so searches never see a half-built index.

**Trie autocomplete:** a prefix tree of every indexed word, weighted by how many documents contain it. Lookups take time proportional to the prefix length, and results per prefix are cached until the next rebuild.

**Crawler safety:** the crawler only fetches http(s) URLs whose host resolves to a public address, and checks again on every redirect, so it can't be pointed at localhost, internal services or cloud metadata endpoints. It caps a crawl at 200 pages and depth 3, skips pages over 2 MB or that aren't HTML, and follows `robots.txt`. A Redis set records every URL once, so pages aren't fetched twice, and each crawl has its own keys.

**Limits:**

- The tokenizer only keeps ASCII letters, so numbers and accented words aren't searchable.
- The index lives in memory, so it suits thousands of pages, not millions.
- Crawl status is kept in the API process, so run a single worker.
- Search has no rate limit.

## Deploying

The API is a long-running Python process, so it needs a container host such as Render, Fly.io or Railway, plus a PostgreSQL database such as Neon or Supabase. Redis is only needed for crawling, and Upstash works for that. The Docker image applies migrations on start.

For a public demo:

1. Deploy with `ADMIN_TOKEN` set and crawl the sites you want to show.
2. Remove `ADMIN_TOKEN` and redeploy. The API is now read-only, and the crawler can't be used by visitors.

### Optional: UI on Netlify

Netlify can't run the API, but it can host the UI and forward API calls to it:

1. Create a Netlify site from this repo. `netlify.toml` sets the build command and publish folder.
2. Set the environment variable `BACKEND_URL` to the API's https URL.

The build script (`scripts/netlify-build.sh`) copies the UI and writes proxy rules for `/search`, `/crawler` and `/documents`, so the browser talks to one origin and CORS isn't needed.

## Project structure

```
src/searchflow/
├── api/
│   ├── crawler.py      # crawl endpoints
│   ├── documents.py    # document endpoints
│   └── search.py       # search, autocomplete and rebuild endpoints
├── crawler/
│   ├── manager.py      # runs a crawl, robots.txt, saving pages
│   ├── queue.py        # Redis-backed crawl queue
│   ├── safety.py       # URL checks that block private addresses
│   └── scraper.py      # HTTP fetching and text extraction
├── search/
│   ├── indexer.py      # inverted index and TF-IDF
│   ├── search.py       # search engine and index rebuilds
│   └── trie.py         # autocomplete trie
├── database/
│   ├── connection.py   # engine and sessions
│   └── models.py       # SQLAlchemy models
├── auth.py             # admin token check
├── config.py           # settings from the environment
└── main.py             # FastAPI app
alembic/                # database migrations
static/                 # browser UI
tests/                  # pytest suite
scripts/                # Netlify build script
```
