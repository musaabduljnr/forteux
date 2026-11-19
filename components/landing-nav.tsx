"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import type { User } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import { Icon } from "./icons";

export function LandingNav() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
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
    <header className="landing-nav-wrapper">
      <div className="landing-nav-container">
        <Link href="/" className="landing-brand" aria-label="Forteux home">
          <span className="brand-mark">
            <Icon name="layers" size={20} />
          </span>
          <span className="brand-copy">
            <strong>forteux</strong>
            <small>Design intelligence</small>
          </span>
        </Link>

        {/* Desktop Navigation */}
        <nav className="landing-nav-links" aria-label="Landing page navigation">
          <a href="#product" className="landing-nav-item">Product</a>
          <a href="#how-it-works" className="landing-nav-item">How it works</a>
          <a href="#features" className="landing-nav-item">Features</a>
          <a href="#faq" className="landing-nav-item">FAQ</a>
        </nav>

        {/* Desktop Actions */}
        <div className="landing-nav-actions">
          {user ? (
            <Link href="/dashboard" className="button button-primary">
              <Icon name="dashboard" size={16} />
              <span>Go to Dashboard</span>
            </Link>
          ) : (
            <>
              <Link href="/login" className="button button-ghost landing-login-btn">
                Log in
              </Link>
              <Link href="/register" className="button button-primary landing-start-btn">
                <span>Get started</span>
                <Icon name="arrow" size={14} />
              </Link>
            </>
          )}
        </div>

        {/* Mobile Hamburger Toggle */}
        <button
          type="button"
          className="icon-button landing-mobile-toggle"
          aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileMenuOpen}
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          <Icon name={mobileMenuOpen ? "close" : "menu"} size={22} />
        </button>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="landing-mobile-menu" role="dialog" aria-modal="true" aria-label="Mobile Navigation">
          <nav className="landing-mobile-links">
            <a href="#product" onClick={() => setMobileMenuOpen(false)} className="landing-mobile-item">
              Product
            </a>
            <a href="#how-it-works" onClick={() => setMobileMenuOpen(false)} className="landing-mobile-item">
              How it works
            </a>
            <a href="#features" onClick={() => setMobileMenuOpen(false)} className="landing-mobile-item">
              Features
            </a>
            <a href="#faq" onClick={() => setMobileMenuOpen(false)} className="landing-mobile-item">
              FAQ
            </a>
          </nav>
          <div className="landing-mobile-actions">
            {user ? (
              <Link
                href="/dashboard"
                onClick={() => setMobileMenuOpen(false)}
                className="button button-primary full-width-button"
              >
                <Icon name="dashboard" size={16} />
                <span>Go to Dashboard</span>
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="button button-secondary full-width-button"
                >
                  Log in
                </Link>
                <Link
                  href="/register"
                  onClick={() => setMobileMenuOpen(false)}
                  className="button button-primary full-width-button"
                >
                  <span>Get started</span>
                  <Icon name="arrow" size={14} />
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
