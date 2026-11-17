"use client";

import { useEffect, useState } from "react";
import { useAppState } from "@/components/app-state";
import { Icon } from "@/components/icons";
import { Badge, Button, PageHeader, SectionTitle } from "@/components/ui";
import { demoUser } from "@/lib/demo-data";

type Theme = "light" | "dark" | "system";

export default function SettingsPage() {
  const { notify, selectedProjectId, setSelectedProjectId, projects, user, updateUser } = useAppState();
  const [theme, setTheme] = useState<Theme>("light");
  const [analysisMode, setAnalysisMode] = useState("single");
  const [displayName, setDisplayName] = useState(user.displayName);
  const [email, setEmail] = useState(user.email);
  const [includeGlobal, setIncludeGlobal] = useState(true);
  const [includeProject, setIncludeProject] = useState(true);
  const [emailUpdates, setEmailUpdates] = useState(false);

  useEffect(() => {
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
  }, []);

  useEffect(() => {
    setDisplayName(user.displayName);
    setEmail(user.email);
  }, [user.displayName, user.email]);

  useEffect(() => {
    const effectiveTheme = theme === "system"
      ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
      : theme;
    document.documentElement.dataset.theme = effectiveTheme;
    window.localStorage.setItem("forteux-theme", theme);
  }, [theme]);

  function updatePreference(message: string) {
    notify(`${message} Preference saved in this browser demo only.`, "success");
  }

  return (
    <div className="page-stack">
      <PageHeader eyebrow="Manage" title="Settings" description="Manage your profile, workspace preferences, and local demo experience." />
      <div className="demo-notice"><span><strong>Local preferences</strong> These settings are stored in this browser and are not linked to an account.</span></div>
      <div className="settings-layout">
        <nav className="settings-nav" aria-label="Settings sections">
          <a href="#profile" className="settings-nav-active"><Icon name="dashboard" size={17} />Profile</a>
          <a href="#appearance"><Icon name="layers" size={17} />Appearance</a>
          <a href="#ai-preferences"><Icon name="spark" size={17} />AI preferences</a>
          <a href="#knowledge-preferences"><Icon name="book" size={17} />Knowledge</a>
          <a href="#account"><Icon name="settings" size={17} />Account</a>
        </nav>
        <div className="settings-content">
          <section className="settings-section panel" id="profile">
            <SectionTitle title="Profile" description="Your personal workspace profile." />
            <div className="profile-settings"><span className="user-avatar profile-avatar-large">{user.avatarInitials}</span><div className="profile-settings-details"><strong>{user.displayName}</strong><span>{user.role} · Personal workspace</span><small>Profile data is a demonstration placeholder.</small></div></div>
            <div className="form-grid settings-form-grid">
              <label className="form-field"><span>Display name</span><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
              <label className="form-field"><span>Email</span><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} /><small>Example only; not an authenticated account address.</small></label>
            </div>
            <div className="settings-save-row"><Button variant="secondary" onClick={() => { updateUser({ displayName: displayName.trim() || demoUser.displayName, email: email.trim() || demoUser.email }); updatePreference("Profile details updated."); }}>Save profile</Button></div>
          </section>
          <section className="settings-section panel" id="appearance">
            <SectionTitle title="Appearance" description="Choose how Forteux looks on this device." />
            <div className="setting-row"><div><strong>Theme</strong><span>Apply a light, dark, or device-based theme.</span></div><div className="segmented-control" role="group" aria-label="Theme preference">{(["light", "dark", "system"] as const).map((item) => <button key={item} className={theme === item ? "segment-active" : ""} aria-pressed={theme === item} onClick={() => { setTheme(item); updatePreference(`${item[0].toUpperCase()}${item.slice(1)} theme selected.`); }}>{item[0].toUpperCase() + item.slice(1)}</button>)}</div></div>
          </section>
          <section className="settings-section panel" id="ai-preferences">
            <SectionTitle title="AI preferences" description="Defaults for future analysis workflows." action={<Badge tone="demo">Not connected</Badge>} />
            <label className="setting-row setting-row-control"><span><strong>Default audit mode</strong><small>Choose the mode preselected when starting an audit.</small></span><select value={analysisMode} onChange={(event) => { setAnalysisMode(event.target.value); window.localStorage.setItem("forteux-default-audit-mode", event.target.value); updatePreference("Default audit mode changed."); }}><option value="single">Single screen</option><option value="multi">Multi-screen UX</option></select></label>
            <div className="setting-row"><div><strong>Analysis preferences</strong><span>Vision, reasoning, and accessibility controls will be available when analysis is integrated.</span></div><Badge>Coming later</Badge></div>
          </section>
          <section className="settings-section panel" id="knowledge-preferences">
            <SectionTitle title="Knowledge preferences" description="Set which knowledge scopes may inform future audits." action={<Badge tone="demo">Not connected</Badge>} />
            <label className="setting-toggle"><span><strong>Include global knowledge</strong><small>Platform-curated guidance available across audits.</small></span><input type="checkbox" checked={includeGlobal} onChange={(event) => { setIncludeGlobal(event.target.checked); window.localStorage.setItem("forteux-preference-global-knowledge", String(event.target.checked)); updatePreference(event.target.checked ? "Global knowledge enabled." : "Global knowledge disabled."); }} /><span className="toggle-control" /></label>
            <label className="setting-toggle"><span><strong>Include project knowledge</strong><small>References scoped to {projects.find((project) => project.id === selectedProjectId)?.name ?? "your selected project"}.</small></span><input type="checkbox" checked={includeProject} onChange={(event) => { setIncludeProject(event.target.checked); window.localStorage.setItem("forteux-preference-project-knowledge", String(event.target.checked)); updatePreference(event.target.checked ? "Project knowledge enabled." : "Project knowledge disabled."); }} /><span className="toggle-control" /></label>
            <label className="setting-row setting-row-control"><span><strong>Default project scope</strong><small>Current project for new audits.</small></span><select value={selectedProjectId} onChange={(event) => { setSelectedProjectId(event.target.value); updatePreference("Default project changed."); }}>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>
          </section>
          <section className="settings-section panel" id="account">
            <SectionTitle title="Account and security" description="Authentication and account security are managed by the future identity provider." />
            <div className="setting-row"><div><strong>Sign-in and security</strong><span>Session management and multi-factor authentication are not connected in this frontend phase.</span></div><Button variant="secondary" onClick={() => notify("Security settings will be provided by the managed identity service.")}>Manage security</Button></div>
            <div className="setting-row"><div><strong>Email updates</strong><span>Receive important product updates.</span></div><label className="setting-toggle-inline"><span className="visually-hidden">Email updates</span><input type="checkbox" checked={emailUpdates} onChange={(event) => { setEmailUpdates(event.target.checked); window.localStorage.setItem("forteux-preference-email-updates", String(event.target.checked)); updatePreference(event.target.checked ? "Email updates enabled." : "Email updates disabled."); }} /><span className="toggle-control" /></label></div>
            <div className="account-note"><Icon name="info" size={17} /><span>No API keys or backend credentials are exposed in this interface.</span></div>
          </section>
        </div>
      </div>
    </div>
  );
}
