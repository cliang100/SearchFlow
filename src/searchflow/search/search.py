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
        
        results = []
        db = SessionLocal()
        try:
            for doc_id, score in scored_docs[:limit]:
                doc = db.query(Document).filter(Document.id == doc_id).first()
                if doc:
                    results.append({
                        'id': doc.id,
                        'title': doc.title,
                        'url': doc.url,
                        'content': doc.content[:200] + '...',
                        'score': round(score, 4)
                    })
        finally:
            db.close()
            
        return results
    
    def autocomplete(self, prefix: str) -> List[str]:
        """Get autocomplete suggestions"""
        return self.trie.search(prefix)