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

        <div className="mt-8 space-y-8 text-sm leading-relaxed text-muted-foreground">
          <section>
            <h2 className="text-lg font-semibold text-foreground">1. Aceptación de los términos</h2>
            <div className="mt-2 space-y-2">
              <p>Al acceder y usar Cadora (en adelante, &quot;el Servicio&quot;), aceptás cumplir con estos Términos del Servicio. Si no estás de acuerdo con alguno de estos términos, no uses el Servicio.</p>
              <p>Estos términos constituyen un acuerdo legal entre vos y [EMPRESA LEGAL] (en adelante, &quot;Cadora&quot;, &quot;nosotros&quot;).</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">2. Descripción del servicio</h2>
            <div className="mt-2">
              <p>Cadora es una plataforma SaaS que permite la conversión de planos arquitectónicos a formatos CAD (DXF/DWG) mediante procesamiento de imagen e inteligencia artificial. Los usuarios pueden subir planos, procesarlos automáticamente y descargar los archivos resultantes.</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">3. Cuentas de usuario</h2>
            <div className="mt-2 space-y-2">
              <p>Sos responsable de mantener la confidencialidad de tu cuenta y contraseña. Acceptás notificarnos inmediatamente sobre cualquier uso no autorizado de tu cuenta.</p>
              <p>No podés transferir tu cuenta a terceros. Una cuenta es personal e intransferible.</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">4. Uso aceptable</h2>
            <div className="mt-2 space-y-2">
              <p>Te comprometés a usar el Servicio de manera lícita y conforme a estos términos. Está prohibido:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Usar el Servicio para fines ilegales o no autorizados.</li>
                <li>Intentar acceder, modificar o interrumpir la infraestructura del Servicio sin autorización.</li>
                <li>Realizar ingeniería inversa, descompilar o extraer el código fuente o los modelos de detección.</li>
                <li>Usar el Servicio para generar contenido que viole derechos de terceros.</li>
                <li>Automatizar o abusar del sistema de forma que afecte la experiencia de otros usuarios (scraper, bots, etc.).</li>
                <li>Re-vender o redistribuir el Servicio sin autorización escrita.</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">5. Planes, precios y facturación</h2>
            <div className="mt-2 space-y-2">
              <p>Ofrecemos planes Free, Starter, Pro y Business con las características y precios publicados en <Link href="/pricing" className="text-primary underline-offset-4 hover:underline">cadora.pro/pricing</Link>. Los precios están expresados en USD y no incluyen impuestos aplicables.</p>
              <p>Las suscripciones de pago se renuevan automáticamente al final de cada período de facturación, salvo que las canceles antes de la fecha de renovación.</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">6. Cancelación y reembolsos</h2>
            <div className="mt-2 space-y-2">
              <p><strong className="text-foreground">Cancelación:</strong> podés cancelar tu suscripción en cualquier momento desde la sección de facturación de tu cuenta. La cancelación es efectiva al final del período ya pagado, y conservás acceso al servicio hasta esa fecha.</p>
              <p><strong className="text-foreground">Reembolso dentro de los primeros 7 días:</strong> si solicitás la cancelación dentro de los primeros 7 días desde tu primer pago, tenés derecho a un reembolso total sin preguntas.</p>
              <p><strong className="text-foreground">Después de los 7 días:</strong> no se realizan reembolsos. La suscripción se mantiene activa hasta el fin del período pagado.</p>
              <p><strong className="text-foreground">Créditos y consumos:</strong> los créditos adicionales comprados no son reembolsables una vez consumidos. Si no fueron consumidos dentro de los 30 días posteriores a la compra, son reembolsables.</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">7. Propiedad intelectual y archivos</h2>
            <div className="mt-2 space-y-2">
              <p><strong className="text-foreground">Tus archivos:</strong> sos el único propietario de los planos que subís y de los archivos DXF/DWG que se generan. Cadora no reclama ningún derecho de propiedad sobre ellos.</p>
              <p><strong className="text-foreground">Licencia de uso:</strong> al subir un plano, nos otorgás una licencia limitada, no exclusiva y temporal para procesarlo y generar el resultado correspondiente. Esta licencia se extingue cuando eliminás el archivo o tu cuenta.</p>
              <p><strong className="text-foreground">Propiedad de Cadora:</strong> la plataforma, el software, los modelos de detección y el diseño de la interfaz son propiedad de [EMPRESA LEGAL] y están protegidos por las leyes de propiedad intelectual de [JURISDICCIÓN].</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">8. Limitación de responsabilidad</h2>
            <div className="mt-2 space-y-2">
              <p><strong className="text-foreground">Precisión de la detección:</strong> Cadora utiliza inteligencia artificial y visión por computadora para detectar elementos arquitectónicos de forma automática. Si bien buscamos ofrecer resultados precisos, la detección automática no es infalible. El usuario es responsable de revisar y verificar los archivos generados antes de usarlos en proyectos profesionales.</p>
              <p><strong className="text-foreground">Garantía:</strong> el Servicio se proporciona &quot;tal cual&quot; y &quot;según disponibilidad&quot;, sin garantías explícitas o implícitas de exactitud, idoneidad para un fin particular o no infracción.</p>
              <p><strong className="text-foreground">Daños:</strong> en ningún caso [EMPRESA LEGAL] será responsable por daños indirectos, incidentales, especiales o consecuentes que resulten del uso o imposibilidad de uso del Servicio.</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">9. Privacidad</h2>
            <div className="mt-2">
              <p>El uso de tus datos personales se rige por nuestra <Link href="/privacidad" className="text-primary underline-offset-4 hover:underline">Política de Privacidad</Link>, que forma parte integral de estos términos.</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">10. Modificaciones</h2>
            <div className="mt-2">
              <p>Nos reservamos el derecho de modificar estos términos en cualquier momento. Te notificaremos sobre cambios significativos por email o mediante un aviso en la plataforma. El uso continuado del Servicio después de los cambios constituye la aceptación de los nuevos términos.</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">11. Ley aplicable y jurisdicción</h2>
            <div className="mt-2">
              <p>Estos términos se rigen por las leyes de [JURISDICCIÓN]. Cualquier controversia derivada de estos términos o del uso del Servicio será sometida a la jurisdicción de los tribunales de [JURISDICCIÓN].</p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground">12. Contacto</h2>
            <div className="mt-2">
              <p>Para consultas sobre estos términos: <a href="mailto:legal@cadora.pro" className="text-primary underline-offset-4 hover:underline">legal@cadora.pro</a>.</p>
              <p className="mt-1">[EMPRESA LEGAL] — [DIRECCIÓN] — [JURISDICCIÓN]</p>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
