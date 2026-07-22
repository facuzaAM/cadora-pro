import { FolderKanban } from "lucide-react";
import { EmptyState } from "@/components/shared/empty-state";

export function EmptyProjects() {
  return (
    <EmptyState
      icon={FolderKanban}
      title="No tenés proyectos todavía"
      description="Subí tu primer plano arquitectónico para empezar a convertirlo a CAD."
      action={{ label: "Subir plano", href: "/projects/upload/new" }}
    />
  );
}
