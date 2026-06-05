from typing import List, Dict, Any
from .indexer import InvertedIndex
from .trie import AutocompleteTrie
from ..database.connection import SessionLocal
from ..database.models import Document

class SearchEngine:
    def __init__(self):
        self.index = InvertedIndex()
        self.trie = AutocompleteTrie()
        self._build_search_engine()
        
    def _build_search_engine(self):
        """Build index and trie from database"""
        print("Building search index...")
        self.index.build_index()
        
        words = list(self.index.index.keys())
        self.trie.build_from_index(words)
        print(f"Search engine ready! Indexed {self.index.doc_count} documents with {len(words)} unique words")
        
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search query and return formatted results"""
        scored_docs = self.index.search(query)
        if not scored_docs:
            return []
        
        top_docs = scored_docs[:limit]
        doc_ids = [doc_id for doc_id, _ in top_docs]
        score_map = {doc_id: score for doc_id, score in top_docs}
        
        db = SessionLocal()
        try:
            documents = db.query(Document).filter(Document.id.in_(doc_ids)).all()
            doc_map = {doc.id: doc for doc in documents}
            
            return [
                {
                    'id': doc.id,
                    'title': doc.title,
                    'url': doc.url,
                    'content': doc.content[:200] + '...',
                    'score': round(score_map[doc.id], 4)
                }
                for doc_id in doc_ids
                if (doc := doc_map.get(doc_id))
            ]
        finally:
            db.close()
    
    def autocomplete(self, prefix: str) -> List[str]:
        """Get autocomplete suggestions"""
        return self.trie.search(prefix)