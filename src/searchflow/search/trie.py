from typing import Dict, List

MAX_SUGGESTIONS = 50


class AutocompleteTrie:
    def __init__(self):
        self.root = {}
        self.cache: Dict[str, List[str]] = {}

    def build(self, word_weights: Dict[str, int]):
        """Insert words with a weight; suggestions come back heaviest first."""
        self.cache.clear()
        for word, weight in word_weights.items():
            node = self.root
            for char in word:
                node = node.setdefault(char, {})
            node["#"] = weight

    def search(self, prefix: str, limit: int = 10) -> List[str]:
        if prefix not in self.cache:
            node = self.root
            for char in prefix:
                if char not in node:
                    return []
                node = node[char]
            found = []
            self._collect(node, prefix, found)
            found.sort(key=lambda item: (-item[1], item[0]))
            self.cache[prefix] = [word for word, _ in found[:MAX_SUGGESTIONS]]
        return self.cache[prefix][:limit]

    def _collect(self, node: dict, prefix: str, found: list):
        # iterative, so very long words can't hit the recursion limit
        stack = [(node, prefix)]
        while stack:
            node, prefix = stack.pop()
            for char, child in node.items():
                if char == "#":
                    found.append((prefix, child))
                else:
                    stack.append((child, prefix + char))
