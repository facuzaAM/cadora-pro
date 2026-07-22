"use client";

import { useEffect, useState } from "react";
import { Layers, DoorOpen, Square, Text, Ruler } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { detectionService } from "@/services/detection.service";
import { documentsService } from "@/services/documents.service";
import type { DetectionResult } from "@/types";

interface EnvironmentListProps {
  projectId: string;
}

export function EnvironmentList({ projectId }: EnvironmentListProps) {
  const [result, setResult] = useState<DetectionResult | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token") || undefined;
    documentsService
      .getByProject(projectId, token)
      .then((docs) => {
        if (docs.length > 0) {
          return detectionService.start(docs[0].id, token);
        }
      })
      .then((res) => {
        if (res) {
          return detectionService.result(res.detection_id, token);
        }
      })
      .then((data) => {
        if (data) setResult(data);
      })
      .catch(() => {});
  }, [projectId]);

  const elements = [
    { icon: Layers, label: "Muros", count: result?.walls?.length ?? 0 },
    { icon: DoorOpen, label: "Puertas", count: result?.doors?.length ?? 0 },
    { icon: Square, label: "Ventanas", count: result?.windows?.length ?? 0 },
    { icon: Text, label: "Textos", count: result?.texts?.length ?? 0 },
    { icon: Ruler, label: "Cotas", count: result?.dimensions?.length ?? 0 },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Elementos Detectados</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            {elements.map((el) => {
              const Icon = el.icon;
              return (
                <div
                  key={el.label}
                  className="flex items-center gap-3 rounded-lg border p-3"
                >
                  <Icon className="h-4 w-4 text-primary" />
                  <div>
                    <p className="text-xs text-muted-foreground">{el.label}</p>
                    <p className="text-lg font-bold">{el.count}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {result?.rooms && result.rooms.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Ambientes Detectados</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {result.rooms.map((room) => (
                <div
                  key={room.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div>
                    <p className="font-medium">{room.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {room.area > 0 ? `${room.area.toFixed(1)} m²` : "Área no calculada"}
                    </p>
                  </div>
                  <Badge variant="secondary">
                    {(room.confidence * 100).toFixed(0)}%
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
