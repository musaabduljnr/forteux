"""Phase 09 Export Generation Service

Generates reports in JSON, Markdown, CSV, and package formats for audits,
design systems, prompts, and complete project archives.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AnalysisJob,
    Audit,
    AuditPrompt,
    AuditScreen,
    DesignSystemAnalysis,
    ExportJob,
    Finding,
    Project,
    ScreenAsset,
)


def generate_export_content(
    db: Session,
    export_job: ExportJob,
    project: Project,
    audit: Audit | None = None,
) -> tuple[str, str, str]:
    """
    Generates content, media_type, and filename for an ExportJob.
    Returns: (content_string, media_type, filename)
    """
    export_type = export_job.export_type
    export_format = export_job.format
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if export_type in ("single_audit", "multi_audit"):
        if audit is None:
            raise ValueError("Audit is required for audit exports")
        return _export_audit(db, project, audit, export_format, now_str)

    elif export_type == "design_system":
        return _export_design_system(db, project, audit, export_format, now_str)

    elif export_type == "stitch_prompt":
        return _export_stitch_prompt(db, project, audit, export_format, now_str)

    elif export_type == "project_package":
        return _export_project_package(db, project, export_format, now_str)

    raise ValueError(f"Unsupported export type: {export_type}")


def _export_audit(
    db: Session,
    project: Project,
    audit: Audit,
    fmt: str,
    ts: str,
) -> tuple[str, str, str]:
    findings = list(
        db.scalars(
            select(Finding)
            .where(Finding.audit_id == audit.id)
            .order_by(Finding.created_at.asc())
        )
    )

    screens = list(
        db.scalars(
            select(AuditScreen)
            .where(AuditScreen.audit_id == audit.id)
            .order_by(AuditScreen.sequence_index.asc())
        )
    )

    safe_title = "".join(c if c.isalnum() else "_" for c in audit.name)[:30]

    if fmt == "json":
        data = {
            "project": {
                "id": str(project.id),
                "name": project.name,
                "category": project.category,
                "platform_type": project.platform_type,
            },
            "audit": {
                "id": str(audit.id),
                "name": audit.name,
                "mode": audit.mode,
                "status": audit.status,
                "created_at": audit.created_at.isoformat() if audit.created_at else None,
                "screens_count": len(screens),
            },
            "screens": [
                {
                    "id": str(s.id),
                    "sequence_index": s.sequence_index,
                    "screen_label": s.screen_label,
                    "screen_description": s.screen_description,
                }
                for s in screens
            ],
            "findings": [
                {
                    "id": str(f.id),
                    "scope": f.scope,
                    "category": f.category,
                    "title": f.title,
                    "severity": f.severity,
                    "confidence": f.confidence,
                    "description": f.description,
                    "why_it_matters": f.why_it_matters,
                    "recommended_fix": f.recommended_fix,
                    "design_principle": f.design_principle,
                    "evidence_type": f.evidence_type,
                    "evidence": f.evidence,
                    "limitations": f.limitations,
                }
                for f in findings
            ],
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        return (
            json.dumps(data, indent=2),
            "application/json",
            f"audit_{safe_title}_{ts}.json",
        )

    elif fmt == "markdown":
        lines = [
            f"# UX Audit Report: {audit.name}",
            "",
            f"**Project:** {project.name}  ",
            f"**Mode:** {audit.mode.capitalize()} Screen  ",
            f"**Status:** {audit.status}  ",
            f"**Exported:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ",
            "",
            "## Summary of Findings",
            "",
            f"Total findings identified: {len(findings)}",
            "",
            "| # | Severity | Category | Title | Scope |",
            "|---|---|---|---|---|",
        ]
        for idx, f in enumerate(findings, start=1):
            lines.append(f"| {idx} | {f.severity.upper()} | {f.category} | {f.title} | {f.scope} |")

        lines.extend(["", "## Detailed Findings", ""])
        for idx, f in enumerate(findings, start=1):
            lines.extend([
                f"### {idx}. [{f.severity.upper()}] {f.title}",
                f"- **Category:** {f.category}",
                f"- **Scope:** {f.scope}",
                f"- **Confidence:** {f.confidence:.2f} ({f.evidence_type})",
                "",
                f"**Description:** {f.description}",
                "",
                f"**Why it matters:** {f.why_it_matters}",
                "",
                f"**Recommended fix:** {f.recommended_fix}",
                "",
                f"**Evidence:** {f.evidence}",
                "",
            ])
            if f.design_principle:
                lines.append(f"**Design Principle:** {f.design_principle}\n")

        return "\n".join(lines), "text/markdown; charset=utf-8", f"audit_{safe_title}_{ts}.md"

    elif fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "index",
            "id",
            "severity",
            "category",
            "scope",
            "title",
            "description",
            "why_it_matters",
            "recommended_fix",
            "confidence",
            "evidence_type",
        ])
        for idx, f in enumerate(findings, start=1):
            writer.writerow([
                idx,
                str(f.id),
                f.severity,
                f.category,
                f.scope,
                f.title,
                f.description,
                f.why_it_matters,
                f.recommended_fix,
                f.confidence,
                f.evidence_type,
            ])
        return output.getvalue(), "text/csv; charset=utf-8", f"audit_{safe_title}_{ts}.csv"

    elif fmt == "zip":
        # Structured zip manifest representation
        package = {
            "archive_type": "audit_package",
            "manifest_version": "1.0",
            "project_name": project.name,
            "audit_name": audit.name,
            "created_at": ts,
            "files_included": [
                f"audit_{safe_title}_{ts}.json",
                f"audit_{safe_title}_{ts}.md",
                f"audit_{safe_title}_{ts}.csv",
            ],
            "findings_count": len(findings),
            "screens_count": len(screens),
        }
        return json.dumps(package, indent=2), "application/json", f"audit_{safe_title}_{ts}_manifest.json"

    raise ValueError(f"Unsupported format: {fmt}")


def _export_design_system(
    db: Session,
    project: Project,
    audit: Audit | None,
    fmt: str,
    ts: str,
) -> tuple[str, str, str]:
    query = select(DesignSystemAnalysis).where(
        DesignSystemAnalysis.project_id == project.id,
        DesignSystemAnalysis.status == "completed",
    )
    if audit is not None:
        query = query.where(DesignSystemAnalysis.audit_id == audit.id)
    ds = db.scalar(query.order_by(DesignSystemAnalysis.updated_at.desc()))

    if ds is None:
        empty = {
            "project_name": project.name,
            "status": "no_completed_analysis",
            "message": "No completed design system analysis found for this project.",
        }
        return json.dumps(empty, indent=2), "application/json", f"design_system_{ts}.json"

    safe_title = "".join(c if c.isalnum() else "_" for c in project.name)[:30]

    if fmt == "json":
        data = {
            "project_id": str(project.id),
            "project_name": project.name,
            "audit_id": str(ds.audit_id),
            "consistency_score": ds.consistency_score,
            "summary": ds.summary,
            "color_palette": json.loads(ds.color_palette_json or "[]"),
            "typography": json.loads(ds.typography_json or "[]"),
            "spacing_layout": json.loads(ds.spacing_layout_json or "{}"),
            "shapes_surfaces": json.loads(ds.shapes_surfaces_json or "{}"),
            "components": json.loads(ds.components_json or "[]"),
            "tokens": json.loads(ds.tokens_json or "[]"),
            "consistency_issues": json.loads(ds.consistency_issues_json or "[]"),
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        return json.dumps(data, indent=2), "application/json", f"design_system_{safe_title}_{ts}.json"

    elif fmt == "markdown":
        colors = json.loads(ds.color_palette_json or "[]")
        typo = json.loads(ds.typography_json or "[]")
        issues = json.loads(ds.consistency_issues_json or "[]")
        lines = [
            f"# Design System Report: {project.name}",
            "",
            f"**Consistency Score:** {ds.consistency_score:.1f}/100" if ds.consistency_score is not None else "**Consistency Score:** N/A",
            f"**Status:** {ds.status}",
            f"**Generated:** {ds.created_at.strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "## Summary",
            ds.summary or "No summary provided.",
            "",
            "## Color Palette",
            "",
            "| Name | Hex | Category | Confidence |",
            "|---|---|---|---|",
        ]
        for c in colors:
            lines.append(f"| {c.get('semantic_name', '')} | `{c.get('hex', '')}` | {c.get('category', '')} | {c.get('confidence', 0):.2f} |")

        lines.extend(["", "## Typography Hierarchy", "", "| Style | Size | Weight | Hierarchy |", "|---|---|---|---|"])
        for t in typo:
            lines.append(f"| {t.get('style_name', '')} | {t.get('font_size_approx', '')} | {t.get('font_weight_category', '')} | {t.get('text_hierarchy', '')} |")

        lines.extend(["", "## Consistency Issues", ""])
        for iss in issues:
            lines.append(f"- **[{iss.get('severity', '').upper()}] {iss.get('title', '')}**: {iss.get('description', '')}")
            lines.append(f"  *Fix:* {iss.get('recommended_fix', '')}\n")

        return "\n".join(lines), "text/markdown; charset=utf-8", f"design_system_{safe_title}_{ts}.md"

    elif fmt == "csv":
        tokens = json.loads(ds.tokens_json or "[]")
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["token_name", "value", "category", "evidence", "confidence"])
        for tok in tokens:
            writer.writerow([
                tok.get("name", ""),
                tok.get("value", ""),
                tok.get("category", ""),
                tok.get("evidence", ""),
                tok.get("confidence", 0),
            ])
        return output.getvalue(), "text/csv; charset=utf-8", f"design_tokens_{safe_title}_{ts}.csv"

    elif fmt == "zip":
        manifest = {
            "archive_type": "design_system_package",
            "project_name": project.name,
            "consistency_score": ds.consistency_score,
            "created_at": ts,
            "tokens_count": len(json.loads(ds.tokens_json or "[]")),
            "colors_count": len(json.loads(ds.color_palette_json or "[]")),
        }
        return json.dumps(manifest, indent=2), "application/json", f"design_system_{safe_title}_{ts}_manifest.json"

    raise ValueError(f"Unsupported format: {fmt}")


def _export_stitch_prompt(
    db: Session,
    project: Project,
    audit: Audit | None,
    fmt: str,
    ts: str,
) -> tuple[str, str, str]:
    query = select(AuditPrompt)
    if audit is not None:
        query = query.where(AuditPrompt.audit_id == audit.id)
    else:
        query = query.join(Audit, Audit.id == AuditPrompt.audit_id).where(Audit.project_id == project.id)

    prompt = db.scalar(query.order_by(AuditPrompt.updated_at.desc()))
    if prompt is None:
        return (
            f"# Google Stitch Prompt\n\nNo prompt generated for project '{project.name}' yet.",
            "text/markdown; charset=utf-8",
            f"stitch_prompt_{ts}.md",
        )

    safe_title = "".join(c if c.isalnum() else "_" for c in project.name)[:30]
    content = prompt.content
    if fmt == "json":
        data = {
            "prompt_id": str(prompt.id),
            "audit_id": str(prompt.audit_id),
            "project_name": project.name,
            "version_number": prompt.version_number,
            "provider": prompt.provider,
            "model": prompt.model,
            "user_instructions": prompt.user_instructions,
            "prompt_content": content,
            "updated_at": prompt.updated_at.isoformat() if prompt.updated_at else None,
        }
        return json.dumps(data, indent=2), "application/json", f"stitch_prompt_{safe_title}_{ts}.json"
    else:
        return content, "text/markdown; charset=utf-8", f"stitch_prompt_{safe_title}_{ts}.md"


def _export_project_package(
    db: Session,
    project: Project,
    fmt: str,
    ts: str,
) -> tuple[str, str, str]:
    audits = list(
        db.scalars(
            select(Audit)
            .where(Audit.project_id == project.id, Audit.deleted_at.is_(None))
            .order_by(Audit.created_at.desc())
        )
    )
    safe_title = "".join(c if c.isalnum() else "_" for c in project.name)[:30]

    package = {
        "project": {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "category": project.category,
            "platform_type": project.platform_type,
            "context_text": project.context_text,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
            "archived_at": project.archived_at.isoformat() if project.archived_at else None,
        },
        "audits": [
            {
                "id": str(a.id),
                "name": a.name,
                "mode": a.mode,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in audits
        ],
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "export_manifest": {
            "archive_format": fmt,
            "total_audits": len(audits),
        },
    }

    if fmt == "markdown":
        lines = [
            f"# Project Summary: {project.name}",
            "",
            f"**Description:** {project.description or 'None'}",
            f"**Category:** {project.category or 'Uncategorized'}",
            f"**Platform:** {project.platform_type or 'General'}",
            f"**Total Audits:** {len(audits)}",
            "",
            "## Audits",
            "",
            "| Audit Name | Mode | Status | Created |",
            "|---|---|---|---|",
        ]
        for a in audits:
            lines.append(f"| {a.name} | {a.mode} | {a.status} | {a.created_at.strftime('%Y-%m-%d')} |")
        return "\n".join(lines), "text/markdown; charset=utf-8", f"project_{safe_title}_{ts}.md"

    elif fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["audit_id", "audit_name", "mode", "status", "created_at"])
        for a in audits:
            writer.writerow([str(a.id), a.name, a.mode, a.status, a.created_at.isoformat() if a.created_at else ""])
        return output.getvalue(), "text/csv; charset=utf-8", f"project_{safe_title}_{ts}.csv"

    # Default to JSON or JSON manifest
    return json.dumps(package, indent=2), "application/json", f"project_{safe_title}_{ts}.json"
