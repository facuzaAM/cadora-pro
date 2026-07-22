"use client";

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/services/api";

interface AuthUser {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  subscription_plan: string;
  subscription_status: string;
  conversions_used: number;
  conversions_limit: number;
  storage_used: number;
  storage_limit: number;
  priority_processing: boolean;
  created_at: string;
}

interface AuthState {
  user: AuthUser | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, name: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

function setCookie(name: string, value: string, days: number) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

function removeCookie(name: string) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const data = await api.get<AuthUser>("/auth/me", token);
      setUser(data);
    } catch {
      localStorage.removeItem("access_token");
      removeCookie("cadora_token");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const signIn = async (email: string, password: string) => {
    const data = await api.post<{ access_token: string; user: AuthUser }>(
      "/auth/login",
      { email, password },
    );
    localStorage.setItem("access_token", data.access_token);
    setCookie("cadora_token", data.access_token, 7);
    setUser(data.user);
    router.push("/dashboard");
  };

  const signUp = async (email: string, password: string, name: string) => {
    const data = await api.post<{ access_token: string; user: AuthUser }>(
      "/auth/register",
      { email, password, name },
    );
    localStorage.setItem("access_token", data.access_token);
    setCookie("cadora_token", data.access_token, 7);
    setUser(data.user);
    router.push("/dashboard");
  };

  const signInWithGoogle = async () => {
    window.location.href = `${api.getBaseUrl()}/auth/google`;
  };

  const signOut = async () => {
    localStorage.removeItem("access_token");
    removeCookie("cadora_token");
    setUser(null);
    router.push("/");
  };

  const refreshUser = useCallback(async () => {
    await fetchUser();
  }, [fetchUser]);

  return (
    <AuthContext.Provider value={{
      user, loading,
      signIn, signUp, signInWithGoogle, signOut, refreshUser,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
