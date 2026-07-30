"use client";

import { useEffect } from "react";
import Script from "next/script";

const gaId = process.env.NEXT_PUBLIC_GA_ID;

function DisableIfNoConsent() {
  useEffect(() => {
    if (!gaId) return;
    let consent = false;
    try {
      const stored = localStorage.getItem("cadora_cookie_consent");
      consent = stored === "accepted";
    } catch {}
    if (!consent) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any)[`ga-disable-${gaId}`] = true;
    }
  }, []);
  return null;
}

export function GoogleAnalytics() {
  if (!gaId) return null;

  return (
    <>
      <DisableIfNoConsent />
      <Script
        src={`https://www.googletagmanager.com/gtag/js?id=${gaId}`}
        strategy="afterInteractive"
      />
      <Script id="google-analytics" strategy="afterInteractive">
        {`
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());
          gtag('config', '${gaId}', {
            page_path: window.location.pathname,
          });
        `}
      </Script>
    </>
  );
}
