"use client";

import { useEffect, useMemo, useState } from "react";
import { Search, ChevronDown } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ProjectCard } from "./project-card";
import { EmptyProjects } from "./empty-projects";
import { projectsService } from "@/services/projects.service";
import { api } from "@/services/api";
import { toast } from "sonner";
import type { Project, ProjectStatus } from "@/types";

const statusMap: Record<ProjectStatus, { label: string; variant: "success" | "warning" | "secondary" | "default" }> = {
  created: { label: "Creado", variant: "secondary" },
  document_uploaded: { label: "Documento subido", variant: "secondary" },
  processing: { label: "Procesando", variant: "warning" },
  detection_running: { label: "Procesando", variant: "warning" },
  detection_processing: { label: "Procesando", variant: "warning" },
  detection_completed: { label: "Detección lista", variant: "success" },
  cad_generated: { label: "Completado", variant: "success" },
  error: { label: "Error", variant: "default" },
};

const PAGE_SIZE = 9;

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

export function ProjectList() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | ProjectStatus>("all");
  const [visible, setVisible] = useState(PAGE_SIZE);

  useEffect(() => {
    const token = api.getAccessToken();
    projectsService
      .list(token)
      .then((list) => {
        setProjects(list);
        setVisible(PAGE_SIZE);
      })
      .catch(() => toast.error("Error al cargar proyectos"))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return projects
      .filter((p) => (statusFilter === "all" ? true : p.status === statusFilter))
      .filter((p) => !q || p.name.toLowerCase().includes(q))
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
  }, [projects, query, statusFilter]);

  const hasQueryOrFilter = query.trim() !== "" || statusFilter !== "all";

  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-32 animate-pulse rounded-lg border bg-muted/30" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setVisible(PAGE_SIZE);
            }}
            placeholder="Buscar por nombre..."
            className="pl-9"
            aria-label="Buscar proyectos por nombre"
          />
        </div>
        <div className="flex items-center gap-2 overflow-x-auto">
          {(["all", "cad_generated", "processing", "error", "created"] as const).map((s) => (
            <Button
              key={s}
              size="sm"
              variant={statusFilter === s ? "default" : "outline"}
              onClick={() => {
                setStatusFilter(s as "all" | ProjectStatus);
                setVisible(PAGE_SIZE);
              }}
            >
              {s === "all" ? "Todos" : statusMap[s].label}
            </Button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        hasQueryOrFilter ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/30 px-6 py-16 text-center">
            <Search className="mb-4 h-8 w-8 text-muted-foreground" />
            <h3 className="text-lg font-semibold">Sin resultados</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              No encontramos proyectos que coincidan con tu búsqueda.
            </p>
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => {
                setQuery("");
                setStatusFilter("all");
                setVisible(PAGE_SIZE);
              }}
            >
              Limpiar filtros
            </Button>
          </div>
        ) : (
          <EmptyProjects />
        )
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.slice(0, visible).map((p) => {
              const cfg = statusMap[p.status] || statusMap.created;
              return (
                <ProjectCard
                  key={p.id}
                  id={p.id}
                  name={p.name}
                  status={cfg.label}
                  statusVariant={cfg.variant}
                  updatedAt={timeAgo(p.updated_at)}
                  documentCount={p.document_count ?? 0}
                  onDelete={(id) => setProjects((prev) => prev.filter((x) => x.id !== id))}
                />
              );
            })}
          </div>
          {filtered.length > visible && (
            <div className="flex justify-center pt-2">
              <Button variant="outline" onClick={() => setVisible((v) => v + PAGE_SIZE)}>
                <ChevronDown className="mr-2 h-4 w-4" />
                Cargar más
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
