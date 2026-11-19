import type { ReactNode } from "react";

/**
 * Auth route group layout — renders without the AppShell sidebar.
 * Pages: /login, /register, /forgot-password, /reset-password, /onboarding
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
