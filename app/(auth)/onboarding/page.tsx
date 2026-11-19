"use client";

import { useState, useEffect, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

const ROLES = [
  { value: "ui_ux_designer", label: "UI/UX Designer" },
  { value: "product_designer", label: "Product Designer" },
  { value: "product_manager", label: "Product Manager" },
  { value: "frontend_developer", label: "Frontend Developer" },
  { value: "design_agency", label: "Design Agency" },
  { value: "other", label: "Other" },
];

const INTENDED_USES = [
  { value: "audit_interfaces", label: "Audit interface designs" },
  { value: "improve_ux", label: "Identify and resolve UX issues" },
  { value: "multiscreen_analysis", label: "Analyse multi-screen journeys" },
  { value: "design_systems", label: "Extract design systems" },
  { value: "stitch_prompts", label: "Generate Google Stitch redesign prompts" },
  { value: "knowledge_resources", label: "Use design knowledge documents" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const supabase = createClient();

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);

  // Form state
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("");
  const [intendedUse, setIntendedUse] = useState<string[]>([]);

  // Prefill from Google metadata
  useEffect(() => {
    async function prefill() {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        router.push("/login");
        return;
      }
      // Check if already onboarded
      const { data: profile } = await supabase
        .from("profiles")
        .select("onboarding_completed, full_name, role")
        .eq("id", user.id)
        .single();

      if (profile?.onboarding_completed) {
        router.push("/dashboard");
        return;
      }

      // Pre-fill from auth metadata or existing profile
      const metaName = user.user_metadata?.full_name || user.user_metadata?.name || "";
      setFullName(profile?.full_name || metaName);
      if (profile?.role) setRole(profile.role);
      setInitialLoading(false);
    }
    prefill();
  }, [supabase, router]);

  function toggleIntendedUse(value: string) {
    setIntendedUse((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  }

  async function completeOnboarding() {
    setLoading(true);
    setError(null);

    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      setError("Session expired. Please sign in again.");
      setLoading(false);
      return;
    }

    const { error: upsertError } = await supabase.from("profiles").upsert({
      id: user.id,
      full_name: fullName,
      email: user.email,
      role,
      intended_use: intendedUse,
      onboarding_completed: true,
      onboarding_completed_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    if (upsertError) {
      setError(upsertError.message);
      setLoading(false);
      return;
    }

    router.push("/dashboard");
    router.refresh();
  }

  if (initialLoading) {
    return (
      <div className="auth-page">
        <div className="auth-card auth-card-center">
          <span className="auth-spinner auth-spinner-lg" aria-label="Loading…" />
        </div>
      </div>
    );
  }

  const totalSteps = 4;
  const progress = (step / totalSteps) * 100;

  return (
    <div className="auth-page">
      <div className="auth-card auth-card-wide">
        {/* Brand */}
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

        {/* Progress */}
        <div className="onboarding-progress" aria-label={`Step ${step} of ${totalSteps}`}>
          <div className="onboarding-progress-bar">
            <div className="onboarding-progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <span className="onboarding-step-label">Step {step} of {totalSteps}</span>
        </div>

        {error && (
          <div className="auth-alert auth-alert-error" role="alert">
            {error}
          </div>
        )}

        {/* Step 1: Name */}
        {step === 1 && (
          <div className="onboarding-step">
            <div className="auth-header">
              <h1>What should we call you?</h1>
              <p>This name will appear across your Forteux workspace.</p>
            </div>
            <form
              className="auth-form"
              onSubmit={(e: FormEvent) => { e.preventDefault(); if (fullName.trim()) setStep(2); }}
            >
              <div className="auth-field">
                <label htmlFor="fullName">Full name</label>
                <input
                  id="fullName"
                  type="text"
                  autoComplete="name"
                  required
                  placeholder="Alex Johnson"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  autoFocus
                />
              </div>
              <button
                type="submit"
                className="auth-submit-button"
                disabled={!fullName.trim()}
              >
                Continue
              </button>
            </form>
          </div>
        )}

        {/* Step 2: Role */}
        {step === 2 && (
          <div className="onboarding-step">
            <div className="auth-header">
              <h1>What best describes your role?</h1>
              <p>This helps us tailor your Forteux experience.</p>
            </div>
            <div className="onboarding-grid">
              {ROLES.map((r) => (
                <button
                  key={r.value}
                  type="button"
                  className={`onboarding-option ${role === r.value ? "onboarding-option-selected" : ""}`}
                  onClick={() => setRole(r.value)}
                >
                  {r.label}
                </button>
              ))}
            </div>
            <div className="onboarding-actions">
              <button
                type="button"
                className="auth-secondary-button"
                onClick={() => setStep(1)}
              >
                Back
              </button>
              <button
                type="button"
                className="auth-submit-button"
                disabled={!role}
                onClick={() => setStep(3)}
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Intended use */}
        {step === 3 && (
          <div className="onboarding-step">
            <div className="auth-header">
              <h1>How will you use Forteux?</h1>
              <p>Select everything that applies — you can change this later.</p>
            </div>
            <div className="onboarding-grid">
              {INTENDED_USES.map((u) => (
                <button
                  key={u.value}
                  type="button"
                  className={`onboarding-option ${intendedUse.includes(u.value) ? "onboarding-option-selected" : ""}`}
                  onClick={() => toggleIntendedUse(u.value)}
                >
                  {u.label}
                </button>
              ))}
            </div>
            <div className="onboarding-actions">
              <button
                type="button"
                className="auth-secondary-button"
                onClick={() => setStep(2)}
              >
                Back
              </button>
              <button
                type="button"
                className="auth-submit-button"
                onClick={() => setStep(4)}
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Completion */}
        {step === 4 && (
          <div className="onboarding-step onboarding-complete">
            <div className="onboarding-complete-icon" aria-hidden="true">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </div>
            <div className="auth-header">
              <h1>You&apos;re all set, {fullName.split(" ")[0] || "there"}.</h1>
              <p>
                Your workspace is ready. Start by uploading a screenshot and running your first audit.
              </p>
            </div>
            <div className="onboarding-summary">
              <div className="onboarding-summary-item">
                <span className="onboarding-summary-label">Name</span>
                <span>{fullName}</span>
              </div>
              <div className="onboarding-summary-item">
                <span className="onboarding-summary-label">Role</span>
                <span>{ROLES.find((r) => r.value === role)?.label || "—"}</span>
              </div>
              {intendedUse.length > 0 && (
                <div className="onboarding-summary-item">
                  <span className="onboarding-summary-label">Focus areas</span>
                  <span>{intendedUse.length} selected</span>
                </div>
              )}
            </div>
            <div className="onboarding-actions">
              <button
                type="button"
                className="auth-secondary-button"
                onClick={() => setStep(3)}
              >
                Back
              </button>
              <button
                type="button"
                className="auth-submit-button"
                disabled={loading}
                onClick={completeOnboarding}
              >
                {loading ? <span className="auth-spinner" aria-hidden="true" /> : null}
                Go to dashboard
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
