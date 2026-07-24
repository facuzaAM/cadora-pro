"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function DashboardError({
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
    <div className="flex items-center justify-center py-16">
      <Card className="w-full max-w-md">
        <CardContent className="flex flex-col items-center p-8 text-center">
          <AlertTriangle className="mb-4 h-10 w-10 text-destructive" />
          <h2 className="text-lg font-bold">Algo salió mal</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Ocurrió un error inesperado. Intentá de nuevo.
          </p>
          <div className="mt-6 flex items-center gap-3">
            <Button onClick={reset} size="sm">Reintentar</Button>
            <Button variant="outline" size="sm" asChild>
              <Link href="/dashboard">Volver al dashboard</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
