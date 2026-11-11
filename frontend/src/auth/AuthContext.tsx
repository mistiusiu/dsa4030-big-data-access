import { createContext, useCallback, useContext, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { api } from "@/lib/api";
import { tokens, useTokens } from "@/lib/tokens";
import type { Me } from "@/lib/types";

interface AuthValue {
  me: Me | undefined;
  loading: boolean;
  signedIn: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  can: (capability: string) => boolean;
}

const Ctx = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { access, refresh } = useTokens();
  const qc = useQueryClient();
  const meQuery = useQuery({
    queryKey: ["me", access],
    queryFn: async () => (await api.get<Me>("/auth/me/")).data,
    enabled: Boolean(access),
  });

  const login = useCallback(async (username: string, password: string) => {
    const { data } = await axios.post("/api/auth/token/", { username, password });
    qc.clear();
    tokens.set({
      access: data.access,
      refresh: data.refresh,
      accessExpires: data.access_expires,
      refreshExpires: data.refresh_expires,
    });
  }, [qc]);

  const logout = useCallback(async () => {
    if (refresh) await api.post("/auth/logout/", { refresh }).catch(() => undefined);
    tokens.clear();
    qc.clear();
  }, [refresh, qc]);

  const me = meQuery.data;
  const value: AuthValue = {
    me,
    loading: Boolean(access) && meQuery.isLoading,
    signedIn: Boolean(access && me),
    login,
    logout,
    can: (c) => Boolean(me?.role.capabilities.includes(c)),
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth outside AuthProvider");
  return v;
}
