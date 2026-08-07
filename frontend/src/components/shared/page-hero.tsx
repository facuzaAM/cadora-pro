import type { ReactNode } from "react";
import { CadCrosshair } from "@/components/features/landing/cad-crosshair";
import { cn } from "@/lib/utils";

export function PageHero({
  title,
  subtitle,
  children,
  className,
}: {
  title: string;
  subtitle?: string;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "relative overflow-hidden border-b bg-gradient-to-b from-primary/[0.05] via-background to-background",
        className,
      )}
    >
      <div className="absolute inset-0 bg-grid-cad bg-grid-cad-fade pointer-events-none" />
      <CadCrosshair className="absolute right-[6%] top-1/2 hidden h-32 w-32 -translate-y-1/2 text-primary/25 lg:block pointer-events-none" />
      <CadCrosshair className="absolute left-[4%] top-[20%] hidden h-20 w-20 text-primary/15 lg:block pointer-events-none" />
      <div className="absolute -left-24 top-1/4 h-56 w-56 animate-blob rounded-full bg-primary/10 blur-3xl pointer-events-none" />
      <div className="absolute -right-24 bottom-0 h-56 w-56 animate-blob-delayed rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />

      <div className="relative mx-auto max-w-3xl px-4 py-16 text-center lg:py-20">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">{title}</h1>
        {subtitle && (
          <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground sm:text-xl">
            {subtitle}
          </p>
        )}
        {children}
      </div>
    </section>
  );
}
