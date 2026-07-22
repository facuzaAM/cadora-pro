"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProcessingStatus } from "@/components/features/projects/processing-status";
import { DETECTION_STEPS } from "@/lib/constants";
import { detectionService } from "@/services/detection.service";
import { documentsService } from "@/services/documents.service";

export default function ProcessingPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;
  const [currentStep, setCurrentStep] = useState(0);
  const [_detectionId, setDetectionId] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token") || undefined;
    documentsService
      .getByProject(projectId, token)
      .then((docs) => {
        if (docs.length > 0) {
          return detectionService.start(docs[0].id, token);
        }
        throw new Error("No documents found");
      })
      .then((res) => setDetectionId(res.detection_id))
      .catch(() => {});
  }, [projectId]);

  useEffect(() => {
    if (currentStep >= DETECTION_STEPS.length) return;

    const timeouts = [2500, 3000, 3500, 4000, 3000, 3500, 2000];
    const timer = setTimeout(
      () => setCurrentStep((prev) => prev + 1),
      timeouts[currentStep],
    );

    return () => clearTimeout(timer);
  }, [currentStep]);

  useEffect(() => {
    if (currentStep === DETECTION_STEPS.length) {
      const t = setTimeout(() => router.push(`/projects/${projectId}/result`), 1500);
      return () => clearTimeout(t);
    }
  }, [currentStep, router, projectId]);

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
