"use client";

import { useEffect, useState } from "react";
import { Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { billingService, type Subscription } from "@/services/billing.service";

export function CreditUsage() {
  const [sub, setSub] = useState<Subscription | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token") || undefined;
    billingService.getSubscription(token).then(setSub).catch(() => {});
  }, []);

  const used = sub?.conversions_used ?? 0;
  const total = sub?.conversions_limit ?? 5;
  const pct = total > 0 ? Math.round((used / total) * 100) : 0;
  const planName = sub?.plan
    ? sub.plan.charAt(0).toUpperCase() + sub.plan.slice(1)
    : "Free";

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between px-5 py-4">
        <CardTitle className="text-sm font-medium">Consumo de Créditos</CardTitle>
        <span className="rounded-full bg-violet-500/10 px-2.5 py-0.5 text-[11px] font-medium text-violet-600 dark:text-violet-400">
          Plan {planName}
        </span>
      </CardHeader>
      <Separator />
      <CardContent className="space-y-5 p-5">
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              {used} de {total} usados
            </span>
            <span className="font-medium tabular-nums">{pct}%</span>
          </div>
          <Progress value={pct} className="h-2" />
        </div>

        {sub && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-lg border p-3">
                <p className="text-muted-foreground">Almacenamiento</p>
                <p className="mt-1 font-medium">
                  {sub.storage_used
                    ? `${(sub.storage_used / (1024 * 1024)).toFixed(1)} MB`
                    : "0 MB"}{" "}
                  / {sub.storage_limit ? `${(sub.storage_limit / (1024 * 1024)).toFixed(0)} MB` : "50 MB"}
                </p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="text-muted-foreground">Procesamiento</p>
                <p className="mt-1 font-medium">
                  {sub.priority_processing ? "Prioritario" : "Estándar"}
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="rounded-lg border bg-muted/30 p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-amber-500" />
              <span className="text-xs font-medium">Plan actual</span>
            </div>
            <span className="text-xs text-muted-foreground">{planName}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
