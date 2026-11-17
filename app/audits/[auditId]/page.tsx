import { AuditPageRouter } from "@/components/audit-page-router";

export default async function AuditPage({ params }: { params: Promise<{ auditId: string }> }) {
  const { auditId } = await params;
  return <AuditPageRouter auditId={auditId} />;
}
