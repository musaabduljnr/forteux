"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const supabase = createClient();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });

    // Always show success — do not reveal whether the email exists
    setSubmitted(true);
    setLoading(false);
  }

  if (submitted) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <div className="auth-brand">
            <span className="auth-brand-mark">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5"/>
                <path d="M2 12l10 5 10-5"/>
              </svg>
            </span>
            <span className="auth-brand-name">forteux</span>
          </div>
          <div className="auth-header">
            <h1>Check your email</h1>
            <p>
              If an account exists for <strong>{email}</strong>, you&apos;ll receive
              a link to reset your password within a few minutes.
            </p>
          </div>
          <div className="auth-alert auth-alert-info" role="status">
            Check your spam folder if you don&apos;t see the email.
          </div>
          <p className="auth-footer-text">
            <Link href="/login">Back to sign in</Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <span className="auth-brand-mark">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </span>
          <span className="auth-brand-name">forteux</span>
        </div>

        <div className="auth-header">
          <h1>Reset your password</h1>
          <p>Enter your email and we&apos;ll send you a secure reset link.</p>
        </div>

        {error && (
          <div className="auth-alert auth-alert-error" role="alert">
            {error}
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <div className="auth-field">
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
            />
          </div>

          <button type="submit" className="auth-submit-button" disabled={loading}>
            {loading ? <span className="auth-spinner" aria-hidden="true" /> : null}
            Send reset link
          </button>
        </form>

        <p className="auth-footer-text">
          Remembered it?{" "}
          <Link href="/login">Back to sign in</Link>
        </p>
      </div>
    </div>
  );
}
