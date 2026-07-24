"use client";

import { useCallback, useEffect, useState } from "react";
import {
  CreditCard,
  HardDrive,
  RefreshCw,
  ShieldCheck,
  Zap,
  ExternalLink,
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { PLANS } from "@/lib/constants";
import { billingService, type Subscription } from "@/services/billing.service";
import { api } from "@/services/api";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 MB";
  const mb = bytes / (1024 * 1024);
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
  return `${Math.round(mb)} MB`;
}

export default function BillingPage() {
  const [sub, setSub] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = api.getAccessToken();
    if (!token) return;
    billingService.getSubscription(token).then(setSub).finally(() => setLoading(false));
  }, []);

  const handleManage = useCallback(async () => {
    if (typeof window !== "undefined" && window.Paddle) {
      window.Paddle.CustomerPortal.open();
    }
  }, []);

  const planInfo = PLANS.find((p) => p.id === sub?.plan);

  const conversionPct = sub && sub.conversions_limit > 0
    ? Math.round((sub.conversions_used / sub.conversions_limit) * 100)
    : 0;

  const storagePct = sub && sub.storage_limit > 0
    ? Math.round((sub.storage_used / sub.storage_limit) * 100)
    : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Facturación"
        description="Administra tu suscripción y límites de uso"
      />

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      ) : sub ? (
        <>
          {/* Plan actual */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between px-5 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <CreditCard className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-sm font-medium">Plan {planInfo?.name || sub.plan}</CardTitle>
                  <p className="text-xs text-muted-foreground">
                    Estado: <Badge variant={sub.status === "active" ? "success" : "secondary"} className="ml-1 text-[10px]">
                      {sub.status === "active" ? "Activo" : sub.status === "canceled" ? "Cancelado" : "Inactivo"}
                    </Badge>
                  </p>
                </div>
              </div>
              {sub.plan !== "free" && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleManage}
                  className="gap-2"
                >
                  <ExternalLink className="h-4 w-4" />
                  Gestionar
                </Button>
              )}
            </CardHeader>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            {/* Conversiones */}
            <Card>
              <CardHeader className="flex flex-row items-center gap-3 px-5 py-4">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                  <RefreshCw className="h-4 w-4 text-primary" />
                </div>
                <CardTitle className="text-sm font-medium">Conversiones</CardTitle>
              </CardHeader>
              <Separator />
              <CardContent className="space-y-3 p-5">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">
                    {sub.conversions_used} de {sub.conversions_limit > 0 ? sub.conversions_limit : "∞"} usadas
                  </span>
                  <span className="font-medium tabular-nums">
                    {sub.conversions_limit > 0 ? `${conversionPct}%` : "—"}
                  </span>
                </div>
                <Progress
                  value={sub.conversions_limit > 0 ? conversionPct : 100}
                  className="h-2"
                />
              </CardContent>
            </Card>

            {/* Almacenamiento */}
            <Card>
              <CardHeader className="flex flex-row items-center gap-3 px-5 py-4">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/10">
                  <HardDrive className="h-4 w-4 text-emerald-500" />
                </div>
                <CardTitle className="text-sm font-medium">Almacenamiento</CardTitle>
              </CardHeader>
              <Separator />
              <CardContent className="space-y-3 p-5">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">
                    {formatBytes(sub.storage_used)} de {formatBytes(sub.storage_limit)} usados
                  </span>
                  <span className="font-medium tabular-nums">
                    {sub.storage_limit > 0 ? `${storagePct}%` : "—"}
                  </span>
                </div>
                <Progress
                  value={sub.storage_limit > 0 ? storagePct : 100}
                  className="h-2"
                />
              </CardContent>
            </Card>
          </div>

          {/* Procesamiento prioritario */}
          <Card>
            <CardHeader className="flex flex-row items-center gap-3 px-5 py-4">
              <div className={sub.priority_processing
                ? "flex h-9 w-9 items-center justify-center rounded-lg bg-amber-500/10"
                : "flex h-9 w-9 items-center justify-center rounded-lg bg-muted"
              }>
                <Zap className={sub.priority_processing ? "h-4 w-4 text-amber-500" : "h-4 w-4 text-muted-foreground"} />
              </div>
              <div>
                <CardTitle className="text-sm font-medium">Procesamiento Prioritario</CardTitle>
                <p className="text-xs text-muted-foreground">
                  {sub.priority_processing
                    ? "Tus archivos se procesan antes que los de usuarios Free/Starter"
                    : "Disponible en planes Pro y Business"}
                </p>
              </div>
              <div className="ml-auto">
                {sub.priority_processing ? (
                  <Badge variant="success" className="gap-1">
                    <ShieldCheck className="h-3 w-3" />
                    Activo
                  </Badge>
                ) : (
                  <Badge variant="secondary">No incluido</Badge>
                )}
              </div>
            </CardHeader>
          </Card>

          {/* Upgrade prompt for free users */}
          {sub.plan === "free" && (
            <Card className="border-primary/30 bg-primary/5">
              <CardContent className="flex items-center justify-between p-5">
                <div className="flex items-center gap-3">
                  <Zap className="h-5 w-5 text-primary" />
                  <div>
                    <p className="text-sm font-medium">Actualiza tu plan</p>
                    <p className="text-xs text-muted-foreground">
                      Obtén más conversiones, almacenamiento y procesamiento prioritario.
                    </p>
                  </div>
                </div>
                <Button size="sm" asChild>
                  <a href="/pricing">Ver planes</a>
                </Button>
              </CardContent>
            </Card>
          )}
        </>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <CreditCard className="mb-4 h-8 w-8 text-muted-foreground" />
            <p className="text-sm font-medium">No se pudo cargar la información</p>
            <p className="mt-1 text-xs text-muted-foreground">Inicia sesión para ver tu facturación.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
