import { PageHeader } from "@/components/shared/page-header";
import { SettingsForm } from "@/components/features/settings/settings-form";

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader
        title="Configuración"
        description="Personaliza tu experiencia en Cadora"
      />
      <SettingsForm />
    </div>
  );
}
