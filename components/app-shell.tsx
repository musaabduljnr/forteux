"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { signIn, signOut, useSession } from "next-auth/react";
import { useAppState } from "./app-state";
import { Icon, type IconName } from "./icons";

const navigation: Array<{ label: string; href: string; icon: IconName; group: string }> = [
  { label: "Dashboard", href: "/", icon: "dashboard", group: "Workspace" },
  { label: "New audit", href: "/audits/new", icon: "plus", group: "Workspace" },
  { label: "Projects", href: "/projects", icon: "folder", group: "Workspace" },
  { label: "Audit history", href: "/history", icon: "history", group: "Workspace" },
  { label: "Knowledge library", href: "/knowledge", icon: "book", group: "Manage" },
  { label: "Design system", href: "/design-system", icon: "layers", group: "Manage" },
  { label: "Settings", href: "/settings", icon: "settings", group: "Manage" },
];

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const { toasts, dismissToast, notify, user } = useAppState();
  const { data: session, status: sessionStatus } = useSession();
  const authEnabled = process.env.NEXT_PUBLIC_OIDC_ENABLED === "true";
  const devAuthEnabled = process.env.NEXT_PUBLIC_DEV_AUTH_ENABLED === "true";
  const profileName = session?.user?.name || session?.user?.email || user.displayName;
  const profileInitials = profileName.trim().split(/\s+/).slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "").join("");
  const isWorkspace = pathname.startsWith("/audits/");

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""} ${mobileOpen ? "mobile-menu-open" : ""} ${isWorkspace ? "workspace-route" : ""}`}>
      <button className="mobile-backdrop" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />
      <aside className="sidebar">
        <Link className="brand" href="/" onClick={() => setMobileOpen(false)} aria-label="Forteux home">
          <span className="brand-mark"><Icon name="layers" size={20} /></span>
          <span className="brand-copy"><strong>forteux</strong><small>Design intelligence</small></span>
        </Link>
        <button className="workspace-switcher" onClick={() => notify("Workspace switching will be connected to team accounts later.", "info")}>
          <span className="workspace-avatar">N</span>
          <span className="workspace-copy"><strong>Northstar Studio</strong><small>Personal workspace</small></span>
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
            <span className="user-avatar">{user.avatarInitials}</span>
            <div className="user-copy"><strong>{user.displayName}</strong><small>{user.role}</small></div>
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
              <span className="user-avatar user-avatar-small">{session ? profileInitials || user.avatarInitials : user.avatarInitials}</span><span className="profile-name">{session ? profileName : user.displayName}</span><Icon name="down" size={15} />
            </button>
            {profileOpen && (
              <div className="topbar-popover profile-popover">
                <strong>{session ? profileName : user.displayName}</strong><span>{session ? "Authenticated account" : "Demo profile · not authenticated"}</span>
                <Link href="/settings" onClick={() => setProfileOpen(false)}>Profile settings</Link>
                {session ? (
                  <button onClick={() => { setProfileOpen(false); void signOut({ callbackUrl: "/" }); }}>Sign out</button>
                ) : authEnabled ? (
                  <button disabled={sessionStatus === "loading"} onClick={() => { setProfileOpen(false); void signIn("cognito"); }}>
                    Sign in with Cognito
                  </button>
                ) : devAuthEnabled ? (
                  <button disabled={sessionStatus === "loading"} onClick={() => { setProfileOpen(false); void signIn("development", { callbackUrl: "/" }); }}>
                    Sign in with Dev Account
                  </button>
                ) : (
                  <span className="profile-auth-note">Authentication is unavailable until configured.</span>
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
