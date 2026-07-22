"use client";

import { CheckCircle2, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { DETECTION_STEPS } from "@/lib/constants";

interface ProcessingStatusProps {
  currentStep: string;
  progress: number;
}

export function ProcessingStatus({ currentStep, progress: _progress }: ProcessingStatusProps) {
  const currentIndex = DETECTION_STEPS.findIndex((s) => s.id === currentStep);

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div className="text-center">
        <div className="flex justify-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        </div>
        <h3 className="mt-4 text-lg font-semibold">Procesando plano</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          El sistema está analizando tu plano arquitectónico...
        </p>
      </div>

      <div className="space-y-3">
        {DETECTION_STEPS.map((step, idx) => {
          const isActive = idx === currentIndex;
          const isDone = idx < currentIndex;
          const isPending = idx > currentIndex;

          return (
            <div
              key={step.id}
              className={cn(
                "flex items-center gap-3 rounded-lg border p-3 transition-colors",
                isActive && "border-primary bg-primary/5",
                isDone && "border-emerald-500/30 bg-emerald-500/5",
                isPending && "border-muted opacity-50",
              )}
            >
              {isDone ? (
                <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" />
              ) : isActive ? (
                <Loader2 className="h-5 w-5 shrink-0 animate-spin text-primary" />
              ) : (
                <div className="h-5 w-5 shrink-0 rounded-full border-2 border-muted-foreground/30" />
              )}
              <span
                className={cn(
                  "text-sm",
                  isActive && "font-medium",
                  isDone && "text-emerald-600 dark:text-emerald-400",
                )}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
