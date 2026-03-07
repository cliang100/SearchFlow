# SearchFlow

A web-based search engine built with Python, FastAPI, and custom indexing algorithms.

## Features

- Async web crawling with Redis queue
- Custom inverted index and TF-IDF ranking
- Trie-based autocomplete system
- RESTful API with FastAPI
- PostgreSQL for document storage
- Docker deployment ready

## Tech Stack

- **Backend**: Python + FastAPI + Asyncio
- **Database**: PostgreSQL
- **Cache**: Redis
- **Testing**: pytest
- **Deployment**: Docker

## Quick Start

1. Clone and setup:
```bash
git clone <your-repo-url>
cd SearchFlow
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt