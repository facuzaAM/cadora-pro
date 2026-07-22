"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { UploadZone } from "@/components/features/projects/upload-zone";
import { projectsService } from "@/services/projects.service";
import { documentsService } from "@/services/documents.service";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "sonner";

export default function UploadPage() {
  const router = useRouter();
  const { user: _user } = useAuth();
  const [projectName, setProjectName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);

  const canSubmit = projectName.length >= 2 && file !== null;

  const handleSubmit = async () => {
    if (!canSubmit || !file) return;
    setLoading(true);
    try {
      const token = localStorage.getItem("access_token") || undefined;
      const project = await projectsService.create(
        { name: projectName, description: description || undefined },
        token,
      );
      await documentsService.upload(project.id, file, token);
      router.push(`/projects/${project.id}/processing`);
    } catch {
      toast.error("Error al crear el proyecto. Intenta de nuevo.");
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <Button variant="ghost" size="sm" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Volver
        </Button>
        <h1 className="mt-2 text-2xl font-bold tracking-tight">Nuevo Proyecto</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Sube tu plano arquitectónico para comenzar el procesamiento.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Información del Proyecto</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Nombre del Proyecto</Label>
            <Input
              id="name"
              placeholder="Ej: Casa Rodríguez"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="desc">Descripción (opcional)</Label>
            <Textarea
              id="desc"
              placeholder="Breve descripción del plano..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Subir Plano</CardTitle>
        </CardHeader>
        <CardContent>
          <UploadZone onFileSelect={setFile} />
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button size="lg" disabled={!canSubmit || loading} onClick={handleSubmit}>
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Creando proyecto...
            </>
          ) : (
            <>
              Procesar Plano
              <ArrowRight className="ml-2 h-4 w-4" />
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
