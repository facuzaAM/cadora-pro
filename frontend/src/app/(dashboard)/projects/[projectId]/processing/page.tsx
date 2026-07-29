"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { cadService } from "@/services/cad.service";
import { api } from "@/services/api";
import { toast } from "sonner";

export default function ProcessingPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;
  const [processing, setProcessing] = useState(true);

  useEffect(() => {
    const token = api.getAccessToken();
    cadService.generate(projectId, "dxf", token)
      .then(() => {
        setProcessing(false);
        setTimeout(() => router.push(`/projects/${projectId}/result?ready=1`), 1000);
      })
      .catch(() => {
        toast.error("Error al procesar el plano");
        router.push(`/projects/${projectId}/result`);
      });
  }, [projectId, router]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Procesando plano"
        description="Estamos analizando tu plano arquitectónico para generar el archivo CAD."
      />

      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/30 px-6 py-16 text-center">
        <Loader2 className="mb-4 h-8 w-8 animate-spin text-primary" />
        <h2 className="text-xl font-bold">
          {processing ? "Procesando..." : "¡Completado!"}
        </h2>
        <p className="mt-2 max-w-md text-sm text-muted-foreground">
          {processing
            ? "Esto puede tomar unos segundos dependiendo del tamaño del plano."
            : "Redirigiendo al resultado..."}
        </p>
      </div>
    </div>
  );
}
