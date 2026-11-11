import { NavLink, Outlet, useNavigate } from "react-router-dom";
import clsx from "clsx";
import { LogOut, ShieldCheck } from "lucide-react";
import { useAuth } from "@/auth/AuthContext";
import { useTokens } from "@/lib/tokens";
import { Icon } from "./Icon";
import { Countdown } from "./Countdown";

const NAV = [
  { to: "/", label: "Overview", end: true },
  { to: "/lake", label: "Data Lake" },
  { to: "/workbench", label: "SQL Workbench" },
  { to: "/grid", label: "Permission Grid" },
  { to: "/tokens", label: "Token Lab" },
  { to: "/audit", label: "Audit & SIEM" },
];

export function Logo({ dark = true }: { dark?: boolean }) {
  return (
    <span className="flex items-center gap-3">
      <svg width="34" height="34" viewBox="0 0 32 32" aria-hidden>
        <rect width="32" height="32" rx="4" fill={dark ? "#ffffff" : "#151515"} fillOpacity={dark ? 0.08 : 1} />
        <path d="M7 23V11l5 6 4-6 4 6 5-6v12" fill="none" stroke="#ee0000" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
      </svg>
      <span className="leading-tight">
        <span className={clsx("block font-display text-[17px] font-bold", dark ? "text-white" : "text-ink")}>Mji Mpya</span>
        <span className={clsx("block text-[11px] uppercase tracking-[0.14em]", dark ? "text-gray-40" : "text-gray-60")}>Data Access Lab</span>
      </span>
    </span>
  );
}

export function Layout() {
  const { me, logout } = useAuth();
  const { accessExpires } = useTokens();
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen flex-col">
      <div className="bg-black text-[12px] text-gray-40">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-6 py-1.5 lg:px-10">
          <span className="flex items-center gap-1.5"><ShieldCheck size={13} className="text-brand" /> Synthetic data only · every request is audited</span>
          <a href="/admin/" className="text-gray-40 hover:text-white">Super-admin console ↗</a>
        </div>
      </div>
      <nav className="sticky top-0 z-30 border-b border-ink-4 bg-ink">
        <div className="mx-auto flex h-[72px] max-w-[1400px] items-center gap-8 px-6 lg:px-10">
          <NavLink to="/" className="no-underline hover:no-underline"><Logo /></NavLink>
          <div className="hidden h-full items-stretch gap-1 lg:flex">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) => clsx(
                  "relative flex items-center px-3 font-display text-[15px] font-medium no-underline transition-colors hover:no-underline",
                  isActive ? "text-white after:absolute after:inset-x-3 after:bottom-0 after:h-[3px] after:bg-brand" : "text-gray-30 hover:text-white",
                )}
              >
                {n.label}
              </NavLink>
            ))}
          </div>
          <div className="ml-auto flex items-center gap-4">
            {me && (
              <div className="hidden items-center gap-3 md:flex">
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand text-white">
                  <Icon name={me.role.icon} size={18} />
                </span>
                <span className="leading-tight">
                  <span className="block text-sm font-medium text-white">{me.first_name} {me.last_name}</span>
                  <span className="block text-xs text-gray-40">
                    {me.role.name} · token <Countdown until={accessExpires} compact />
                  </span>
                </span>
              </div>
            )}
            <button
              className="btn-dark btn-sm"
              onClick={async () => { await logout(); navigate("/login"); }}
            >
              <LogOut size={15} /> Sign out
            </button>
          </div>
        </div>
        <div className="scroll-thin flex gap-1 overflow-x-auto border-t border-ink-4 px-4 lg:hidden">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => clsx("whitespace-nowrap px-3 py-2 text-sm no-underline", isActive ? "text-white" : "text-gray-40")}>
              {n.label}
            </NavLink>
          ))}
        </div>
      </nav>
      <main className="flex-1"><Outlet /></main>
      <footer className="border-t border-gray-30 bg-white">
        <div className="mx-auto flex max-w-[1400px] flex-wrap justify-between gap-2 px-6 py-5 text-xs text-gray-60 lg:px-10">
          <span>DSA 4030 · Big Data Access Control Lab — Django · DuckDB · Parquet · React</span>
          <span>All people, places and records are synthetic.</span>
        </div>
      </footer>
    </div>
  );
}
