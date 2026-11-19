# Phase 10: AI Cost & Resource Optimization Report

**Date**: November 17, 2026  
**Scope**: Token Economics, Image Downsampling, Context Pruning & Model Tiering Strategy  
**Status**: Completed

---

## 1. Executive Summary & Cost Overview

AI vision and generative reasoning represent the primary operational variable cost in the Forteux platform. This report provides a quantitative breakdown of token consumption across single-screen audits, multi-screen journeys, design system extraction, and RAG retrieval, establishing cost-reduction guardrails.

---

## 2. Token Usage & Unit Cost Breakdown

Estimates below are based on Google Gemini 2.5 Flash pricing (\$0.075 per 1M input tokens, \$0.30 per 1M output tokens, or vision equivalent $\approx \$0.00013$ per high-res tile).

| Pipeline Stage | Input Tokens (Avg) | Output Tokens (Avg) | Cost Per Run (Est.) | Primary Driver |
| :--- | :--- | :--- | :--- | :--- |
| **Single-Screen Audit** | 2,100 (Image + Prompt) | 650 (Findings JSON) | **\$0.00035** | Image resolution & finding detail |
| **Multi-Screen Journey (4 screens)** | 8,500 (4 Images + Flow) | 1,400 (Flow Report) | **\$0.00105** | Image count & sequence context |
| **Design System Extraction** | 7,200 (3 Screens + Rules) | 1,800 (Token Manifest) | **\$0.00108** | Token schemas & color palettes |
| **Google Stitch Prompt Gen** | 1,200 (Finding Subset) | 800 (Markdown Prompt) | **\$0.00033** | Finding context & layout tokens |
| **RAG Embedding Query** | 150 (User Question) | 0 (Vector lookup) | **\$0.00001** | Embedding API |

### Monthly Operational Cost Projections

| Monthly Usage Tier | Audits / Mo | Est. AI Operational Cost | Recommended Provisioning |
| :--- | :--- | :--- | :--- |
| **Startup / Pilot** | 100 | **\$0.28** | Serverless pay-as-you-go |
| **Growth Stage** | 1,000 | **\$2.81** | Standard API tier |
| **Scale / Enterprise** | 10,000 | **\$28.10** | Provisioned throughput & cached prefixes |
| **High Enterprise** | 100,000 | **\$281.00** | Dedicated enterprise quota with batch discounts |

---

## 3. Cost Optimization Strategies Implemented

1. **Intelligent Image Resizing & Downsampling**:
   - High-resolution uploads (e.g. 4K $3840 \times 2160$) are capped to maximum dimension 1920px prior to AI ingestion via `image.py`.
   - Preserves crisp text legibility for font detection while eliminating excessive vision tiles that inflate token bills by $4\times$.
2. **Context-Window Pruning in RAG**:
   - Instead of injecting full design manuals, the RAG retriever filters by cosine threshold ($\ge 0.65$) and caps injected chunks to $\text{top\_k} = 3$ ($\approx 600$ tokens).
3. **Structured Schema Constraints**:
   - Utilizing Pydantic JSON schemas with model temperature $0.1$ prevents verbose preamble text ("Sure, here are your findings..."), saving 15–20% of output token generation.
4. **Token Caching for Design System Refinement**:
   - For multi-turn Stitch prompt generation within the same audit, the base design token payload can be cached, avoiding duplicate visual token re-extraction.

---

## 4. Recommended Model Tiering

| Workload | Recommended Model | Rationale | Fallback Model |
| :--- | :--- | :--- | :--- |
| **Single-Screen Audit** | **Gemini 2.5 Flash** | Ultra-low latency ($<1.5\text{s}$), superior vision token pricing, high bounding-box fidelity. | Deterministic CV Provider |
| **Multi-Screen Reasoning** | **Gemini 2.5 Flash** | Large 1M context window accommodates 10+ high-res journey screenshots in a single prompt. | Gemini 2.5 Pro |
| **Design System Extraction** | **Gemini 2.5 Flash** | Precise structured JSON schema adherence for colors, fonts, and spacing tokens. | Deterministic Provider |
| **Stitch Prompt Synthesis** | **Gemini 2.5 Flash** | High markdown instruction compliance, rich design vocabulary for Stitch UI compiler. | Deterministic Prompt Engine |
| **Knowledge Embeddings** | **text-embedding-004** | 768-dimensional normalized vectors with fast nearest-neighbor retrieval. | Deterministic v1 Vectorizer |
