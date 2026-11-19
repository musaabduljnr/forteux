import { Icon, type IconName } from "./icons";

interface FeatureCard {
  id: string;
  title: string;
  description: string;
  icon: IconName;
  tag: string;
}

const valueProps: FeatureCard[] = [
  {
    id: "prop-1",
    title: "AI Interface Auditing",
    description: "Analyse interface screenshots and identify potential usability and visual design problems with pixel-level precision.",
    icon: "eye",
    tag: "Vision Analysis",
  },
  {
    id: "prop-2",
    title: "Evidence-Based Findings",
    description: "Review findings with transparent descriptions, severity classification, confidence scores, and bounding-box indicators.",
    icon: "warning",
    tag: "Visual Proof",
  },
  {
    id: "prop-3",
    title: "Multi-Screen Analysis",
    description: "Evaluate user flow continuity, button placement drift, and visual consistency across complete multi-step journeys.",
    icon: "grid",
    tag: "User Flows",
  },
  {
    id: "prop-4",
    title: "Design System Intelligence",
    description: "Extract visual foundations, color palettes, modular typography, spacing scales, and reusable component tokens.",
    icon: "layers",
    tag: "Tokens & Tokens",
  },
  {
    id: "prop-5",
    title: "Knowledge-Assisted Recommendations",
    description: "Upload internal design systems or guidelines (PDF/DOCX/MD) to ground audit findings in contextual heuristics.",
    icon: "book",
    tag: "RAG Knowledge",
  },
  {
    id: "prop-6",
    title: "Stitch Prompt Generation",
    description: "Turn selected findings into structured markdown prompts with layout rules and tokens ready for Google Stitch.",
    icon: "spark",
    tag: "Redesign Handoff",
  },
];

const workflowSteps = [
  {
    number: "01",
    title: "Upload your interface",
    description: "Upload one or more interface screenshots across mobile, tablet, or desktop viewports.",
    icon: "upload" as IconName,
  },
  {
    number: "02",
    title: "Analyse with AI",
    description: "Forteux evaluates the interface and identifies potential design, usability, and hierarchy issues.",
    icon: "spark" as IconName,
  },
  {
    number: "03",
    title: "Review insights",
    description: "Inspect visual bounding boxes, severity ratings, observable evidence, and recommended fixes.",
    icon: "eye" as IconName,
  },
  {
    number: "04",
    title: "Generate redesign prompts",
    description: "Select findings and generate a comprehensive redesign prompt optimized for Google Stitch.",
    icon: "file" as IconName,
  },
];

export function LandingFeatures() {
  return (
    <>
      {/* SECTION C: Product Value Proposition */}
      <section className="landing-section" id="features">
        <div className="landing-section-header">
          <span className="section-eyebrow">CAPABILITIES</span>
          <h2 className="landing-section-heading">Everything you need to improve your interface.</h2>
          <p className="landing-section-subhead">
            Comprehensive AI analysis designed specifically for user experience, interface hierarchy, and design system governance.
          </p>
        </div>

        <div className="landing-bento-grid">
          {valueProps.map((card) => (
            <article key={card.id} className="bento-card">
              <div className="bento-card-top">
                <span className="bento-icon-wrapper">
                  <Icon name={card.icon} size={20} />
                </span>
                <span className="bento-tag">{card.tag}</span>
              </div>
              <h3 className="bento-title">{card.title}</h3>
              <p className="bento-description">{card.description}</p>
            </article>
          ))}
        </div>
      </section>

      {/* SECTION D: How It Works */}
      <section className="landing-section section-alternate" id="how-it-works">
        <div className="landing-section-header">
          <span className="section-eyebrow">PROCESS</span>
          <h2 className="landing-section-heading">From screenshots to actionable design improvements.</h2>
          <p className="landing-section-subhead">
            A straightforward workflow designed to fit directly into your existing product design cycle.
          </p>
        </div>

        <div className="landing-steps-grid">
          {workflowSteps.map((step) => (
            <div key={step.number} className="workflow-step-card">
              <div className="step-number-row">
                <span className="step-number">{step.number}</span>
                <span className="step-icon">
                  <Icon name={step.icon} size={18} />
                </span>
              </div>
              <h3 className="step-title">{step.title}</h3>
              <p className="step-description">{step.description}</p>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
