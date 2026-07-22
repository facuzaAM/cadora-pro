"use client";

import { useState, useEffect } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/shared/logo";

const steps = [
  { title: "Subí tu plano", desc: "Cargá un PDF o imagen de tu plano arquitectónico." },
  { title: "Lo procesa automáticamente", desc: "Detecta muros, puertas y ventanas en segundos." },
  { title: "Editá si querés", desc: "Ajustá los elementos detectados antes de exportar." },
  { title: "Descargá CAD", desc: "Obtené un archivo DXF editable en AutoCAD o LibreCAD." },
];

export function OnboardingTour() {
  const [visible, setVisible] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    const done = localStorage.getItem("onboarding_done");
    if (!done) setVisible(true);
  }, []);

  const dismiss = () => {
    localStorage.setItem("onboarding_done", "true");
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/20 sm:items-center">
      <div className="w-full max-w-sm rounded-t-2xl border bg-card p-6 shadow-2xl sm:rounded-2xl">
        <div className="flex items-center justify-between">
          <Logo />
          <Button variant="ghost" size="icon" onClick={dismiss}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="mt-6">
          <div className="flex gap-1">
            {steps.map((_, i) => (
              <div
                key={i}
                className={`h-1 flex-1 rounded-full ${i <= step ? "bg-primary" : "bg-muted"}`}
              />
            ))}
          </div>
          <h3 className="mt-4 text-lg font-bold">{steps[step].title}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{steps[step].desc}</p>
        </div>
        <div className="mt-6 flex items-center justify-between">
          <button
            onClick={dismiss}
            className="text-xs text-muted-foreground underline-offset-4 hover:underline"
          >
            Omitir
          </button>
          <Button
            size="sm"
            onClick={() => {
              if (step < steps.length - 1) setStep(step + 1);
              else dismiss();
            }}
          >
            {step < steps.length - 1 ? "Siguiente" : "Comenzar"}
          </Button>
        </div>
      </div>
    </div>
  );
}
