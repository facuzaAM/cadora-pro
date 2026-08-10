"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading } = useAuth();
  const [handled, setHandled] = useState(false);

  useEffect(() => {
    if (handled) return;
    const error = searchParams.get("error");
    if (error) {
      setHandled(true);
      router.replace(`/login?error=${encodeURIComponent(error)}`);
      return;
    }
    if (loading) return;
    setHandled(true);
    if (user) {
      const plan = searchParams.get("plan");
      if (plan) {
        router.replace(
          user.email_verified
            ? `/pricing?plan=${encodeURIComponent(plan)}`
            : `/verify-email?redirectTo=${encodeURIComponent(`/pricing?plan=${encodeURIComponent(plan)}`)}`,
        );
        return;
      }
      router.replace(user.email_verified ? "/dashboard" : "/verify-email");
    } else {
      router.replace("/login?error=oauth_failed");
    }
  }, [router, searchParams, user, loading, handled]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
      <p className="text-sm text-muted-foreground">Iniciando sesión con Google...</p>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen flex-col items-center justify-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Iniciando sesión con Google...</p>
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}
