import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { tokens } from "./tokens";

export const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((config) => {
  const { access } = tokens.get();
  if (access && !config.headers.Authorization) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

let refreshing: Promise<string | null> | null = null;

export async function refreshTokens(): Promise<string | null> {
  const { refresh } = tokens.get();
  if (!refresh) return null;
  refreshing ??= axios
    .post("/api/auth/token/refresh/", { refresh })
    .then(({ data }) => {
      tokens.set({
        access: data.access,
        accessExpires: data.access_expires,
        ...(data.refresh ? { refresh: data.refresh, refreshExpires: data.refresh_expires } : {}),
      });
      return data.access as string;
    })
    .catch(() => {
      tokens.clear();
      return null;
    })
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

// Transparent renewal of an *expired* access token. Any other 401 (tampered,
// revoked, role changed) is surfaced as-is so the lab can show it.
api.interceptors.response.use(undefined, async (error: AxiosError<{ detail?: string; code?: string }>) => {
  const cfg = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
  const expired = JSON.stringify(error.response?.data ?? "").toLowerCase().includes("expired");
  if (error.response?.status === 401 && expired && cfg && !cfg._retried && tokens.get().autoRefresh) {
    cfg._retried = true;
    const fresh = await refreshTokens();
    if (fresh) {
      cfg.headers.Authorization = `Bearer ${fresh}`;
      return api(cfg);
    }
  }
  return Promise.reject(error);
});

export function errorMessage(e: unknown): string {
  const err = e as AxiosError<Record<string, unknown>>;
  const data = err?.response?.data;
  if (data && typeof data === "object") {
    if (typeof data.detail === "string") return data.detail;
    if (data.detail && typeof data.detail === "object") return JSON.stringify(data.detail);
    return JSON.stringify(data);
  }
  return err?.message ?? "Request failed";
}

export function errorStatus(e: unknown): number | undefined {
  return (e as AxiosError)?.response?.status;
}
