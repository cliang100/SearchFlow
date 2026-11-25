import math
import re
from collections import Counter, defaultdict
from typing import Iterable, List, Tuple

TOKEN = re.compile(r"[a-z]+")


def tokenize(text: str) -> List[str]:
    # shortcut: ASCII letters only, so accented words and numbers are not searchable
    return TOKEN.findall((text or "").lower())


class InvertedIndex:
    def __init__(self):
        self.index = defaultdict(set)
        self.doc_count = 0
        self.doc_lengths = {}
        self.term_frequencies = {}

    def build(self, documents: Iterable[Tuple[int, str]]):
        """Index (id, text) pairs."""
        for doc_id, text in documents:
            words = tokenize(text)
            counts = Counter(words)
            self.term_frequencies[doc_id] = counts
            self.doc_lengths[doc_id] = len(words)
            for word in counts:
                self.index[word].add(doc_id)
        self.doc_count = len(self.doc_lengths)

    def document_frequency(self, word: str) -> int:
        return len(self.index.get(word, ()))

    def search(self, query: str) -> List[Tuple[int, float]]:
        """Return (doc id, score) for documents containing any query word, best first."""
        query_words = tokenize(query)
        candidates = set()
        for word in query_words:
            candidates |= self.index.get(word, set())
        scores = [(doc_id, self._tf_idf(query_words, doc_id)) for doc_id in candidates]
        scores.sort(key=lambda item: (-item[1], item[0]))
        return scores

    def _tf_idf(self, query_words: List[str], doc_id: int) -> float:
        score = 0.0
        for word in query_words:
            df = self.document_frequency(word)
            if df == 0:
                continue
            tf = self.term_frequencies[doc_id][word] / self.doc_lengths[doc_id]
            score += tf * math.log(self.doc_count / df)
        return score
