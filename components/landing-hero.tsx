"use client";

import { useState } from "react";
import Link from "next/link";
import { Icon } from "./icons";
import { Badge, SeverityBadge } from "./ui";

export function LandingHero() {
  const [activeFinding, setActiveFinding] = useState<number>(0);

  const sampleFindings = [
    {
      id: "f-1",
      category: "Visual Hierarchy",
      title: "Primary Action Competes with Utility Controls",
      severity: "high" as const,
      confidence: 0.88,
      evidence: "Three adjacent header buttons share identical #365690 fill and 8px border radius.",
      fix: "Demote secondary actions to outline variants; reserve solid primary fill for the checkout trigger.",
      principle: "Hick's Law & Visual Prominence",
      box: { x: 62, y: 8, width: 34, height: 12 },
    },
    {
      id: "f-2",
      category: "Touch Target & Safe Area",
      title: "Bottom Action Clearance Violates 48dp Standard",
      severity: "critical" as const,
      confidence: 0.94,
      evidence: "Bottom container padding is 12px; touch zone overlaps iOS home indicator gesture.",
      fix: "Enforce env(safe-area-inset-bottom) with a minimum 48px interactive touch clearance.",
      principle: "Fitts's Law & Touch Accessibility (WCAG 2.5.5)",
      box: { x: 8, y: 78, width: 84, height: 16 },
    },
    {
      id: "f-3",
      category: "Typography",
      title: "Subheading Lacks Modular Scale Separation",
      severity: "medium" as const,
      confidence: 0.82,
      evidence: "14px caption text placed directly adjacent to 15px section label.",
      fix: "Establish a minimum 1.25x scale step between section headings and supporting body text.",
      principle: "Typographic Hierarchy & Scanning Efficiency",
      box: { x: 8, y: 32, width: 50, height: 14 },
    },
  ];

  const current = sampleFindings[activeFinding];

  return (
    <section className="landing-hero" id="hero">
      <div className="landing-hero-content">
        <div className="landing-eyebrow">
          <span className="eyebrow-pill">
            <Icon name="spark" size={14} />
            <span>AI-POWERED DESIGN INTELLIGENCE</span>
          </span>
        </div>

        <h1 className="landing-hero-headline">
          Design better interfaces.<br className="desktop-break" />
          Back every decision with insight.
        </h1>

        <p className="landing-hero-subhead">
          Analyse your interfaces, uncover usability problems and turn design insights into actionable improvements with AI-powered design intelligence.
        </p>

        <div className="landing-hero-ctas">
          <Link href="/audits/new" className="button button-primary hero-primary-btn">
            <span>Start analysing</span>
            <Icon name="arrow" size={16} />
          </Link>
          <a href="#how-it-works" className="button button-secondary hero-secondary-btn">
            <span>Explore the platform</span>
            <Icon name="chevron" size={16} />
          </a>
        </div>

        {/* Feature quick badges */}
        <div className="landing-hero-pills">
          <span className="hero-feature-tag"><Icon name="check" size={14} /> Screen Bounding Boxes</span>
          <span className="hero-feature-tag"><Icon name="check" size={14} /> Multi-Screen User Flows</span>
          <span className="hero-feature-tag"><Icon name="check" size={14} /> Design System Extraction</span>
          <span className="hero-feature-tag"><Icon name="check" size={14} /> Google Stitch Redesign Prompts</span>
        </div>
      </div>

      {/* Hero Visual: Interactive Mockup Canvas */}
      <div className="landing-hero-visual-wrapper" id="product">
        <div className="landing-mockup-browser">
          {/* Mockup Top Window Chrome */}
          <div className="mockup-window-header">
            <div className="mockup-window-dots">
              <span className="window-dot dot-red" />
              <span className="window-dot dot-yellow" />
              <span className="window-dot dot-green" />
            </div>
            <div className="mockup-address-bar">
              <Icon name="eye" size={13} />
              <span>forteux.ai/audits/checkout-flow-v2</span>
            </div>
            <div className="mockup-header-stats">
              <Badge tone="demo">Demo Workspace</Badge>
            </div>
          </div>

          {/* Mockup Workspace Body */}
          <div className="mockup-workspace-grid">
            {/* Left: Simulated Screenshot Canvas with Real Bounding Box Overlays */}
            <div className="mockup-canvas-pane">
              <div className="mockup-canvas-toolbar">
                <span className="canvas-badge">Mobile Checkout (390 x 844px)</span>
                <span className="canvas-zoom">100%</span>
              </div>

              <div className="mockup-screen-container">
                {/* Simulated Mobile Screen Content */}
                <div className="simulated-app-screen">
                  {/* App Header */}
                  <div className="sim-header">
                    <span className="sim-title">Checkout</span>
                    <div className="sim-header-actions">
                      <span className="sim-btn-action">Cancel</span>
                      <span className="sim-btn-action sim-btn-primary">Continue</span>
                    </div>
                  </div>

                  {/* App Content Body */}
                  <div className="sim-body">
                    <div className="sim-card">
                      <div className="sim-label">Delivery Address</div>
                      <div className="sim-subtext">Flat 4B, King&apos;s Cross Road, London</div>
                    </div>

                    <div className="sim-card">
                      <div className="sim-label">Payment Method</div>
                      <div className="sim-subtext">Visa ending in 4242 · Exp 12/28</div>
                    </div>

                    <div className="sim-card">
                      <div className="sim-label">Order Summary</div>
                      <div className="sim-subtext">2 items · Subtotal £128.00 · Free delivery</div>
                    </div>
                  </div>

                  {/* App Bottom Safe Area */}
                  <div className="sim-bottom-bar">
                    <button type="button" className="sim-pay-button">Place order (£128.00)</button>
                  </div>
                </div>

                {/* Overlaid Bounding Boxes */}
                {sampleFindings.map((finding, idx) => {
                  const isSelected = activeFinding === idx;
                  return (
                    <button
                      key={finding.id}
                      type="button"
                      onClick={() => setActiveFinding(idx)}
                      className={`hero-bounding-box box-${finding.severity} ${isSelected ? "box-selected" : ""}`}
                      style={{
                        left: `${finding.box.x}%`,
                        top: `${finding.box.y}%`,
                        width: `${finding.box.width}%`,
                        height: `${finding.box.height}%`,
                      }}
                      aria-label={`Select finding: ${finding.title}`}
                    >
                      <span className="box-tag">#{idx + 1} {finding.severity}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Right: Interactive Finding Inspector */}
            <div className="mockup-inspector-pane">
              <div className="inspector-header">
                <div>
                  <span className="inspector-eyebrow">AI Finding Inspector</span>
                  <h3>Detected Issues ({sampleFindings.length})</h3>
                </div>
                <Badge tone="blue">{Math.round(current.confidence * 100)}% match</Badge>
              </div>

              {/* Finding Selection Tabs */}
              <div className="inspector-tabs" role="tablist">
                {sampleFindings.map((finding, idx) => (
                  <button
                    key={finding.id}
                    type="button"
                    role="tab"
                    aria-selected={activeFinding === idx}
                    onClick={() => setActiveFinding(idx)}
                    className={`inspector-tab-item ${activeFinding === idx ? "tab-active" : ""}`}
                  >
                    <span className={`tab-num num-${finding.severity}`}>{idx + 1}</span>
                    <span className="tab-title">{finding.category}</span>
                  </button>
                ))}
              </div>

              {/* Active Finding Card */}
              <div className="inspector-card">
                <div className="inspector-card-heading">
                  <SeverityBadge severity={current.severity} />
                  <span className="inspector-finding-id">ID: {current.id}</span>
                </div>

                <h4 className="inspector-finding-title">{current.title}</h4>

                <div className="inspector-block">
                  <div className="block-label"><Icon name="eye" size={13} /> Visible Evidence</div>
                  <p className="block-text">{current.evidence}</p>
                </div>

                <div className="inspector-block">
                  <div className="block-label"><Icon name="spark" size={13} /> Recommended Fix</div>
                  <p className="block-text fix-highlight">{current.fix}</p>
                </div>

                <div className="inspector-block">
                  <div className="block-label"><Icon name="book" size={13} /> Design Standard Reference</div>
                  <span className="principle-pill">{current.principle}</span>
                </div>

                <div className="inspector-actions">
                  <Link href="/audits/new" className="button button-primary button-small full-width-button">
                    <span>Audit your interface with Forteux</span>
                    <Icon name="arrow" size={13} />
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
