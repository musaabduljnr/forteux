"""
Knowledge retrieval service.

Implements hybrid semantic + keyword retrieval with:
- Strict tenant and project permission isolation
- Ready-state document filtering
- Active-version scoping
- Cosine similarity ranking via embedding
- Keyword search fallback / RRF blending
- Citations with page numbers and section headings
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.db.models import DocumentVersion, KnowledgeChunk, KnowledgeDocument
from app.services.embedding import EmbeddingProvider, cosine_similarity, get_embedding_provider


@dataclass
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    document_name: str
    category: str
    scope: str
    text: str
    page_start: int | None
    page_end: int | None
    section_heading: str | None
    score: float
    retrieval_rank: int


class KnowledgeRetrieval:
    def __init__(self, embedding_provider: EmbeddingProvider | None = None) -> None:
        self.embedding_provider = embedding_provider or get_embedding_provider()

    def retrieve(
        self,
        query: str,
        tenant_id: UUID,
        project_id: UUID | None = None,
        include_global: bool = True,
        include_project: bool = True,
        top_k: int = 8,
        threshold: float = 0.25,
        db: Session = None,  # type: ignore[assignment]
    ) -> list[RetrievedChunk]:
        """
        Retrieve relevant knowledge chunks with strict tenant and project isolation.
        """
        assert tenant_id is not None, "tenant_id must be provided for security isolation"

        clean_query = query.strip()
        if not clean_query:
            return []

        # 1. Build scope conditions
        scope_conditions = []
        if include_global:
            # Global: project_id IS NULL and tenant matches
            scope_conditions.append(
                and_(
                    KnowledgeDocument.project_id.is_(None),
                    KnowledgeDocument.tenant_id == tenant_id,
                )
            )

        if include_project and project_id is not None:
            # Project-specific: project_id matches and tenant matches
            scope_conditions.append(
                and_(
                    KnowledgeDocument.project_id == project_id,
                    KnowledgeDocument.tenant_id == tenant_id,
                )
            )

        if not scope_conditions:
            return []

        # 2. Query chunks from ready, non-deleted documents and active versions
        stmt = (
            select(
                KnowledgeChunk,
                KnowledgeDocument.display_name,
                KnowledgeDocument.category,
                KnowledgeDocument.scope,
            )
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(
                KnowledgeDocument.tenant_id == tenant_id,
                KnowledgeDocument.status == "ready",
                KnowledgeDocument.deleted_at.is_(None),
                KnowledgeChunk.document_version_id == KnowledgeDocument.active_version_id,
                or_(*scope_conditions),
            )
        )

        rows = db.execute(stmt).all()
        if not rows:
            return []

        # 3. Semantic scoring via embedding
        query_embedding = self.embedding_provider.embed([clean_query])[0]

        scored_items: list[tuple[KnowledgeChunk, str, str, str, float]] = []
        query_tokens = set(re.findall(r"\b\w{3,}\b", clean_query.lower()))

        for chunk, doc_name, category, scope in rows:
            score = 0.0
            if chunk.embedding_json:
                try:
                    emb = json.loads(chunk.embedding_json)
                    score = cosine_similarity(query_embedding, emb)
                except Exception:
                    score = 0.0

            # Keyword boost: if keywords appear in chunk text, give a bump / fallback score
            if query_tokens:
                chunk_lower = chunk.text.lower()
                matches = sum(1 for t in query_tokens if t in chunk_lower)
                if matches > 0:
                    overlap_ratio = matches / len(query_tokens)
                    keyword_boost = 0.35 + 0.5 * (matches / max(1, len(query_tokens)))
                    score = max(score, keyword_boost)

            if score >= threshold:
                scored_items.append((chunk, doc_name, category, scope, score))

        # 4. Sort by score descending and take top_k
        scored_items.sort(key=lambda x: x[4], reverse=True)
        top_items = scored_items[:top_k]

        results: list[RetrievedChunk] = []
        for rank, (chunk, doc_name, category, scope, score) in enumerate(top_items, start=1):
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_name=doc_name,
                    category=category,
                    scope=scope,
                    text=chunk.text,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    section_heading=chunk.section_heading,
                    score=round(score, 4),
                    retrieval_rank=rank,
                )
            )

        return results
