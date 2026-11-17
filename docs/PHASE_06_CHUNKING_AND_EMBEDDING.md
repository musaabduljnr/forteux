# Phase 06 Chunking & Embedding Architecture

## 1. Chunking Strategy

Implemented in `backend/app/services/document_chunker.py`, the chunker splits extracted text into semantically cohesive, overlapping segments:

- **Target Chunk Size**: ~1,200 characters (~200–250 tokens).
- **Chunk Overlap**: 150 characters (~25–30 tokens) carried over across segment boundaries to preserve cross-sentence semantic context.
- **Minimum Chunk Size**: 20 characters to avoid indexing single punctuation marks or empty headings.
- **Boundary Awareness**: Chunks split on natural paragraph boundaries (`\n\n`) first, rather than raw character slicing.
- **Section Heading Detection**:
  - Automatically identifies markdown headers (`#`, `##`, `###`) and ALL-CAPS short titles (<80 chars).
  - Injects detected headings into chunk metadata and snapshots for citation provenance.
- **Page Provenance**:
  - Each chunk tracks its originating `page_start` and `page_end`.
  - When a chunk spans across page boundaries, both are recorded.

---

## 2. Embedding Architecture & Provider Abstraction

Implemented in `backend/app/services/embedding.py`, the embedding subsystem is provider-abstracted:

### Supported Providers

1. **DeterministicEmbeddingProvider** (`deterministic-v1`):
   - Fast, reproducible hash-based embedding using SHA-256 and Knuth MMIX 64-bit LCG.
   - Generates normalized 768-dimensional float vectors.
   - Used in automated test suites and offline local development; requires zero external API keys or network latency.

2. **GeminiEmbeddingProvider** (`models/text-embedding-004`):
   - Uses Google Generative AI Python SDK.
   - Generates 768-dimensional dense vector embeddings with `task_type="retrieval_document"`.

3. **OpenAIEmbeddingProvider** (`text-embedding-3-small`):
   - Uses OpenAI Python SDK with standard 1536-dimensional or reduced embeddings.

### Cosine Similarity Engine

- Implemented in **pure Python** using the standard library `math` module (vector dot product divided by Euclidean norms).
- Operates with zero binary C-compiler dependencies, avoiding environment-specific compilation barriers while maintaining sub-millisecond ranking performance across hundreds of chunks.
