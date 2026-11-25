from src.searchflow.search.indexer import InvertedIndex, tokenize
from src.searchflow.search.trie import AutocompleteTrie


def build(*texts):
    index = InvertedIndex()
    index.build(enumerate(texts, start=1))
    return index


def test_tokenize():
    assert tokenize("Go's goroutines, 2 channels!") == ["go", "s", "goroutines", "channels"]
    assert tokenize(None) == []


def test_ranks_by_tf_idf():
    index = build(
        "goroutines goroutines channels",
        "goroutines and maps",
        "maps maps maps",
    )
    ranked = [doc_id for doc_id, _ in index.search("goroutines")]
    assert ranked == [1, 2]


def test_rare_terms_outweigh_common_ones():
    index = build("python snake", "python language", "python tutorial")
    # "python" is in every document, so only "snake" separates them
    assert index.search("python snake")[0][0] == 1
    assert all(score == 0 for _, score in index.search("python"))


def test_any_word_matches():
    index = build("alpha", "beta", "gamma")
    assert {doc_id for doc_id, _ in index.search("alpha beta")} == {1, 2}


def test_no_match():
    index = build("alpha")
    assert index.search("zzz") == []
    assert index.search("!!!") == []


def test_trie_ranks_by_weight():
    trie = AutocompleteTrie()
    trie.build({"go": 1, "goroutine": 5, "golang": 5, "gopher": 2, "rust": 9})
    assert trie.search("go") == ["golang", "goroutine", "gopher", "go"]
    assert trie.search("go", limit=2) == ["golang", "goroutine"]
    assert trie.search("x") == []


def test_trie_handles_long_words():
    trie = AutocompleteTrie()
    trie.build({"a" * 5000: 1})
    assert trie.search("aaa") == ["a" * 5000]
