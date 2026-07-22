"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft, Download, Share2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { DetectionViewer } from "@/components/features/result/detection-viewer";
import { EnvironmentList } from "@/components/features/result/environment-list";
import { projectsService } from "@/services/projects.service";
import { cadService } from "@/services/cad.service";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "sonner";

export default function ResultPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;
  const { user: _user } = useAuth();
  const [projectName, setProjectName] = useState("Proyecto");
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token") || undefined;
    projectsService.getById(projectId, token).then((p) => setProjectName(p.name)).catch(() => {});
  }, [projectId]);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const token = localStorage.getItem("access_token") || undefined;
      await cadService.generate(projectId, token);
      const url = cadService.downloadUrl(projectId);
      window.open(url, "_blank");
      toast.success("Archivo DXF generado");
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
            <Button size="sm" onClick={handleDownload} disabled={downloading}>
              {downloading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Download className="mr-2 h-4 w-4" />
              )}
              Exportar Todo
            </Button>
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
