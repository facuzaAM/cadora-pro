import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const error = searchParams.get("error");

  if (error) {
    const message = error === "invalid_state" ? "Sesión expirada. Intenta de nuevo." : "Error de autenticación.";
    return NextResponse.redirect(`${origin}/login?error=${encodeURIComponent(message)}`);
  }

  return NextResponse.redirect(`${origin}/login`);
}
