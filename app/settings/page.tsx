"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { User } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import { useAppState } from "@/components/app-state";
import { Icon } from "@/components/icons";
import { Button, PageHeader, SectionTitle } from "@/components/ui";

type Theme = "light" | "dark" | "system";

const ROLES = [
  { value: "ui_ux_designer", label: "UI/UX Designer" },
  { value: "product_designer", label: "Product Designer" },
  { value: "product_manager", label: "Product Manager" },
  { value: "frontend_developer", label: "Frontend Developer" },
  { value: "design_agency", label: "Design Agency" },
  { value: "other", label: "Other" },
];

export default function SettingsPage() {
  const router = useRouter();
  const { notify, selectedProjectId, setSelectedProjectId, projects, user: appUser, updateUser } = useAppState();

  const [supabaseUser, setSupabaseUser] = useState<User | null>(null);
  const [profileRole, setProfileRole] = useState("ui_ux_designer");
  const [theme, setTheme] = useState<Theme>("light");
  const [analysisMode, setAnalysisMode] = useState("single");
  const [displayName, setDisplayName] = useState(appUser.displayName);
  const [email, setEmail] = useState(appUser.email);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordUpdating, setPasswordUpdating] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [includeGlobal, setIncludeGlobal] = useState(true);
  const [includeProject, setIncludeProject] = useState(true);
  const [emailUpdates, setEmailUpdates] = useState(false);

  const supabase = createClient();

  useEffect(() => {
    async function loadUser() {
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        setSupabaseUser(user);
        setEmail(user.email || "");
        const name = user.user_metadata?.full_name || user.user_metadata?.name || user.email?.split("@")[0] || "";
        if (name) setDisplayName(name);

        const { data: profile } = await supabase
          .from("profiles")
          .select("full_name, role")
          .eq("id", user.id)
          .single();

        if (profile?.full_name) setDisplayName(profile.full_name);
        if (profile?.role) setProfileRole(profile.role);
      }
    }
    loadUser();

    const savedTheme = window.localStorage.getItem("forteux-theme") as Theme | null;
    if (savedTheme === "light" || savedTheme === "dark" || savedTheme === "system") setTheme(savedTheme);
    const savedMode = window.localStorage.getItem("forteux-default-audit-mode");
    if (savedMode === "single" || savedMode === "multi") setAnalysisMode(savedMode);
    const savedGlobalKnowledge = window.localStorage.getItem("forteux-preference-global-knowledge");
    const savedProjectKnowledge = window.localStorage.getItem("forteux-preference-project-knowledge");
    const savedEmailUpdates = window.localStorage.getItem("forteux-preference-email-updates");
    if (savedGlobalKnowledge !== null) setIncludeGlobal(savedGlobalKnowledge === "true");
    if (savedProjectKnowledge !== null) setIncludeProject(savedProjectKnowledge === "true");
    if (savedEmailUpdates !== null) setEmailUpdates(savedEmailUpdates === "true");
  }, [supabase]);

  useEffect(() => {
    const effectiveTheme = theme === "system"
      ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
      : theme;
    document.documentElement.dataset.theme = effectiveTheme;
    window.localStorage.setItem("forteux-theme", theme);
  }, [theme]);

  function updatePreference(message: string) {
    notify(message, "success");
  }

  async function handleSaveProfile() {
    setProfileSaving(true);
    if (supabaseUser) {
      await supabase.from("profiles").upsert({
        id: supabaseUser.id,
        full_name: displayName.trim(),
        role: profileRole,
        updated_at: new Date().toISOString(),
      });
      await supabase.auth.updateUser({
        data: { full_name: displayName.trim() },
      });
    }
    updateUser({ displayName: displayName.trim(), email: email.trim() });
    setProfileSaving(false);
    notify("Profile updated successfully.", "success");
  }

  async function handlePasswordUpdate() {
    if (!newPassword || newPassword !== confirmPassword) {
      notify("Passwords do not match.", "error");
      return;
    }
    if (newPassword.length < 8) {
      notify("Password must be at least 8 characters long.", "error");
      return;
    }
    setPasswordUpdating(true);
    const { error } = await supabase.auth.updateUser({ password: newPassword });
    setPasswordUpdating(false);
    if (error) {
      notify(error.message, "error");
    } else {
      setNewPassword("");
      setConfirmPassword("");
      notify("Password updated successfully.", "success");
    }
  }

  async function handleSignOut() {
    await supabase.auth.signOut();
    notify("Signed out successfully.", "info");
    router.push("/login");
    router.refresh();
  }

  const authProvider = supabaseUser?.app_metadata?.provider || (supabaseUser ? "Email / Password" : "Local demo");

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Manage"
        title="Settings"
        description="Manage your profile, authentication, and workspace preferences."
      />

      <div className="settings-layout">
        <nav className="settings-nav" aria-label="Settings sections">
          <a href="#profile" className="settings-nav-active"><Icon name="dashboard" size={17} />Profile</a>
          <a href="#appearance"><Icon name="layers" size={17} />Appearance</a>
          <a href="#security"><Icon name="settings" size={17} />Security & Auth</a>
          <a href="#ai-preferences"><Icon name="spark" size={17} />AI preferences</a>
          <a href="#knowledge-preferences"><Icon name="book" size={17} />Knowledge</a>
        </nav>

        <div className="settings-content">
          {/* Profile Section */}
          <section className="settings-section panel" id="profile">
            <SectionTitle title="Profile" description="Your personal workspace profile." />
            <div className="profile-settings">
              <span className="user-avatar profile-avatar-large">
                {displayName.trim().slice(0, 2).toUpperCase() || "U"}
              </span>
              <div className="profile-settings-details">
                <strong>{displayName}</strong>
                <span>{ROLES.find(r => r.value === profileRole)?.label || "Designer"} · {email}</span>
                <small>Authentication provider: {authProvider}</small>
              </div>
            </div>
            <div className="form-grid settings-form-grid">
              <label className="form-field">
                <span>Display name</span>
                <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
              </label>
              <label className="form-field">
                <span>Email address</span>
                <input type="email" value={email} disabled readOnly title="Email cannot be changed directly" />
              </label>
              <label className="form-field form-field-wide">
                <span>Professional role</span>
                <select value={profileRole} onChange={(e) => setProfileRole(e.target.value)}>
                  {ROLES.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="settings-save-row">
              <Button variant="primary" disabled={profileSaving} onClick={handleSaveProfile}>
                {profileSaving ? "Saving..." : "Save profile"}
              </Button>
            </div>
          </section>

          {/* Security & Authentication */}
          <section className="settings-section panel" id="security">
            <SectionTitle
              title="Security & Authentication"
              description="Manage your account access, password, and session."
            />
            {supabaseUser ? (
              <div className="form-grid settings-form-grid">
                <label className="form-field">
                  <span>New password</span>
                  <input
                    type="password"
                    placeholder="••••••••"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                  />
                </label>
                <label className="form-field">
                  <span>Confirm new password</span>
                  <input
                    type="password"
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                  />
                </label>
                <div className="form-field-wide" style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                  <Button
                    variant="secondary"
                    disabled={passwordUpdating || !newPassword}
                    onClick={handlePasswordUpdate}
                  >
                    {passwordUpdating ? "Updating..." : "Update password"}
                  </Button>
                  <Button variant="secondary" onClick={handleSignOut}>
                    Sign out
                  </Button>
                </div>
              </div>
            ) : (
              <div className="setting-row">
                <div>
                  <strong>Session state</strong>
                  <span>Running in demo mode. Sign in to connect a real Supabase account.</span>
                </div>
                <Button variant="primary" onClick={() => router.push("/login")}>
                  Sign in
                </Button>
              </div>
            )}
          </section>

          {/* Appearance Section */}
          <section className="settings-section panel" id="appearance">
            <SectionTitle title="Appearance" description="Choose how Forteux looks on this device." />
            <div className="setting-row">
              <div>
                <strong>Theme</strong>
                <span>Apply a light, dark, or device-based theme.</span>
              </div>
              <div className="segmented-control" role="group" aria-label="Theme preference">
                {(["light", "dark", "system"] as const).map((item) => (
                  <button
                    key={item}
                    className={theme === item ? "segment-active" : ""}
                    aria-pressed={theme === item}
                    onClick={() => {
                      setTheme(item);
                      updatePreference(`${item[0].toUpperCase()}${item.slice(1)} theme selected.`);
                    }}
                  >
                    {item[0].toUpperCase() + item.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {/* AI Preferences */}
          <section className="settings-section panel" id="ai-preferences">
            <SectionTitle title="AI preferences" description="Defaults for future analysis workflows." />
            <label className="setting-toggle">
              <span>
                <strong>Product update notifications</strong>
                <small>Receive email announcements when new design auditing features are released.</small>
              </span>
              <input
                type="checkbox"
                checked={emailUpdates}
                onChange={(event) => {
                  setEmailUpdates(event.target.checked);
                  window.localStorage.setItem("forteux-preference-email-updates", String(event.target.checked));
                  updatePreference(event.target.checked ? "Product updates enabled." : "Product updates disabled.");
                }}
              />
              <span className="toggle-control" />
            </label>
            <label className="setting-row setting-row-control">
              <span>
                <strong>Default audit mode</strong>
                <small>Choose the mode preselected when starting an audit.</small>
              </span>
              <select
                value={analysisMode}
                onChange={(event) => {
                  setAnalysisMode(event.target.value);
                  window.localStorage.setItem("forteux-default-audit-mode", event.target.value);
                  updatePreference("Default audit mode changed.");
                }}
              >
                <option value="single">Single screen</option>
                <option value="multi">Multi-screen UX</option>
              </select>
            </label>
          </section>

          {/* Knowledge Preferences */}
          <section className="settings-section panel" id="knowledge-preferences">
            <SectionTitle title="Knowledge preferences" description="Set which knowledge scopes may inform future audits." />
            <label className="setting-toggle">
              <span>
                <strong>Include global knowledge</strong>
                <small>Platform-curated guidance available across audits.</small>
              </span>
              <input
                type="checkbox"
                checked={includeGlobal}
                onChange={(event) => {
                  setIncludeGlobal(event.target.checked);
                  window.localStorage.setItem("forteux-preference-global-knowledge", String(event.target.checked));
                  updatePreference(event.target.checked ? "Global knowledge enabled." : "Global knowledge disabled.");
                }}
              />
              <span className="toggle-control" />
            </label>
            <label className="setting-toggle">
              <span>
                <strong>Include project knowledge</strong>
                <small>References scoped to {projects.find((project) => project.id === selectedProjectId)?.name ?? "your selected project"}.</small>
              </span>
              <input
                type="checkbox"
                checked={includeProject}
                onChange={(event) => {
                  setIncludeProject(event.target.checked);
                  window.localStorage.setItem("forteux-preference-project-knowledge", String(event.target.checked));
                  updatePreference(event.target.checked ? "Project knowledge enabled." : "Project knowledge disabled.");
                }}
              />
              <span className="toggle-control" />
            </label>
            <label className="setting-toggle">
              <span>
                <strong>Product update notifications</strong>
                <small>Receive email announcements when new design auditing features are released.</small>
              </span>
              <input
                type="checkbox"
                checked={emailUpdates}
                onChange={(event) => {
                  setEmailUpdates(event.target.checked);
                  window.localStorage.setItem("forteux-preference-email-updates", String(event.target.checked));
                  updatePreference(event.target.checked ? "Product updates enabled." : "Product updates disabled.");
                }}
              />
              <span className="toggle-control" />
            </label>
            <label className="setting-row setting-row-control">
              <span>
                <strong>Default project scope</strong>
                <small>Current project for new audits.</small>
              </span>
              <select
                value={selectedProjectId}
                onChange={(event) => {
                  setSelectedProjectId(event.target.value);
                  updatePreference("Default project changed.");
                }}
              >
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>{project.name}</option>
                ))}
              </select>
            </label>
          </section>
        </div>
      </div>
    </div>
  );
}
