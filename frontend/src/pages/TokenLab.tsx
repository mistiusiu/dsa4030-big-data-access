import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import clsx from "clsx";
import { BadgeCheck, Copy, FlaskConical, KeyRound, RefreshCw, Send, ShieldOff } from "lucide-react";
import { useAuth } from "@/auth/AuthContext";
import { Countdown, ExpiryBar } from "@/components/Countdown";
import { Callout, Code, Page, PageHeader, SectionTitle, Tag } from "@/components/ui";
import { api, errorMessage, refreshTokens } from "@/lib/api";
import { decodeJwt, forgeJwt } from "@/lib/jwt";
import { tokens, useTokens } from "@/lib/tokens";

interface Jwks { algorithm: string; issuer: string; audience: string; public_key_pem: string; keys: Record<string, string>[] }
interface Replay { label: string; status: number; body: unknown; auditId: string | null; token: string }

const TARGETS = [
  { label: "GET /api/auth/me/", method: "GET", url: "/api/auth/me/" },
  { label: "GET /api/audit/detections/ (admin only)", method: "GET", url: "/api/audit/detections/" },
  { label: "POST /api/lake/datasets/felonies/query/", method: "POST", url: "/api/lake/datasets/felonies/query/" },
  { label: "POST /api/lake/datasets/medical_records/query/", method: "POST", url: "/api/lake/datasets/medical_records/query/" },
];

type SigMode = "keep" | "none" | "random";

function TokenParts({ token }: { token: string }) {
  const [h, p, s] = token.split(".");
  return (
    <p className="break-all rounded bg-ink-2 p-3 font-mono text-[12px] leading-relaxed">
      <span className="text-[#f56e6e]">{h}</span><span className="text-gray-50">.</span>
      <span className="text-[#b6a6e9]">{p}</span><span className="text-gray-50">.</span>
      <span className="text-[#63bdbd]">{s}</span>
    </p>
  );
}

function TokenCard({ title, token, expires, kind }: { title: string; token: string | null; expires: string | null; kind: "access" | "refresh" }) {
  const d = decodeJwt(token);
  const [verify, setVerify] = useState<{ ok: boolean; msg: string } | null>(null);
  useEffect(() => setVerify(null), [token]);
  if (!token || !d) return <div className="card p-5 text-sm text-gray-60">No {kind} token.</div>;
  const iat = d.payload.iat as number;
  return (
    <div className="card flex flex-col gap-4 p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold">{title}</h3>
          <p className="text-xs text-gray-60">jti <span className="font-mono">{String(d.payload.jti)}</span></p>
        </div>
        <Tag tone="dark">{String(d.header.alg)}</Tag>
      </div>
      <div className="space-y-1.5">
        <div className="flex justify-between text-sm">
          <span className="text-gray-60">Expires {expires && new Date(expires).toLocaleTimeString("en-KE")}</span>
          <Countdown until={expires} />
        </div>
        <ExpiryBar issued={iat} until={expires} />
      </div>
      <TokenParts token={token} />
      <div className="flex flex-wrap gap-2">
        <button className="btn-tertiary btn-sm" onClick={() => navigator.clipboard.writeText(token)}><Copy size={14} /> Copy</button>
        <button
          className="btn-tertiary btn-sm"
          onClick={async () => {
            try {
              await axios.post("/api/auth/token/verify/", { token });
              setVerify({ ok: true, msg: "Signature valid and not expired." });
            } catch (e) {
              setVerify({ ok: false, msg: errorMessage(e) });
            }
          }}
        >
          <BadgeCheck size={14} /> Verify with server
        </button>
      </div>
      {verify && <Callout tone={verify.ok ? "success" : "danger"} title={verify.ok ? "Valid" : "Invalid"}>{verify.msg}</Callout>}
    </div>
  );
}

