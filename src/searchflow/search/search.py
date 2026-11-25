import logging
import threading
from typing import Any, Dict, List

from ..database.connection import SessionLocal
from ..database.models import Document
from .indexer import InvertedIndex
from .trie import AutocompleteTrie

log = logging.getLogger(__name__)

SNIPPET_LENGTH = 200


class SearchEngine:
    def __init__(self, documents):
        self.index = InvertedIndex()
        self.index.build(documents)
        self.trie = AutocompleteTrie()
        self.trie.build({word: len(ids) for word, ids in self.index.index.items()})

    @classmethod
    def from_db(cls) -> "SearchEngine":
        with SessionLocal() as db:
            documents = db.query(Document.id, Document.content).all()
        engine = cls(documents)
        log.info("Indexed %d documents, %d unique words", engine.index.doc_count, len(engine.index.index))
        return engine

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        top = self.index.search(query)[:limit]
        if not top:
            return []
        with SessionLocal() as db:
            rows = db.query(Document).filter(Document.id.in_([doc_id for doc_id, _ in top])).all()
        by_id = {doc.id: doc for doc in rows}
        results = []
        for doc_id, score in top:
            doc = by_id.get(doc_id)
            if doc is None:
                continue  # deleted since the index was built
            content = doc.content or ""
            results.append({
                "id": doc.id,
                "title": doc.title or doc.url,
                "url": doc.url,
                "content": content[:SNIPPET_LENGTH] + ("..." if len(content) > SNIPPET_LENGTH else ""),
                "score": round(score, 4),
            })
        return results

    def autocomplete(self, prefix: str, limit: int = 10) -> List[str]:
        return self.trie.search(prefix.lower(), limit)


_engine = None
_lock = threading.Lock()


def get_engine() -> SearchEngine:
    global _engine
    with _lock:
        if _engine is None:
            _engine = SearchEngine.from_db()
        return _engine


def rebuild() -> SearchEngine:
    """Build a fresh index off to the side, then swap it in."""
    global _engine
    engine = SearchEngine.from_db()
    with _lock:
        _engine = engine
    return engine
