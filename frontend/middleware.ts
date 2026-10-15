/**
 * Next.js middleware: protect /admin routes.
 * Redirects to /admin/login if no access token in localStorage.
 * NOTE: Middleware runs on the Edge — we read the token from a cookie
 * (set by the client after login) for SSR-compatible auth guard.
 */
import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/admin/login", "/admin/register"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Only protect /admin routes
  if (!pathname.startsWith("/admin")) {
    return NextResponse.next();
  }

  // Allow public auth pages
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Check for auth cookie (set by client after login)
  const token = request.cookies.get("gr_auth")?.value;
  if (!token) {
    const loginUrl = new URL("/admin/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*"],
};
