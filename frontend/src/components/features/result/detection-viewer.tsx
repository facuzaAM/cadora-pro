"use client";

import { useState, useEffect } from "react";
import { Eye, EyeOff, Download, ChevronDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { detectionService } from "@/services/detection.service";
import { documentsService } from "@/services/documents.service";
import { cadService, type CadFormat } from "@/services/cad.service";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/services/api";

interface DetectionViewerProps {
  projectId: string;
}

const defaultLayers = [
  { id: "walls", label: "Muros", visible: true, color: "#18181b" },
  { id: "doors", label: "Puertas", visible: true, color: "#2563eb" },
  { id: "windows", label: "Ventanas", visible: true, color: "#059669" },
  { id: "rooms", label: "Ambientes", visible: true, color: "#d97706" },
  { id: "text", label: "Textos", visible: true, color: "#7c3aed" },
  { id: "dimensions", label: "Cotas", visible: true, color: "#dc2626" },
];

const DWG_PLANS = new Set(["pro", "business"]);

export function DetectionViewer({ projectId }: DetectionViewerProps) {
  const { user } = useAuth();
  const [layerState, setLayerState] = useState(defaultLayers);
  const [wallCount, setWallCount] = useState(0);

  const canExportDwg = user && DWG_PLANS.has(user.subscription_plan);

  useEffect(() => {
    const token = api.getAccessToken();
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
      .then((result) => {
        if (result) {
          setWallCount(result.walls?.length ?? 0);
        }
      })
      .catch(() => {});
  }, [projectId]);

  const toggleLayer = (id: string) => {
    setLayerState((prev) =>
      prev.map((l) => (l.id === id ? { ...l, visible: !l.visible } : l)),
    );
  };

  const handleDownload = (format: CadFormat) => {
    window.open(cadService.downloadUrl(projectId, format), "_blank");
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-sm">Vista Previa del Plano</CardTitle>
        <div className="flex items-center gap-2">
          {canExportDwg ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  <Download className="mr-2 h-4 w-4" />
                  Descargar
                  <ChevronDown className="ml-1 h-3 w-3" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => handleDownload("dxf")}>
                  DXF
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleDownload("dwg")}>
                  DWG
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button variant="outline" size="sm" onClick={() => handleDownload("dxf")}>
              <Download className="mr-2 h-4 w-4" />
              DXF
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="preview">
          <TabsList>
            <TabsTrigger value="preview">Vista previa</TabsTrigger>
            <TabsTrigger value="layers">Capas</TabsTrigger>
          </TabsList>

          <TabsContent value="preview" className="mt-4">
            <div className="flex aspect-[4/3] items-center justify-center rounded-lg border bg-muted/30">
              <div className="text-center">
                <p className="text-sm text-muted-foreground">
                  Vista previa del plano procesado
                </p>
                <Badge variant="secondary" className="mt-2">
                  Muros detectados: {wallCount}
                </Badge>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="layers" className="mt-4">
            <div className="space-y-2">
              {layerState.map((layer) => (
                <div
                  key={layer.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="h-3 w-3 rounded-full"
                      style={{ backgroundColor: layer.color }}
                    />
                    <span className="text-sm">{layer.label}</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => toggleLayer(layer.id)}
                  >
                    {layer.visible ? (
                      <Eye className="h-4 w-4" />
                    ) : (
                      <EyeOff className="h-4 w-4 text-muted-foreground" />
                    )}
                  </Button>
                </div>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
