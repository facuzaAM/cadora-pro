"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";

export function CookieConsent() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const accepted = localStorage.getItem("cookies_accepted");
    if (!accepted) setVisible(true);
  }, []);

  const accept = () => {
    localStorage.setItem("cookies_accepted", "true");
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="fixed bottom-0 z-50 w-full border-t bg-card p-4 shadow-lg">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 sm:flex-row">
        <p className="text-sm text-muted-foreground">
          Usamos cookies esenciales para el funcionamiento del sitio.{" "}
          <Link href="/cookies" className="text-primary underline-offset-4 hover:underline">
            Más información
          </Link>
        </p>
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={accept}>
            Aceptar
          </Button>
          <Button variant="ghost" size="icon" onClick={accept}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
