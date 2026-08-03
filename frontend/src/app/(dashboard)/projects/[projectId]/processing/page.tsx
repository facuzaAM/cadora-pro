"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { cadService } from "@/services/cad.service";
import { projectsService } from "@/services/projects.service";
import { api, ApiError } from "@/services/api";
import { toast } from "sonner";

const POLL_INTERVAL_MS = 4000;

export default function ProcessingPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;
  const [processing, setProcessing] = useState(true);
  const generatedRef = useRef(false);
  const finishedRef = useRef(false);

  const finish = useCallback(() => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    setProcessing(false);
    setTimeout(() => router.replace(`/projects/${projectId}/result?ready=1`), 1000);
  }, [projectId, router]);

  useEffect(() => {
    const token = api.getAccessToken();
    let timer: ReturnType<typeof setInterval> | null = null;
    let stopped = false;

    const stop = () => {
      stopped = true;
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    };

    const generateOnce = async (): Promise<void> => {
      if (generatedRef.current) return;
      generatedRef.current = true;
      try {
        await cadService.generate(projectId, "dxf", token);
        finish();
      } catch (err) {
        generatedRef.current = false;
        if (err instanceof ApiError && err.status === 402) {
          toast.error("Alcanzaste el límite de conversiones de tu plan");
          router.replace("/billing");
          return;
        }
        if (err instanceof ApiError && err.status === 409) {
          return;
        }
        toast.error("Error al procesar el plano");
        router.replace(`/projects/${projectId}/result`);
      }
    };

    const checkStatus = async (): Promise<boolean> => {
      try {
        const p = await projectsService.getById(projectId, token);
        if (p.status === "cad_generated") {
          finish();
          return true;
        }
        if (p.status === "error") {
          toast.error("El plano no pudo procesarse");
          router.replace(`/projects/${projectId}/result`);
          return true;
        }
        if (
          p.status === "created" ||
          p.status === "document_uploaded" ||
          p.status === "detection_completed"
        ) {
          await generateOnce();
          return false;
        }
        return false;
      } catch {
        toast.error("Error cargando proyecto");
        return true;
      }
    };

    checkStatus().then((done) => {
      if (!done && !stopped) {
        timer = setInterval(async () => {
          if (stopped) return;
          const doneNow = await checkStatus();
          if (doneNow) stop();
        }, POLL_INTERVAL_MS);
      }
    });

    return stop;
  }, [projectId, router, finish]);

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
