import type { Metadata } from "next";
import { LandingNav } from "@/components/features/landing/landing-nav";
import { SiteFooter } from "@/components/layout/site-footer";
import { PageHero } from "@/components/shared/page-hero";

export const metadata: Metadata = {
  title: "Política de Cookies - Cadora",
  description: "Política de cookies de Cadora",
};

export default function CookiesPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <LandingNav />
      <PageHero
        title="Política de Cookies"
        subtitle="Última actualización: Julio 2026"
      />
      <main className="mx-auto max-w-3xl px-4 py-12">

        <div className="mt-8 space-y-6 text-sm leading-relaxed text-muted-foreground">
          <section>
            <h2 className="text-lg font-semibold text-foreground">1. ¿Qué son las cookies?</h2>
            <p className="mt-2">Las cookies son pequeños archivos que se almacenan en tu navegador para mejorar tu experiencia en nuestro sitio.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">2. Cookies que utilizamos</h2>
            <div className="mt-2 overflow-hidden rounded-lg border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-muted/50">
                    <th className="px-4 py-2 text-left font-medium">Tipo</th>
                    <th className="px-4 py-2 text-left font-medium">Propósito</th>
                    <th className="px-4 py-2 text-left font-medium">Duración</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-t"><td className="px-4 py-2">Esenciales</td><td className="px-4 py-2">Autenticación y seguridad</td><td className="px-4 py-2">Sesión</td></tr>
                  <tr className="border-t"><td className="px-4 py-2">Preferencias</td><td className="px-4 py-2">Tema oscuro/claro</td><td className="px-4 py-2">1 año</td></tr>
                  <tr className="border-t"><td className="px-4 py-2">Analítica</td><td className="px-4 py-2">Uso del sitio (anónimo)</td><td className="px-4 py-2">30 días</td></tr>
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">3. Control de cookies</h2>
            <p className="mt-2">Podés gestionar las cookies desde la configuración de tu navegador. Las cookies esenciales son necesarias para el funcionamiento del sitio.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">4. Más información</h2>
            <p className="mt-2">Para más información: <a href="mailto:privacidad@cadora.pro" className="text-primary underline-offset-4 hover:underline">privacidad@cadora.pro</a></p>
          </section>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
