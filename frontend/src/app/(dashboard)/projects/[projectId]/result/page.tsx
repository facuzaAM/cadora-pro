"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft, Download, Share2, Loader2, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { PageHeader } from "@/components/shared/page-header";
import { DetectionViewer } from "@/components/features/result/detection-viewer";
import { EnvironmentList } from "@/components/features/result/environment-list";
import { projectsService } from "@/services/projects.service";
import { cadService, type CadFormat } from "@/services/cad.service";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/services/api";
import { toast } from "sonner";

const DWG_PLANS = new Set(["pro", "business"]);

export default function ResultPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;
  const { user } = useAuth();
  const [projectName, setProjectName] = useState("Proyecto");
  const [downloading, setDownloading] = useState(false);

  const canExportDwg = user && DWG_PLANS.has(user.subscription_plan);

  useEffect(() => {
    const token = api.getAccessToken();
    projectsService.getById(projectId, token).then((p) => setProjectName(p.name)).catch(() => {});
  }, [projectId]);

  const handleDownload = async (format: CadFormat = "dxf") => {
    setDownloading(true);
    try {
      await cadService.generate(projectId, format, api.getAccessToken());
      const url = cadService.downloadUrl(projectId, format);
      window.open(url, "_blank");
      toast.success(`Archivo ${format.toUpperCase()} generado`);
    } catch {
      toast.error("Error al generar el archivo");
    } finally {
      setDownloading(false);
    }
  };

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({ title: projectName, url: window.location.href });
    } else {
      navigator.clipboard.writeText(window.location.href);
      toast.success("Enlace copiado al portapapeles");
    }
  };

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" onClick={() => router.back()}>
        <ArrowLeft className="mr-2 h-4 w-4" />
        Volver
      </Button>

      <PageHeader
        title={projectName}
        description="Plano procesado exitosamente"
        action={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleShare}>
              <Share2 className="mr-2 h-4 w-4" />
              Compartir
            </Button>
            {canExportDwg ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button size="sm" disabled={downloading}>
                    {downloading ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Download className="mr-2 h-4 w-4" />
                    )}
                    Exportar
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
              <Button size="sm" onClick={() => handleDownload("dxf")} disabled={downloading}>
                {downloading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Download className="mr-2 h-4 w-4" />
                )}
                Exportar DXF
              </Button>
            )}
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <DetectionViewer projectId={projectId} />
        </div>
        <div>
          <EnvironmentList projectId={projectId} />
        </div>
      </div>
    </div>
  );
}
