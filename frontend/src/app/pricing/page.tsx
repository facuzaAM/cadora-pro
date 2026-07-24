"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Script from "next/script";
import { PricingCard } from "@/components/features/pricing/pricing-card";
import { LandingNav } from "@/components/features/landing/landing-nav";
import { SiteFooter } from "@/components/layout/site-footer";
import { PLANS } from "@/lib/constants";
import { billingService } from "@/services/billing.service";
import { api } from "@/services/api";

export default function PricingPage() {
  const [userPlan, setUserPlan] = useState<string | undefined>();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const paddleReady = useRef(false);

  useEffect(() => {
    const token = api.getAccessToken();
    if (token) {
      setIsAuthenticated(true);
      billingService.getSubscription(token).then((sub) => {
        setUserPlan(sub.plan);
      }).catch(() => {});
    }
  }, []);

  useEffect(() => {
    const initPaddle = async () => {
      if (paddleReady.current || typeof window === "undefined" || !window.Paddle) return;
      try {
        const config = await billingService.getConfig();
        window.Paddle.Initialize({
          token: config.client_token,
          environment: config.environment === "sandbox" ? "sandbox" : "production",
        });
        paddleReady.current = true;
      } catch {
        // Paddle init failed — checkout won't work
      }
    };

    const checkPaddle = setInterval(() => {
      if (typeof window !== "undefined" && window.Paddle) {
        clearInterval(checkPaddle);
        initPaddle();
      }
    }, 100);

    return () => clearInterval(checkPaddle);
  }, []);

  const handleSubscribe = useCallback(async (planId: string) => {
    if (!window.Paddle || !paddleReady.current) return;
    const plan = PLANS.find((p) => p.id === planId);
    if (!plan?.paddlePriceId) return;

    window.Paddle.Checkout.open({
      items: [{ priceId: plan.paddlePriceId, quantity: 1 }],
      customData: { plan: planId },
      settings: {
        displayMode: "overlay",
        theme: "light",
      },
    });
  }, []);

  return (
    <div className="flex min-h-screen flex-col">
      <Script src="https://cdn.paddle.com/paddle/v2/paddle.js" strategy="afterInteractive" />

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

      <SiteFooter />
    </div>
  );
}
