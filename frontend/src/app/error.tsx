"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Logo } from "@/components/shared/logo";
import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-4">
      <Logo />
      <div className="mt-8 text-center">
        <p className="text-6xl font-bold text-destructive">500</p>
        <h1 className="mt-4 text-2xl font-bold">Error del servidor</h1>
        <p className="mt-2 text-muted-foreground">
          Algo salió mal. Intentá de nuevo o contactanos si el problema persiste.
        </p>
        <div className="mt-8 flex items-center justify-center gap-4">
          <Button onClick={reset}>Intentar de nuevo</Button>
            <Button variant="outline" asChild>
            <Link href="/">Volver al inicio</Link>
            </Button>
        </div>
      </div>
    </div>
  );
}
