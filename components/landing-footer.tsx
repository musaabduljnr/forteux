"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import type { User } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import { Icon } from "./icons";

export function LandingFooter() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => setUser(data.user ?? null));
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  return (
    <footer className="landing-footer-wrapper">
      <div className="landing-footer-container">
        {/* Brand & Description Column */}
        <div className="footer-brand-col">
          <Link href="/" className="landing-brand" aria-label="Forteux home">
            <span className="brand-mark">
              <Icon name="layers" size={20} />
            </span>
            <span className="brand-copy">
              <strong>forteux</strong>
              <small>Design intelligence</small>
            </span>
          </Link>
          <p className="footer-brand-desc">
            AI-powered UI/UX design intelligence and auditing platform. Identify usability problems, extract design systems, and generate Google Stitch redesign prompts.
          </p>
          <div className="footer-security-note">
            <Icon name="info" size={14} />
            <span>Private multi-tenant architecture on Supabase with row-level security.</span>
          </div>
        </div>

        {/* Product Navigation */}
        <div className="footer-link-col">
          <h4>Product</h4>
          <ul>
            <li><a href="#features">Features</a></li>
            <li><a href="#how-it-works">How it works</a></li>
            <li><a href="#multi-screen">Multi-screen analysis</a></li>
            <li><a href="#design-system">Design system extraction</a></li>
            <li><a href="#stitch-workflow">Google Stitch prompts</a></li>
            <li><a href="#faq">FAQ</a></li>
          </ul>
        </div>

        {/* Platform Workspaces */}
        <div className="footer-link-col">
          <h4>Platform</h4>
          <ul>
            <li><Link href="/dashboard">Dashboard</Link></li>
            <li><Link href="/audits/new">New audit</Link></li>
            <li><Link href="/projects">Projects</Link></li>
            <li><Link href="/history">Audit history</Link></li>
            <li><Link href="/exports">Exports center</Link></li>
            <li><Link href="/knowledge">Knowledge library</Link></li>
            <li><Link href="/design-system">Design system</Link></li>
          </ul>
        </div>

        {/* Authentication & Access */}
        <div className="footer-link-col">
          <h4>Access</h4>
          <ul>
            {user ? (
              <>
                <li><Link href="/dashboard">Open Workspace</Link></li>
                <li><Link href="/settings">Account Settings</Link></li>
              </>
            ) : (
              <>
                <li><Link href="/login" className="footer-text-btn">Sign in</Link></li>
                <li><Link href="/register">Start free analysis</Link></li>
              </>
            )}
            <li>
              <span className="footer-muted-item">Protected via Supabase Auth</span>
            </li>
          </ul>
        </div>
      </div>

      <div className="footer-bottom-bar">
        <div className="footer-bottom-container">
          <p className="footer-copyright">
            © 2026 Forteux. All rights reserved.
          </p>
          <div className="footer-meta-tags">
            <span>Next.js 15 App Router</span>
            <span>FastAPI Backend</span>
            <span>Supabase Infrastructure</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
