"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const error = searchParams.get("error");
    if (error) {
      router.replace(`/login?error=${encodeURIComponent(error)}`);
    } else {
      router.replace("/dashboard");
    }
  }, [router, searchParams]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-muted-foreground">Redirigiendo...</p>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Redirigiendo...</p>
      </div>
    }>
      <CallbackContent />
    </Suspense>
  );
}
