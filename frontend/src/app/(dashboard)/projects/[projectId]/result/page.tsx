"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import { ArrowLeft, Download, Share2, Loader2, ChevronDown, Pencil, AlertCircle, RefreshCw } from "lucide-react";
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
import { editorService } from "@/services/editor.service";
import { track } from "@/lib/analytics";
import type { EditorDetection } from "@/types/editor";
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
  const [error, setError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const generatedRef = useRef(false);
  const readyRef = useRef(false);
  const [detectionPreview, setDetectionPreview] = useState<EditorDetection | null>(null);

  const canExportDwg = user && DWG_PLANS.has(user.subscription_plan);
  const token = api.getAccessToken();

  const markReady = useCallback(() => {
    if (readyRef.current) return;
    readyRef.current = true;
    setCadReady(true);
    track("cad_generated");
    // Cargar preview de detección para mostrarlo
    editorService.getDetection(projectId, token).then(setDetectionPreview).catch(() => {});
  }, [projectId, token]);

  const generateCad = useCallback(
    async (token?: string) => {
      if (generatedRef.current) return;
      generatedRef.current = true;
      try {
        await cadService.generate(projectId, "dxf", token);
        markReady();
      } catch (err) {
        if (err instanceof ApiError && err.status === 402) {
          generatedRef.current = true;
          toast.error("Alcanzaste el límite de conversiones de tu plan");
          return;
        }
        generatedRef.current = false;
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
        setError(false);
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
        setError(true);
        return false;
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
  }, [projectId, generateCad, markReady, retryCount]);

  const handleDownload = async (format: CadFormat = "dxf") => {
    setDownloading(true);
    try {
      const url = cadService.downloadUrl(projectId, format);
      window.open(url, "_blank");
      track("cad_download", { format });
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

      {!cadReady && !error && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/30 px-6 py-16 text-center">
          <Loader2 className="mb-4 h-8 w-8 animate-spin text-primary" />
          <h2 className="text-xl font-bold">Procesando plano</h2>
          <p className="mt-2 max-w-md text-sm text-muted-foreground">
            Estamos generando el archivo CAD a partir de tu plano. Esto puede tomar unos segundos.
          </p>
        </div>
      )}

      {error && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/30 px-6 py-16 text-center">
          <AlertCircle className="mb-4 h-8 w-8 text-destructive" />
          <h2 className="text-xl font-bold">No pudimos conectar</h2>
          <p className="mt-2 max-w-md text-sm text-muted-foreground">
            Hubo un problema al consultar el estado del proyecto. Revisá tu conexión e intentá de nuevo.
          </p>
          <Button
            className="mt-6"
            onClick={() => {
              setError(false);
              setRetryCount((c) => c + 1);
            }}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Reintentar
          </Button>
        </div>
      )}

      {cadReady && detectionPreview && (
        <div className="rounded-xl border bg-card overflow-hidden shadow-sm">
          <div className="relative aspect-[4/3] bg-muted/20 bg-grid-cad overflow-hidden">
            {detectionPreview.image_width && (
              <svg
                className="absolute inset-0 h-full w-full"
                viewBox={`0 0 ${detectionPreview.image_width || 1} ${detectionPreview.image_height || 1}`}
                preserveAspectRatio="xMidYMid meet"
              >
                {detectionPreview.walls.map((wall, i) => (
                  <line key={`w-${i}`} x1={wall.x1} y1={wall.y1} x2={wall.x2} y2={wall.y2}
                    stroke="#1e293b" strokeWidth={2} strokeLinecap="round" opacity={0.8} />
                ))}
                {detectionPreview.doors.map((door, i) => (
                  <rect key={`d-${i}`} x={door.x - door.width / 2} y={door.y - 2}
                    width={door.width} height={4} fill="#2563eb" rx={1} opacity={0.8} />
                ))}
                {detectionPreview.windows.map((win, i) => (
                  <rect key={`wi-${i}`} x={win.x - win.width / 2} y={win.y - win.height / 2}
                    width={win.width} height={win.height} fill="none" stroke="#059669" strokeWidth={2} rx={1} opacity={0.8} />
                ))}
              </svg>
            )}
            <div className="absolute bottom-2 left-2 flex gap-2">
              <span className="rounded bg-background/80 px-2 py-0.5 text-xs">{detectionPreview.walls.length} muros</span>
              <span className="rounded bg-background/80 px-2 py-0.5 text-xs">{detectionPreview.doors.length} puertas</span>
              <span className="rounded bg-background/80 px-2 py-0.5 text-xs">{detectionPreview.windows.length} ventanas</span>
            </div>
          </div>
        </div>
      )}

      {cadReady && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/30 px-6 py-8 text-center">
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
