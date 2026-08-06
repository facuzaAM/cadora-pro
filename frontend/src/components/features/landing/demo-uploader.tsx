"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import Link from "next/link";
import { Upload, AlertCircle, Loader2, Download, ArrowRight, Check } from "lucide-react";
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
import { PLANS, APP_TAGLINE, APP_DESCRIPTION } from "@/lib/constants";
import { CadCrosshair } from "@/components/features/landing/cad-crosshair";
import { CadCursor } from "@/components/features/landing/cad-cursor";
import { CadDimension } from "@/components/features/landing/cad-dimension";
import { api } from "@/services/api";

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
  const demoSessionRef = useRef<string>(`demo_${crypto.randomUUID()}`);

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

      const data = await api.upload<DemoResult>(
        "/demo/process",
        formData,
        undefined,
        { "X-Demo-Session": demoSessionRef.current },
      );

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
    <>
      <section className="relative flex min-h-[85vh] items-center justify-center overflow-hidden isolate bg-gradient-to-b from-primary/[0.06] via-background to-background pt-14">
        <div className="absolute inset-0 bg-grid-cad bg-grid-cad-fade -z-10 pointer-events-none" />
        <CadCrosshair className="absolute right-[8%] top-1/2 hidden h-48 w-48 -translate-y-1/2 text-primary/30 lg:block -z-10 pointer-events-none" />
        <CadCrosshair className="absolute left-[6%] bottom-[12%] hidden h-32 w-32 text-primary/20 -z-10 pointer-events-none" />
        <CadDimension label="4.80 m" className="absolute left-[10%] top-[22%] hidden h-14 w-32 text-primary/50 lg:block -z-10" />
        <CadDimension label="3.20 m" horizontal={false} className="absolute right-[11%] top-[16%] hidden h-32 w-14 text-primary/50 lg:block -z-10" />
        <CadDimension label="6.40 m" className="absolute left-[14%] bottom-[14%] hidden h-14 w-32 text-primary/35 lg:block -z-10" />
        <div className="absolute -left-24 top-1/4 h-64 w-64 animate-blob rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute -right-24 top-1/3 h-64 w-64 animate-blob-delayed rounded-full bg-blue-500/10 blur-3xl pointer-events-none" />
        <div className="absolute left-1/2 top-1/2 h-48 w-48 -translate-x-1/2 -translate-y-1/2 animate-blob-slow rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />

        <div className="mx-auto max-w-4xl px-4 text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm text-primary">
            <span className="inline-block h-2 w-2 rounded-full bg-primary animate-pulse" />
            Plataforma de conversión CAD
          </div>

          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
            {APP_TAGLINE}
          </h1>

          <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground sm:text-xl">
            {APP_DESCRIPTION}
          </p>

          <div className="mt-10">
            {state === "used" ? (
              <div className="rounded-xl border bg-card p-10 text-center shadow-sm">
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
                <h3 className="font-semibold text-lg">Subí tu plano arquitectónico</h3>
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
              <div className="rounded-xl border bg-card p-10 text-center shadow-sm">
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
                <div className="rounded-xl border bg-card overflow-hidden shadow-sm">
                  <div className="relative aspect-[4/3] bg-muted/30 bg-grid-cad overflow-hidden">
                    {imageUrl && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={imageUrl}
                        alt="Plano subido"
                        className="absolute inset-0 h-full w-full object-contain opacity-80"
                      />
                    )}

                    <svg
                      className="absolute inset-0 h-full w-full text-foreground"
                      viewBox={`0 0 ${result.image_width || 1} ${result.image_height || 1}`}
                      preserveAspectRatio="xMidYMid meet"
                    >
                      <g className="cad-draw">
                        {result.walls.map((wall, i) => (
                          <line
                            key={`w-${i}`}
                            x1={wall.x1}
                            y1={wall.y1}
                            x2={wall.x2}
                            y2={wall.y2}
                            stroke="currentColor"
                            strokeWidth={3}
                            strokeLinecap="round"
                            opacity={0.9}
                          />
                        ))}
                      </g>
                      <g className="cad-draw cad-draw-delay-1">
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
                      </g>
                      <g className="cad-draw cad-draw-delay-2">
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
                            opacity={0.9}
                          />
                        ))}
                      </g>
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

        <CadCursor />
      </section>

      <Dialog open={showAuthModal} onOpenChange={setShowAuthModal}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl">Elegí tu plan para descargar</DialogTitle>
            <DialogDescription>
              Creá una cuenta gratuita para descargar tu DXF, o elegí un plan premium para más conversiones.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-3 mt-4 sm:grid-cols-2">
            {PLANS.map((plan) => (
              <div
                key={plan.id}
                className={cn(
                  "relative flex flex-col rounded-xl border p-4 transition-colors",
                  plan.popular
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-muted-foreground/50",
                )}
              >
                {plan.popular && (
                  <Badge className="absolute -top-2.5 left-4">Popular</Badge>
                )}
                <div className="flex items-baseline justify-between">
                  <h3 className="font-semibold">{plan.name}</h3>
                  <span className="text-2xl font-bold">
                    {plan.price === 0 ? "Gratis" : `$${plan.price}`}
                    {plan.price > 0 && (
                      <span className="text-sm font-normal text-muted-foreground">/mes</span>
                    )}
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{plan.description}</p>
                <ul className="mt-3 flex-1 space-y-1.5">
                  {plan.features.slice(0, 4).map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm">
                      <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Button
                  asChild
                  className="mt-4 w-full"
                  variant={plan.popular ? "default" : "outline"}
                >
                  <Link href={`/register?plan=${plan.id}`}>
                    {plan.cta}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            ))}
          </div>

          <div className="mt-4 flex flex-col items-center gap-2">
            <Link
              href="/login"
              className="text-sm text-muted-foreground underline-offset-4 hover:underline"
            >
              Ya tengo cuenta →
            </Link>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
