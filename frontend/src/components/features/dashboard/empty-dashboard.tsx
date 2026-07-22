"use client";

import { useAuth } from "@/hooks/useAuth";
import { FolderKanban, ArrowRight } from "lucide-react";
import Link from "next/link";

export function EmptyDashboard() {
  const { user } = useAuth();
  const name = user?.name || user?.email?.split("@")[0] || "";

  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/30 px-6 py-16 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
        <FolderKanban className="h-8 w-8 text-primary" />
      </div>
      <h2 className="mt-6 text-xl font-bold">¡Bienvenido, {name}!</h2>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        Empezá subiendo tu primer plano arquitectónico. En segundos obtené un archivo CAD editable con detección automática de muros, puertas y ventanas.
      </p>
      <div className="mt-8 grid gap-3 sm:grid-cols-3">
        {[
          { step: "1", title: "Subí tu plano", desc: "PDF o imagen, hasta 50 MB" },
          { step: "2", title: "Se procesa solo", desc: "Detección en segundos" },
          { step: "3", title: "Descargá CAD", desc: "DXF listo para editar" },
        ].map((s) => (
          <div key={s.step} className="rounded-lg border bg-card p-4 text-left">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
              {s.step}
            </div>
            <p className="mt-2 text-sm font-medium">{s.title}</p>
            <p className="text-xs text-muted-foreground">{s.desc}</p>
          </div>
        ))}
      </div>
      <Link
        href="/projects/upload/new"
        className="mt-8 inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-6 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90"
      >
        Subir mi primer plano
        <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
