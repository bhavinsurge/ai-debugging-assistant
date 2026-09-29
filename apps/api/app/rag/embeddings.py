"""
Deterministic local embeddings for RAG without paid APIs.

Produces unit-normalized float32 vectors of fixed dimension suitable for pgvector.
When Ollama is available you can swap to an embedding model; this hasher remains
the default for CI and MockLLM mode.
"""

from __future__ import annotations

import hashlib
import math
import re

import numpy as np

from app.core.config import get_settings

_TOKEN_RE = re.compile(r"[a-z0-9_./:-]+", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "") if len(t) > 1]


def embed_text(text: str, dim: int | None = None) -> list[float]:
    settings = get_settings()
    dimension = dim or settings.embedding_dim
    vec = np.zeros(dimension, dtype=np.float64)
    tokens = tokenize(text)
    if not tokens:
        vec[0] = 1.0
        return vec.astype(np.float32).tolist()

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        # Use multiple hash slices for denser coverage
        for offset in range(0, 24, 4):
            idx = int.from_bytes(digest[offset : offset + 4], "big") % dimension
            sign = 1.0 if digest[offset + 4] % 2 == 0 else -1.0
            weight = 1.0 + (digest[offset + 5] / 255.0)
            vec[idx] += sign * weight

    # Character n-grams for short error codes
    compact = "".join(tokens)[:200]
    for i in range(max(0, len(compact) - 2)):
        gram = compact[i : i + 3]
        digest = hashlib.md5(gram.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dimension
        vec[idx] += 0.35

    norm = math.sqrt(float(np.dot(vec, vec)))
    if norm < 1e-12:
        vec[0] = 1.0
    else:
        vec /= norm
    return vec.astype(np.float32).tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.asarray(a, dtype=np.float64)
    vb = np.asarray(b, dtype=np.float64)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom < 1e-12:
        return 0.0
    return float(np.dot(va, vb) / denom)


def to_pgvector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
