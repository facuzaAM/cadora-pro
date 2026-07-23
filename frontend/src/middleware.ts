import { type NextRequest, NextResponse } from "next/server";

const protectedRoutes = ["/dashboard", "/projects", "/settings", "/profile", "/billing"];

export function middleware(request: NextRequest) {
  const token = request.cookies.get("cadora_refresh")?.value;
  const { pathname } = request.nextUrl;

  const isProtected = protectedRoutes.some((route) => pathname.startsWith(route));
  if (isProtected && !token) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("redirect", pathname);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
