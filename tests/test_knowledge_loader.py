"""Tests for knowledge.knowledge_loader."""
from knowledge.knowledge_loader import KnowledgeLoader, get_knowledge_loader


def test_knowledge_loader_loads_books():
    kb = KnowledgeLoader()
    assert len(kb.books) >= 8  # we ported 9 book JSONs


def test_list_books_returns_list():
    kb = KnowledgeLoader()
    books = kb.list_books()
    assert isinstance(books, list)
    assert any(b["id"] == "book_62" for b in books)


def test_get_rules_returns_rules():
    kb = KnowledgeLoader()
    rules = kb.get_rules("book_62", "long")
    assert len(rules) > 0
    assert all("rule" in r for r in rules)


def test_get_rules_missing_book_returns_empty():
    kb = KnowledgeLoader()
    rules = kb.get_rules("nonexistent_book", "long")
    assert rules == []


def test_get_rules_for_setup():
    kb = KnowledgeLoader()
    matches = kb.get_rules_for_setup("absorption")
    assert isinstance(matches, list)


def test_query_by_concept():
    kb = KnowledgeLoader()
    results = kb.query_by_concept("FVG")
    assert isinstance(results, list)


def test_get_confluence_weights():
    kb = KnowledgeLoader()
    weights = kb.get_confluence_weights(["volume_cluster", "delta_positive"])
    assert isinstance(weights, dict)
    assert "volume_cluster" in weights
    assert "delta_positive" in weights


def test_get_knowledge_loader_singleton():
    kb1 = get_knowledge_loader()
    kb2 = get_knowledge_loader()
    assert kb1 is kb2
