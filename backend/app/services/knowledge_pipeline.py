"""
Knowledge pipeline service.

Orchestrates:
1. Document ingestion and validation
2. Text extraction with page provenance
3. Semantic chunking
4. Embedding generation
5. Chunk persistence and indexing
6. Secure document deletion and cleanup
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import DeletionTask, DocumentVersion, KnowledgeChunk, KnowledgeDocument, utc_now
from app.services.document_chunker import DocumentChunker
from app.services.document_extractor import DocumentExtractor, ExtractionError
from app.services.embedding import EmbeddingProvider, get_embedding_provider
from app.services.storage import S3Storage


class KnowledgePipelineError(Exception):
    """Raised when knowledge document processing fails."""


class KnowledgePipeline:
    def __init__(
        self,
        extractor: DocumentExtractor | None = None,
        chunker: DocumentChunker | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.extractor = extractor or DocumentExtractor()
        self.chunker = chunker or DocumentChunker()
        self.embedding_provider = embedding_provider or get_embedding_provider()

    def process_document(
        self,
        document: KnowledgeDocument,
        version: DocumentVersion,
        raw_bytes: bytes,
        db: Session,
    ) -> None:
        """
        Execute the full extraction, chunking, embedding, and indexing pipeline.
        Updates document and version records in-place.
        """
        try:
            # 1. Extraction
            document.status = "extracting"
            version.status = "extracting"
            db.commit()

            extraction_result = self.extractor.extract(
                raw_bytes=raw_bytes,
                mime_type=version.mime_type,
                filename=version.original_filename,
            )

            # 2. Chunking
            document.status = "chunking"
            version.status = "chunking"
            db.commit()

            chunks = self.chunker.chunk(extraction_result.pages)
            if not chunks:
                raise KnowledgePipelineError(
                    "No usable text segments could be created from this document."
                )

            # 3. Embedding
            document.status = "embedding"
            version.status = "embedding"
            db.commit()

            chunk_texts = [c.text for c in chunks]
            # Embed in batches of 32
            embeddings: list[list[float]] = []
            batch_size = 32
            for i in range(0, len(chunk_texts), batch_size):
                batch = chunk_texts[i : i + batch_size]
                batch_embeddings = self.embedding_provider.embed(batch)
                embeddings.extend(batch_embeddings)

            # 4. Indexing (persistence)
            document.status = "indexing"
            db.commit()

            # Clean any old chunks for this version (e.g. on retry)
            db.execute(
                delete(KnowledgeChunk).where(KnowledgeChunk.document_version_id == version.id)
            )

            chunk_records: list[KnowledgeChunk] = []
            for chunk_data, emb in zip(chunks, embeddings):
                chunk_rec = KnowledgeChunk(
                    id=uuid4(),
                    tenant_id=document.tenant_id,
                    project_id=document.project_id,
                    document_id=document.id,
                    document_version_id=version.id,
                    chunk_index=chunk_data.chunk_index,
                    text=chunk_data.text,
                    page_start=chunk_data.page_start,
                    page_end=chunk_data.page_end,
                    section_heading=chunk_data.section_heading,
                    char_count=chunk_data.char_count,
                    embedding_json=json.dumps(emb),
                    embedding_model=self.embedding_provider.model_name,
                    embedding_dimensions=len(emb),
                    metadata_json=json.dumps({
                        "document_name": document.display_name,
                        "category": document.category,
                        "scope": document.scope,
                    }),
                    created_at=utc_now(),
                )
                chunk_records.append(chunk_rec)
                db.add(chunk_rec)

            # 5. Finalize version & document status
            version.status = "ready"
            version.page_count = extraction_result.page_count
            version.chunk_count = len(chunks)
            version.extractor_version = extraction_result.extractor_version
            version.embedding_model = self.embedding_provider.model_name
            version.extraction_warnings = (
                json.dumps(extraction_result.warnings) if extraction_result.warnings else None
            )
            version.error_message = None
            version.processed_at = utc_now()

            document.status = "ready"
            document.active_version_id = version.id
            document.error_message = None
            document.updated_at = utc_now()

            db.commit()

        except Exception as exc:
            db.rollback()
            error_msg = str(exc)
            version.status = "failed"
            version.error_message = error_msg
            document.status = "failed"
            document.error_message = error_msg
            document.updated_at = utc_now()
            db.commit()
            raise KnowledgePipelineError(f"Document processing failed: {error_msg}") from exc

    def delete_document_data(
        self,
        document: KnowledgeDocument,
        db: Session,
        storage: S3Storage | None = None,
    ) -> DeletionTask:
        """
        Permanently remove chunks and storage objects associated with a document.
        Excludes document from any future retrieval.
        """
        task = DeletionTask(
            id=uuid4(),
            document_id=document.id,
            tenant_id=document.tenant_id,
            status="in_progress",
            requested_at=utc_now(),
            chunks_deleted=0,
        )
        db.add(task)
        document.status = "deleting"
        db.commit()

        try:
            # 1. Delete all knowledge chunks for this document
            chunk_delete_stmt = delete(KnowledgeChunk).where(
                KnowledgeChunk.document_id == document.id,
                KnowledgeChunk.tenant_id == document.tenant_id,
            )
            result = db.execute(chunk_delete_stmt)
            task.chunks_deleted = result.rowcount or 0

            # 2. Delete raw files from S3 for all versions
            if storage is not None:
                versions = db.scalars(
                    select(DocumentVersion).where(DocumentVersion.document_id == document.id)
                ).all()
                for v in versions:
                    try:
                        storage.delete(v.object_key)
                    except Exception as s3_err:
                        # Log but continue to ensure DB cleanup proceeds
                        task.error_message = f"S3 deletion warning: {s3_err}"

            # 3. Soft-delete the document record (marked deleted with timestamp)
            document.status = "deleted"
            document.deleted_at = utc_now()
            document.updated_at = utc_now()

            task.status = "completed"
            task.completed_at = utc_now()
            db.commit()
            return task

        except Exception as exc:
            db.rollback()
            task.status = "failed"
            task.error_message = str(exc)
            db.commit()
            raise
