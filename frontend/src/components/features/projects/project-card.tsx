"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileText, MoreHorizontal, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { projectsService } from "@/services/projects.service";
import { api } from "@/services/api";
import { toast } from "sonner";

interface ProjectCardProps {
  id: string;
  name: string;
  status: string;
  statusVariant: "success" | "warning" | "secondary" | "default";
  updatedAt: string;
  documentCount: number;
  onDelete?: (id: string) => void;
}

export function ProjectCard({
  id,
  name,
  status,
  statusVariant,
  updatedAt,
  documentCount,
  onDelete,
}: ProjectCardProps) {
  const router = useRouter();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await projectsService.delete(id, api.getAccessToken());
      toast.success("Proyecto eliminado");
      onDelete?.(id);
    } catch {
      toast.error("Error al eliminar el proyecto");
    } finally {
      setDeleting(false);
      setDeleteOpen(false);
    }
  };

  return (
    <>
      <Card className="transition-colors hover:border-primary/50">
        <CardContent className="p-5">
          <div className="flex items-start justify-between">
            <Link href={`/projects/${id}/result`} className="flex items-start gap-3 flex-1">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                <FileText className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold leading-none">{name}</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {documentCount} documento{documentCount !== 1 ? "s" : ""} · {updatedAt}
                </p>
              </div>
            </Link>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="-mr-2 -mt-2">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => router.push(`/projects/${id}/result`)}>
                  Ver proyecto
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => router.push(`/projects/${id}/upload`)}>
                  Subir archivo
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="text-destructive"
                  onClick={() => setDeleteOpen(true)}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Eliminar
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardContent>
        <CardFooter className="border-t px-5 py-3">
          <Badge variant={statusVariant}>{status}</Badge>
        </CardFooter>
      </Card>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar proyecto</DialogTitle>
            <DialogDescription>
              ¿Estás seguro de que quieres eliminar &quot;{name}&quot;? Esta acción no se puede deshacer.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)} disabled={deleting}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? "Eliminando..." : "Eliminar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
