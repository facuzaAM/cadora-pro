"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText, ArrowUpRight, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { projectsService } from "@/services/projects.service";
import { api } from "@/services/api";
import type { Project } from "@/types";

const statusConfig: Record<string, { label: string; variant: "success" | "warning" | "secondary" | "destructive" }> = {
  created: { label: "Creado", variant: "secondary" },
  document_uploaded: { label: "Documento subido", variant: "secondary" },
  processing: { label: "Procesando", variant: "warning" },
  detection_completed: { label: "Detección lista", variant: "success" },
  cad_generated: { label: "Completado", variant: "success" },
  error: { label: "Error", variant: "destructive" },
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "ahora";
  if (mins < 60) return `hace ${mins} min`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `hace ${hrs}h`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `hace ${days}d`;
  return `hace ${Math.floor(days / 7)}sem`;
}

export function RecentProjects() {
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    const token = api.getAccessToken();
    projectsService.list(token).then(setProjects).catch(() => {});
  }, []);

  return (
    <Card className="overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between px-5 py-4">
        <CardTitle className="text-sm font-medium">Últimos Proyectos</CardTitle>
        <Button variant="ghost" size="sm" className="gap-1 text-xs" asChild>
          <Link href="/projects">
            Ver todos
            <ArrowUpRight className="h-3 w-3" />
          </Link>
        </Button>
      </CardHeader>
      <Separator />
      <CardContent className="p-0">
        {projects.length === 0 ? (
          <div className="px-5 py-8 text-center text-sm text-muted-foreground">
            No hay proyectos aún. Sube tu primer plano.
          </div>
        ) : (
          <div className="divide-y">
            {projects.slice(0, 5).map((p) => {
              const cfg = statusConfig[p.status] || statusConfig.created;
              const Icon = FileText;
              return (
                <Link
                  key={p.id}
                  href={`/projects/${p.id}/result`}
                  className="flex items-center gap-4 px-5 py-3.5 transition-colors hover:bg-muted/30"
                >
                  <div className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ring-1",
                    p.status === "cad_generated" ? "bg-emerald-500/10 ring-emerald-500/20 text-emerald-600 dark:text-emerald-400" :
                    p.status === "processing" ? "bg-amber-500/10 ring-amber-500/20 text-amber-600 dark:text-amber-400" :
                    p.status === "error" ? "bg-red-500/10 ring-red-500/20 text-red-600 dark:text-red-400" :
                    "bg-muted ring-border text-muted-foreground",
                  )}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{p.name}</p>
                    <div className="mt-0.5 flex items-center gap-3 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {timeAgo(p.updated_at)}
                      </span>
                    </div>
                  </div>
                  <Badge variant={cfg.variant} className="shrink-0">
                    {cfg.label}
                  </Badge>
                </Link>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
