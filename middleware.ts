import { NextResponse, type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

const PROTECTED_ROUTES = [
  "/dashboard",
  "/projects",
  "/audits",
  "/history",
  "/exports",
  "/knowledge",
  "/design-system",
  "/settings",
  "/onboarding",
];

const AUTH_ROUTES = ["/login", "/register", "/forgot-password", "/reset-password"];

function isProtected(pathname: string) {
  return PROTECTED_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );
}

function isAuthRoute(pathname: string) {
  return AUTH_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );
}

export async function middleware(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl;
  const { supabaseResponse, user } = await updateSession(request);
  const isSupabaseConfigured = Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL &&
    !process.env.NEXT_PUBLIC_SUPABASE_URL.includes("placeholder")
  );

  // Redirect unauthenticated users away from protected routes
  if (isProtected(pathname) && isSupabaseConfigured && !user) {
    const loginUrl = new URL("/login", request.url);
    // Safe redirect: only allow relative paths starting with /
    const nextPath = pathname + (searchParams.toString() ? `?${searchParams}` : "");
    if (nextPath.startsWith("/")) {
      loginUrl.searchParams.set("next", nextPath);
    }
    return NextResponse.redirect(loginUrl);
  }

  // Redirect authenticated users away from auth pages (except onboarding)
  if (isAuthRoute(pathname) && user) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return supabaseResponse;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimisation)
     * - favicon.ico, sitemap.xml, robots.txt
     * - api routes (handled by their own auth)
     */
    "/((?!_next/static|_next/image|favicon\\.ico|sitemap\\.xml|robots\\.txt|api/).*)",
  ],
};
