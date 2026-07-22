"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { LayoutDashboard, FolderKanban, CreditCard, User, Settings, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Logo } from "@/components/shared/logo";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { PLANS } from "@/lib/constants";
import { useAuth } from "@/hooks/useAuth";
import { billingService } from "@/services/billing.service";

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Mis Proyectos", href: "/projects", icon: FolderKanban },
  { label: "Facturación", href: "/billing", icon: CreditCard },
  { label: "Perfil", href: "/profile", icon: User },
  { label: "Configuración", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, loading } = useAuth();
  const [plan, setPlan] = useState("free");

  useEffect(() => {
    const token = localStorage.getItem("access_token") || undefined;
    billingService.getSubscription(token).then((sub) => {
      setPlan(sub.plan);
    }).catch(() => {});
  }, []);

  const planInfo = PLANS.find((p) => p.id === plan);
  const planLabel = planInfo?.name || (plan.charAt(0).toUpperCase() + plan.slice(1));
  const name = user?.name || user?.email?.split("@")[0] || "";
  const avatarUrl = user?.avatar_url || "";
  const initials = name
    .split(" ")
    .map((n: string) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <aside className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-64 lg:flex-col">
      <div className="flex h-full flex-col gap-4 border-r bg-card px-4 py-6">
        <div className="flex items-center gap-2 px-2">
          <Logo />
        </div>

        <Button variant="outline" className="w-full justify-start gap-2" asChild>
          <Link href="/projects/upload/new">
            <Plus className="h-4 w-4" /> Nuevo Proyecto
          </Link>
        </Button>

        <Separator />

        <nav className="flex flex-1 flex-col gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <Separator />

        <Link
          href="/billing"
          className="flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-accent"
        >
          {loading ? (
            <Skeleton className="h-8 w-8 rounded-full" />
          ) : (
            <Avatar className="h-8 w-8">
              <AvatarImage src={avatarUrl} alt={name} />
              <AvatarFallback className="text-xs">{initials}</AvatarFallback>
            </Avatar>
          )}
          <div className="flex flex-1 flex-col">
            {loading ? (
              <>
                <Skeleton className="h-4 w-24" />
                <Skeleton className="mt-1 h-3 w-16" />
              </>
            ) : (
              <>
                <span className="text-sm font-medium">{name}</span>
                <span className="text-xs text-muted-foreground">Plan {planLabel}</span>
              </>
            )}
          </div>
        </Link>
      </div>
    </aside>
  );
}
