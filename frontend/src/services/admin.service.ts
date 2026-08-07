import { api } from "./api";

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  is_admin: boolean;
  email_verified: boolean;
  subscription_plan: string;
  subscription_status: string;
  conversions_used: number;
  conversions_limit: number;
  storage_used: number;
  storage_limit: number;
  project_count: number;
  created_at: string;
}

export interface AdminStats {
  total_users: number;
  total_projects: number;
}

export const adminService = {
  listUsers: (params: { q?: string; skip?: number; limit?: number } = {}, token?: string) =>
    api.get<AdminUser[]>("/admin/users", token, params),

  getStats: (token?: string) => api.get<AdminStats>("/admin/stats", token),

  deleteUser: (id: string, token?: string) => api.delete(`/admin/users/${id}`, token),
};
