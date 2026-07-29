import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Cta() {
  return (
    <section className="relative py-16 lg:py-24">
      <div className="mx-auto max-w-6xl px-4">
        <div className="relative overflow-hidden rounded-2xl border bg-gradient-to-br from-primary/10 via-card to-emerald-500/5 px-6 py-16 text-center lg:px-16 shadow-xl shadow-primary/5">
          <div className="absolute -left-16 -top-16 h-32 w-32 animate-blob rounded-full bg-primary/10 blur-3xl" />
          <div className="absolute -bottom-16 -right-16 h-32 w-32 animate-blob-delayed rounded-full bg-emerald-500/10 blur-3xl" />
          <div className="relative z-10">
            <h2 className="text-3xl font-bold tracking-tight">
              ¿Listo para digitalizar tus planos?
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
              Únete a profesionales que ya convierten sus planos arquitectónicos en archivos CAD editables.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Button size="lg" className="shadow-lg shadow-primary/25" asChild>
                <Link href="/register">
                  Comenzar Gratis
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button variant="outline" size="lg" asChild>
                <Link href="/pricing">Ver Planes</Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
