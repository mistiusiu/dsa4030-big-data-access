/**
 * Token store. Kept in localStorage so the lab can display and tamper with the
 * tokens. In production these belong in HttpOnly, Secure, SameSite cookies
 * where page scripts (and XSS payloads) cannot read them.
 */
import { useSyncExternalStore } from "react";

export interface TokenState {
  access: string | null;
  refresh: string | null;
  accessExpires: string | null;
  refreshExpires: string | null;
  autoRefresh: boolean;
}

const KEY = "mjimpya.tokens";
const empty: TokenState = { access: null, refresh: null, accessExpires: null, refreshExpires: null, autoRefresh: true };

let state: TokenState = (() => {
  try {
    return { ...empty, ...JSON.parse(localStorage.getItem(KEY) || "{}") };
  } catch {
    return empty;
  }
})();
const listeners = new Set<() => void>();

export const tokens = {
  get: () => state,
  set(patch: Partial<TokenState>) {
    state = { ...state, ...patch };
    localStorage.setItem(KEY, JSON.stringify(state));
    listeners.forEach((l) => l());
  },
  clear() {
    tokens.set({ access: null, refresh: null, accessExpires: null, refreshExpires: null });
  },
  subscribe(l: () => void) {
    listeners.add(l);
    return () => listeners.delete(l);
  },
};

export function useTokens(): TokenState {
  return useSyncExternalStore(tokens.subscribe, tokens.get);
}
