import type { Metadata } from "next";
import Link from "next/link";
import { Logo } from "@/components/shared/logo";

export const metadata: Metadata = {
  title: "Términos del Servicio - Cadora",
  description: "Términos y condiciones de uso de Cadora",
};

export default function TerminosPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b">
        <div className="mx-auto flex h-14 max-w-3xl items-center px-4">
          <Link href="/"><Logo /></Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="text-3xl font-bold">Términos del Servicio</h1>
        <p className="mt-2 text-sm text-muted-foreground">Última actualización: Julio 2026</p>

        <div className="mt-8 space-y-6 text-sm leading-relaxed text-muted-foreground">
          <section>
            <h2 className="text-lg font-semibold text-foreground">1. Aceptación de los términos</h2>
            <p className="mt-2">Al acceder y usar Cadora, aceptás cumplir con estos términos. Si no estás de acuerdo, no uses el servicio.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">2. Descripción del servicio</h2>
            <p className="mt-2">Cadora es una plataforma SaaS que permite la conversión de planos arquitectónicos a formatos CAD. Los usuarios pueden subir planos, procesarlos y descargar los resultados.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">3. Cuentas de usuario</h2>
            <p className="mt-2">Sos responsable de mantener la confidencialidad de tu cuenta y contraseña. Notificanos inmediatamente sobre cualquier uso no autorizado.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">4. Planes y facturación</h2>
            <p className="mt-2">Ofrecemos planes Free, Starter, Pro y Business. Las suscripciones se renuevan automáticamente. Podés cancelar en cualquier momento desde tu panel de facturación.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">5. Limitación de responsabilidad</h2>
            <p className="mt-2">Cadora no se responsabiliza por la exactitud de las conversiones generadas por el sistema. El usuario es responsable de verificar los resultados.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">6. Contacto</h2>
            <p className="mt-2">Para consultas sobre estos términos, escribinos a <a href="mailto:legal@cadora.pro" className="text-primary underline-offset-4 hover:underline">legal@cadora.pro</a>.</p>
          </section>
        </div>
      </main>
    </div>
  );
}
