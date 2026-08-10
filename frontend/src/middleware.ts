import { type NextRequest, NextResponse } from "next/server";
import { decodeJwtPayload } from "@/lib/jwt";

const protectedRoutes = ["/dashboard", "/projects", "/settings", "/profile", "/billing", "/admin"];

function isTokenValid(token: string): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") return false;
  const now = Math.floor(Date.now() / 1000);
  return payload.exp > now;
}

export function middleware(request: NextRequest) {
  const token = request.cookies.get("cadora_refresh")?.value;
  const { pathname } = request.nextUrl;

  const isProtected = protectedRoutes.some((route) => pathname.startsWith(route));
  if (isProtected) {
    if (!token || !isTokenValid(token)) {
      const url = request.nextUrl.clone();
      url.pathname = "/login";
      url.searchParams.set("redirect", pathname);
      return NextResponse.redirect(url);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
