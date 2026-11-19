"use client";

import { useState } from "react";
import Link from "next/link";
import { Icon } from "./icons";
import { Badge } from "./ui";

export function LandingDeepDive() {
  const [copied, setCopied] = useState(false);

  const samplePrompt = `### Google Stitch UI Redesign Specification

**Target Component**: Checkout Progression & Action Hierarchy
**Goal**: Resolve primary call-to-action prominence and touch target clearance.

**Design Tokens**:
- Primary Color: #365690 (--color-primary-base)
- Secondary Surface: #F7F8FA (--color-surface-soft)
- Border Radius: 8px (--radius-md)
- Touch Clearance: 48px min height (WCAG 2.5.5)

**Layout & Styling Directives**:
1. Elevate primary action "Place Order" to a full-width high-contrast solid button.
2. Demote utility actions in header to ghost outline variants.
3. Apply 24px bottom container padding respecting safe-area-inset-bottom.`;

  const handleCopyPrompt = () => {
    void navigator.clipboard.writeText(samplePrompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="landing-deep-dive-sections">
      {/* SECTION E: Multi-Screen Intelligence */}
      <section className="landing-section" id="multi-screen">
        <div className="deep-dive-grid">
          <div className="deep-dive-copy">
            <span className="section-eyebrow">USER JOURNEY INTELLIGENCE</span>
            <h2 className="landing-section-heading">Look beyond individual screens.</h2>
            <p className="deep-dive-lead">
              Great user experiences require harmony across every step of a workflow. Isolated screen audits miss crucial journey friction — button placement drift, typographic shifts, and inconsistent step anchors.
            </p>

            <ul className="deep-dive-checklist">
              <li>
                <div className="check-icon"><Icon name="check" size={16} /></div>
                <div>
                  <strong>Navigation and Action Anchors</strong>
                  <span>Detect when primary buttons shift between bottom, top-right, or floating bars across sequential screens.</span>
                </div>
              </li>
              <li>
                <div className="check-icon"><Icon name="check" size={16} /></div>
                <div>
                  <strong>Component Styling Cohesion</strong>
                  <span>Ensure card containers, inputs, and corner radii remain identical from step 1 to checkout confirmation.</span>
                </div>
              </li>
              <li>
                <div className="check-icon"><Icon name="check" size={16} /></div>
                <div>
                  <strong>Visual Progression Continuity</strong>
                  <span>Validate that progress indicators, step headers, and breadcrumbs orient users predictably.</span>
                </div>
              </li>
            </ul>

            <div className="deep-dive-cta">
              <Link href="/audits/new" className="button button-primary">
                <span>Try multi-screen audit</span>
                <Icon name="arrow" size={14} />
              </Link>
            </div>
          </div>

          {/* Visual: Multi-Screen Journey Sequence Preview */}
          <div className="deep-dive-visual">
            <div className="journey-preview-container">
              <div className="journey-preview-header">
                <span className="journey-pill">3-Screen E-Commerce Journey</span>
                <span className="journey-status">Sequence Verified</span>
              </div>

              <div className="journey-flow-cards">
                {/* Step 1 */}
                <div className="flow-screen-card">
                  <div className="screen-card-top">
                    <span className="screen-step-tag">Step 1</span>
                    <span className="screen-name">Cart</span>
                  </div>
                  <div className="screen-mockup-inner">
                    <div className="mock-bar-top" />
                    <div className="mock-item-block" />
                    <div className="mock-item-block" />
                    <div className="mock-btn-bottom btn-highlight" />
                  </div>
                </div>

                <div className="journey-connector">
                  <Icon name="arrow" size={16} />
                </div>

                {/* Step 2 */}
                <div className="flow-screen-card">
                  <div className="screen-card-top">
                    <span className="screen-step-tag">Step 2</span>
                    <span className="screen-name">Shipping</span>
                  </div>
                  <div className="screen-mockup-inner">
                    <div className="mock-bar-top" />
                    <div className="mock-item-block" />
                    <div className="mock-item-block" />
                    <div className="mock-btn-bottom btn-drifted" />
                  </div>
                </div>

                <div className="journey-connector">
                  <Icon name="arrow" size={16} />
                </div>

                {/* Step 3 */}
                <div className="flow-screen-card">
                  <div className="screen-card-top">
                    <span className="screen-step-tag">Step 3</span>
                    <span className="screen-name">Payment</span>
                  </div>
                  <div className="screen-mockup-inner">
                    <div className="mock-bar-top" />
                    <div className="mock-item-block" />
                    <div className="mock-item-block" />
                    <div className="mock-btn-bottom btn-highlight" />
                  </div>
                </div>
              </div>

              {/* Cross-Screen Finding Banner */}
              <div className="cross-screen-finding-banner">
                <div className="banner-icon-side"><Icon name="warning" size={18} /></div>
                <div className="banner-content">
                  <strong>Cross-Screen Button Drift Detected</strong>
                  <p>Primary CTA switches between full-width bottom bar (Steps 1 & 3) and top-right header anchor (Step 2).</p>
                </div>
                <Badge tone="warning">Medium</Badge>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION F: Design System Intelligence */}
      <section className="landing-section section-alternate" id="design-system">
        <div className="deep-dive-grid deep-dive-reverse">
          <div className="deep-dive-copy">
            <span className="section-eyebrow">DESIGN SYSTEM EXTRACTION</span>
            <h2 className="landing-section-heading">Understand the design system behind your interface.</h2>
            <p className="deep-dive-lead">
              Forteux extracts raw visual evidence from your screenshots, synthesizing color palettes, typographic scales, spacing patterns, and reusable tokens into an exportable design specification.
            </p>

            <div className="design-token-specs">
              <div className="spec-item">
                <span className="spec-label">Color Foundations</span>
                <span className="spec-val">Primary, secondary, surface, background, and status roles</span>
              </div>
              <div className="spec-item">
                <span className="spec-label">Modular Typography</span>
                <span className="spec-val">Scale ratios, font weights, line-height estimates, and headings</span>
              </div>
              <div className="spec-item">
                <span className="spec-label">Spacing & Grids</span>
                <span className="spec-val">4px / 8px base units, card padding, and layout gutters</span>
              </div>
              <div className="spec-item">
                <span className="spec-label">Reproducible Scoring</span>
                <span className="spec-val">0–100 consistency score with granular category breakdown</span>
              </div>
            </div>

            <div className="deep-dive-cta">
              <Link href="/design-system" className="button button-secondary">
                <span>View design system tools</span>
                <Icon name="arrow" size={14} />
              </Link>
            </div>
          </div>

          {/* Visual: Design System Token Preview */}
          <div className="deep-dive-visual">
            <div className="tokens-preview-card">
              <div className="tokens-card-header">
                <div>
                  <span className="preview-label">Extracted Design Foundations</span>
                  <h4>Design Language Specification</h4>
                </div>
                <div className="consistency-gauge">
                  <span className="gauge-score">94</span>
                  <span className="gauge-label">Score / 100</span>
                </div>
              </div>

              {/* Color Swatches */}
              <div className="tokens-section">
                <div className="token-group-title">Color Palette</div>
                <div className="swatch-row">
                  <div className="swatch-item">
                    <span className="swatch-chip" style={{ background: "#365690" }} />
                    <span className="swatch-name">Primary</span>
                    <span className="swatch-hex">#365690</span>
                  </div>
                  <div className="swatch-item">
                    <span className="swatch-chip" style={{ background: "#202532" }} />
                    <span className="swatch-name">Ink</span>
                    <span className="swatch-hex">#202532</span>
                  </div>
                  <div className="swatch-item">
                    <span className="swatch-chip" style={{ background: "#FFFFFF", border: "1px solid #E7E9EE" }} />
                    <span className="swatch-name">Surface</span>
                    <span className="swatch-hex">#FFFFFF</span>
                  </div>
                  <div className="swatch-item">
                    <span className="swatch-chip" style={{ background: "#238263" }} />
                    <span className="swatch-name">Success</span>
                    <span className="swatch-hex">#238263</span>
                  </div>
                </div>
              </div>

              {/* Typography Scale */}
              <div className="tokens-section">
                <div className="token-group-title">Typography Scale (1.25x Ratio)</div>
                <div className="type-sample-row">
                  <div className="type-sample">
                    <span className="type-tag">h1</span>
                    <span className="type-render" style={{ fontSize: "20px", fontWeight: 700 }}>Heading Title (28px / 700)</span>
                  </div>
                  <div className="type-sample">
                    <span className="type-tag">body</span>
                    <span className="type-render" style={{ fontSize: "13px", fontWeight: 400 }}>Standard interface copy (14px / 400)</span>
                  </div>
                </div>
              </div>

              {/* CSS Token Export Snippet */}
              <div className="tokens-section">
                <div className="token-group-title">CSS Variables Output</div>
                <pre className="code-snippet-preview">
                  <code>
{`:root {
  --color-primary-base: #365690;
  --color-surface: #FFFFFF;
  --space-base-unit: 8px;
  --radius-cards: 8px;
}`}
                  </code>
                </pre>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION G: Stitch Workflow */}
      <section className="landing-section" id="stitch-workflow">
        <div className="deep-dive-grid">
          <div className="deep-dive-copy">
            <span className="section-eyebrow">REDESIGN PROMPT SYNTHESIS</span>
            <h2 className="landing-section-heading">Turn design insights into your next iteration.</h2>
            <p className="deep-dive-lead">
              Bridge the gap between audit findings and rapid redesign prototyping. Forteux transforms selected issues into structured markdown specifications optimized for Google Stitch.
            </p>

            <div className="stitch-feature-list">
              <div className="stitch-feature-item">
                <span className="stitch-feature-icon"><Icon name="check" size={16} /></span>
                <div>
                  <strong>Curate Your Redesign Scope</strong>
                  <p>Select specific findings or prioritize high-severity usability issues for your redesign iteration.</p>
                </div>
              </div>
              <div className="stitch-feature-item">
                <span className="stitch-feature-icon"><Icon name="check" size={16} /></span>
                <div>
                  <strong>Preserve Design Constraints</strong>
                  <p>Prompts instruct Google Stitch to maintain established layout anchors, color tokens, and accessibility baselines.</p>
                </div>
              </div>
              <div className="stitch-feature-item">
                <span className="stitch-feature-icon"><Icon name="check" size={16} /></span>
                <div>
                  <strong>Copy-and-Handoff Workflow</strong>
                  <p>Generate copy-ready markdown prompts to paste directly into Google Stitch or your team&apos;s design agent.</p>
                </div>
              </div>
            </div>

            <div className="deep-dive-cta">
              <Link href="/audits/new" className="button button-primary">
                <span>Start creating prompts</span>
                <Icon name="arrow" size={14} />
              </Link>
            </div>
          </div>

          {/* Visual: Generated Stitch Prompt Card */}
          <div className="deep-dive-visual">
            <div className="stitch-prompt-preview-card">
              <div className="prompt-card-header">
                <div className="prompt-header-title">
                  <Icon name="spark" size={16} />
                  <span>Generated Stitch Specification</span>
                </div>
                <button
                  type="button"
                  onClick={handleCopyPrompt}
                  className="button button-secondary button-small"
                  aria-label="Copy prompt to clipboard"
                >
                  <Icon name={copied ? "check" : "copy"} size={13} />
                  <span>{copied ? "Copied!" : "Copy prompt"}</span>
                </button>
              </div>

              <div className="prompt-preview-content">
                <div className="prompt-chip-selection">
                  <span className="prompt-chip active">✓ Primary Action Prominence</span>
                  <span className="prompt-chip active">✓ Touch Target 48dp</span>
                  <span className="prompt-chip">✕ Secondary Contrast (Deselected)</span>
                </div>

                <div className="prompt-body-block">
                  <pre>
                    <code>{samplePrompt}</code>
                  </pre>
                </div>
              </div>

              <div className="prompt-card-footer">
                <span className="prompt-footer-note">
                  <Icon name="info" size={13} />
                  Ready to paste into Google Stitch for automated component and layout generation.
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
