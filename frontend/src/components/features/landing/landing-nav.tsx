"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { Logo } from "@/components/shared/logo";
import { ThemeToggle } from "@/components/shared/theme-toggle";
import { UserButton } from "@/components/features/auth/user-button";

const links = [
  { href: "/", label: "Inicio" },
  { href: "/como-funciona", label: "Cómo funciona" },
  { href: "/tecnologia", label: "Tecnología" },
  { href: "/comparativa", label: "Comparativa" },
  { href: "/pricing", label: "Precios" },
  { href: "/contacto", label: "Contacto" },
];

export function LandingNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  return (
    <>
    <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 animate-nav-bg">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:grid sm:grid-cols-3">
        <Link href="/" onClick={() => setOpen(false)}>
          <Logo />
        </Link>
        <nav className="hidden items-center justify-center gap-4 sm:flex" style={{ minWidth: 0 }}>
          {links.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`nav-link whitespace-nowrap text-sm font-medium transition-colors hover:text-foreground ${
                  active ? "text-foreground nav-link-active" : "text-muted-foreground"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
        <div className="flex items-center gap-2 sm:justify-end">
          <ThemeToggle />
          <UserButton />
          <button
            type="button"
            aria-label={open ? "Cerrar menú" : "Abrir menú"}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
            className="flex h-9 w-9 items-center justify-center rounded-lg border text-muted-foreground transition-colors hover:text-foreground sm:hidden"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {open && (
        <nav className="border-t bg-background/95 backdrop-blur sm:hidden">
          <div className="mx-auto max-w-6xl space-y-1 px-4 py-3">
            {links.map((link) => {
              const active = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setOpen(false)}
                  className={`block rounded-lg px-3 py-2.5 text-sm font-medium transition-colors hover:bg-accent hover:text-foreground ${
                    active ? "bg-accent/60 text-foreground" : "text-muted-foreground"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>
        </nav>
      )}
    </header>
    </>
  );
}