export default function TokenLab() {
  const { me } = useAuth();
  const t = useTokens();
  const access = decodeJwt(t.access);
  const jwks = useQuery({ queryKey: ["jwks"], queryFn: async () => (await axios.get<Jwks>("/api/auth/jwks/")).data });

  const [payloadText, setPayloadText] = useState("");
  const [sigMode, setSigMode] = useState<SigMode>("keep");
  const [target, setTarget] = useState(TARGETS[0]);
  const [replays, setReplays] = useState<Replay[]>([]);
  const [parseError, setParseError] = useState<string | null>(null);
  const [refreshMsg, setRefreshMsg] = useState<string | null>(null);
  const [revokeMsg, setRevokeMsg] = useState<{ ok: boolean; msg: string } | null>(null);

  useEffect(() => {
    if (access) setPayloadText(JSON.stringify(access.payload, null, 2));
    // Reset only when the real token changes, not on every render.
  }, [t.access]);

  const mutate = (fn: (p: Record<string, unknown>) => void) => {
    try {
      const p = JSON.parse(payloadText);
      fn(p);
      setPayloadText(JSON.stringify(p, null, 2));
      setParseError(null);
    } catch (e) {
      setParseError(String(e));
    }
  };

  const fire = async (label: string, token: string) => {
    const res = await fetch(target.url, {
      method: target.method,
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: target.method === "POST" ? JSON.stringify({ limit: 5 }) : undefined,
    });
    let body: unknown;
    try { body = await res.json(); } catch { body = await res.text(); }
    setReplays((r) => [{ label, status: res.status, body, auditId: res.headers.get("X-Audit-Id"), token }, ...r].slice(0, 6));
  };

  const sendForged = () => {
    if (!access) return;
    let payload: object;
    try { payload = JSON.parse(payloadText); setParseError(null); } catch (e) { setParseError(String(e)); return; }
    const header = sigMode === "none" ? { ...access.header, alg: "none" } : access.header;
    const sig = sigMode === "keep" ? access.signature : sigMode === "none" ? "" : btoa(crypto.getRandomValues(new Uint8Array(32)).join("")).replace(/=+$/, "");
    const forged = forgeJwt(header, payload, sig);
    fire(`Forged (${sigMode === "keep" ? "original signature" : sigMode === "none" ? "alg: none" : "random signature"})`, forged);
  };

  return (
    <>
      <PageHeader eyebrow="Authentication" title="Token Lab">
        Your session is a pair of JSON Web Tokens signed with the backend's <b className="text-white">RSA private key (RS256)</b>.
        Anyone can read them — they are only base64 — but nobody can change them without the key. Edit one below and watch it fail.
      </PageHeader>
      <Page className="space-y-10">
        <Callout tone="warning" title="Illustrative storage">
          Tokens sit in <code>localStorage</code> here so you can inspect them. In production they belong in HttpOnly, Secure,
          SameSite cookies, out of reach of page scripts.
        </Callout>

        <section>
          <SectionTitle sub="Short-lived access token for API calls; longer-lived refresh token to mint new ones. Refresh tokens rotate: each use blacklists the old one.">
            Your tokens
          </SectionTitle>
          <div className="grid gap-6 lg:grid-cols-2">
            <TokenCard title="Access token" token={t.access} expires={t.accessExpires} kind="access" />
            <TokenCard title="Refresh token" token={t.refresh} expires={t.refreshExpires} kind="refresh" />
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              className="btn-primary"
              onClick={async () => {
                const ok = await refreshTokens();
                setRefreshMsg(ok ? "New access token issued; the old refresh token is now blacklisted." : "Refresh failed — sign in again.");
              }}
            >
              <RefreshCw size={16} /> Renew tokens now
            </button>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={t.autoRefresh} onChange={(e) => tokens.set({ autoRefresh: e.target.checked })} />
              Auto-renew when the access token expires
            </label>
            {refreshMsg && <span className="text-sm text-ok">{refreshMsg}</span>}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <div>
            <SectionTitle sub="What the server signed. Claims the backend added: username, role, role_name.">Decoded access token</SectionTitle>
            <p className="mb-1 text-xs font-bold uppercase tracking-wide text-[#a60000]">Header</p>
            <Code>{JSON.stringify(access?.header, null, 2)}</Code>
            <p className="mb-1 mt-3 text-xs font-bold uppercase tracking-wide text-purple">Payload</p>
            <Code>{JSON.stringify(access?.payload, null, 2)}</Code>
          </div>
          <div>
            <SectionTitle sub="Verification needs only this public key. The private key never leaves the backend container.">Public key (JWKS)</SectionTitle>
            {jwks.data && (
              <>
                <div className="mb-2 flex flex-wrap gap-2 text-xs">
                  <Tag tone="dark">{jwks.data.algorithm}</Tag><Tag>iss: {jwks.data.issuer}</Tag><Tag>aud: {jwks.data.audience}</Tag>
                </div>
                <Code className="max-h-48">{jwks.data.public_key_pem}</Code>
                <Code className="mt-3 max-h-40">{JSON.stringify(jwks.data.keys[0], null, 2)}</Code>
              </>
            )}
          </div>
        </section>

        <section className="card overflow-hidden">
          <div className="flex items-center gap-3 bg-ink px-6 py-4 text-white">
            <FlaskConical className="text-brand" />
            <div>
              <h2 className="font-display text-xl font-bold text-white">Tamper bench</h2>
              <p className="text-sm text-gray-40">Edit the payload, choose what to do with the signature, and replay it against the API.</p>
            </div>
          </div>
          <div className="grid gap-6 p-6 lg:grid-cols-2">
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <button className="btn-tertiary btn-sm" onClick={() => mutate((p) => { p.role = "administrator"; p.role_name = "Administrator"; })}>Escalate to administrator</button>
                <button className="btn-tertiary btn-sm" onClick={() => mutate((p) => { p.role = "law_enforcement"; })}>Become law enforcement</button>
                <button className="btn-tertiary btn-sm" onClick={() => mutate((p) => { p.exp = Math.floor(Date.now() / 1000) + 365 * 86400; })}>Extend expiry 1 year</button>
                <button className="btn-tertiary btn-sm" onClick={() => mutate((p) => { p.user_id = "1"; })}>Impersonate user 1</button>
              </div>
              <textarea
                value={payloadText}
                onChange={(e) => setPayloadText(e.target.value)}
                spellCheck={false}
                className="h-64 w-full rounded border border-ink bg-ink-2 p-4 font-mono text-[13px] text-gray-10 outline-none"
              />
              {parseError && <p className="text-sm text-bad">{parseError}</p>}
              <fieldset className="space-y-1.5">
                <legend className="label">Signature</legend>
                {([
                  ["keep", "Keep the original signature (it no longer matches)"],
                  ["random", "Replace with random bytes"],
                  ["none", "Strip it and set alg: none (classic JWT attack)"],
                ] as [SigMode, string][]).map(([v, l]) => (
                  <label key={v} className="flex items-center gap-2 text-sm">
                    <input type="radio" name="sig" checked={sigMode === v} onChange={() => setSigMode(v)} /> {l}
                  </label>
                ))}
              </fieldset>
              <div>
                <label className="label">Target endpoint</label>
                <select className="field font-mono text-sm" value={target.url} onChange={(e) => setTarget(TARGETS.find((x) => x.url === e.target.value)!)}>
                  {TARGETS.map((x) => <option key={x.url} value={x.url}>{x.label}</option>)}
                </select>
              </div>
              <div className="flex flex-wrap gap-3">
                <button className="btn-primary" onClick={sendForged}><Send size={16} /> Send forged token</button>
                <button className="btn-secondary" onClick={() => t.access && fire("Genuine token (control)", t.access)}>Send genuine token</button>
              </div>
            </div>

            <div className="space-y-3">
              <p className="label">Responses</p>
              {!replays.length && <p className="text-sm text-gray-60">Nothing sent yet. Forged tokens should come back <b>401</b>; the genuine one as {me?.role.name} gets 200 or 403 depending on the grid.</p>}
              {replays.map((r, i) => (
                <div key={i} className={clsx("rounded border-l-4 bg-gray-10 p-3", r.status === 401 ? "border-brand" : r.status === 403 ? "border-[#dca614]" : "border-[#3d7317]")}>
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="font-mono font-bold">HTTP {r.status}</span>
                    <span>{r.label}</span>
                    {r.auditId && <Tag>audit #{r.auditId}</Tag>}
                  </div>
                  <Code className="mt-2 max-h-40 text-[12px]">{JSON.stringify(r.body, null, 2).slice(0, 1500)}</Code>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section>
          <SectionTitle sub="Logging out blacklists the refresh token server-side. The access token, being stateless, keeps working until it expires — which is why it is short-lived.">
            Revocation
          </SectionTitle>
          <div className="flex flex-wrap items-center gap-3">
            <button
              className="btn-secondary"
              disabled={!t.refresh}
              onClick={async () => {
                const refresh = t.refresh!;
                await api.post("/auth/logout/", { refresh });
                try {
                  await axios.post("/api/auth/token/refresh/", { refresh });
                  setRevokeMsg({ ok: false, msg: "Unexpected: the revoked token still refreshed." });
                } catch (e) {
                  setRevokeMsg({ ok: true, msg: `Re-using the revoked refresh token → ${errorMessage(e)}. Your access token still works until it expires; then you will be signed out.` });
                }
                tokens.set({ refresh: null, refreshExpires: null });
              }}
            >
              <ShieldOff size={16} /> Revoke my refresh token, then try to reuse it
            </button>
            <KeyRound size={16} className="text-gray-40" />
          </div>
          {revokeMsg && <div className="mt-3"><Callout tone={revokeMsg.ok ? "success" : "danger"} title="Result">{revokeMsg.msg}</Callout></div>}
        </section>
      </Page>
    </>
  );
}
