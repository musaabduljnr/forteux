"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect, type ReactNode } from "react";
import type { User } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import { useAppState } from "./app-state";
import { Icon, type IconName } from "./icons";

const navigation: Array<{ label: string; href: string; icon: IconName; group: string }> = [
  { label: "Dashboard", href: "/dashboard", icon: "dashboard", group: "Workspace" },
  { label: "New audit", href: "/audits/new", icon: "plus", group: "Workspace" },
  { label: "Projects", href: "/projects", icon: "folder", group: "Workspace" },
  { label: "Audit history", href: "/history", icon: "history", group: "Workspace" },
  { label: "Exports", href: "/exports", icon: "file", group: "Workspace" },
  { label: "Knowledge library", href: "/knowledge", icon: "book", group: "Manage" },
  { label: "Design system", href: "/design-system", icon: "layers", group: "Manage" },
  { label: "Settings", href: "/settings", icon: "settings", group: "Manage" },
];

function isActive(pathname: string, href: string) {
  if (href === "/dashboard") return pathname === "/dashboard";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [supabaseUser, setSupabaseUser] = useState<User | null>(null);
  const { toasts, dismissToast, notify, user } = useAppState();

  const supabase = createClient();

  // Listen for Supabase auth state
  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setSupabaseUser(data.user ?? null));
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSupabaseUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, [supabase.auth]);

  async function handleSignOut() {
    await supabase.auth.signOut();
    setProfileOpen(false);
    router.push("/login");
    router.refresh();
  }

  const profileName =
    supabaseUser?.user_metadata?.full_name ||
    supabaseUser?.user_metadata?.name ||
    supabaseUser?.email ||
    user.displayName;
  const profileInitials = profileName
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part: string) => part[0]?.toUpperCase() ?? "")
    .join("");
  const isWorkspace = pathname.startsWith("/audits/");
  const isAuthPage = ["/login", "/register", "/forgot-password", "/reset-password", "/onboarding", "/auth"].some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );

  if (pathname === "/" || isAuthPage) {
    return (
      <div className={pathname === "/" ? "public-landing-container" : undefined}>
        {children}
        <div className="toast-region" aria-live="polite" aria-relevant="additions removals">
          {toasts.map((toast) => (
            <div className={`toast toast-${toast.tone}`} role={toast.tone === "error" ? "alert" : "status"} key={toast.id}>
              <Icon name={toast.tone === "success" ? "check" : toast.tone === "error" ? "warning" : "info"} size={18} />
              <span>{toast.message}</span>
              <button aria-label="Dismiss notification" onClick={() => dismissToast(toast.id)}><Icon name="close" size={16} /></button>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""} ${mobileOpen ? "mobile-menu-open" : ""} ${isWorkspace ? "workspace-route" : ""}`}>
      <button className="mobile-backdrop" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />
      <aside className="sidebar">
        <Link className="brand" href="/dashboard" onClick={() => setMobileOpen(false)} aria-label="Forteux home">
          <span className="brand-mark"><Icon name="layers" size={20} /></span>
          <span className="brand-copy"><strong>forteux</strong><small>Design intelligence</small></span>
        </Link>
        <button className="workspace-switcher" onClick={() => notify("Workspace switching will be connected to team accounts later.", "info")}>
          <span className="workspace-avatar">{profileInitials?.[0] || "W"}</span>
          <span className="workspace-copy"><strong>{supabaseUser ? (profileName.split(" ")[0] + "'s workspace") : "Personal workspace"}</strong><small>Personal workspace</small></span>
          <Icon name="down" size={16} />
        </button>
        <nav className="primary-nav" aria-label="Main navigation">
          {["Workspace", "Manage"].map((group) => (
            <div className="nav-group" key={group}>
              <div className="nav-group-label">{group}</div>
              {navigation.filter((item) => item.group === group).map((item) => {
                const active = isActive(pathname, item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    className={`nav-link ${active ? "nav-link-active" : ""}`}
                    aria-current={active ? "page" : undefined}
                    title={collapsed ? item.label : undefined}
                  >
                    <Icon name={item.icon} size={19} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-help">
            <span className="help-icon"><Icon name="info" size={17} /></span>
            <div><strong>Need a hand?</strong><span>Explore the getting started guide.</span></div>
            <button aria-label="Open getting started guide" onClick={() => notify("The getting started guide will be available in a later release.")}><Icon name="arrow" size={16} /></button>
          </div>
          <div className="sidebar-user">
            <span className="user-avatar">{supabaseUser ? (profileInitials || "U") : user.avatarInitials}</span>
            <div className="user-copy"><strong>{supabaseUser ? profileName : user.displayName}</strong><small>{supabaseUser ? (supabaseUser.email || "User") : user.role}</small></div>
            <button className="icon-button sidebar-collapse-button" onClick={() => setCollapsed(!collapsed)} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} title={collapsed ? "Expand sidebar" : "Collapse sidebar"}><Icon name="move" size={17} /></button>
          </div>
        </div>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <button className="icon-button mobile-menu-button" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Icon name="menu" /></button>
          <div className="topbar-context">
            <span className="topbar-section">{navigation.find((item) => isActive(pathname, item.href))?.label ?? "Audit workspace"}</span>
            {pathname.startsWith("/projects/") && <><Icon name="chevron" size={14} /><span className="topbar-muted">Project details</span></>}
          </div>
          <div className="topbar-actions">
            <button className="icon-button notification-button" aria-label="Notifications" aria-expanded={notificationsOpen} onClick={() => { setNotificationsOpen(!notificationsOpen); setProfileOpen(false); }}>
              <Icon name="bell" size={19} /><span className="notification-dot" />
            </button>
            {notificationsOpen && <div className="topbar-popover notification-popover"><strong>You’re all caught up</strong><p>New audit and document updates will appear here.</p></div>}
            <button className="topbar-profile" aria-expanded={profileOpen} onClick={() => { setProfileOpen(!profileOpen); setNotificationsOpen(false); }}>
              <span className="user-avatar user-avatar-small">{supabaseUser ? (profileInitials || "U") : user.avatarInitials}</span><span className="profile-name">{supabaseUser ? profileName : user.displayName}</span><Icon name="down" size={15} />
            </button>
            {profileOpen && (
              <div className="topbar-popover profile-popover">
                <strong>{supabaseUser ? profileName : user.displayName}</strong><span>{supabaseUser ? "Authenticated account" : "Demo profile · not authenticated"}</span>
                <Link href="/settings" onClick={() => setProfileOpen(false)}>Profile settings</Link>
                {supabaseUser ? (
                  <button onClick={() => void handleSignOut()}>Sign out</button>
                ) : (
                  <Link href="/login" className="button button-sm button-secondary" onClick={() => setProfileOpen(false)}>
                    Sign in
                  </Link>
                )}
              </div>
            )}
          </div>
        </header>
        <main className="page-content">{children}</main>
      </div>
      <div className="toast-region" aria-live="polite" aria-relevant="additions removals">
        {toasts.map((toast) => (
          <div className={`toast toast-${toast.tone}`} role={toast.tone === "error" ? "alert" : "status"} key={toast.id}>
            <Icon name={toast.tone === "success" ? "check" : toast.tone === "error" ? "warning" : "info"} size={18} />
            <span>{toast.message}</span>
            <button aria-label="Dismiss notification" onClick={() => dismissToast(toast.id)}><Icon name="close" size={16} /></button>
          </div>
        ))}
      </div>
    </div>
  );
}
