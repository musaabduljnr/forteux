"use client";

import { useAppState } from "@/components/app-state";
import { Icon } from "@/components/icons";
import { Badge, Button, EmptyState, PageHeader, SectionTitle } from "@/components/ui";

const sections = [
  { title: "Colour palette", description: "Core, accent, surface, and semantic colours.", icon: "layers" as const },
  { title: "Typography", description: "Typefaces, sizes, weights, and text hierarchy.", icon: "file" as const },
  { title: "Spacing scale", description: "Recurring spacing and layout rhythm.", icon: "grid" as const },
  { title: "Border radius", description: "Corner treatments used across components.", icon: "dashboard" as const },
  { title: "Buttons", description: "Primary, secondary, and contextual actions.", icon: "plus" as const },
  { title: "Form elements", description: "Inputs, selection controls, and validation states.", icon: "edit" as const },
  { title: "Cards and surfaces", description: "Content containers, elevation, and grouping.", icon: "folder" as const },
  { title: "Navigation patterns", description: "Navigation and orientation patterns.", icon: "menu" as const },
];

export default function DesignSystemPage() {
  const { projects, selectedProjectId, setSelectedProjectId } = useAppState();
  return (
    <div className="page-stack">
      <PageHeader eyebrow="Manage" title="Design system" description="Review visual patterns extracted from your project screens." action={<label className="project-picker"><span>Project</span><select value={selectedProjectId} onChange={(event) => setSelectedProjectId(event.target.value)}>{projects.map((project) => <option value={project.id} key={project.id}>{project.name}</option>)}</select></label>} />
      <div className="demo-notice"><span><strong>Not extracted yet</strong> No design patterns have been analysed. The sections below are empty states, not detected project tokens.</span></div>
      <div className="design-system-intro panel">
        <div className="design-system-symbol"><Icon name="layers" size={23} /></div>
        <div><h2>A shared language for better screens</h2><p>Once analysis is connected, this space will collect visual patterns across your project and help identify where screens align or diverge.</p></div>
        <Badge tone="demo">Awaiting analysis</Badge>
      </div>
      <section>
        <SectionTitle title="Pattern library" description="Sections are ready for future design-system extraction." />
        <div className="design-system-grid">{sections.map((section) => (
          <article className="design-system-card" key={section.title}>
            <div className="design-system-card-top"><span className="design-system-card-icon"><Icon name={section.icon} size={19} /></span><Badge>Not available</Badge></div>
            <h3>{section.title}</h3><p>{section.description}</p>
            <div className="design-system-empty"><Icon name="info" size={15} /><span>No extracted patterns yet</span></div>
          </article>
        ))}</div>
      </section>
      <EmptyState icon="spark" title="Run an audit to get started" description="This phase builds the interface only. Screenshot analysis and design-system extraction will be connected in a later phase." action={<Button href="/audits/new" variant="secondary" icon="plus">Create a demo audit</Button>} />
    </div>
  );
}
