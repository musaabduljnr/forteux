"""
Embedding service with provider abstraction.

Providers:
- DeterministicEmbeddingProvider: reproducible hash-based embeddings (tests only, no AI calls)
- GeminiEmbeddingProvider: Google Generative AI embedding API
- OpenAIEmbeddingProvider: OpenAI embedding API

Cosine similarity is implemented in pure Python (no numpy dependency) using
the math module for maximum compatibility.
"""

from __future__ import annotations

import hashlib
import math
import os
from typing import Protocol, runtime_checkable

from app.core.config import get_settings

_DEFAULT_DIMENSIONS = 768


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    @property
    def model_name(self) -> str:
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a list of float vectors, one per input text."""
        ...


# ---------------------------------------------------------------------------
# Deterministic provider (tests / offline)
# ---------------------------------------------------------------------------


class DeterministicEmbeddingProvider:
    """
    Generates reproducible, normalised embedding vectors from text via SHA-256 hashing.
    Uses no AI calls and no external dependencies.
    Suitable for tests and offline environments.
    """

    _model = "deterministic-v1"

    def __init__(self, dimensions: int = _DEFAULT_DIMENSIONS) -> None:
        self._dimensions = dimensions

    @property
    def model_name(self) -> str:
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        """
        Produce a stable unit-length vector for `text`.

        Strategy:
        1. Hash the text with SHA-256.
        2. Seed a simple LCG PRNG with the hash to produce `dimensions` floats.
        3. Normalise to unit length.
        """
        digest = hashlib.sha256(text.encode("utf-8", errors="replace")).digest()
        seed = int.from_bytes(digest[:8], "little")

        # LCG parameters (Knuth MMIX)
        a = 6364136223846793005
        c = 1442695040888963407
        m = 2**64

        values: list[float] = []
        state = seed
        for _ in range(self._dimensions):
            state = (a * state + c) % m
            # Map to [-1.0, 1.0]
            values.append((state / (m - 1)) * 2.0 - 1.0)

        return _normalise(values)


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------


class GeminiEmbeddingProvider:
    """Google Generative AI embedding provider."""

    _model = "models/text-embedding-004"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if model:
            self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            import google.generativeai as genai  # type: ignore[import]
        except ImportError:
            raise RuntimeError(
                "google-generativeai is not installed. "
                "Run: pip install google-generativeai"
            )

        genai.configure(api_key=self._api_key)
        result = genai.embed_content(
            model=self._model,
            content=texts,
            task_type="retrieval_document",
        )
        return result["embedding"] if isinstance(result["embedding"][0], float) else result["embedding"]


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------


class OpenAIEmbeddingProvider:
    """OpenAI embedding provider."""

    _model = "text-embedding-3-small"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if model:
            self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            from openai import OpenAI  # type: ignore[import]
        except ImportError:
            raise RuntimeError(
                "openai is not installed. Run: pip install openai"
            )

        client = OpenAI(api_key=self._api_key)
        response = client.embeddings.create(input=texts, model=self._model)
        return [item.embedding for item in response.data]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_embedding_provider() -> EmbeddingProvider:
    """
    Return the appropriate embedding provider based on settings.

    Resolution order:
    1. KNOWLEDGE_EMBEDDING_MODEL env/setting:
       - "deterministic-v1"  → DeterministicEmbeddingProvider
       - "gemini-*"           → GeminiEmbeddingProvider
       - "openai-*"           → OpenAIEmbeddingProvider
       - anything else        → DeterministicEmbeddingProvider (safe fallback)
    """
    settings = get_settings()
    model = getattr(settings, "knowledge_embedding_model", "deterministic-v1")
    dimensions = int(getattr(settings, "knowledge_embedding_dimensions", _DEFAULT_DIMENSIONS))

    if model.startswith("gemini"):
        return GeminiEmbeddingProvider(model=model)
    if model.startswith("openai"):
        return OpenAIEmbeddingProvider(model=model)
    return DeterministicEmbeddingProvider(dimensions=dimensions)


# ---------------------------------------------------------------------------
# Pure-Python cosine similarity (no numpy)
# ---------------------------------------------------------------------------


def _normalise(v: list[float]) -> list[float]:
    """Return a unit-length copy of v. If |v|==0, return v unchanged."""
    magnitude = math.sqrt(sum(x * x for x in v))
    if magnitude == 0.0:
        return list(v)
    return [x / magnitude for x in v]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Compute cosine similarity between two equal-length float vectors.
    Returns a value in [-1.0, 1.0].
    Uses pure Python arithmetic; no numpy required.
    """
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} vs {len(b)}")

    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))

    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0

    return dot / (mag_a * mag_b)


def get_top_k_chunks(
    query_embedding: list[float],
    chunks_with_embeddings: list[tuple[object, list[float]]],
    k: int = 10,
    threshold: float = 0.3,
) -> list[tuple[object, float]]:
    """
    Rank chunks by cosine similarity to the query embedding.

    Args:
        query_embedding: The embedded query vector.
        chunks_with_embeddings: List of (chunk_object, embedding_vector) pairs.
        k: Maximum results to return.
        threshold: Minimum similarity score (inclusive).

    Returns:
        List of (chunk_object, score) pairs sorted descending by score.
    """
    scored = [
        (chunk, cosine_similarity(query_embedding, emb))
        for chunk, emb in chunks_with_embeddings
    ]
    filtered = [(chunk, score) for chunk, score in scored if score >= threshold]
    filtered.sort(key=lambda x: x[1], reverse=True)
    return filtered[:k]
