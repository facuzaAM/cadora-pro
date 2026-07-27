import { api } from "./api";
import { getCached, setCache } from "@/lib/cache";

export interface Plan {
  name: string;
  price: number;
  conversions_limit: number;
  storage_limit: number;
  priority_processing: boolean;
}

export interface Subscription {
  plan: string;
  status: string;
  conversions_used: number;
  conversions_limit: number;
  storage_used: number;
  storage_limit: number;
  priority_processing: boolean;
}

export interface PaddleConfig {
  client_token: string;
  environment: string;
}

export const billingService = {
  getPlans: (token?: string) => api.get<Plan[]>("/billing/plans", token),

  getSubscription: async (token?: string) => {
    const cached = getCached<Subscription>("billing:subscription");
    if (cached) return cached;
    const result = await api.get<Subscription>("/billing/subscription", token);
    setCache("billing:subscription", result, 30000);
    return result;
  },

  getConfig: () => api.get<PaddleConfig>("/billing/config"),
};
