import { api } from "./api";

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

export const billingService = {
  getPlans: (token?: string) => api.get<Plan[]>("/billing/plans", token),

  getSubscription: (token?: string) =>
    api.get<Subscription>("/billing/subscription", token),

  createCheckoutSession: (plan: string, priceId: string, token?: string) =>
    api.post<{ url: string }>(
      "/billing/create-checkout-session",
      { plan, price_id: priceId },
      token,
    ),

  createPortalSession: (token?: string) =>
    api.post<{ url: string }>("/billing/create-portal-session", {}, token),
};
