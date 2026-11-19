import Link from "next/link";
import { Icon } from "./icons";

export function LandingCTA() {
  return (
    <section className="landing-cta-section">
      <div className="landing-cta-card">
        <div className="cta-spark-decor">
          <Icon name="spark" size={32} />
        </div>

        <span className="section-eyebrow cta-eyebrow">START AUDITING TODAY</span>
        <h2 className="landing-cta-heading">
          Your next design decision starts with better insight.
        </h2>
        <p className="landing-cta-subhead">
          Bring your interface, uncover opportunities for improvement and build better digital experiences.
        </p>

        <div className="landing-cta-buttons">
          <Link href="/audits/new" className="button button-primary cta-primary-btn">
            <span>Get started with Forteux</span>
            <Icon name="arrow" size={16} />
          </Link>
          <Link href="/dashboard" className="button button-secondary cta-secondary-btn">
            <span>Explore Demo Workspace</span>
            <Icon name="chevron" size={16} />
          </Link>
        </div>

        <div className="cta-footnote">
          <span><Icon name="check" size={14} /> Instant screenshot analysis</span>
          <span><Icon name="check" size={14} /> Private & isolated storage</span>
          <span><Icon name="check" size={14} /> No credit card required to explore</span>
        </div>
      </div>
    </section>
  );
}
