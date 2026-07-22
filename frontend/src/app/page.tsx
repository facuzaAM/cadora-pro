import { Logo } from "@/components/shared/logo";
import { Hero } from "@/components/features/landing/hero";
import { FeaturesGrid } from "@/components/features/landing/features-grid";
import { HowItWorks } from "@/components/features/landing/how-it-works";
import { Cta } from "@/components/features/landing/cta";
import { LandingNav } from "@/components/features/landing/landing-nav";

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <LandingNav />
      <main className="flex-1">
        <Hero />
        <FeaturesGrid />
        <HowItWorks />
        <Cta />
      </main>
      <footer className="border-t py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 sm:flex-row">
          <Logo />
          <p className="text-sm text-muted-foreground">
            &copy; 2026 Cadora. Todos los derechos reservados.
          </p>
        </div>
      </footer>
    </div>
  );
}
