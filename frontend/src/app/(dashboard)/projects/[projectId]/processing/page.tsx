"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { projectsService } from "@/services/projects.service";
import { api } from "@/services/api";
import { toast } from "sonner";

const POLL_INTERVAL_MS = 2500;

export default function ProcessingPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;
  const [processing, setProcessing] = useState(true);
  const finishedRef = useRef(false);

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

    const checkStatus = async (): Promise<boolean> => {
      if (finishedRef.current) return true;
      try {
        const p = await projectsService.getById(projectId, token);
        if (p.status === "error") {
          finishedRef.current = true;
          toast.error("El plano no pudo procesarse");
          router.replace(`/projects/${projectId}/result`);
          return true;
        }
        if (p.status !== "created") {
          finishedRef.current = true;
          setProcessing(false);
          setTimeout(() => router.replace(`/projects/${projectId}/editor`), 800);
          return true;
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
  }, [projectId, router]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Preparando plano"
        description="Vas a poder revisar y ajustar el plano antes de exportar el archivo CAD."
      />

      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/30 px-6 py-16 text-center">
        <Loader2 className="mb-4 h-8 w-8 animate-spin text-primary" />
        <h2 className="text-xl font-bold">
          {processing ? "Preparando..." : "¡Listo!"}
        </h2>
        <p className="mt-2 max-w-md text-sm text-muted-foreground">
          {processing
            ? "Estamos cargando tu plano para abrir el editor."
            : "Abriendo el editor de planos..."}
        </p>
      </div>
    </div>
  );
}
