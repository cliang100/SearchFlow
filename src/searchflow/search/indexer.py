import math
import re
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple
from ..database.connection import SessionLocal
from ..database.models import Document

class InvertedIndex:
    def __init__(self):
        self.index = defaultdict(set)
        self.doc_count = 0
        self.doc_lengths = {}
        self.term_frequencies = {}
        
    def build_index(self):
        """Build inverted index from database documents"""
        db = SessionLocal()
        try:
            documents = db.query(Document).all()
            self.doc_count = len(documents)
            
            for doc in documents:
                doc_id = doc.id
                words = self._tokenize(doc.content)
                word_counts = Counter(words)
                self.term_frequencies[doc_id] = dict(word_counts)
                
                for word in word_counts:
                    self.index[word].add(doc_id)
                
                self.doc_lengths[doc_id] = len(words)
        
        finally:
            db.close()
            
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words"""
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        return words

    def search(self, query: str) -> List[Tuple[int, float]]:
        """Search query and return ranked documents"""
        query_words = self._tokenize(query)
        if not query_words:
            return []
        
        result_docs = None
        for word in query_words:
            if word in self.index:
                docs_with_word = self.index[word]
                if result_docs is None:
                    result_docs = docs_with_word
                else:
                    result_docs &= docs_with_word
            else:
                return []
        
        if not result_docs:
            return []
        
        scores = []
        for doc_id in result_docs:
            score = self._calculate_tf_idf(query_words, doc_id)
            scores.append((doc_id, score))
            
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores
    
    def _calculate_tf_idf(self, query_words: List[str], doc_id: int) -> float:
        """Calculate TF-IDF score for document"""
        score = 0.0
        doc_length = self.doc_lengths[doc_id]
        
        for word in query_words:
            # Term Frequency (TF)
            tf_count = self.term_frequencies.get(doc_id, {}).get(word, 0)
            tf = tf_count / doc_length
            
            # Inverse Document (IDF)
            df = len(self.index[word])
            idf = math.log(self.doc_count / df)

            score += tf * idf
        
        return score