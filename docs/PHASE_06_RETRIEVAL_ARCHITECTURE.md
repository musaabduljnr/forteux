# Phase 06 Retrieval Architecture

## 1. Multi-Stage Hybrid Retrieval

The retrieval engine in `backend/app/services/knowledge_retrieval.py` provides high-precision matching of design references against audit screens and user prompts:

```
  User Query / Audit Context
             │
             ▼
  ┌────────────────────────────────────────┐
  │  Scope & Tenant Authorization Filter   │  (Strict DB WHERE clause)
  │  (Tenant ID, Project ID, Status=ready) │
  └──────────────────┬─────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
  ┌──────────────┐        ┌──────────────┐
  │ Dense Vector │        │ Keyword Token│
  │ Similarity   │        │ Matching     │
  └──────┬───────┘        └──────┬───────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
  ┌────────────────────────────────────────┐
  │    Score Combination & Re-ranking      │
  │    (Cosine score + Keyword boost)      │
  └──────────────────┬─────────────────────┘
                     │
                     ▼
  ┌────────────────────────────────────────┐
  │ Threshold Filter & Top-K Truncation    │
  │ (score >= 0.25, top_k <= 20)           │
  └──────────────────┬─────────────────────┘
                     │
                     ▼
             Retrieved Chunks
```

---

## 2. Security & Scoping Rules

Every retrieval query enforces:
1. **Mandatory Tenant Scoping**: Chunks are never queried without an explicit `KnowledgeDocument.tenant_id == tenant_id` assertion.
2. **Project Isolation**:
   - When querying in a project audit context, chunks from `project_id == current_project_id` AND `project_id IS NULL` (Global) are included.
   - Chunks from another project (`project_id != current_project_id`) are unconditionally excluded.
3. **State Scoping**:
   - Only documents with `status == 'ready'` and `deleted_at IS NULL` are candidates.
   - Only chunks belonging to the document's `active_version_id` are returned.

---

## 3. Hybrid Ranking

- **Dense Similarity**: Cosine similarity between query embedding and chunk vector.
- **Lexical Overlap**: Matches clean 3+ letter query tokens against the chunk text.
- If lexical overlap is strong, a keyword boost ensures domain-specific terminology (e.g., `#0052CC`, `border-radius`, `WCAG`) surfaces even if semantic embedding scores fluctuate.
- Results are ranked descending by score and capped at `top_k` (default 8).
