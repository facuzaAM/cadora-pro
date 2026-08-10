"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Mail, RefreshCw, AlertCircle, Loader2 } from "lucide-react";
import { Logo } from "@/components/shared/logo";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/services/api";

function safeInternalRedirect(value?: string): string {
  if (!value) return "/dashboard";
  if (!value.startsWith("/") || value.startsWith("//")) return "/dashboard";
  return value;
}

export default function VerifyEmailPage({
  searchParams,
}: {
  searchParams: Promise<{ redirectTo?: string }>;
}) {
  const router = useRouter();
  const params = use(searchParams);
  const redirectTo = safeInternalRedirect(params.redirectTo);
  const { user, loading, refreshUser } = useAuth();
  const [code, setCode] = useState("");
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [sent, setSent] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const sendCode = async () => {
    setSending(true);
    setError("");
    setMessage("");
    try {
      await api.post("/auth/send-verification", {}, api.getAccessToken());
      setSent(true);
      setMessage("Te enviamos un código de verificación a tu email.");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No pudimos enviar el código. Intentá de nuevo más tarde.",
      );
    } finally {
      setSending(false);
    }
  };

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (user.email_verified) {
      router.replace("/dashboard");
      return;
    }
    if (!sent && !message) {
      sendCode();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, user, router]);

  const handleVerify = async () => {
    if (code.length !== 6 || verifying) return;
    setVerifying(true);
    setError("");
    setMessage("");
    try {
      await api.post("/auth/verify-email", { code }, api.getAccessToken());
      await refreshUser();
      router.replace(redirectTo);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Código incorrecto o expirado");
    } finally {
      setVerifying(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-gradient-to-b from-primary/[0.03] via-background to-background p-4">
      <div className="absolute inset-0 bg-dot-pattern-sm opacity-50 pointer-events-none" />
      <div className="relative">
        <Link href="/" className="mb-8 flex justify-center">
          <Logo />
        </Link>
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle>Verificá tu email</CardTitle>
            <CardDescription>
              Para usar el servicio necesitás confirmar tu dirección de email.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-start gap-3 rounded-lg border bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
              <Mail className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              <p>
                {sent
                  ? `Enviamos un código de 6 dígitos a ${user?.email}. Revisá tu bandeja de entrada (y la carpeta de spam).`
                  : "Estamos preparando el envío del código de verificación..."}
              </p>
            </div>

            {message && <p className="text-sm text-emerald-600">{message}</p>}
            {error && (
              <p className="flex items-start gap-2 text-sm text-destructive">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                {error}
              </p>
            )}

            <div className="space-y-2">
              <label htmlFor="code" className="text-sm font-medium">
                Código de verificación
              </label>
              <input
                id="code"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                placeholder="000000"
                className="w-full rounded-lg border bg-card px-3 py-2 text-center font-mono text-2xl tracking-[0.5em] outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <Button className="w-full" onClick={handleVerify} disabled={code.length !== 6 || verifying}>
              {verifying && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Verificar email
            </Button>

            <div className="flex items-center justify-center gap-2 text-center text-sm text-muted-foreground">
              <span>¿No llegó el código?</span>
              <button
                onClick={sendCode}
                disabled={sending}
                className="inline-flex items-center gap-1 font-medium text-primary underline-offset-4 hover:underline disabled:opacity-50"
              >
                {sending && <RefreshCw className="h-3 w-3 animate-spin" />}
                Reenviar
              </button>
            </div>

            <div className="text-center">
              <Button variant="ghost" size="sm" onClick={() => router.push(redirectTo)}>
                Hacerlo más tarde
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
