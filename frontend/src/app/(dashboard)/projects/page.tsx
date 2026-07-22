"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { ProjectList } from "@/components/features/projects/project-list";

export default function ProjectsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Mis Proyectos"
        description="Gestiona tus proyectos de conversión CAD"
        action={
          <Button asChild>
            <Link href="/projects/upload/new">
              <Plus className="mr-2 h-4 w-4" />
              Nuevo Proyecto
            </Link>
          </Button>
        }
      />

      <ProjectList />
    </div>
  );
}
