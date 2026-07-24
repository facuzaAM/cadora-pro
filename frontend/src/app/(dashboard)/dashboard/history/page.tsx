"use client";

import { PageHeader } from "@/components/shared/page-header";
import { ConversionHistory } from "@/components/features/dashboard/conversion-history";

export default function HistoryPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Historial de Conversiones"
        description="Todos tus planos procesados con estado y acciones"
      />
      <ConversionHistory />
    </div>
  );
}
