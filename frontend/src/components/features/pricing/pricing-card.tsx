"use client";

import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useState } from "react";

interface PricingCardProps {
  id: string;
  name: string;
  price: number;
  description: string;
  features: readonly string[];
  cta: string;
  popular: boolean;
  conversions: string;
  storage: string;
  priority: boolean;
  userPlan?: string;
  isAuthenticated?: boolean;
  onSubscribe?: (planId: string) => Promise<void>;
}

export function PricingCard({
  id,
  name,
  price,
  description,
  features,
  cta,
  popular,
  conversions,
  storage,
  priority,
  userPlan,
  isAuthenticated,
  onSubscribe,
}: PricingCardProps) {
  const [loading, setLoading] = useState(false);
  const isCurrentPlan = userPlan === id;

  const handleClick = async () => {
    if (id === "free") {
      window.location.href = isAuthenticated ? "/dashboard" : "/register";
      return;
    }
    if (!isAuthenticated) {
      window.location.href = "/login";
      return;
    }
    if (onSubscribe) {
      setLoading(true);
      try {
        await onSubscribe(id);
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <Card
      className={cn(
        "relative flex flex-col p-6 transition-all duration-300",
        popular && "border-primary shadow-lg ring-1 ring-primary",
        isCurrentPlan && "ring-2 ring-emerald-500/50",
      )}
    >
      {popular && !isCurrentPlan && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-1 text-xs font-medium text-primary-foreground">
          Más popular
        </div>
      )}
      {isCurrentPlan && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-emerald-500 px-3 py-1 text-xs font-medium text-white">
          Plan actual
        </div>
      )}

      <div className="mb-6">
        <h3 className="text-lg font-semibold">{name}</h3>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        <div className="mt-4 flex items-baseline gap-1">
          <span className="text-3xl font-bold">
            {price === 0 ? "Gratis" : `$${price}`}
          </span>
          {price > 0 && (
            <span className="text-sm text-muted-foreground">/mes</span>
          )}
        </div>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 rounded-lg border bg-muted/30 p-3 text-sm">
        <div>
          <p className="text-xs text-muted-foreground">Conversiones</p>
          <p className="font-medium">{conversions}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Almacenamiento</p>
          <p className="font-medium">{storage}</p>
        </div>
        {priority && (
          <div className="col-span-2">
            <p className="text-xs text-muted-foreground">Procesamiento</p>
            <p className="font-medium text-amber-600 dark:text-amber-400">
              Prioritario
            </p>
          </div>
        )}
      </div>

      <ul className="mb-8 flex flex-1 flex-col gap-3">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <span>{f}</span>
          </li>
        ))}
      </ul>

      <Button
        variant={isCurrentPlan ? "secondary" : popular ? "default" : "outline"}
        className="w-full"
        disabled={loading || isCurrentPlan}
        onClick={handleClick}
      >
        {loading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Procesando...
          </>
        ) : isCurrentPlan ? (
          "Plan actual"
        ) : (
          cta
        )}
      </Button>
    </Card>
  );
}
