import { api } from "@/services/api";

export interface ExportData {
  exported_at: string;
  profile: {
    id: string;
    email: string;
    name: string;
    avatar_url: string | null;
    email_verified: boolean;
    created_at: string;
  };
  subscription: {
    plan: string;
    status: string;
    subscription_end: string | null;
    conversions_used: number;
    conversions_limit: number;
    storage_used: number;
    storage_limit: number;
  };
  projects: Array<{
    id: string;
    name: string;
    description: string | null;
    status: string;
    created_at: string;
    documents: Array<{
      id: string;
      filename: string;
      file_type: string;
      file_size: number;
      download_url: string | null;
      created_at: string;
    }>;
  }>;
}

export async function exportMyData(token?: string): Promise<ExportData> {
  return api.get<ExportData>("/auth/me/export", token);
}

export async function deleteMyAccount(password: string, token?: string): Promise<void> {
  await api.delete<void>("/auth/me", token, { password });
}

export function downloadExportAsJson(data: ExportData): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `cadora-export-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
