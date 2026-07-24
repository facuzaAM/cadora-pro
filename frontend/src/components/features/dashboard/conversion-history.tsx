"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileText,
  Download,
  RefreshCw,
  Eye,
  CheckCircle2,
  AlertCircle,
  Loader2,
  MoreHorizontal,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { projectsService } from "@/services/projects.service";
import { documentsService } from "@/services/documents.service";
import { cadService } from "@/services/cad.service";
import { toast } from "sonner";
import type { Project, ProjectStatus } from "@/types";

interface ConversionRow {
  project: Project;
  filename: string;
  fileSize: number | null;
}

const statusConfig: Record<
  ProjectStatus,
  { label: string; variant: "success" | "warning" | "secondary" | "destructive"; icon: React.ComponentType<{ className?: string }> }
> = {
  created: { label: "Creado", variant: "secondary", icon: FileText },
  document_uploaded: { label: "Subido", variant: "secondary", icon: FileText },
  processing: { label: "Procesando", variant: "warning", icon: Loader2 },
  detection_completed: { label: "Detección lista", variant: "success", icon: CheckCircle2 },
  cad_generated: { label: "Completado", variant: "success", icon: CheckCircle2 },
  error: { label: "Error", variant: "destructive", icon: AlertCircle },
};

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("es-AR", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatFileSize(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ConversionHistory() {
  const [rows, setRows] = useState<ConversionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [reprocessing, setReprocessing] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token") || undefined;
    projectsService
      .list(token)
      .then(async (projects) => {
        const sorted = [...projects].sort(
          (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
        );

        const rowsWithDocs = await Promise.all(
          sorted.map(async (p) => {
            let filename = p.name;
            let fileSize: number | null = null;
            try {
              const docs = await documentsService.getByProject(p.id, token);
              if (docs.length > 0) {
                filename = docs[0].filename;
                fileSize = docs[0].file_size;
              }
            } catch {
              // use project name as fallback
            }
            return { project: p, filename, fileSize };
          }),
        );

        setRows(rowsWithDocs);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleDownload = async (projectId: string) => {
    const token = localStorage.getItem("access_token") || undefined;
    try {
      await cadService.generate(projectId, "dxf", token);
      const url = cadService.downloadUrl(projectId, "dxf");
      window.open(url, "_blank");
      toast.success("Archivo DXF descargado");
    } catch {
      toast.error("Error al generar el archivo");
    }
  };

  const handleReprocess = async (projectId: string) => {
    setReprocessing(projectId);
    const token = localStorage.getItem("access_token") || undefined;
    try {
      await cadService.generate(projectId, "dxf", token);
      toast.success("Proyecto reprocesado correctamente");
      setRows((prev) =>
        prev.map((r) =>
          r.project.id === projectId
            ? { ...r, project: { ...r.project, status: "cad_generated" as ProjectStatus } }
            : r,
        ),
      );
    } catch {
      toast.error("Error al reprocesar");
    } finally {
      setReprocessing(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 animate-pulse rounded-lg border bg-muted/30" />
        ))}
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border p-12 text-center">
        <FileText className="mx-auto h-10 w-10 text-muted-foreground/40" />
        <p className="mt-3 text-sm text-muted-foreground">
          No hay conversiones aún. Subí tu primer plano para empezar.
        </p>
        <Button asChild className="mt-4" size="sm">
          <Link href="/projects/upload/new">Nuevo Proyecto</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {rows.map((row) => {
        const cfg = statusConfig[row.project.status] || statusConfig.created;
        const StatusIcon = cfg.icon;
        const isProcessing = row.project.status === "processing";
        const isCompleted = row.project.status === "cad_generated";

        return (
          <div
            key={row.project.id}
            className="flex items-center gap-4 rounded-lg border px-4 py-3 transition-colors hover:bg-muted/30"
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <FileText className="h-4 w-4 text-primary" />
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <p className="truncate text-sm font-medium">{row.project.name}</p>
                <Badge variant={cfg.variant} className="shrink-0 gap-1">
                  <StatusIcon className={`h-3 w-3 ${isProcessing ? "animate-spin" : ""}`} />
                  {cfg.label}
                </Badge>
              </div>
              <div className="mt-0.5 flex items-center gap-3 text-xs text-muted-foreground">
                <span className="truncate">{row.filename}</span>
                {row.fileSize && <span>· {formatFileSize(row.fileSize)}</span>}
                <span>· {formatDate(row.project.updated_at)}</span>
              </div>
            </div>

            <div className="flex items-center gap-1 shrink-0">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                asChild
              >
                <Link href={`/projects/${row.project.id}/result`} title="Ver resultado">
                  <Eye className="h-4 w-4" />
                </Link>
              </Button>

              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                disabled={!isCompleted}
                onClick={() => handleDownload(row.project.id)}
                title="Descargar DXF"
              >
                <Download className="h-4 w-4" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                disabled={isProcessing || reprocessing === row.project.id}
                onClick={() => handleReprocess(row.project.id)}
                title="Reprocesar"
              >
                {reprocessing === row.project.id ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
              </Button>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem asChild>
                    <Link href={`/projects/${row.project.id}/result`}>
                      <Eye className="mr-2 h-4 w-4" />
                      Ver resultado
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    disabled={!isCompleted}
                    onClick={() => handleDownload(row.project.id)}
                  >
                    <Download className="mr-2 h-4 w-4" />
                    Descargar DXF
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    disabled={isProcessing}
                    onClick={() => handleReprocess(row.project.id)}
                  >
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Reprocesar
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        );
      })}
    </div>
  );
}
