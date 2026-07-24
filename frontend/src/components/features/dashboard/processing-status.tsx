"use client";

import { useEffect, useState } from "react";
import { Loader2, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { projectsService } from "@/services/projects.service";
import { api } from "@/services/api";

interface ActiveProcess {
  id: string;
  name: string;
  stage: string;
  progress: number;
}

export function ProcessingStatus() {
  const [active, setActive] = useState<ActiveProcess[]>([]);

  useEffect(() => {
    const token = api.getAccessToken();
    projectsService.list(token).then((projects) => {
      const processing = projects
        .filter((p) => p.status === "processing")
        .map((p, i) => ({
          id: p.id,
          name: p.name,
          stage: "Procesando plano",
          progress: Math.min(20 + i * 25, 80),
        }));
      setActive(processing);
    }).catch(() => {});
  }, []);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between px-5 py-4">
        <CardTitle className="text-sm font-medium">Estado del Procesamiento</CardTitle>
        {active.length > 0 && (
          <Badge variant="warning" className="gap-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            {active.length} activos
          </Badge>
        )}
      </CardHeader>
      <Separator />
      <CardContent className="p-5">
        {active.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <CheckCircle2 className="mb-2 h-8 w-8 text-emerald-500" />
            <p className="text-sm font-medium">Sin procesos activos</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Todos los proyectos han sido procesados.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {active.map((p) => (
              <div key={p.id} className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    <Loader2 className="h-4 w-4 shrink-0 animate-spin text-amber-500" />
                    <span className="truncate text-sm font-medium">{p.name}</span>
                  </div>
                  <span className="shrink-0 text-xs text-muted-foreground">{p.progress}%</span>
                </div>
                <Progress value={p.progress} className="h-1.5" />
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{p.stage}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
