"use client";

import { useEffect, useState } from "react";
import { FolderKanban, Timer, Cpu, Zap } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { projectsService } from "@/services/projects.service";
import { billingService } from "@/services/billing.service";
import { api } from "@/services/api";

interface Stat {
  icon: React.ElementType;
  label: string;
  value: string;
  sublabel?: string;
  trend?: { value: string; positive: boolean };
  accentClass?: string;
}

export function StatsCards() {
  const [stats, setStats] = useState<Stat[]>([
    { icon: FolderKanban, label: "Proyectos", value: "-", accentClass: "text-primary" },
    { icon: Timer, label: "Tiempo promedio", value: "-", accentClass: "text-emerald-500 dark:text-emerald-400" },
    { icon: Cpu, label: "En procesamiento", value: "-", accentClass: "text-amber-500 dark:text-amber-400" },
    { icon: Zap, label: "Créditos usados", value: "-", accentClass: "text-violet-500 dark:text-violet-400" },
  ]);

  useEffect(() => {
    const token = api.getAccessToken();
    Promise.all([
      projectsService.list(token).catch(() => []),
      billingService.getSubscription(token).catch(() => null),
    ]).then(([projects, sub]) => {
      const total = projects.length;
      const processing = projects.filter(
        (p) => p.status === "processing",
      ).length;

      setStats([
        {
          icon: FolderKanban,
          label: "Proyectos",
          value: String(total),
          sublabel: `${total} en total`,
          accentClass: "text-primary",
        },
        {
          icon: Timer,
          label: "Procesados",
          value: String(projects.filter((p) => p.status === "cad_generated").length),
          sublabel: "completados",
          accentClass: "text-emerald-500 dark:text-emerald-400",
        },
        {
          icon: Cpu,
          label: "En procesamiento",
          value: String(processing),
          sublabel: processing > 0 ? "activos" : "sin procesos",
          accentClass: "text-amber-500 dark:text-amber-400",
        },
        {
          icon: Zap,
          label: "Créditos usados",
          value: sub ? String(sub.conversions_used) : "-",
          sublabel: sub ? `de ${sub.conversions_limit} disponibles` : "inicia sesión",
          accentClass: "text-violet-500 dark:text-violet-400",
        },
      ]);
    });
  }, []);

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((s) => {
        const Icon = s.icon;
        return (
          <Card
            key={s.label}
            className="group relative overflow-hidden transition-all duration-300 hover:shadow-md hover:border-foreground/20"
          >
            <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-gradient-to-br from-foreground/[0.03] to-transparent" />
            <CardContent className="p-5">
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">{s.label}</p>
                  <p className="text-2xl font-bold tracking-tight">{s.value}</p>
                  {s.sublabel && (
                    <p className="text-xs text-muted-foreground/70">{s.sublabel}</p>
                  )}
                </div>
                <div className={cn(
                  "flex h-9 w-9 items-center justify-center rounded-lg bg-foreground/[0.04] ring-1 ring-foreground/[0.06]",
                  s.accentClass,
                )}>
                  <Icon className="h-4 w-4" />
                </div>
              </div>
              {s.trend && (
                <div className="mt-3 flex items-center gap-1.5">
                  <span className={cn(
                    "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium leading-none",
                    s.trend.positive
                      ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                      : "bg-amber-500/10 text-amber-600 dark:text-amber-400",
                  )}>
                    {s.trend.value}
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
