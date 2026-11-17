import { AuditWorkspace } from "@/components/audit-workspace";

export default async function AuditPage({ params }: { params: Promise<{ auditId: string }> }) {
  const { auditId } = await params;
  return <AuditWorkspace auditId={auditId} />;
}
