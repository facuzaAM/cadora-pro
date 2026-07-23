"use client";

import { createContext, useContext, useEffect, useRef, useState, useCallback, type ReactNode } from "react";
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

interface TokenData {
  access_token: string;
  refresh_token: string;
  user: AuthUser;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const REFRESH_COOKIE = "cadora_token";
const REFRESH_INTERVAL_MS = 14 * 60 * 1000;

function setCookie(name: string, value: string, days: number) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

function removeCookie(name: string) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
}

function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

function storeTokens(accessToken: string, refreshToken: string) {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  setCookie(REFRESH_COOKIE, refreshToken, 7);
}

function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  removeCookie(REFRESH_COOKIE);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const refreshTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearRefreshTimer = useCallback(() => {
    if (refreshTimerRef.current) {
      clearInterval(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }
  }, []);

  const tryRefreshToken = useCallback(async (): Promise<boolean> => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;
    try {
      const data = await api.post<TokenData>("/auth/refresh", { refresh_token: refreshToken });
      storeTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      return true;
    } catch {
      clearTokens();
      setUser(null);
      clearRefreshTimer();
      return false;
    }
  }, [clearRefreshTimer]);

  const scheduleRefresh = useCallback(() => {
    clearRefreshTimer();
    refreshTimerRef.current = setInterval(async () => {
      const success = await tryRefreshToken();
      if (!success) clearRefreshTimer();
    }, REFRESH_INTERVAL_MS);
  }, [clearRefreshTimer, tryRefreshToken]);

  const fetchUser = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      const refreshed = await tryRefreshToken();
      if (!refreshed) {
        setUser(null);
        setLoading(false);
        return;
      }
      setLoading(false);
      scheduleRefresh();
      return;
    }
    try {
      const data = await api.get<AuthUser>("/auth/me", token);
      setUser(data);
      scheduleRefresh();
    } catch {
      const refreshed = await tryRefreshToken();
      if (!refreshed) {
        setUser(null);
      } else {
        scheduleRefresh();
      }
    } finally {
      setLoading(false);
    }
  }, [tryRefreshToken, scheduleRefresh]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const at = params.get("access_token");
      const rt = params.get("refresh_token");
      if (at && rt) {
        storeTokens(at, rt);
        window.history.replaceState({}, "", window.location.pathname);
      }
    }
    fetchUser();
    return () => clearRefreshTimer();
  }, [fetchUser, clearRefreshTimer]);

  const signIn = async (email: string, password: string) => {
    const data = await api.post<TokenData>("/auth/login", { email, password });
    storeTokens(data.access_token, data.refresh_token);
    setUser(data.user);
    scheduleRefresh();
    router.push("/dashboard");
  };

  const signUp = async (email: string, password: string, name: string) => {
    const data = await api.post<TokenData>("/auth/register", { email, password, name });
    storeTokens(data.access_token, data.refresh_token);
    setUser(data.user);
    scheduleRefresh();
    router.push("/dashboard");
  };

  const signInWithGoogle = async () => {
    window.location.href = `${api.getBaseUrl()}/auth/google`;
  };

  const signOut = async () => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await api.post("/auth/logout", { refresh_token: refreshToken });
      } catch {
        // best-effort server-side logout
      }
    }
    clearTokens();
    clearRefreshTimer();
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
