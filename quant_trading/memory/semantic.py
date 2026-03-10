from __future__ import annotations

import math
import re
from collections import Counter
from functools import lru_cache
from typing import Iterable


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _counter_norm(counter: Counter[str]) -> float:
    return math.sqrt(sum(value * value for value in counter.values()))


def sparse_similarity(query: str, document: str) -> float:
    query_counter = Counter(tokenize(query))
    document_counter = Counter(tokenize(document))
    if not query_counter or not document_counter:
        return 0.0
    numerator = sum(query_counter[token] * document_counter[token] for token in query_counter.keys() & document_counter.keys())
    denominator = _counter_norm(query_counter) * _counter_norm(document_counter)
    if denominator == 0:
        return 0.0
    return numerator / denominator


@lru_cache(maxsize=1)
def _sentence_transformer():
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except Exception:
        return None
    try:
        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        return None


def _dense_dot(left: Iterable[float], right: Iterable[float]) -> float:
    return float(sum(a * b for a, b in zip(left, right)))


def dense_similarity(query: str, document: str) -> float | None:
    model = _sentence_transformer()
    if model is None:
        return None
    try:
        query_embedding = model.encode(query, normalize_embeddings=True)
        doc_embedding = model.encode(document, normalize_embeddings=True)
    except Exception:
        return None
    return _dense_dot(query_embedding, doc_embedding)
