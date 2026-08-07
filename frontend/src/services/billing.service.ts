import { api } from "./api";
import { getCached, setCache } from "@/lib/cache";

export interface Plan {
  id: string;
  name: string;
  price: number;
  conversions_limit: number;
  storage_limit: number;
  priority_processing: boolean;
  paddle_price_id: string;
}

export interface Subscription {
  plan: string;
  status: string;
  conversions_used: number;
  conversions_limit: number;
  storage_used: number;
  storage_limit: number;
  priority_processing: boolean;
  paddle_customer_id?: string | null;
}

export interface PortalSession {
  url: string | null;
  available: boolean;
}

export interface PaddleConfig {
  client_token: string;
  environment: string;
}

export const billingService = {
  getPlans: (token?: string) => api.get<Plan[]>("/billing/plans", token),

  getSubscription: async (token?: string) => {
    const key = `billing:subscription:${token ?? "anon"}`;
    const cached = getCached<Subscription>(key);
    if (cached) return cached;
    const result = await api.get<Subscription>("/billing/subscription", token);
    setCache(key, result, 30000);
    return result;
  },

  getPortalUrl: (token?: string) => api.get<PortalSession>("/billing/portal", token),

  getConfig: () => api.get<PaddleConfig>("/billing/config"),
};
