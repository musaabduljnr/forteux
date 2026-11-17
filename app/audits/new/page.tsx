import { NewAuditForm } from "@/components/new-audit-form";
import { PageHeader } from "@/components/ui";

export default function NewAuditPage() {
  return (
    <div className="page-stack">
      <PageHeader eyebrow="Create an audit" title="Start with a screen" description="Choose an audit mode, add your screenshots, and share a little context." />
      <div className="demo-notice"><span><strong>Frontend demo</strong> Uploads are previewed locally. No files are sent to a backend and no analysis runs.</span></div>
      <NewAuditForm />
    </div>
  );
}
