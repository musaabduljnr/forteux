import { getToken } from "next-auth/jwt";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const MAX_API_BODY_BYTES = 128 * 1024;
const allowedMethods = new Set(["GET", "POST", "PATCH", "DELETE"]);

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  if (!allowedMethods.has(request.method)) {
    return NextResponse.json({ error: { code: "method_not_allowed", message: "Method not allowed" } }, { status: 405 });
  }
  const backendBase = process.env.BACKEND_API_URL;
  if (!backendBase) {
    return NextResponse.json({ error: { code: "backend_not_configured", message: "Backend API is not configured" } }, { status: 503 });
  }
  let base: URL;
  try {
    base = new URL(backendBase);
  } catch {
    return NextResponse.json({ error: { code: "backend_not_configured", message: "Backend API URL is invalid" } }, { status: 503 });
  }
  if (process.env.NODE_ENV === "production" && base.protocol !== "https:") {
    return NextResponse.json({ error: { code: "backend_transport_invalid", message: "Backend API must use HTTPS" } }, { status: 503 });
  }

  const token = await getToken({ req: request, secret: process.env.NEXTAUTH_SECRET });
  const accessToken = token?.apiAccessToken;
  if (typeof accessToken !== "string" || !accessToken) {
    return NextResponse.json({ error: { code: "authentication_required", message: "Sign in is required" } }, { status: 401 });
  }
  if (
    typeof token?.apiAccessTokenExpiresAt === "number"
    && token.apiAccessTokenExpiresAt <= Math.floor(Date.now() / 1000)
  ) {
    return NextResponse.json({ error: { code: "session_expired", message: "Sign in again to continue" } }, { status: 401 });
  }

  const { path } = await context.params;
  if (path.some((part) => part === "." || part === ".." || part.includes("\\"))) {
    return NextResponse.json({ error: { code: "invalid_path", message: "Invalid API path" } }, { status: 400 });
  }
  const prefix = base.pathname.endsWith("/") ? base.pathname : `${base.pathname}/`;
  base.pathname = `${prefix}${path.map(encodeURIComponent).join("/")}`;
  base.search = request.nextUrl.search;

  const contentLength = Number(request.headers.get("content-length") ?? 0);
  if (contentLength > MAX_API_BODY_BYTES) {
    return NextResponse.json({ error: { code: "request_too_large", message: "API request body is too large" } }, { status: 413 });
  }

  const headers = new Headers();
  headers.set("Authorization", `Bearer ${accessToken}`);
  headers.set("Accept", request.headers.get("accept") ?? "application/json");
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);
  const idempotencyKey = request.headers.get("idempotency-key");
  if (idempotencyKey) headers.set("Idempotency-Key", idempotencyKey);
  const requestId = request.headers.get("x-request-id");
  if (requestId) headers.set("X-Request-ID", requestId);

  let body: ArrayBuffer | undefined;
  if (request.method !== "GET") {
    body = await request.arrayBuffer();
    if (body.byteLength > MAX_API_BODY_BYTES) {
      return NextResponse.json({ error: { code: "request_too_large", message: "API request body is too large" } }, { status: 413 });
    }
  }

  try {
    const upstream = await fetch(base, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(10_000),
    });
    const responseHeaders = new Headers();
    const upstreamType = upstream.headers.get("content-type");
    const upstreamRequestId = upstream.headers.get("x-request-id");
    if (upstreamType) responseHeaders.set("content-type", upstreamType);
    if (upstreamRequestId) responseHeaders.set("x-request-id", upstreamRequestId);
    return new NextResponse(await upstream.arrayBuffer(), {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch {
    return NextResponse.json({ error: { code: "backend_unavailable", message: "Backend API is temporarily unavailable" } }, { status: 503 });
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
