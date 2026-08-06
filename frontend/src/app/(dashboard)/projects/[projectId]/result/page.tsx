"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import { ArrowLeft, Download, Share2, Loader2, ChevronDown, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { PageHeader } from "@/components/shared/page-header";
import { projectsService } from "@/services/projects.service";
import { cadService, type CadFormat } from "@/services/cad.service";
import { useAuth } from "@/hooks/useAuth";
import { api, ApiError } from "@/services/api";
import { toast } from "sonner";

const DWG_PLANS = new Set(["pro", "business"]);

export default function ResultPage() {
  return (
    <Suspense fallback={<div className="space-y-6" />}>
      <ResultContent />
    </Suspense>
  );
}

function ResultContent() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const projectId = params.projectId as string;
  const { user } = useAuth();
  const [projectName, setProjectName] = useState("Proyecto");
  const [downloading, setDownloading] = useState(false);
  const [cadReady, setCadReady] = useState(searchParams.has("ready"));
  const generatedRef = useRef(false);
  const readyRef = useRef(false);

  const canExportDwg = user && DWG_PLANS.has(user.subscription_plan);

  const markReady = useCallback(() => {
    if (readyRef.current) return;
    readyRef.current = true;
    setCadReady(true);
  }, []);

  const generateCad = useCallback(
    async (token?: string) => {
      if (generatedRef.current) return;
      generatedRef.current = true;
      try {
        await cadService.generate(projectId, "dxf", token);
        markReady();
      } catch (err) {
        generatedRef.current = false;
        if (err instanceof ApiError && err.status === 402) {
          toast.error("Alcanzaste el límite de conversiones de tu plan");
          return;
        }
        if (err instanceof ApiError && err.status === 409) {
          return;
        }
        toast.error("Error al generar el archivo CAD");
      }
    },
    [projectId, markReady],
  );

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
      try {
        const p = await projectsService.getById(projectId, token);
        setProjectName(p.name);
        if (p.status === "cad_generated") {
          markReady();
          return true;
        }
        if (p.status === "error") {
          toast.error("El plano no pudo procesarse");
          return true;
        }
        if (
          p.status === "created" ||
          p.status === "document_uploaded" ||
          p.status === "detection_completed"
        ) {
          await generateCad(token);
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
        }, 4000);
      }
    });

    return stop;
  }, [projectId, generateCad, markReady]);

  const handleDownload = async (format: CadFormat = "dxf") => {
    setDownloading(true);
    try {
      const url = cadService.downloadUrl(projectId, format);
      window.open(url, "_blank");
      toast.success(`Archivo ${format.toUpperCase()} en descarga`);
    } catch {
      toast.error("Error al descargar el archivo");
    } finally {
      setDownloading(false);
    }
  };

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({ title: projectName, url: window.location.href });
    } else {
      navigator.clipboard.writeText(window.location.href);
      toast.success("Enlace copiado al portapapeles");
    }
  };

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" onClick={() => router.back()}>
        <ArrowLeft className="mr-2 h-4 w-4" />
        Volver
      </Button>

      <PageHeader
        title={projectName}
        description={cadReady ? "Plano procesado exitosamente" : "Procesando plano..."}
        action={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleShare}>
              <Share2 className="mr-2 h-4 w-4" />
              Compartir
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push(`/projects/${projectId}/editor`)}
            >
              <Pencil className="mr-2 h-4 w-4" />
              Editar plano
            </Button>
            {cadReady ? (
              canExportDwg ? (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button size="sm" disabled={downloading}>
                      {downloading ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <Download className="mr-2 h-4 w-4" />
                      )}
                      Exportar
                      <ChevronDown className="ml-1 h-3 w-3" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => handleDownload("dxf")}>
                      DXF
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleDownload("dwg")}>
                      DWG
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              ) : (
                <Button size="sm" onClick={() => handleDownload("dxf")} disabled={downloading}>
                  {downloading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="mr-2 h-4 w-4" />
                  )}
                  Exportar DXF
                </Button>
              )
            ) : (
              <Button size="sm" disabled>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Procesando...
              </Button>
            )}
          </div>
        }
      />

      {!cadReady && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/30 px-6 py-16 text-center">
          <Loader2 className="mb-4 h-8 w-8 animate-spin text-primary" />
          <h2 className="text-xl font-bold">Procesando plano</h2>
          <p className="mt-2 max-w-md text-sm text-muted-foreground">
            Estamos generando el archivo CAD a partir de tu plano. Esto puede tomar unos segundos.
          </p>
        </div>
      )}

      {cadReady && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/30 px-6 py-16 text-center">
          <Download className="mb-4 h-8 w-8 text-emerald-500" />
          <h2 className="text-xl font-bold">Plano listo para descargar</h2>
          <p className="mt-2 max-w-md text-sm text-muted-foreground">
            El archivo CAD se generó correctamente. Usá el botón Exportar para descargarlo en formato DXF{canExportDwg ? " o DWG" : ""}.
          </p>
        </div>
      )}
    </div>
  );
}
