"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import * as Sentry from "@sentry/nextjs";
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
  const [paddleLoaded, setPaddleLoaded] = useState(false);
  const [paddleReady, setPaddleReady] = useState(false);

  useEffect(() => {
    const token = api.getAccessToken();
    if (token) {
      setIsAuthenticated(true);
      billingService.getSubscription(token).then((sub) => {
        setUserPlan(sub.plan);
      }).catch((err) => { Sentry.captureException(err); });
    }
  }, []);

  const initPaddle = useCallback(async () => {
    if (typeof window === "undefined" || !window.Paddle) return;
    try {
      const config = await billingService.getConfig();
      window.Paddle.Initialize({
        token: config.client_token,
        environment: config.environment === "sandbox" ? "sandbox" : "production",
      });
      setPaddleReady(true);
    } catch (err) {
      Sentry.captureException(err);
    }
  }, []);

  useEffect(() => {
    if (paddleLoaded) initPaddle();
  }, [paddleLoaded, initPaddle]);

  const handleSubscribe = useCallback(async (planId: string) => {
    if (!window.Paddle || !paddleReady) return;
    const plan = PLANS.find((p) => p.id === planId);
    if (!plan?.paddlePriceId) return;

    const token = api.getAccessToken();
    let userId: string | undefined;
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        userId = payload.sub;
      } catch {}
    }
    window.Paddle.Checkout.open({
      items: [{ priceId: plan.paddlePriceId, quantity: 1 }],
      customData: { plan: planId, user_id: userId },
      settings: {
        displayMode: "overlay",
        theme: "light",
      },
    });
  }, []);

  return (
    <div className="flex min-h-screen flex-col">
      <Script
        src="https://cdn.paddle.com/paddle/v2/paddle.js"
        strategy="afterInteractive"
        onLoad={() => setPaddleLoaded(true)}
      />

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
