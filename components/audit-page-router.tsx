"use client";

import { useAppState } from "./app-state";
import { AuditWorkspace } from "./audit-workspace";
import { MultiScreenWorkspace } from "./multi-screen-workspace";

interface AuditPageRouterProps {
  auditId: string;
}

export function AuditPageRouter({ auditId }: AuditPageRouterProps) {
  const { audits } = useAppState();

  // Find audit in app state (may be null during initial hydration)
  const audit = audits.find((a) => a.id === auditId);

  if (audit?.mode === "multi") {
    return (
      <MultiScreenWorkspace
        auditId={audit.id}
        projectId={audit.projectId}
        auditName={audit.name}
      />
    );
  }

  // Default / single-screen: use existing AuditWorkspace
  // AuditWorkspace handles its own loading state if audit is not yet in state
  return <AuditWorkspace auditId={auditId} />;
}
