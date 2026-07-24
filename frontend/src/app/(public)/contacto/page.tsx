import type { Metadata } from "next";
import { Mail, MessageSquare, Zap } from "lucide-react";
import { LandingNav } from "@/components/features/landing/landing-nav";
import { ContactForm } from "./contact-form";

export const metadata: Metadata = {
  title: "Contacto - Cadora",
  description: "Comunicate con el equipo de Cadora. Soporte técnico y ventas.",
};

export default function ContactoPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <LandingNav />
      <main className="mx-auto flex w-full max-w-4xl flex-1 items-center justify-center px-4 py-12">
        <div className="grid w-full gap-12 md:grid-cols-2">
          <div>
            <h1 className="text-3xl font-bold">Contacto</h1>
            <p className="mt-2 text-muted-foreground">
              Estamos para ayudarte. Respondemos en menos de 24 horas hábiles.
            </p>

            <div className="mt-8 space-y-6">
              <div className="flex items-start gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <Mail className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium">Email de soporte</p>
                  <a
                    href="mailto:soporte@cadora.pro"
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    soporte@cadora.pro
                  </a>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <MessageSquare className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium">Ventas</p>
                  <a
                    href="mailto:ventas@cadora.pro"
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    ventas@cadora.pro
                  </a>
                </div>
              </div>

              <div className="rounded-lg border bg-muted/30 p-4">
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-amber-500" />
                  <p className="text-sm font-medium">Soporte prioritario</p>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Los usuarios de los planes <strong>Pro</strong> y <strong>Business</strong> cuentan con soporte prioritario por email con respuesta en menos de 4 horas hábiles.
                </p>
              </div>
            </div>
          </div>

          <div>
            <ContactForm />
          </div>
        </div>
      </main>
    </div>
  );
}
