"""
Pure-Python TF-IDF Cosine Similarity Search Engine.
No external dependencies — uses only stdlib math and collections.
Also provides fuzzy string matching via difflib for admin keyword searches.
"""

import math
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# ─── Tokenizer ───────────────────────────────────────────────────────────────

STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "as",
    "is",
    "was",
    "are",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "must",
    "shall",
    "can",
    "i",
    "my",
    "me",
    "we",
    "our",
    "you",
    "your",
    "he",
    "she",
    "it",
    "they",
    "his",
    "her",
    "its",
    "their",
    "this",
    "that",
    "these",
    "those",
    "not",
    "no",
    "so",
    "if",
    "then",
    "than",
    "when",
    "what",
    "who",
    "which",
    "how",
    "all",
    "any",
    "each",
    "every",
    "both",
    "few",
    "more",
    "most",
    "other",
    "into",
    "about",
    "up",
    "out",
    "over",
    "after",
    "before",
    "just",
    "now",
    "also",
    "only",
    "very",
    "well",
    "even",
    "still",
    "again",
    "never",
}


def _tokenize(text: str) -> List[str]:
    """Lowercase, strip punctuation, remove stopwords, return token list."""
    text = text.lower()
    tokens = re.findall(r"[a-z']+", text)
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]


# ─── TF-IDF Engine ───────────────────────────────────────────────────────────


