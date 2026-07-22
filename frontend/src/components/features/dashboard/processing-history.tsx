"use client";

import { useEffect, useState } from "react";
import type React from "react";
import { CheckCircle2, Clock, AlertCircle, Loader2, FileDown, Upload } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { projectsService } from "@/services/projects.service";
import type { Project } from "@/types";

interface HistoryItem {
  id: string;
  type: "upload" | "processing" | "completed" | "export" | "error";
  title: string;
  description: string;
  timestamp: string;
}

function projectToHistory(p: Project): HistoryItem {
  const typeMap: Record<string, HistoryItem["type"]> = {
    created: "upload",
    document_uploaded: "upload",
    processing: "processing",
    detection_completed: "completed",
    cad_generated: "completed",
    error: "error",
  };
  const descMap: Record<string, string> = {
    created: "Proyecto creado",
    document_uploaded: "Documento subido al sistema",
    processing: "Procesando detección del plano",
    detection_completed: "Detección completada",
    cad_generated: "Archivo DXF generado",
    error: "Error en el procesamiento",
  };
  return {
    id: p.id,
    type: typeMap[p.status] || "upload",
    title: p.name,
    description: descMap[p.status] || "Estado desconocido",
    timestamp: p.updated_at,
  };
}

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

const iconMap: Record<string, { icon: React.ComponentType<{ className?: string }>; color: string; bg: string; spin?: boolean }> = {
  upload: { icon: Upload, color: "text-primary", bg: "bg-primary/10 ring-primary/20" },
  processing: { icon: Loader2, color: "text-amber-500 dark:text-amber-400", bg: "bg-amber-500/10 ring-amber-500/20", spin: true },
  completed: { icon: CheckCircle2, color: "text-emerald-500 dark:text-emerald-400", bg: "bg-emerald-500/10 ring-emerald-500/20" },
  export: { icon: FileDown, color: "text-violet-500 dark:text-violet-400", bg: "bg-violet-500/10 ring-violet-500/20" },
  error: { icon: AlertCircle, color: "text-red-500 dark:text-red-400", bg: "bg-red-500/10 ring-red-500/20" },
};

export function ProcessingHistory() {
  const [history, setHistory] = useState<HistoryItem[]>([]);

  useEffect(() => {
    const token = localStorage.getItem("access_token") || undefined;
    projectsService.list(token).then((projects) => {
      const sorted = [...projects]
        .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
        .slice(0, 6)
        .map(projectToHistory);
      setHistory(sorted);
    }).catch(() => {});
  }, []);

  return (
    <Card>
      <CardHeader className="px-5 py-4">
        <CardTitle className="text-sm font-medium">Historial</CardTitle>
      </CardHeader>
      <Separator />
      <CardContent className="p-0">
        {history.length === 0 ? (
          <div className="px-5 py-8 text-center text-sm text-muted-foreground">
            Sin actividad reciente.
          </div>
        ) : (
          <div className="p-1">
            {history.map((item, idx) => {
              const cfg = iconMap[item.type];
              const Icon = cfg.icon;
              const isLast = idx === history.length - 1;
              return (
                <div key={item.id} className="relative flex gap-4 px-4 py-3">
                  {!isLast && (
                    <div className="absolute left-[26px] top-12 bottom-0 w-px bg-border" />
                  )}
                  <div className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-full ring-1",
                    cfg.bg,
                  )}>
                    <Icon className={cn("h-4 w-4", cfg.color, cfg.spin && "animate-spin")} />
                  </div>
                  <div className="min-w-0 flex-1 pt-1">
                    <p className="text-sm font-medium">{item.title}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{item.description}</p>
                    <p className="mt-1 flex items-center gap-1 text-[11px] text-muted-foreground/60">
                      <Clock className="h-3 w-3" />
                      {timeAgo(item.timestamp)}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
