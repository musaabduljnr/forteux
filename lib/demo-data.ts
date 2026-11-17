import type { Audit, DetectedIssue, KnowledgeDocument, Project, User } from "./types";

export const demoUser: User = {
  id: "demo-user",
  displayName: "Musa Abubakar",
  email: "musa@example.com",
  role: "Design lead",
  avatarInitials: "MA",
};

export const demoProjects: Project[] = [
  {
    id: "project-northstar",
    name: "Northstar Commerce",
    description: "A considered checkout experience for independent brands.",
    updatedAt: "2026-11-14T09:30:00.000Z",
    status: "Active",
  },
  {
    id: "project-fieldnotes",
    name: "Fieldnotes Mobile",
    description: "Research and planning tools for teams in the field.",
    updatedAt: "2026-11-12T14:10:00.000Z",
    status: "Active",
  },
  {
    id: "project-atlas",
    name: "Atlas Workspace",
    description: "An internal knowledge workspace concept.",
    updatedAt: "2026-11-08T11:00:00.000Z",
    status: "Archived",
  },
];

export const demoIssues: DetectedIssue[] = [
  {
    id: "fixture-issue-1",
    number: 1,
    title: "Primary action competes with secondary links",
    category: "Visual hierarchy",
    severity: "high",
    confidence: 0.91,
    description: "The main continue action and secondary navigation have similar visual emphasis.",
    whyItMatters: "People may have to pause to determine the intended next step.",
    recommendation: "Give the primary action a clearer visual priority while keeping secondary links quieter.",
    evidenceClass: "demonstration",
    certainty: "suspected",
    screenIds: ["fixture-screen"],
    boundingBoxes: [{ screenId: "fixture-screen", box: { x: 0.57, y: 0.76, width: 0.26, height: 0.08 } }],
    selected: true,
  },
  {
    id: "fixture-issue-2",
    number: 2,
    title: "Order summary is visually detached",
    category: "Layout and spacing",
    severity: "medium",
    confidence: 0.84,
    description: "The total appears far from the item details in this illustrative layout.",
    whyItMatters: "A separated total can make it harder to verify the amount before continuing.",
    recommendation: "Group the total and item details into one clearly related summary region.",
    evidenceClass: "demonstration",
    certainty: "suspected",
    screenIds: ["fixture-screen"],
    boundingBoxes: [{ screenId: "fixture-screen", box: { x: 0.58, y: 0.41, width: 0.24, height: 0.13 } }],
    selected: true,
  },
];

export const demoAudits: Audit[] = [
  {
    id: "demo-audit",
    projectId: "project-northstar",
    name: "Checkout — illustrative workspace",
    mode: "single",
    status: "demo",
    createdAt: "2026-11-15T10:20:00.000Z",
    screens: [
      {
        id: "fixture-screen",
        name: "Checkout",
        fileName: "illustrative-checkout.svg",
        mimeType: "image/svg+xml",
        fileSize: 0,
        previewUrl: "/demo-checkout.svg",
      },
    ],
    issues: demoIssues,
    isDemo: true,
  },
  {
    id: "demo-flow",
    projectId: "project-fieldnotes",
    name: "Field planning flow — sample",
    mode: "multi",
    status: "demo",
    createdAt: "2026-11-13T08:45:00.000Z",
    screens: [
      { id: "flow-1", name: "Project overview", fileName: "sample-01.png", mimeType: "image/png", fileSize: 0 },
      { id: "flow-2", name: "Create a plan", fileName: "sample-02.png", mimeType: "image/png", fileSize: 0 },
      { id: "flow-3", name: "Plan saved", fileName: "sample-03.png", mimeType: "image/png", fileSize: 0 },
    ],
    issues: [
      {
        id: "fixture-flow-issue-1",
        number: 1,
        title: "Progress indicator changes treatment",
        category: "Cross-screen consistency",
        severity: "medium",
        confidence: 0.79,
        description: "The illustrative progress cue uses different styling between the first and second supplied screens.",
        whyItMatters: "A shifting progress pattern may make it harder to understand where a person is in the example journey.",
        recommendation: "Use a consistent progress treatment and clearly indicate the current step on each screen.",
        evidenceClass: "demonstration",
        certainty: "suspected",
        screenIds: ["flow-1", "flow-2"],
        boundingBoxes: [
          { screenId: "flow-1", box: { x: 0.12, y: 0.12, width: 0.74, height: 0.09 } },
          { screenId: "flow-2", box: { x: 0.12, y: 0.12, width: 0.74, height: 0.09 } },
        ],
        selected: true,
      },
      {
        id: "fixture-flow-issue-2",
        number: 2,
        title: "Confirmation feedback is not shown in the sample sequence",
        category: "Flow",
        severity: "low",
        confidence: 0.62,
        description: "The supplied illustrative sequence does not show a visible confirmation state after the planning step.",
        whyItMatters: "People may benefit from visible reassurance that their action was received.",
        recommendation: "Consider a clear confirmation state, if one is not already provided outside these supplied screens.",
        evidenceClass: "demonstration",
        certainty: "suspected",
        screenIds: ["flow-2", "flow-3"],
        boundingBoxes: [],
        selected: true,
      },
    ],
    isDemo: true,
  },
];

export const demoKnowledge: KnowledgeDocument[] = [
  {
    id: "knowledge-example-1",
    name: "Product design principles.pdf",
    type: "PDF",
    size: 2_400_000,
    updatedAt: "2026-11-10T12:15:00.000Z",
    status: "ready",
    scope: "Project",
    projectId: "project-northstar",
    category: "Design principles",
    pages: 18,
    description: "Example project reference (illustrative, not uploaded content).",
    isDemo: true,
  },
  {
    id: "knowledge-example-4",
    name: "Navigation patterns.txt",
    type: "TXT",
    size: 12_600,
    updatedAt: "2026-11-06T10:00:00.000Z",
    status: "failed",
    scope: "Global",
    category: "Navigation",
    pages: 0,
    description: "Example processing error: text extraction returned no usable content. Retry is unavailable in this frontend demo.",
    isDemo: true,
  },
  {
    id: "knowledge-example-2",
    name: "Accessibility checklist.md",
    type: "Markdown",
    size: 18_400,
    updatedAt: "2026-11-09T15:40:00.000Z",
    status: "ready",
    scope: "Global",
    category: "Accessibility",
    pages: 4,
    description: "Example global reference (illustrative, not uploaded content).",
    isDemo: true,
  },
  {
    id: "knowledge-example-3",
    name: "Brand guidelines.docx",
    type: "DOCX",
    size: 860_000,
    updatedAt: "2026-11-08T09:05:00.000Z",
    status: "processing",
    scope: "Project",
    projectId: "project-fieldnotes",
    category: "Brand",
    pages: 0,
    isDemo: true,
  },
];

export function formatDate(date: string): string {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(date));
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
