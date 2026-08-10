"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Clock,
  FileText,
  FileUp,
  Pencil,
  Trash2,
  Calendar,
  Download,
  Loader2,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import { projectsService } from "@/services/projects.service";
import { documentsService } from "@/services/documents.service";
import { cadService } from "@/services/cad.service";
import { api } from "@/services/api";
import { toast } from "sonner";
import type { Project, ProjectStatus } from "@/types";
import type { Document as CadoraDocument } from "@/types";

const statusConfig: Record<
  ProjectStatus,
  { label: string; variant: "success" | "warning" | "secondary" | "destructive" | "default"; icon: React.ComponentType<{ className?: string }> }
> = {
  created: { label: "Creado", variant: "secondary", icon: FileText },
  document_uploaded: { label: "Documento subido", variant: "secondary", icon: FileText },
  processing: { label: "Procesando", variant: "warning", icon: RefreshCw },
  detection_running: { label: "Procesando", variant: "warning", icon: RefreshCw },
  detection_processing: { label: "Procesando", variant: "warning", icon: RefreshCw },
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

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ProjectDetailPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;
  const [project, setProject] = useState<Project | null>(null);
  const [documents, setDocuments] = useState<CadoraDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const token = api.getAccessToken();
    let active = true;
    Promise.all([
      projectsService.getById(projectId, token),
      documentsService.getByProject(projectId, token).catch(() => []),
    ])
      .then(([p, docs]) => {
        if (!active) return;
        setProject(p);
        setDocuments(docs);
      })
      .catch(() => {
        if (active) toast.error("Error al cargar el proyecto");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await projectsService.delete(projectId, api.getAccessToken());
      toast.success("Proyecto eliminado");
      router.push("/projects");
    } catch {
      toast.error("Error al eliminar el proyecto");
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-24 animate-pulse rounded-lg border bg-muted/30" />
        <div className="h-48 animate-pulse rounded-lg border bg-muted/30" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/30 px-6 py-16 text-center">
        <AlertCircle className="mb-4 h-8 w-8 text-destructive" />
        <h2 className="text-xl font-bold">Proyecto no encontrado</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Es posible que ya haya sido eliminado.
        </p>
        <Button className="mt-6" asChild variant="outline">
          <Link href="/projects">Volver a mis proyectos</Link>
        </Button>
      </div>
    );
  }

  const cfg = statusConfig[project.status] || statusConfig.created;
  const StatusIcon = cfg.icon;
  const isCompleted = project.status === "cad_generated";

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" onClick={() => router.back()}>
        <ArrowLeft className="mr-2 h-4 w-4" />
        Volver
      </Button>

      <PageHeader
        title={project.name}
        description={project.description || "Detalle del proyecto"}
        action={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => router.push(`/projects/${projectId}/editor`)}>
              <Pencil className="mr-2 h-4 w-4" />
              Editar plano
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link href={`/projects/${projectId}/upload`}>
                <FileUp className="mr-2 h-4 w-4" />
                Subir archivo
              </Link>
            </Button>
            <Button size="sm" asChild>
              <Link href={`/projects/${projectId}/result`}>
                Ver resultado
              </Link>
            </Button>
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          {/* Estado */}
          <Card>
            <CardContent className="flex flex-wrap items-center justify-between gap-4 p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <StatusIcon className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium">Estado del proyecto</p>
                  <p className="text-xs text-muted-foreground">
                    {project.document_count} documento{project.document_count !== 1 ? "s" : ""}
                  </p>
                </div>
              </div>
              <Badge variant={cfg.variant} className="gap-1">
                <StatusIcon className="h-3 w-3" />
                {cfg.label}
              </Badge>
            </CardContent>
          </Card>

          {/* Documentos */}
          <Card>
            <CardContent className="p-5">
              <div className="mb-4 flex items-center gap-2">
                <FileText className="h-4 w-4 text-muted-foreground" />
                <h2 className="text-sm font-medium">Documentos</h2>
              </div>
              {documents.length === 0 ? (
                <div className="flex flex-col items-center justify-center rounded-lg border border-dashed px-6 py-10 text-center">
                  <FileUp className="mb-3 h-6 w-6 text-muted-foreground/50" />
                  <p className="text-sm text-muted-foreground">
                    Este proyecto todavía no tiene documentos.
                  </p>
                  <Button className="mt-4" size="sm" asChild variant="outline">
                    <Link href={`/projects/${projectId}/upload`}>Subir un plano</Link>
                  </Button>
                </div>
              ) : (
                <ul className="divide-y">
                  {documents.map((doc) => (
                    <li key={doc.id} className="flex items-center gap-3 py-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                        <FileText className="h-4 w-4 text-primary" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{doc.filename}</p>
                        <p className="text-xs text-muted-foreground">
                          {doc.file_type.toUpperCase()} · {formatFileSize(doc.file_size)}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          {/* Información */}
          <Card>
            <CardContent className="space-y-3 p-5">
              <h2 className="text-sm font-medium">Información</h2>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Calendar className="h-4 w-4" />
                <span>Creado: {formatDate(project.created_at)}</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Clock className="h-4 w-4" />
                <span>Actualizado: {formatDate(project.updated_at)}</span>
              </div>
            </CardContent>
          </Card>

          {/* Acciones */}
          <Card>
            <CardContent className="space-y-2 p-5">
              <h2 className="text-sm font-medium">Acciones</h2>
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-start"
                onClick={() => router.push(`/projects/${projectId}/editor`)}
              >
                <Pencil className="mr-2 h-4 w-4" />
                Editar plano en línea
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-start"
                disabled={!isCompleted}
                onClick={() => {
                  window.open(cadService.downloadUrl(projectId, "dxf"), "_blank");
                }}
              >
                <Download className="mr-2 h-4 w-4" />
                Descargar DXF
              </Button>
              <Button
                variant="destructive"
                size="sm"
                className="w-full justify-start"
                disabled={deleting}
                onClick={handleDelete}
              >
                {deleting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="mr-2 h-4 w-4" />
                )}
                Eliminar proyecto
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
