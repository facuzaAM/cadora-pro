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
  user: AuthUser;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

const REFRESH_INTERVAL_MS = 14 * 60 * 1000;

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const accessTokenRef = useRef<string | null>(null);
  const refreshTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearRefreshTimer = useCallback(() => {
    if (refreshTimerRef.current) {
      clearInterval(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }
  }, []);

  const tryRefreshToken = useCallback(async (): Promise<boolean> => {
    try {
      const data = await api.post<TokenData>("/auth/refresh", {});
      accessTokenRef.current = data.access_token;
      api.setAccessToken(data.access_token);
      setUser(data.user);
      return true;
    } catch {
      accessTokenRef.current = null;
      api.setAccessToken(null);
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
    try {
      const data = await api.get<AuthUser>("/auth/me", accessTokenRef.current ?? undefined);
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
    fetchUser();
    return () => clearRefreshTimer();
  }, [fetchUser, clearRefreshTimer]);

  const signIn = async (email: string, password: string) => {
    const data = await api.post<TokenData>("/auth/login", { email, password });
    accessTokenRef.current = data.access_token;
    api.setAccessToken(data.access_token);
    setUser(data.user);
    scheduleRefresh();
    router.push("/dashboard");
  };

  const signUp = async (email: string, password: string, name: string) => {
    const data = await api.post<TokenData>("/auth/register", { email, password, name });
    accessTokenRef.current = data.access_token;
    api.setAccessToken(data.access_token);
    setUser(data.user);
    scheduleRefresh();
    router.push("/dashboard");
  };

  const signInWithGoogle = async () => {
    window.location.href = `${api.getBaseUrl()}/auth/google`;
  };

  const signOut = async () => {
    try {
      await api.post("/auth/logout", {});
    } catch {
      // best-effort server-side logout
    }
    accessTokenRef.current = null;
    api.setAccessToken(null);
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
