"use client";

import { useCallback, useEffect, useState } from "react";
import { PricingCard } from "@/components/features/pricing/pricing-card";
import { LandingNav } from "@/components/features/landing/landing-nav";
import { Logo } from "@/components/shared/logo";
import { PLANS } from "@/lib/constants";
import { billingService } from "@/services/billing.service";

export default function PricingPage() {
  const [userPlan, setUserPlan] = useState<string | undefined>();
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      setIsAuthenticated(true);
      billingService.getSubscription(token).then((sub) => {
        setUserPlan(sub.plan);
      }).catch(() => {});
    }
  }, []);

  const handleSubscribe = useCallback(async (planId: string) => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    const plan = PLANS.find((p) => p.id === planId);
    if (!plan?.stripePriceId) return;
    const res = await billingService.createCheckoutSession(planId, plan.stripePriceId, token);
    if (res.url) {
      window.location.href = res.url;
    }
  }, []);

  return (
    <div className="flex min-h-screen flex-col">
      <LandingNav />

      <main className="flex-1 py-16 lg:py-24">
        <div className="mx-auto max-w-6xl px-4">
          <div className="text-center">
            <h1 className="text-4xl font-bold tracking-tight">Planes y Precios</h1>
            <p className="mt-2 text-muted-foreground">
              Elige el plan que mejor se adapte a tus necesidades
            </p>
          </div>

          <div className="mt-12 grid gap-8 lg:grid-cols-4">
            {PLANS.map((plan) => (
              <PricingCard
                key={plan.id}
                {...plan}
                userPlan={userPlan}
                isAuthenticated={isAuthenticated}
                onSubscribe={handleSubscribe}
              />
            ))}
          </div>
        </div>
      </main>

      <footer className="border-t py-8">
        <div className="mx-auto max-w-6xl px-4">
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <Logo />
            <p className="text-sm text-muted-foreground">
              &copy; 2026 Cadora. Todos los derechos reservados.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
