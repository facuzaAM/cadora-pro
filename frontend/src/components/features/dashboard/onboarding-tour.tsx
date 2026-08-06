"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Sparkles, Upload, Download, X } from "lucide-react";
import { Button } from "@/components/ui/button";

const STORAGE_KEY = "cadora_onboarding";

const steps = [
  {
    icon: Sparkles,
    title: "Bienvenido a Cadora",
    desc: "Convertimos tus planos en PDF, PNG, JPG, JPEG o TIFF a archivos DXF/DWG editables. Te mostramos el camino en 3 pasos.",
  },
  {
    icon: Upload,
    title: "Subí tu primer plano",
    desc: "Andá a Nuevo Proyecto, subí tu plano y elegí el formato de salida. El procesamiento toma entre 1 y 3 minutos.",
  },
  {
    icon: Download,
    title: "Descargá tu archivo CAD",
    desc: "Desde el proyecto vas a poder descargar el DXF/DWG con capas organizadas: muros, puertas, ventanas, textos y cotas.",
  },
];

export function OnboardingTour() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (typeof window !== "undefined" && localStorage.getItem(STORAGE_KEY) === "pending") {
      setOpen(true);
    }
  }, []);

  const finish = (value = "done") => {
    localStorage.setItem(STORAGE_KEY, value);
    setOpen(false);
  };

  if (!open) return null;

  const current = steps[step];
  const Icon = current.icon;
  const isLast = step === steps.length - 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => finish("done")}
      />
      <div className="relative w-full max-w-md rounded-2xl border bg-card p-6 shadow-2xl">
        <button
          onClick={() => finish("done")}
          className="absolute right-4 top-4 text-muted-foreground hover:text-foreground"
          aria-label="Cerrar"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-blue-600 text-primary-foreground shadow-lg shadow-primary/25">
          <Icon className="h-7 w-7" />
        </div>
        <h2 className="mt-4 text-xl font-bold">{current.title}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{current.desc}</p>

        <div className="mt-6 flex items-center justify-center gap-1.5">
          {steps.map((_, i) => (
            <span
              key={i}
              className={`h-1.5 rounded-full transition-all ${
                i === step ? "w-6 bg-primary" : "w-1.5 bg-muted-foreground/30"
              }`}
            />
          ))}
        </div>

        <div className="mt-6 flex items-center justify-between gap-2">
          <Button variant="ghost" size="sm" onClick={() => finish("done")}>
            Saltar
          </Button>
          <div className="flex gap-2">
            {step > 0 && (
              <Button variant="outline" size="sm" onClick={() => setStep(step - 1)}>
                Anterior
              </Button>
            )}
            {isLast ? (
              <Button size="sm" asChild onClick={() => finish("done")}>
                <Link href="/projects/upload/new">Subir mi primer plano</Link>
              </Button>
            ) : (
              <Button size="sm" onClick={() => setStep(step + 1)}>
                Siguiente
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
