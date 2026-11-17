# Acceptance Criteria

**Status:** Draft for review — Phase 01  
**Last reviewed:** 2026-11-16

Thresholds below are proposed beta gates. They must be measured on a held-out, permissioned, expert-annotated set. Report confidence intervals, task difficulty, model/version, and annotator agreement. If a target is not met, change the product behavior or disclose the limitation; do not tune only on the test set.

## 1. Product behavior

- **AC-PROD-01:** A user can submit one valid screenshot in Single mode and receive independently addressable findings or an explicit processing failure.
- **AC-PROD-02:** A user can submit at least 2 and no more than the approved multi-screen maximum; reorder and labels are reflected in analysis and prompt.
- **AC-PROD-03:** Multi-screen output includes screen-specific results plus relationship-level findings; a benchmark verifies cross-screen reasoning rather than a concatenation of independent audits.
- **AC-PROD-04:** Findings can be selected/deselected; the system generates one editable/copyable Stitch prompt containing all selected findings (or all when none are selected).
- **AC-PROD-05:** Prompt includes screen context, order/relationships when applicable, locations, prioritized improvements, consistency requirements, preservation constraints, and expected redesign output.
- **AC-PROD-06:** Failed, partial, and uncertain analysis states are distinguishable from a successful zero-finding result.

## 2. Finding quality and localization

- **AC-AI-01:** Every finding conforms to the versioned schema and has title, category, scope, severity, confidence, certainty, description, impact, recommendation, and evidence classification.
- **AC-AI-02:** 100% of returned boxes pass server-side finite-value, image association, positivity, normalized range, and bounds validation; screen-level findings may omit boxes.
- **AC-AI-03:** On the beta benchmark, target finding precision is at least 0.80 and recall at least 0.70 for in-scope, screenshot-evident issues. Report per-category scores and label disagreement; tune targets after pilot baseline.
- **AC-AI-04:** For findings requiring localization, median box IoU with expert reference is at least 0.50; report IoU distribution and proportion with IoU >= 0.5. Broad/full-screen issues are evaluated separately.
- **AC-AI-05:** False positives are measured as unsupported findings per screen; target no more than 1.0 mean unsupported finding per screen on the held-out set.
- **AC-AI-06:** Severity agreement with experts achieves weighted Cohen's kappa >= 0.60, with confusion matrix and critical/high issue recall reported.
- **AC-AI-07:** Recommendations are rated actionable and contextually appropriate by two reviewers on a defined rubric; target >= 80% acceptable agreement with adjudication.
- **AC-AI-08:** Confidence calibration is measured (e.g., expected calibration error); do not label scores “probability” unless calibration is adequate. Findings below the approved threshold are suppressed or clearly marked suspected/uncertain.
- **AC-AI-09:** No output claims verified functional behavior, keyboard accessibility, or screen-reader compatibility based solely on screenshots in adversarial and standard test cases.

## 3. Multi-screen quality

- **AC-FLOW-01:** For each cross-screen finding, output identifies at least two relevant screens, explains the relationship, and distinguishes visible inconsistency from inferred missing transition.
- **AC-FLOW-02:** On the labeled pairwise consistency set, target precision >= 0.75 and recall >= 0.65; score screen-specific and cross-screen findings separately.
- **AC-FLOW-03:** On journey cases, expert reviewers rate at least 80% of material flow findings as evidence-linked and useful; missing-step assertions must be marked suspected unless directly visible.
- **AC-FLOW-04:** Compare against an independent-screen concatenation baseline; cross-screen model must improve the agreed relationship-level quality metric without materially reducing per-screen precision.
- **AC-FLOW-05:** Reordering input screens changes sequence-dependent analysis/prompt context and does not silently retain stale sequence-derived results.

## 4. Knowledge and citations

- **AC-KNOW-01:** Supported files show clear queued/processing/ready/failed states and actionable errors; failed replacements do not deactivate the last ready version.
- **AC-KNOW-02:** Retrieval returns only global and authorized project chunks; automated tests attempt cross-tenant/project leakage for search and citations.
- **AC-KNOW-03:** Citation precision is 100% for emitted citations: every cited document/version/chunk exists in the retrieved set and every page reference matches stored metadata. Missing page metadata is shown as unavailable, never guessed.
- **AC-KNOW-04:** On a labeled retrieval set, target Recall@5 >= 0.80 and nDCG@5 >= 0.70; report by category, corpus size, and scope.
- **AC-KNOW-05:** Recommendations distinguish visual observation, source-supported advice, and professional guidance. Documents do not constrain all reasoning or override application instructions.
- **AC-KNOW-06:** Deleting a document removes it from retrieval immediately and eventually from vector/object stores; the operation reports completion or an explicit retryable failure.

## 5. Security, privacy, and operations

- **AC-SEC-01:** Authorization tests deny unauthorized access to every tenant/project resource class, including signed URLs and asynchronous jobs.
- **AC-SEC-02:** Invalid type, oversized file, spoofed MIME, malformed image, excessive dimensions/pages, and parser timeout are rejected or isolated without worker instability.
- **AC-SEC-03:** Adversarial uploaded documents cannot change system policy, reveal secrets, invoke unauthorized tools, or cause out-of-scope citations.
- **AC-SEC-04:** Provider keys and raw customer content do not appear in client bundles, standard logs, metrics, or error responses.
- **AC-SEC-05:** Retry, duplicate delivery, cancellation/deletion, provider timeout, and dead-letter scenarios preserve correct state and do not duplicate user-visible findings.
- **AC-SEC-06:** Data retention, export/deletion behavior, backups, provider terms, and regional processing match the approved policy and are exercised before launch.
- **AC-OPS-01:** Proposed p95 audit targets (90 seconds single; 180 seconds 12-screen) are measured on representative workload; exceedances and provider outages are surfaced, never silently reported as success.
- **AC-OPS-02:** Per-audit and per-document cost is observable by stage, and tenant limits/budget alerts prevent unbounded usage.

## 6. Accessibility and usability

- **AC-UX-01:** Annotation markers have accessible names and keyboard interaction; the finding list provides equivalent information without relying on color or canvas-only UI.
- **AC-UX-02:** Audit progress, failure, uncertainty, and completion are announced accessibly and have visible status text.
- **AC-UX-03:** The application UI is evaluated against WCAG 2.2 AA; this is separate from screenshot-based audit capability.

## 7. Phase 02 frontend acceptance

- **AC-FE-01:** Dashboard, new audit, single/multi audit workspace, projects/details, history, knowledge library, design-system, and settings routes render and are navigable.
- **AC-FE-02:** Screenshot previews accept PNG/JPG, are replaceable/removable, and multi-screen order can be changed by drag/drop and keyboard-operable controls.
- **AC-FE-03:** Normalized bounding-box fixtures remain aligned at different zoom levels; selecting a marker and its finding card stay synchronized.
- **AC-FE-04:** Findings can be included/excluded, and one prompt is generated from selected items (or all items by default), edited, regenerated, and copied with success/error feedback.
- **AC-FE-05:** Project and document metadata interactions work locally; all non-backend actions disclose that they are demo-only.
- **AC-FE-06:** Example findings, activity, and document states are clearly labeled demonstration data and are never presented as live AI output.
- **AC-FE-07:** Responsive layouts work without horizontal page overflow at desktop, tablet, and mobile breakpoints; annotation and finding details remain accessible.
- **AC-FE-08:** No backend, AI, OCR, embedding, or vector search is invoked during this phase; screenshot/document content is not persisted or sent to external services.
