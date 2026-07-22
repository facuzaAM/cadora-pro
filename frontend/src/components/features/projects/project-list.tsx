"use client";

import { useEffect, useState } from "react";
import { ProjectCard } from "./project-card";
import { EmptyProjects } from "./empty-projects";
import { projectsService } from "@/services/projects.service";
import type { Project, ProjectStatus } from "@/types";

const statusMap: Record<ProjectStatus, { label: string; variant: "success" | "warning" | "secondary" | "default" }> = {
  created: { label: "Creado", variant: "secondary" },
  document_uploaded: { label: "Documento subido", variant: "secondary" },
  processing: { label: "Procesando", variant: "warning" },
  detection_completed: { label: "Detección lista", variant: "success" },
  cad_generated: { label: "Completado", variant: "success" },
  error: { label: "Error", variant: "default" },
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

export function ProjectList() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token") || undefined;
    projectsService
      .list(token)
      .then(setProjects)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-32 animate-pulse rounded-lg border bg-muted/30" />
        ))}
      </div>
    );
  }

  if (projects.length === 0) {
    return <EmptyProjects />;
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {projects.map((p) => {
        const cfg = statusMap[p.status] || statusMap.created;
        return (
          <ProjectCard
            key={p.id}
            id={p.id}
            name={p.name}
            status={cfg.label}
            statusVariant={cfg.variant}
            updatedAt={timeAgo(p.updated_at)}
            documentCount={0}
          />
        );
      })}
    </div>
  );
}
