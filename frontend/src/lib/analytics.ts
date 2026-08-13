"use client";

/**
 * GA4 event helper. GA4 is loaded by GoogleAnalytics only when the user has
 * consented (cadora_cookie_consent). This enqueues a gtag event if available,
 * so we can measure the product funnel (upload → detect → export) and the
 * engine quality signal.
 */
type EventParams = Record<string, string | number | boolean | null | undefined>;

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
  }
}

export function track(event: string, params?: EventParams) {
  if (typeof window === "undefined" || typeof window.gtag !== "function") return;
  try {
    window.gtag("event", event, params ?? {});
  } catch {
    /* analytics must never break the product */
  }
}
