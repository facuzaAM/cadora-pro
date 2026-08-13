"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import * as Sentry from "@sentry/nextjs";
import Script from "next/script";
import { Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { PricingCard } from "@/components/features/pricing/pricing-card";
import { LandingNav } from "@/components/features/landing/landing-nav";
import { SiteFooter } from "@/components/layout/site-footer";
import { PageHero } from "@/components/shared/page-hero";
import { PLANS as DISPLAY_PLANS } from "@/lib/constants";
import { billingService, type Plan } from "@/services/billing.service";
import { api } from "@/services/api";
import { decodeJwtPayload } from "@/lib/jwt";
import { useAuth } from "@/hooks/useAuth";
import { track } from "@/lib/analytics";

function getUserIdFromToken(): string | undefined {
  const token = api.getAccessToken();
  if (!token) return undefined;
  const payload = decodeJwtPayload(token);
  return typeof payload?.sub === "string" ? payload.sub : undefined;
}

export default function PricingPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" />}>
      <PricingContent />
    </Suspense>
  );
}

function PricingContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const requestedPlan = searchParams.get("plan");
  const { refreshUser } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [userPlan, setUserPlan] = useState<string | undefined>();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [paddleLoaded, setPaddleLoaded] = useState(false);
  const [paddleReady, setPaddleReady] = useState(false);
  const autoOpenedRef = useRef(false);

  useEffect(() => {
    billingService.getPlans().then(setPlans).catch((err) => { Sentry.captureException(err); });
  }, []);

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

  const handleCheckoutCompleted = useCallback(async () => {
    toast.success("Suscripción activada. ¡Bienvenido a Cadora!");
    try {
      await refreshUser();
    } finally {
      router.push("/billing");
    }
  }, [refreshUser, router]);

  const eventCallback = useCallback((event: Paddle.CheckoutEvent) => {
    if (event.name === "checkout.completed") {
      track("checkout_completed");
      void handleCheckoutCompleted();
    }
  }, [handleCheckoutCompleted]);

  useEffect(() => {
    if (autoOpenedRef.current || !paddleReady || !isAuthenticated || !requestedPlan) return;
    if (userPlan === requestedPlan) return;
    const plan = plans.find((p) => p.id === requestedPlan);
    if (!plan?.paddle_price_id) return;

    autoOpenedRef.current = true;
    const userId = getUserIdFromToken();
    window.Paddle.Checkout.open({
      items: [{ priceId: plan.paddle_price_id, quantity: 1 }],
      customData: { plan: plan.id, user_id: userId },
      settings: {
        displayMode: "overlay",
        theme: "light",
      },
      eventCallback,
    });
  }, [paddleReady, isAuthenticated, requestedPlan, userPlan, plans, eventCallback]);

  const handleSubscribe = useCallback(async (planId: string) => {
    if (!window.Paddle || !paddleReady) return;
    const plan = plans.find((p) => p.id === planId);
    if (!plan?.paddle_price_id) return;

    const userId = getUserIdFromToken();
    window.Paddle.Checkout.open({
      items: [{ priceId: plan.paddle_price_id, quantity: 1 }],
      customData: { plan: planId, user_id: userId },
      settings: {
        displayMode: "overlay",
        theme: "light",
      },
      eventCallback,
    });
  }, [paddleReady, plans, eventCallback]);

  return (
    <div className="flex min-h-screen flex-col">
      <Script
        src="https://cdn.paddle.com/paddle/v2/paddle.js"
        strategy="afterInteractive"
        onLoad={() => setPaddleLoaded(true)}
      />

      <LandingNav />

      <PageHero
        title="Planes y Precios"
        subtitle="Elegí el plan que mejor se adapte a tus necesidades"
      />

      <main className="flex-1 py-16 lg:py-24">
        <div className="mx-auto max-w-6xl px-4">
          <div className="grid gap-8 lg:grid-cols-4">
            {DISPLAY_PLANS.map((display) => (
              <PricingCard
                key={display.id}
                {...display}
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
