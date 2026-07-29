"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { StatsCards } from "@/components/features/dashboard/stats-cards";
import { RecentProjects } from "@/components/features/dashboard/recent-projects";
import { ProcessingStatus } from "@/components/features/dashboard/processing-status";
import { ProcessingHistory } from "@/components/features/dashboard/processing-history";
import { CreditUsage } from "@/components/features/dashboard/credit-usage";
import { EmailVerificationBanner } from "@/components/features/dashboard/email-verification-banner";
import { useAuth } from "@/hooks/useAuth";

export default function DashboardPage() {
  const { user } = useAuth();
  const name = user?.name || user?.email?.split("@")[0] || "";

  return (
    <div className="space-y-6">
      <EmailVerificationBanner />
      <PageHeader
        title="Dashboard"
        description={`Bienvenido de nuevo, ${name}`}
        action={
          <Button asChild>
            <Link href="/projects/upload/new">
              <Plus className="mr-2 h-4 w-4" />
              Nuevo Proyecto
            </Link>
          </Button>
        }
      />

      <StatsCards />

      <div className="relative">
        <div className="absolute inset-0 bg-dot-pattern-sm opacity-40 pointer-events-none" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-background/80 to-transparent pointer-events-none" />
        <div className="relative grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <RecentProjects />
          </div>
          <div>
            <ProcessingStatus />
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ProcessingHistory />
        </div>
        <div>
          <CreditUsage />
        </div>
      </div>
    </div>
  );
}
