# SearchFlow

A full-stack search engine built from scratch. Crawls web pages, builds a custom inverted index with TF-IDF ranking, and serves results through a REST API and browser UI — no Elasticsearch, no Solr.

---

## How It Works

1. **Crawl** — seed a URL via the UI or API. The async crawler follows links within the same domain, respects rate limits, and stores pages in PostgreSQL.
2. **Index** — after each crawl, the in-memory inverted index rebuilds automatically. Every term maps to the set of documents containing it.
3. **Search** — queries are tokenized, scored with TF-IDF across all candidate documents, and returned ranked by relevance.
4. **Autocomplete** — a Trie built from indexed terms provides prefix-based suggestions in real time.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | Python, FastAPI, Asyncio |
| Database | PostgreSQL (document storage) |
| Cache / Queue | Redis (crawl queue, deduplication) |
| Crawler | httpx (async HTTP), BeautifulSoup |
| Search | Custom inverted index + TF-IDF (pure Python) |
| Autocomplete | Custom Trie data structure |
| Frontend | Vanilla HTML/CSS/JS |
| Deployment | Docker, Docker Compose |

---

## Running Locally

**Prerequisites:** Docker and Docker Compose

```bash
git clone https://github.com/yourusername/SearchFlow.git
cd SearchFlow
docker compose up --build
```

The API will be available at `http://localhost:8000` and the UI at `http://localhost:8000/ui`.

### Without Docker

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Requires a running PostgreSQL and Redis instance
# Set connection strings in .env (see .env.example)

uvicorn src.searchflow.main:app --reload
```

---

## API Endpoints

### Search
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/search/?q={query}&limit={n}` | Search indexed documents |
| `GET` | `/search/autocomplete?q={prefix}` | Prefix-based autocomplete suggestions |
| `POST` | `/search/rebuild-index` | Rebuild the in-memory index from the database |

### Crawler
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/crawler/start` | Start an async crawl from a seed URL |
| `GET` | `/crawler/status/{url}` | Get crawl progress for a URL |

### Documents
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/documents/` | List indexed documents (paginated) |
| `GET` | `/documents/{id}` | Get a single document |
| `DELETE` | `/documents/{id}` | Remove a document from the index |

Full interactive docs available at `http://localhost:8000/docs`.

---

## Example Usage

**Start a crawl:**
```bash
curl -X POST http://localhost:8000/crawler/start \
  -H "Content-Type: application/json" \
  -d '{"start_url": "https://gobyexample.com", "max_pages": 50}'
```

**Search:**
```bash
curl "http://localhost:8000/search/?q=goroutines&limit=10"
```

**Autocomplete:**
```bash
curl "http://localhost:8000/search/autocomplete?q=go"
```

---

## Technical Notes

**TF-IDF scoring** — Term Frequency × Inverse Document Frequency. Terms rare across the corpus score higher. A word appearing in every document (e.g. "python" across an all-python.org corpus) scores zero — this is correct behavior, not a bug.

**Inverted index** — maps each term to the set of document IDs containing it. Search unions candidates across query terms and scores each with TF-IDF. Built in-memory from PostgreSQL on startup and after each crawl.

**Trie autocomplete** — prefix tree built from all indexed terms. O(k) lookup where k is the prefix length, regardless of corpus size.

**Async crawler** — uses httpx with asyncio. Redis tracks the crawl queue and completed URLs to prevent duplicates. Domain-scoped by default to avoid uncontrolled link following.

---

## Project Structure

```
src/searchflow/
├── api/
│   ├── crawler.py      # Crawl endpoints
│   ├── documents.py    # Document CRUD endpoints
│   └── search.py       # Search and autocomplete endpoints
├── crawler/
│   ├── manager.py      # Orchestrates crawl jobs
│   ├── scraper.py      # Async HTTP fetching and content extraction
│   └── queue.py        # Redis-backed crawl queue
├── search/
│   ├── indexer.py      # Inverted index + TF-IDF implementation
│   ├── search.py       # Search engine (wraps index + trie)
│   └── trie.py         # Trie for autocomplete
├── database/
│   ├── models.py       # SQLAlchemy models
│   └── connection.py   # Database session management
└── main.py             # FastAPI app entrypoint
```