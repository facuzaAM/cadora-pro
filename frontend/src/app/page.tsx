import { Hero } from "@/components/features/landing/hero";
import { DemoUploader } from "@/components/features/landing/demo-uploader";
import { FeaturesGrid } from "@/components/features/landing/features-grid";
import { HowItWorks } from "@/components/features/landing/how-it-works";
import { Cta } from "@/components/features/landing/cta";
import { LandingNav } from "@/components/features/landing/landing-nav";
import { SiteFooter } from "@/components/layout/site-footer";

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <LandingNav />
      <main className="flex-1">
        <Hero />
        <DemoUploader />
        <FeaturesGrid />
        <HowItWorks />
        <Cta />
      </main>
      <SiteFooter />
    </div>
  );
}
