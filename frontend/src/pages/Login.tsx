import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import clsx from "clsx";
import { ArrowRight, KeyRound, Lock } from "lucide-react";
import { useAuth } from "@/auth/AuthContext";
import { Icon } from "@/components/Icon";
import { Logo } from "@/components/Layout";
import { Callout } from "@/components/ui";
import { errorMessage, errorStatus } from "@/lib/api";
import { useTokens } from "@/lib/tokens";
import type { Role } from "@/lib/types";

interface DemoAccounts {
  accounts: { username: string; role: Role }[];
  password: string | null;
}

export default function Login() {
  const { login } = useAuth();
  const { access } = useTokens();
  const navigate = useNavigate();
  const location = useLocation();
  const demo = useQuery({
    queryKey: ["demo-accounts"],
    queryFn: async () => (await axios.get<DemoAccounts>("/api/auth/demo-accounts/")).data,
  });
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<{ status?: number; msg: string } | null>(null);
  const [busy, setBusy] = useState(false);

  if (access) return <Navigate to="/" replace />;

  const pick = (u: string) => {
    setUsername(u);
    setPassword(demo.data?.password ?? "");
    setError(null);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username, password);
      navigate((location.state as { from?: string })?.from ?? "/", { replace: true });
    } catch (err) {
      setError({ status: errorStatus(err), msg: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  };

  const selected = demo.data?.accounts.find((a) => a.username === username);

  return (
    <div className="min-h-screen bg-ink">
      <div className="mx-auto grid min-h-screen max-w-[1400px] lg:grid-cols-[1fr_1.15fr]">
        {/* Left: story */}
        <section className="relative flex flex-col justify-between overflow-hidden px-8 py-10 text-white lg:px-14">
          <div className="pointer-events-none absolute -bottom-40 -left-40 h-[520px] w-[520px] rounded-full border-[70px] border-white/[0.035]" />
          <Logo />
          <div className="relative my-14 max-w-xl">
            <p className="eyebrow mb-4 text-[#f56e6e]">DSA 4030 · Big data access control</p>
            <h1 className="font-display text-4xl font-bold leading-[1.1] text-white md:text-[3.25rem]">
              One city. Fourteen data silos. <span className="text-brand">Nine ways</span> to see them.
            </h1>
            <p className="mt-6 text-lg leading-relaxed text-gray-30">
              Pick a role and sign in. The permission grid decides, column by column, whether you see the
              real value, a mask, a pseudonym, an aggregate — or nothing at all. Every request is signed,
              checked and logged.
            </p>
            <dl className="mt-10 grid grid-cols-3 gap-6 border-t border-white/10 pt-6">
              {[["14", "Parquet datasets"], ["9", "Roles on the grid"], ["RS256", "Signed JWTs"]].map(([v, l]) => (
                <div key={l}>
                  <dt className="font-display text-3xl font-bold text-white">{v}</dt>
                  <dd className="text-sm text-gray-40">{l}</dd>
                </div>
              ))}
            </dl>
          </div>
          <p className="relative text-xs text-gray-50">
            Synthetic data for the fictional city of Mji Mpya. Super-admins manage the grid in the{" "}
            <a href="/admin/" className="text-gray-30 underline">Django console</a>.
          </p>
        </section>

        {/* Right: role picker + form */}
        <section className="bg-gray-10 px-6 py-10 lg:rounded-tl-[48px] lg:px-12">
          <h2 className="text-2xl font-bold">Choose a role</h2>
          <p className="mt-1 text-sm text-gray-60">Each card signs in as that role's seeded demo account.</p>

          <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {demo.data?.accounts.map(({ username: u, role }) => (
              <button
                key={u}
                type="button"
                onClick={() => pick(u)}
                className={clsx(
                  "group relative flex flex-col items-start rounded-md border bg-white p-4 text-left transition-all",
                  username === u ? "border-brand shadow-raised ring-1 ring-brand" : "border-gray-30 hover:border-ink hover:shadow-raised",
                )}
              >
                <span className={clsx("mb-3 flex h-10 w-10 items-center justify-center rounded transition-colors",
                  username === u ? "bg-brand text-white" : "bg-gray-10 text-ink group-hover:bg-ink group-hover:text-white")}>
                  <Icon name={role.icon} size={20} />
                </span>
                <span className="font-display text-[15px] font-bold leading-snug">{role.name}</span>
                <span className="mt-0.5 font-mono text-xs text-gray-60">{u}</span>
              </button>
            ))}
            {demo.isError && <Callout tone="warning" title="Backend unreachable">Is the backend container running?</Callout>}
          </div>

          {selected && (
            <p className="mt-4 rounded border-l-4 border-ink bg-white p-4 text-sm text-ink-4">{selected.role.description}</p>
          )}

          <form onSubmit={submit} className="card mt-6 space-y-4 p-6">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="u">Username</label>
                <input id="u" className="field font-mono" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
              </div>
              <div>
                <label className="label" htmlFor="p">Password</label>
                <input id="p" type="password" className="field font-mono" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
              </div>
            </div>
            {error && (
              <Callout tone="danger" title={error.status === 429 ? "Too many attempts — throttled" : `Sign-in failed (${error.status ?? "network"})`}>
                {error.msg} This attempt was written to the audit log.
              </Callout>
            )}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="flex items-center gap-1.5 text-xs text-gray-60">
                <KeyRound size={14} /> Try a wrong password a few times, then check Audit &amp; SIEM as <span className="font-mono">admin</span>.
              </p>
              <button className="btn-primary" disabled={busy || !username || !password}>
                <Lock size={16} /> {busy ? "Signing in…" : "Sign in"} <ArrowRight size={16} />
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}
