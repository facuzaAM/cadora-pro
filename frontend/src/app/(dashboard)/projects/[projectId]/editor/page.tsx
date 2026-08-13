"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft, Loader2, AlertCircle, Check, AlertTriangle, Eye, Pencil } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { CadEditor } from "@/components/features/editor/cad-editor";
import { editorService } from "@/services/editor.service";
import { cadService } from "@/services/cad.service";
import { api, ApiError } from "@/services/api";
import { track } from "@/lib/analytics";
import type { EditorElements, EditorDetection } from "@/types/editor";
import { toast } from "sonner";

const POLL_INTERVAL_MS = 3000;
const MAX_WAIT_MS = 4 * 60 * 1000;

export default function EditorPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;
  const token = api.getAccessToken();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detection, setDetection] = useState<EditorDetection | null>(null);
  const [savedElements, setSavedElements] = useState<EditorElements | null>(null);
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [showReview, setShowReview] = useState(true);

  const imageUrl = detection ? editorService.previewUrl(projectId) : null;

  const loadSaved = useCallback(
    async (loaded: EditorDetection) => {
      try {
        const saved = await editorService.getElements(projectId, token);
        setSavedElements(saved);
      } catch {
        setSavedElements(null);
      }
      setDetection(loaded);
      setLoading(false);
    },
    [projectId, token],
  );

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setInterval> | null = null;
    const startedAt = Date.now();

    const stop = () => {
      stopped = true;
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    };

    const poll = async (): Promise<boolean> => {
      if (stopped) return true;
      try {
        const res = await editorService.getDetection(projectId, token);
        if (res.status === "error") {
          setError(
            "No pudimos procesar el plano. Revisá que el archivo sea válido e intentá de nuevo.",
          );
          setLoading(false);
          return true;
        }
        if (res.status === "completed") {
          track("detection_completed");
          await loadSaved(res);
          return true;
        }
        if (Date.now() - startedAt > MAX_WAIT_MS) {
          setError("El análisis está tardando más de lo esperado. Intentá nuevamente.");
          setLoading(false);
          return true;
        }
        return false;
      } catch {
        setError("Error cargando el plano. Intentá nuevamente.");
        setLoading(false);
        return true;
      }
    };

    const start = async () => {
      try {
        await editorService.runDetection(projectId, token);
      } catch (err) {
        if (err instanceof ApiError && err.status === 402) {
          toast.error("Alcanzaste el límite de conversiones de tu plan");
          router.replace("/billing");
          return;
        }
        if (!stopped) {
          setError(
            err instanceof ApiError
              ? err.message
              : "No pudimos iniciar el análisis del plano.",
          );
          setLoading(false);
        }
        return;
      }
      const done = await poll();
      if (!done && !stopped) {
        timer = setInterval(async () => {
          if (stopped) return;
          const doneNow = await poll();
          if (doneNow) stop();
        }, POLL_INTERVAL_MS);
      }
    };

    start();
    return stop;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, token, attempt]);

  const handleSave = useCallback(
    async (elements: EditorElements) => {
      setSaving(true);
      try {
        await editorService.saveElements(projectId, elements, token);
        toast.success("Cambios guardados");
      } catch {
        toast.error("Error al guardar los cambios");
      } finally {
        setSaving(false);
      }
    },
    [projectId, token],
  );

  const handleExport = useCallback(
    async (elements: EditorElements) => {
      setExporting(true);
      try {
        await editorService.saveElements(projectId, elements, token);
        await cadService.generate(projectId, "dxf", token, true);
        window.open(cadService.downloadUrl(projectId, "dxf"), "_blank");
        toast.success("Archivo DXF generado");
      } catch (err) {
        if (err instanceof ApiError && err.status === 402) {
          toast.error("Alcanzaste el límite de conversiones de tu plan");
          router.replace("/billing");
          return;
        }
        if (err instanceof ApiError && err.status === 409) {
          return;
        }
        toast.error("Error al generar el archivo CAD");
      } finally {
        setExporting(false);
      }
    },
    [projectId, token, router],
  );

  const initial: EditorElements | null = savedElements ?? detection;

  return (
    <div className="space-y-6">
      <button
        type="button"
        onClick={() => router.push(`/projects/${projectId}/result`)}
        className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Volver al resultado
      </button>

      <PageHeader
        title="Editor de planos"
        description="Ajustá muros, puertas y ventanas detectados automáticamente antes de exportar."
      />

      {loading && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/30 px-6 py-16 text-center">
          <Loader2 className="mb-4 h-8 w-8 animate-spin text-primary" />
          <h2 className="text-xl font-bold">Analizando plano</h2>
          <p className="mt-2 max-w-md text-sm text-muted-foreground">
            Estamos detectando muros, puertas y ventanas en tu plano. Esto puede tomar unos segundos.
          </p>
        </div>
      )}

      {!loading && error && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/30 px-6 py-16 text-center">
          <AlertCircle className="mb-4 h-8 w-8 text-destructive" />
          <h2 className="text-xl font-bold">No pudimos cargar el plano</h2>
          <p className="mt-2 max-w-md text-sm text-muted-foreground">{error}</p>
          <div className="mt-4 flex items-center gap-4">
            <button
              className="text-sm font-medium text-primary underline-offset-4 hover:underline"
              onClick={() => {
                setError(null);
                setLoading(true);
                setAttempt((a) => a + 1);
              }}
            >
              Reintentar
            </button>
            <button
              className="text-sm text-muted-foreground underline-offset-4 hover:underline"
              onClick={() => router.replace(`/projects/${projectId}/result`)}
            >
              Volver al resultado
            </button>
          </div>
        </div>
      )}

      {!loading && !error && initial && detection && showReview && (
        <div className="rounded-xl border bg-card p-6">
          <div className="flex items-center gap-3">
            <Eye className="h-6 w-6 text-primary" />
            <div>
              <h2 className="text-lg font-semibold">Revisión de la detección</h2>
              <p className="text-sm text-muted-foreground">
                El motor detectó los siguientes elementos. Revisá la calidad antes de editar.
              </p>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-3 gap-4">
            <div className="rounded-lg border p-3 text-center">
              <p className="text-2xl font-bold">{detection.walls.length}</p>
              <p className="text-xs text-muted-foreground">Muros</p>
            </div>
            <div className="rounded-lg border p-3 text-center">
              <p className="text-2xl font-bold">{detection.doors.length}</p>
              <p className="text-xs text-muted-foreground">Puertas</p>
            </div>
            <div className="rounded-lg border p-3 text-center">
              <p className="text-2xl font-bold">{detection.windows.length}</p>
              <p className="text-xs text-muted-foreground">Ventanas</p>
            </div>
          </div>

          {(() => {
            const allConf = [
              ...detection.doors.map((d) => d.confidence ?? 0),
              ...detection.windows.map((w) => w.confidence ?? 0),
            ];
            const avg =
              allConf.length > 0
                ? allConf.reduce((s, c) => s + c, 0) / allConf.length
                : 1;
            const low = allConf.filter((c) => c < 0.65).length;
            return (
              <div className="mt-4 flex flex-wrap items-center gap-4 text-sm">
                <span className="flex items-center gap-1.5">
                  {avg >= 0.8 ? (
                    <Check className="h-4 w-4 text-emerald-500" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-amber-500" />
                  )}
                  Confianza media:{" "}
                  <span className={avg >= 0.8 ? "text-emerald-600 font-medium" : "text-amber-600 font-medium"}>
                    {Math.round(avg * 100)}%
                  </span>
                </span>
                {low > 0 && (
                  <span className="text-amber-600">
                    {low} elemento{low !== 1 ? "s" : ""} con confianza baja (&lt;65%)
                  </span>
                )}
              </div>
            );
          })()}

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              onClick={() => setShowReview(false)}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              <Pencil className="h-4 w-4" />
              Editar plano
            </button>
            <button
              onClick={() => router.replace(`/projects/${projectId}/processing`)}
              className="inline-flex items-center gap-2 rounded-lg border bg-background px-5 py-2.5 text-sm font-medium hover:bg-muted"
            >
              Re-procesar
            </button>
          </div>
        </div>
      )}

      {!loading && !error && initial && detection && !showReview && (
        <CadEditor
          imageUrl={imageUrl ?? ""}
          width={detection.image_width || 1}
          height={detection.image_height || 1}
          initial={initial}
          measurements={detection.ocr_measurements}
          onSave={handleSave}
          onExport={handleExport}
          saving={saving}
          exporting={exporting}
        />
      )}
    </div>
  );
}
