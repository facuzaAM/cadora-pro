import { DemoUploader } from "@/components/features/landing/demo-uploader";
import { FeaturesGrid } from "@/components/features/landing/features-grid";
import { HowItWorks } from "@/components/features/landing/how-it-works";
import { StructuredData } from "@/components/shared/structured-data";
import { Cta } from "@/components/features/landing/cta";
import { LandingNav } from "@/components/features/landing/landing-nav";
import { SiteFooter } from "@/components/layout/site-footer";

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <LandingNav />
      <main className="flex-1">
        <DemoUploader />
        <FeaturesGrid />
        <div className="relative">
          <div className="absolute inset-x-0 -top-24 h-24 bg-gradient-to-b from-background to-transparent pointer-events-none z-10" />
          <HowItWorks />
        </div>
        <div className="relative">
          <div className="absolute -left-32 top-1/2 h-72 w-72 -translate-y-1/2 rounded-full bg-primary/5 blur-3xl pointer-events-none" />
          <div className="absolute -right-32 top-1/2 h-72 w-72 -translate-y-1/2 rounded-full bg-emerald-500/5 blur-3xl pointer-events-none" />
          <Cta />
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
