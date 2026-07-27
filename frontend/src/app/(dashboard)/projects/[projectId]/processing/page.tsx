"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProcessingStatus } from "@/components/features/projects/processing-status";
import { DETECTION_STEPS } from "@/lib/constants";
import { detectionService } from "@/services/detection.service";
import { documentsService } from "@/services/documents.service";
import { api } from "@/services/api";
import { toast } from "sonner";

const POLL_INTERVAL = 3000;
const MAX_POLLS = 120;

export default function ProcessingPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;
  const [currentStep, setCurrentStep] = useState(0);
  const currentStepRef = useRef(0);
  const [completed, setCompleted] = useState(false);
  const pollCount = useRef(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const cleanup = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    const token = api.getAccessToken();
    let detectionId: string | null = null;

    documentsService
      .getByProject(projectId, token)
      .then((docs) => {
        if (docs.length > 0) {
          return detectionService.start(docs[0].id, token);
        }
        throw new Error("No documents found");
      })
      .then((res) => {
        if (!res) throw new Error("No detection started");
        detectionId = res.detection_id;
        setCurrentStep(1);
        currentStepRef.current = 1;

        intervalRef.current = setInterval(async () => {
          if (!detectionId) return;
          pollCount.current += 1;

          if (pollCount.current > MAX_POLLS) {
            cleanup();
            toast.error("El procesamiento está tomando más de lo esperado");
            router.push(`/projects/${projectId}/result`);
            return;
          }

          try {
            const status = await detectionService.status(detectionId, token);
            const statusMap: Record<string, number> = {
              preprocessing: 0,
              lines: 1,
              doors_windows: 2,
              rooms: 3,
              text: 4,
              dimensions: 5,
              cad: 6,
              completed: 7,
            };
            const stepIdx = statusMap[status.status] ?? 0;
            const newStep = Math.max(currentStepRef.current, stepIdx);
            currentStepRef.current = newStep;
            setCurrentStep(newStep);

            if (status.status === "completed" || status.status === "error") {
              cleanup();
              if (status.status === "completed") {
                setCompleted(true);
              } else {
                toast.error("Error durante el procesamiento");
              }
            }
          } catch {
            pollCount.current += 1;
          }
        }, POLL_INTERVAL);
      })
      .catch(() => {
        toast.error("Error al iniciar el procesamiento");
        router.push(`/projects/${projectId}/result`);
      });

    return cleanup;
  }, [projectId, router, cleanup]);

  useEffect(() => {
    if (completed) {
      const t = setTimeout(() => router.push(`/projects/${projectId}/result`), 1500);
      return () => clearTimeout(t);
    }
  }, [completed, router, projectId]);

  const progress = Math.round(
    (Math.min(currentStep, DETECTION_STEPS.length) / DETECTION_STEPS.length) * 100,
  );

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" onClick={() => router.back()}>
        <ArrowLeft className="mr-2 h-4 w-4" />
        Volver
      </Button>

      <ProcessingStatus
        currentStep={DETECTION_STEPS[Math.min(currentStep, DETECTION_STEPS.length - 1)]?.id ?? "cad"}
        progress={progress}
      />
    </div>
  );
}
