from typing import List, Optional

class AutocompleteTrie:
    def __init__(self):
        self.root = {}
        self.suggestions = {}   # Cache
        
    def insert(self, word: str):
        """Insert a word into the trie"""
        node = self.root
        for char in word:
            if char not in node:
                node[char] = {}
            node = node[char]
        node['#'] = True
        
    def search(self, prefix: str) -> List[str]:
        """Find all words starting with prefix"""
        if prefix in self.suggestions:
            return self.suggestions[prefix]
        
        node = self.root
        for char in prefix:
            if char not in node:
                return []
            node = node[char]
            
        words = []
        self._collect_words(node, prefix, words)
        
        # 10 word suggestion limit
        self.suggestions[prefix] = words[:10]
        return words[:10]

    def _collect_words(self, node: dict, prefix: str, words: List[str]):
        """Recursively collect all words from node"""
        if '#' in node:
            words.append(prefix)
        
        for char in node:
            if char != '#':
                self._collect_words(node[char], prefix + char, words)
        
    def build_from_index(self, index_words: List[str]):
        """Build trie from inverted index words"""
        for word in index_words:
            self.insert(word)
        