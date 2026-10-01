"""Knowledge Loader - query API for the 62-book knowledge base.

Provides:
    get_rules(book_id, direction, timeframe=None)
    get_rules_for_setup(setup_type)
    query_by_concept(concept)
    get_confluence_weights(concepts)

Usage:
    kb = KnowledgeLoader()
    rules = kb.get_rules("book_62", "long")
    weights = kb.get_confluence_weights(["volume_cluster", "delta_positive"])
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


class KnowledgeLoader:
    def __init__(self, knowledge_dir: str = None):
        if knowledge_dir is None:
            knowledge_dir = Path(__file__).resolve().parent
        self.knowledge_dir = Path(knowledge_dir)
        self.books: Dict[str, dict] = {}
        self.index: dict = {}
        self._load_all()

    def _load_all(self) -> None:
        index_path = self.knowledge_dir / "books_index.json"
        if not index_path.exists():
            logger.error(f"books_index.json not found at {index_path}")
            return

        self.index = _load_json(index_path)
        loaded = 0
        for entry in self.index.get("books", []):
            fname = entry.get("file")
            if not fname:
                continue
            fpath = self.knowledge_dir / fname
            if not fpath.exists():
                logger.warning(f"Missing book file: {fpath}")
                continue
            try:
                self.books[entry["id"]] = _load_json(fpath)
                loaded += 1
            except json.JSONDecodeError as e:
                logger.error(f"Bad JSON in {fpath}: {e}")
        logger.success(f"KnowledgeLoader: {loaded} books loaded")

    def list_books(self) -> List[dict]:
        return [
            {"id": k, "title": v.get("title"), "category": v.get("category")}
            for k, v in self.books.items()
        ]

    def get_rules(self, book_id: str, direction: str, timeframe: Optional[str] = None) -> List[dict]:
        if book_id not in self.books:
            return []
        book = self.books[book_id]
        key = f"{direction}_entries"
        return book.get("rules", {}).get(key, [])

    def get_rules_for_setup(self, setup_type: str) -> List[dict]:
        setup_lower = setup_type.lower()
        matches = []
        for book_id, book in self.books.items():
            for direction in ("long_entries", "short_entries"):
                for rule in book.get("rules", {}).get(direction, []):
                    text = rule.get("rule", "").lower()
                    if setup_lower in text:
                        matches.append({
                            "book_id": book_id,
                            "direction": direction.replace("_entries", ""),
                            "rule": rule["rule"],
                            "weight": rule.get("weight", 0.5),
                            "confluence": rule.get("confluence", []),
                        })
            patterns = book.get("confirmation_patterns", {})
            if isinstance(patterns, dict):
                for pname, pdata in patterns.items():
                    if setup_lower in pname.lower():
                        matches.append({
                            "book_id": book_id,
                            "direction": "pattern",
                            "rule": f"Pattern: {pname}",
                            "weight": pdata.get("weight", 0.5) if isinstance(pdata, dict) else 0.5,
                        })
        return matches

    def query_by_concept(self, concept: str) -> List[dict]:
        concept_lower = concept.lower()
        results = []
        for book_id, book in self.books.items():
            for core in book.get("core_concepts", []):
                if concept_lower in core.lower():
                    results.append({
                        "book_id": book_id,
                        "title": book.get("title"),
                        "concept": core,
                        "category": book.get("category"),
                    })
        return results

    def get_confluence_weights(self, concepts: List[str]) -> Dict[str, float]:
        weights: Dict[str, float] = {}
        for book in self.books.values():
            for direction in ("long_entries", "short_entries"):
                for rule in book.get("rules", {}).get(direction, []):
                    rule_confluence = rule.get("confluence", [])
                    for tag in concepts:
                        if tag in rule_confluence:
                            weights[tag] = weights.get(tag, 0.0) + rule.get("weight", 0.5)
        for tag in weights:
            weights[tag] = round(min(weights[tag], 1.0), 3)
        for c in concepts:
            if c not in weights:
                weights[c] = 0.0
        return weights

    def get_synergies(self, book_id: str) -> dict:
        return self.books.get(book_id, {}).get("synergies", {})

    def get_all_rules(self, direction: str) -> List[dict]:
        all_rules = []
        for book_id, book in self.books.items():
            for rule in book.get("rules", {}).get(f"{direction}_entries", []):
                all_rules.append({
                    "book_id": book_id,
                    "rule": rule["rule"],
                    "weight": rule.get("weight", 0.5),
                    "confluence": rule.get("confluence", []),
                })
        return all_rules

    def stats(self) -> dict:
        total_rules = 0
        for book in self.books.values():
            for direction in ("long_entries", "short_entries"):
                total_rules += len(book.get("rules", {}).get(direction, []))
        return {
            "books_loaded": len(self.books),
            "total_entry_rules": total_rules,
            "categories": list({b.get("category") for b in self.books.values()}),
        }


_loader_instance: Optional[KnowledgeLoader] = None


def get_knowledge_loader() -> KnowledgeLoader:
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = KnowledgeLoader()
    return _loader_instance
