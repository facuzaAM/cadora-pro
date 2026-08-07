"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { UploadZone } from "@/components/features/projects/upload-zone";
import { documentsService } from "@/services/documents.service";
import { api } from "@/services/api";
import { toast } from "sonner";

export default function UploadToProjectPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!file || loading) return;
    setLoading(true);
    try {
      const token = api.getAccessToken();
      await documentsService.upload(projectId, file, token);
      router.push(`/projects/${projectId}/processing`);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Error al subir el archivo. Intenta de nuevo.",
      );
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
        <h1 className="mt-2 text-2xl font-bold tracking-tight">Subir Plano</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Sube un nuevo plano a este proyecto para reprocesarlo.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Subir Plano</CardTitle>
        </CardHeader>
        <CardContent>
          <UploadZone onFileSelect={setFile} />
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button size="lg" disabled={!file || loading} onClick={handleSubmit}>
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Subiendo...
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
