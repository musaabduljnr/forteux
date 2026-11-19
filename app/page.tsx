import type { Metadata } from "next";
import { LandingNav } from "@/components/landing-nav";
import { LandingHero } from "@/components/landing-hero";
import { LandingFeatures } from "@/components/landing-features";
import { LandingDeepDive } from "@/components/landing-deep-dive";
import { LandingFAQ } from "@/components/landing-faq";
import { LandingCTA } from "@/components/landing-cta";
import { LandingFooter } from "@/components/landing-footer";

export const metadata: Metadata = {
  title: "Forteux — AI-Powered UI/UX Design Intelligence",
  description:
    "Analyse interfaces, uncover usability problems, evaluate design consistency and turn AI-powered design insights into actionable improvements with Forteux.",
  openGraph: {
    title: "Forteux — AI-Powered UI/UX Design Intelligence",
    description:
      "Analyse interfaces, uncover usability problems, evaluate design consistency and turn AI-powered design insights into actionable improvements with Forteux.",
    type: "website",
    siteName: "Forteux",
  },
  twitter: {
    card: "summary_large_image",
    title: "Forteux — AI-Powered UI/UX Design Intelligence",
    description:
      "Analyse interfaces, uncover usability problems, evaluate design consistency and turn AI-powered design insights into actionable improvements with Forteux.",
  },
};

export default function PublicLandingPage() {
  return (
    <div className="landing-page">
      <LandingNav />
      <main id="main-content">
        <LandingHero />
        <LandingFeatures />
        <LandingDeepDive />
        <LandingFAQ />
        <LandingCTA />
      </main>
      <LandingFooter />
    </div>
  );
}
