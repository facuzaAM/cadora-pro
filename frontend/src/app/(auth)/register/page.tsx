"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Logo } from "@/components/shared/logo";
import { CadCrosshair } from "@/components/features/landing/cad-crosshair";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "sonner";
import { Eye, EyeOff, AlertCircle } from "lucide-react";
import { validatePassword } from "@/lib/password";

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" />}>
      <RegisterContent />
    </Suspense>
  );
}

function RegisterContent() {
  const searchParams = useSearchParams();
  const plan = searchParams.get("plan");
  const { signUp, signInWithGoogle } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const err = validatePassword(password);
    if (err) {
      setPasswordError(err);
      return;
    }
    setPasswordError(null);
    setSubmitting(true);
    try {
      await signUp(
        email,
        password,
        name,
        plan && plan !== "free" ? `/pricing?plan=${encodeURIComponent(plan)}` : undefined,
      );
      toast.success("Cuenta creada correctamente");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Error al registrarse";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogle = async () => {
    setGoogleLoading(true);
    try {
      await signInWithGoogle(plan && plan !== "free" ? plan : undefined);
    } catch {
      setGoogleLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-gradient-to-b from-primary/[0.05] via-background to-background p-4">
      <div className="absolute inset-0 bg-grid-cad bg-grid-cad-fade pointer-events-none" />
      <CadCrosshair className="absolute right-[6%] top-1/2 hidden h-32 w-32 -translate-y-1/2 text-primary/25 lg:block pointer-events-none" />
      <CadCrosshair className="absolute left-[4%] top-[20%] hidden h-20 w-20 text-primary/15 lg:block pointer-events-none" />
      <div className="absolute -left-24 top-1/4 h-56 w-56 animate-blob rounded-full bg-primary/10 blur-3xl pointer-events-none" />
      <div className="absolute -right-24 bottom-0 h-56 w-56 animate-blob-delayed rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />
      <div className="relative">
        <Link href="/" className="mb-8 flex justify-center">
          <Logo />
        </Link>
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle>Crear Cuenta</CardTitle>
          <CardDescription>Regístrate para empezar a usar Cadora</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <button
            onClick={handleGoogle}
            disabled={googleLoading}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg border bg-card px-4 py-3 text-sm font-medium shadow-sm transition-colors hover:bg-accent disabled:opacity-50"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            {googleLoading ? "Conectando..." : "Continuar con Google"}
          </button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">o con email</span>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Nombre</Label>
              <Input
                id="name"
                placeholder="Tu nombre"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="tu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Contraseña</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Mín. 8 caracteres, 1 mayúscula, 1 número, 1 especial"
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setPasswordError(null); }}
                  required
                  minLength={8}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {passwordError && (
                <p className="flex items-center gap-1 text-xs text-destructive">
                  <AlertCircle className="h-3 w-3" />
                  {passwordError}
                </p>
              )}
            </div>
            <div className="flex items-start gap-2">
              <input
                id="terms"
                type="checkbox"
                checked={acceptedTerms}
                onChange={(e) => setAcceptedTerms(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-input"
                required
              />
              <label htmlFor="terms" className="text-sm text-muted-foreground">
                Acepto los{" "}
                <Link href="/terminos" target="_blank" className="text-primary underline-offset-4 hover:underline">
                  Términos de Servicio
                </Link>{" "}
                y la{" "}
                <Link href="/privacidad" target="_blank" className="text-primary underline-offset-4 hover:underline">
                  Política de Privacidad
                </Link>
              </label>
            </div>
            <Button type="submit" className="w-full" disabled={submitting || !acceptedTerms}>
              {submitting ? "Creando cuenta..." : "Crear Cuenta"}
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground">
            ¿Ya tienes cuenta?{" "}
            <Link href="/login" className="text-primary underline-offset-4 hover:underline">
              Iniciar Sesión
            </Link>
          </p>
        </CardContent>
      </Card>
      </div>
    </div>
  );
}