class TFIDFIndex:
    """
    In-memory TF-IDF index for fast cosine similarity search.

    Each document is stored as a {token: tf_idf_weight} vector.
    At query time we compute cosine similarity against all docs.
    """

    def __init__(self):
        # doc_id -> {"tokens": Counter, "tf_idf": dict, "meta": dict}
        self._docs: Dict[str, Dict[str, Any]] = {}
        # token -> set of doc_ids containing it (for IDF calculation)
        self._df: Dict[str, int] = {}
        self._dirty = True  # re-compute IDF on next search

    def add_document(
        self, doc_id: str, text: str, meta: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add or replace a document in the index."""
        tokens = _tokenize(text)
        if not tokens:
            return

        tf = Counter(tokens)
        total = len(tokens)
        # Raw TF (normalised by doc length)
        tf_norm = {t: count / total for t, count in tf.items()}

        self._docs[doc_id] = {
            "tokens": tf_norm,
            "tf_idf": {},  # filled lazily
            "meta": meta or {},
            "raw_text": text,
        }

        # Update document frequency
        for t in set(tokens):
            self._df[t] = self._df.get(t, 0) + 1

        self._dirty = True

    def _compute_tf_idf(self) -> None:
        """Recompute TF-IDF weights for all docs (called before search)."""
        N = len(self._docs)
        if N == 0:
            return

        for doc_id, doc in self._docs.items():
            tf_idf = {}
            for token, tf in doc["tokens"].items():
                df = self._df.get(token, 1)
                idf = math.log((N + 1) / (df + 1)) + 1.0  # smoothed IDF
                tf_idf[token] = tf * idf
            doc["tf_idf"] = tf_idf

        self._dirty = False

    def _cosine_similarity(
        self, vec_a: Dict[str, float], vec_b: Dict[str, float]
    ) -> float:
        """Compute cosine similarity between two sparse TF-IDF vectors."""
        if not vec_a or not vec_b:
            return 0.0

        dot = sum(vec_a.get(t, 0.0) * w for t, w in vec_b.items())
        norm_a = math.sqrt(sum(v**2 for v in vec_a.values()))
        norm_b = math.sqrt(sum(v**2 for v in vec_b.values()))

        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(
        self,
        query: str,
        top_k: int = 20,
        filter_meta: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search the index using cosine similarity.

        Args:
            query: Natural language query string
            top_k: Number of results to return
            filter_meta: Optional dict of meta key->value filters

        Returns:
            List of result dicts with keys: doc_id, score, meta, snippet
        """
        if self._dirty:
            self._compute_tf_idf()

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        # Build query TF-IDF vector
        q_tf = Counter(query_tokens)
        total_q = len(query_tokens)
        q_vec: Dict[str, float] = {}
        for t, count in q_tf.items():
            tf = count / total_q
            df = self._df.get(t, 1)
            idf = math.log((len(self._docs) + 1) / (df + 1)) + 1.0
            q_vec[t] = tf * idf

        scores: List[Tuple[str, float]] = []
        for doc_id, doc in self._docs.items():
            # Apply meta filters
            if filter_meta:
                if not all(doc["meta"].get(k) == v for k, v in filter_meta.items()):
                    continue
            score = self._cosine_similarity(q_vec, doc["tf_idf"])
            if score > 0:
                scores.append((doc_id, score))

        scores.sort(key=lambda x: -x[1])

        results = []
        for doc_id, score in scores[:top_k]:
            doc = self._docs[doc_id]
            snippet = _extract_snippet(doc["raw_text"], query_tokens)
            results.append(
                {
                    "doc_id": doc_id,
                    "score": round(score, 4),
                    "meta": doc["meta"],
                    "snippet": snippet,
                }
            )
        return results

    def clear(self) -> None:
        self._docs.clear()
        self._df.clear()
        self._dirty = True

    def size(self) -> int:
        return len(self._docs)


# ─── Snippet Extractor ────────────────────────────────────────────────────────


def _extract_snippet(text: str, query_tokens: List[str], window: int = 40) -> str:
    """
    Extract a ~80-character snippet from text centred around the best query match.
    Returns the snippet with matched tokens wrapped in **bold** markers.
    """
    lower = text.lower()
    best_pos = -1
    for token in query_tokens:
        idx = lower.find(token)
        if idx != -1:
            best_pos = idx
            break

    if best_pos == -1:
        snippet_raw = text[:160]
    else:
        start = max(0, best_pos - window)
        end = min(
            len(text),
            best_pos + window + len(query_tokens[0])
            if query_tokens
            else best_pos + window,
        )
        snippet_raw = (
            ("..." if start > 0 else "")
            + text[start:end]
            + ("..." if end < len(text) else "")
        )

    # Bold matched tokens
    for token in query_tokens:
        pattern = re.compile(re.escape(token), re.IGNORECASE)
        snippet_raw = pattern.sub(lambda m: f"**{m.group(0)}**", snippet_raw)

    return snippet_raw


# ─── Fuzzy Search ────────────────────────────────────────────────────────────


def fuzzy_search(
    query: str,
    documents: List[Dict[str, Any]],
    text_field: str = "text_content",
    threshold: float = 0.3,
    top_k: int = 20,
) -> List[Dict[str, Any]]:
    """
    Fuzzy string matching using SequenceMatcher.

    Args:
        query: Search string
        documents: List of dicts containing `text_field`
        text_field: Key in each dict to search against
        threshold: Minimum similarity ratio to include in results (0-1)
        top_k: Max results to return

    Returns:
        Documents sorted by fuzzy match score, descending
    """
    query_lower = query.lower()
    scored = []

    for doc in documents:
        text = doc.get(text_field, "")
        if not text:
            continue

        text_lower = text.lower()

        # Check for direct substring (fastest path)
        if query_lower in text_lower:
            ratio = 1.0
        else:
            ratio = SequenceMatcher(None, query_lower, text_lower[:500]).ratio()

        if ratio >= threshold:
            scored.append({**doc, "_fuzzy_score": round(ratio, 4)})

    scored.sort(key=lambda x: -x["_fuzzy_score"])
    return scored[:top_k]


# ─── Global singleton index ───────────────────────────────────────────────────

_global_index: Optional[TFIDFIndex] = None


def get_search_index() -> TFIDFIndex:
    """Get (or lazily create) the global TF-IDF index."""
    global _global_index
    if _global_index is None:
        _global_index = TFIDFIndex()
    return _global_index


def index_response(
    run_id: str,
    response_id: int,
    agent_id: str,
    agent_name: str,
    agent_role: str,
    agent_region: str,
    cycle: int,
    text_content: str,
) -> None:
    """Add an agent response to the in-memory search index."""
    idx = get_search_index()
    doc_id = f"{run_id}:{response_id}"
    idx.add_document(
        doc_id=doc_id,
        text=text_content,
        meta={
            "run_id": run_id,
            "response_id": response_id,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "agent_role": agent_role,
            "agent_region": agent_region,
            "cycle": cycle,
        },
    )


def semantic_search(
    query: str,
    run_id: Optional[str] = None,
    top_k: int = 20,
) -> List[Dict[str, Any]]:
    """
    Run cosine similarity search against the in-memory index.
    Optionally filter by run_id.
    """
    idx = get_search_index()
    filter_meta = {"run_id": run_id} if run_id else None
    return idx.search(query, top_k=top_k, filter_meta=filter_meta)


def reload_index_from_db() -> int:
    """
    Rebuild the in-memory TF-IDF index from persisted search_index table.
    Called on startup to restore the index after a server restart.
    Returns number of entries loaded.
    """
    from app.simulation.db import get_search_entries

    idx = get_search_index()
    idx.clear()

    entries = get_search_entries()
    for e in entries:
        idx.add_document(
            doc_id=f"{e['run_id']}:{e['response_id']}",
            text=e["text_content"],
            meta={
                "run_id": e["run_id"],
                "response_id": e["response_id"],
                "agent_id": e["agent_id"],
            },
        )

    logger.info(f"Search index reloaded from DB: {idx.size()} documents")
    return idx.size()
