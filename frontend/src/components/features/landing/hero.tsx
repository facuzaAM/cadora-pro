import Link from "next/link";
import { APP_TAGLINE, APP_DESCRIPTION } from "@/lib/constants";

export function Hero() {
  return (
    <section className="relative flex min-h-screen items-center justify-center overflow-hidden">
      <div
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: "url(/images/e2747d55-610b-470f-b749-b4e1e8b9ec2d.png)" }}
      />
      <div className="absolute inset-0 bg-black/60" />
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-background" />

      <div className="relative z-10 mx-auto max-w-4xl px-4 text-center">
        <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-sm text-white/80 backdrop-blur-sm">
          <span className="inline-block h-2 w-2 rounded-full bg-primary animate-pulse" />
          Lanzamos nueva plataforma de conversión CAD
        </div>

        <h1 className="text-5xl font-bold leading-tight tracking-tight text-white sm:text-6xl lg:text-7xl">
          {APP_TAGLINE}
        </h1>

        <p className="mx-auto mt-6 max-w-2xl text-lg text-white/60 sm:text-xl">
          {APP_DESCRIPTION}
        </p>

        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link
            href="/register"
            className="inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-primary px-8 text-base font-semibold text-white shadow-lg shadow-primary/25 transition-all hover:bg-primary/90 hover:shadow-primary/30 active:scale-[0.98]"
          >
            Comenzar gratis
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </Link>
          <Link
            href="/pricing"
            className="inline-flex h-12 items-center justify-center rounded-xl border border-white/10 bg-white/5 px-8 text-base font-medium text-white/80 backdrop-blur-sm transition-all hover:bg-white/10 hover:text-white active:scale-[0.98]"
          >
            Ver Planes
          </Link>
        </div>
      </div>
    </section>
  );
}
