"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import Link from "next/link";
import { Upload, AlertCircle, Loader2, Download, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

const DEMO_MAX_SIZE_MB = 10;
const DEMO_ACCEPT = ".pdf,.png,.jpg,.jpeg,.tiff";
const SESSION_KEY = "cadora_demo_used";

interface DemoResult {
  walls: Array<{ x1: number; y1: number; x2: number; y2: number; length: number }>;
  doors: Array<{ x: number; y: number; width: number; rotation: number; swing: string }>;
  windows: Array<{ x: number; y: number; width: number; height: number; rotation: number }>;
  ocr_texts: Array<{ text: string; bbox: [number, number, number, number]; category: string }>;
  ocr_measurements: Array<{ text: string; bbox: [number, number, number, number] }>;
  image_width: number;
  image_height: number;
}

type DemoState = "idle" | "processing" | "result" | "used" | "error";

const PROCESSING_STEPS = [
  "Cargando plano...",
  "Detectando muros...",
  "Detectando puertas...",
  "Detectando ventanas...",
  "Analizando textos...",
  "¡Listo!",
];

export function DemoUploader() {
  const [state, setState] = useState<DemoState>("idle");
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DemoResult | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const stepTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (sessionStorage.getItem(SESSION_KEY)) {
      setState("used");
    }
    return () => {
      if (stepTimerRef.current) clearInterval(stepTimerRef.current);
    };
  }, []);

  const simulateProgress = useCallback(() => {
    setStep(0);
    let current = 0;
    stepTimerRef.current = setInterval(() => {
      current++;
      if (current < PROCESSING_STEPS.length) {
        setStep(current);
      } else {
        if (stepTimerRef.current) clearInterval(stepTimerRef.current);
      }
    }, 800);
  }, []);

  const validateFile = useCallback((f: File): boolean => {
    const ext = "." + f.name.split(".").pop()?.toLowerCase();
    if (!DEMO_ACCEPT.split(",").includes(ext)) {
      setError("Formato no soportado. Usa PDF, PNG, JPG o TIFF.");
      return false;
    }
    if (f.size > DEMO_MAX_SIZE_MB * 1024 * 1024) {
      setError(`El archivo excede el límite de ${DEMO_MAX_SIZE_MB} MB.`);
      return false;
    }
    return true;
  }, []);

  const processFile = useCallback(async (file: File) => {
    if (!validateFile(file)) return;

    setError(null);
    setState("processing");
    simulateProgress();

    const objectUrl = URL.createObjectURL(file);
    setImageUrl(objectUrl);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
      const res = await fetch(`${apiBase}/api/v1/demo/process`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || "Error al procesar el archivo");
      }

      const data: DemoResult = await res.json();
      setResult(data);
      setState("result");
      sessionStorage.setItem(SESSION_KEY, "1");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al procesar el archivo";
      setError(msg);
      setState("idle");
      if (imageUrl) URL.revokeObjectURL(imageUrl);
      setImageUrl(null);
    } finally {
      if (stepTimerRef.current) clearInterval(stepTimerRef.current);
    }
  }, [validateFile, simulateProgress, imageUrl]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) processFile(f);
  }, [processFile]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) processFile(f);
  }, [processFile]);

  const reset = () => {
    setState("idle");
    setResult(null);
    if (imageUrl) URL.revokeObjectURL(imageUrl);
    setImageUrl(null);
    setStep(0);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const wallCount = result?.walls.length ?? 0;
  const doorCount = result?.doors.length ?? 0;
  const windowCount = result?.windows.length ?? 0;

  return (
    <section className="py-16 lg:py-24">
      <div className="mx-auto max-w-4xl px-4">
        <div className="text-center">
          <h2 className="text-3xl font-bold tracking-tight">Probá con tu plano</h2>
          <p className="mt-2 text-muted-foreground">
            Subí un plano arquitectónico y mirá cómo Cadora detecta los elementos automáticamente.
          </p>
        </div>

        <div className="mt-10">
          {state === "used" ? (
            <div className="rounded-xl border bg-muted/30 p-10 text-center">
              <p className="text-muted-foreground">
                Ya usaste la demo.{" "}
                <Link href="/register" className="text-primary underline-offset-4 hover:underline">
                  Registrate gratis
                </Link>{" "}
                para procesar ilimitadamente.
              </p>
            </div>
          ) : state === "idle" || state === "error" ? (
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              className={cn(
                "relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 transition-colors",
                dragOver && "border-primary bg-primary/5",
                "border-muted-foreground/25 hover:border-muted-foreground/50",
              )}
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 mb-4">
                <Upload className="h-8 w-8 text-primary" />
              </div>
              <h3 className="font-semibold">Subí tu plano arquitectónico</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Arrastrá tu archivo aquí o hacé clic para seleccionar
              </p>
              <Badge variant="secondary" className="mt-4">
                PDF, PNG, JPG, TIFF — hasta {DEMO_MAX_SIZE_MB} MB
              </Badge>

              <input
                ref={fileInputRef}
                type="file"
                accept={DEMO_ACCEPT}
                className="hidden"
                onChange={handleChange}
              />
            </div>
          ) : state === "processing" ? (
            <div className="rounded-xl border bg-muted/30 p-10 text-center">
              <Loader2 className="mx-auto h-10 w-10 animate-spin text-primary" />
              <p className="mt-4 font-medium">{PROCESSING_STEPS[step]}</p>
              <div className="mx-auto mt-4 h-1.5 w-48 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-500"
                  style={{ width: `${((step + 1) / PROCESSING_STEPS.length) * 100}%` }}
                />
              </div>
            </div>
          ) : state === "result" && result ? (
            <div className="space-y-6">
              <div className="rounded-xl border bg-card overflow-hidden">
                <div className="relative aspect-[4/3] bg-muted/30">
                  {imageUrl && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={imageUrl}
                      alt="Plano subido"
                      className="absolute inset-0 h-full w-full object-contain"
                    />
                  )}

                  <svg
                    className="absolute inset-0 h-full w-full"
                    viewBox={`0 0 ${result.image_width || 1} ${result.image_height || 1}`}
                    preserveAspectRatio="xMidYMid meet"
                  >
                    {result.walls.map((wall, i) => (
                      <line
                        key={`w-${i}`}
                        x1={wall.x1}
                        y1={wall.y1}
                        x2={wall.x2}
                        y2={wall.y2}
                        stroke="#18181b"
                        strokeWidth={3}
                        strokeLinecap="round"
                        opacity={0.8}
                      />
                    ))}
                    {result.doors.map((door, i) => (
                      <g key={`d-${i}`} transform={`translate(${door.x},${door.y}) rotate(${door.rotation})`}>
                        <rect
                          x={-door.width / 2}
                          y={-2}
                          width={door.width}
                          height={4}
                          fill="#2563eb"
                          rx={1}
                        />
                        <path
                          d={`M ${-door.width / 2} 0 A ${door.width} ${door.width} 0 0 ${door.swing === "left" ? 0 : 1} ${door.swing === "left" ? -door.width : door.width} ${door.swing === "left" ? -door.width : door.width}`}
                          fill="none"
                          stroke="#2563eb"
                          strokeWidth={1.5}
                          strokeDasharray="4 2"
                          opacity={0.6}
                        />
                      </g>
                    ))}
                    {result.windows.map((win, i) => (
                      <rect
                        key={`wi-${i}`}
                        x={win.x - win.width / 2}
                        y={win.y - win.height / 2}
                        width={win.width}
                        height={win.height}
                        fill="none"
                        stroke="#059669"
                        strokeWidth={2.5}
                        rx={1}
                        transform={`rotate(${win.rotation} ${win.x} ${win.y})`}
                        opacity={0.85}
                      />
                    ))}
                  </svg>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-4 border-t p-4">
                  <div className="flex gap-4 text-sm">
                    <Badge variant="secondary">{wallCount} muros</Badge>
                    <Badge variant="secondary">{doorCount} puertas</Badge>
                    <Badge variant="secondary">{windowCount} ventanas</Badge>
                  </div>
                  <Button onClick={() => setShowAuthModal(true)}>
                    <Download className="mr-2 h-4 w-4" />
                    Descargá tu archivo DXF
                  </Button>
                </div>
              </div>

              <div className="text-center">
                <Button variant="ghost" size="sm" onClick={reset}>
                  Probar con otro plano
                </Button>
              </div>
            </div>
          ) : null}
        </div>

        {error && (
          <div className="mt-4 flex items-center justify-center gap-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}
      </div>

      <Dialog open={showAuthModal} onOpenChange={setShowAuthModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Descargá tu archivo</DialogTitle>
            <DialogDescription>
              Registrate gratis para descargar el DXF con todos los elementos detectados, o iniciá sesión si ya tenés cuenta.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3 mt-4">
            <Button asChild className="w-full">
              <Link href="/register">
                Crear Cuenta Gratis
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" className="w-full">
              <Link href="/login">Ya tengo cuenta</Link>
            </Button>
          </div>
          <p className="text-center text-xs text-muted-foreground mt-2">
            Plan Free: 3 conversiones/mes, sin tarjeta.
          </p>
        </DialogContent>
      </Dialog>
    </section>
  );
}
