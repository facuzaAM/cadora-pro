"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Logo } from "@/components/shared/logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { toast } from "sonner";
import { ArrowLeft, Mail, CheckCircle } from "lucide-react";
import { api } from "@/services/api";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email });
      setSubmitted(true);
    } catch (err) {
      if (err instanceof TypeError) {
        toast.error("Error de conexión. Revisá tu conexión a internet e intentá de nuevo.");
        return;
      }
      toast.error("Error al enviar el código. Intentalo de nuevo más tarde.");
    } finally {
      setLoading(false);
    }
  };

  // Move straight to the code-entry page so the user always has a place to
  // type the code they receive by email.
  useEffect(() => {
    if (!submitted) return;
    const timer = setTimeout(() => router.push("/reset-password"), 2500);
    return () => clearTimeout(timer);
  }, [submitted, router]);

  if (submitted) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center p-4">
        <Link href="/" className="mb-8">
          <Logo />
        </Link>
        <Card className="w-full max-w-sm">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
              <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <CardTitle>Revisá tu email</CardTitle>
            <CardDescription>
              Si existe una cuenta con <strong>{email}</strong>, te enviamos un código de 6 dígitos para restablecer tu contraseña.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button className="w-full" asChild>
              <Link href="/reset-password">Ingresar código</Link>
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              Te redirigimos a la página para ingresar el código...
            </p>
            <Button variant="outline" className="w-full" asChild>
              <Link href="/login">Volver a Iniciar Sesión</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-4">
      <Link href="/" className="mb-8">
        <Logo />
      </Link>
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle>Recuperar Contraseña</CardTitle>
          <CardDescription>
            Ingresá tu email y te enviaremos un código de verificación.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  placeholder="tu@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="pl-10"
                />
              </div>
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Enviando..." : "Enviar código"}
            </Button>
          </form>
          <div className="text-center">
            <Link
              href="/login"
              className="inline-flex items-center gap-1 text-sm text-muted-foreground underline-offset-4 hover:underline"
            >
              <ArrowLeft className="h-3 w-3" />
              Volver a Iniciar Sesión
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
