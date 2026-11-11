import { Fragment, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Ban, CheckCircle2, CircleAlert, Download, KeyRound, Radar, ShieldAlert, TriangleAlert } from "lucide-react";
import { useAuth } from "@/auth/AuthContext";
import { Callout, Code, Empty, Page, PageHeader, SectionTitle, Spinner, Stat, Tag } from "@/components/ui";
import { api } from "@/lib/api";
import { clock, fmt, relTime } from "@/lib/format";
import { tokens } from "@/lib/tokens";
import type { AuditEntry, Finding } from "@/lib/types";

const OUTCOME_TONE: Record<string, Parameters<typeof Tag>[0]["tone"]> = {
  allowed: "green", login_success: "green", denied: "orange", unauthenticated: "red",
  login_failed: "red", throttled: "yellow", rejected: "yellow", error: "red",
};

export function OutcomeTag({ outcome }: { outcome: string }) {
  return <Tag tone={OUTCOME_TONE[outcome] ?? "gray"}>{outcome.replace("_", " ")}</Tag>;
}

// Outcomes are states, so they wear the reserved status palette, grouped into
// four buckets and always paired with a label (legend) and an icon.
const BUCKETS = [
  { key: "ok", label: "Allowed", color: "#0ca30c", accent: "bg-[#0ca30c]", match: ["allowed", "login_success"], icon: CheckCircle2 },
  { key: "warn", label: "Rejected / throttled", color: "#fab219", accent: "bg-[#fab219]", match: ["rejected", "throttled"], icon: CircleAlert },
  { key: "serious", label: "Denied by grid", color: "#ec835a", accent: "bg-[#ec835a]", match: ["denied"], icon: Ban },
  { key: "critical", label: "Auth failure", color: "#d03b3b", accent: "bg-[#d03b3b]", match: ["unauthenticated", "login_failed", "error"], icon: KeyRound },
] as const;

interface Stats {
  minutes: number; total: number; by_outcome: Record<string, number>;
  by_role: { role: string; n: number }[]; timeline: { t: string; outcome: string; n: number }[];
}

export default function Audit() {
  const { can } = useAuth();
  const all = can("audit.view_all");
  const [minutes, setMinutes] = useState(60);
  const [filters, setFilters] = useState({ outcome: "", username: "", dataset: "" });
  const [open, setOpen] = useState<number | null>(null);
  const [live, setLive] = useState(true);
  const refetchInterval = live ? 5000 : false;

  const stats = useQuery({
    queryKey: ["audit-stats", minutes],
    refetchInterval,
    queryFn: async () => (await api.get<Stats>("/audit/stats/", { params: { minutes } })).data,
  });
  const logs = useQuery({
    queryKey: ["audit-logs", filters],
    refetchInterval,
    queryFn: async () => (await api.get<{ total: number; results: AuditEntry[]; scope: string }>("/audit/logs/", {
      params: { ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)), limit: 100 },
    })).data,
  });
  const det = useQuery({
    queryKey: ["detections", minutes],
    enabled: all,
    refetchInterval,
    queryFn: async () => (await api.get<{ findings: Finding[]; rules: { id: string; title: string; mitre: string; medium: number; high: number }[] }>("/audit/detections/", { params: { minutes } })).data,
  });

  const timeline = useMemo(() => {
    const rows = new Map<string, Record<string, number | string>>();
    for (const p of stats.data?.timeline ?? []) {
      const key = clock(p.t).slice(0, 5);
      const row = rows.get(key) ?? { t: key, ok: 0, warn: 0, serious: 0, critical: 0 };
      const b = BUCKETS.find((x) => (x.match as readonly string[]).includes(p.outcome));
      if (b) row[b.key] = (row[b.key] as number) + p.n;
      rows.set(key, row);
    }
    return [...rows.values()];
  }, [stats.data]);

  const bucketTotal = (k: string) => BUCKETS.find((b) => b.key === k)!.match.reduce((s, o) => s + (stats.data?.by_outcome[o] ?? 0), 0);

  const exportNdjson = async () => {
    const res = await fetch("/api/audit/export/", { headers: { Authorization: `Bearer ${tokens.get().access}` } });
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "mji-mpya-audit.ndjson";
    a.click();
  };

  return (
    <>
      <PageHeader
        eyebrow="Accountability"
        title="Audit trail & SIEM"
        actions={all && <button className="btn-dark" onClick={exportNdjson}><Download size={16} /> Export NDJSON for SIEM</button>}
      >
        Every API request — allowed or not — is recorded with who, what, which dataset, which columns and transforms,
        and the result. {all ? "As an administrator you see everyone's trail and the correlation rules below." : "You can see your own trail; administrators see everyone's."}
      </PageHeader>
      <Page className="space-y-10">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex overflow-hidden rounded border border-gray-30 bg-white text-sm">
            {[15, 60, 240, 1440].map((m) => (
              <button key={m} onClick={() => setMinutes(m)} className={clsx("px-3 py-1.5", minutes === m ? "bg-ink text-white" : "hover:bg-gray-10")}>
                {m < 60 ? `${m} min` : m === 1440 ? "24 h" : `${m / 60} h`}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} /> Live (every 5 s)
          </label>
          <Tag tone={all ? "dark" : "gray"}>scope: {logs.data?.scope ?? "…"}</Tag>
        </div>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {BUCKETS.map((b) => (
            <Stat key={b.key} label={b.label} value={fmt.format(bucketTotal(b.key))} accent={b.accent} hint={b.match.join(" · ").replace(/_/g, " ")} />
          ))}
        </section>

        <figure className="card p-5">
          <figcaption className="mb-3 font-display font-bold">Requests per minute by outcome <span className="font-normal text-gray-60">· last {minutes < 60 ? `${minutes} min` : `${minutes / 60} h`}</span></figcaption>
          {timeline.length ? (
            <div className="h-64">
              <ResponsiveContainer>
                <BarChart data={timeline} margin={{ left: -10, right: 8 }}>
                  <CartesianGrid vertical={false} stroke="#e0e0e0" />
                  <XAxis dataKey="t" tick={{ fontSize: 12, fill: "#4d4d4d" }} tickLine={false} axisLine={{ stroke: "#c7c7c7" }} minTickGap={24} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#4d4d4d" }} tickLine={false} axisLine={false} />
                  <Tooltip cursor={{ fill: "#f2f2f2" }} contentStyle={{ borderRadius: 3, border: "1px solid #c7c7c7", fontSize: 13 }} />
                  <Legend iconType="square" wrapperStyle={{ fontSize: 13, color: "#151515" }} />
                  {BUCKETS.map((b) => (
                    <Bar key={b.key} dataKey={b.key} name={b.label} stackId="a" fill={b.color} stroke="#ffffff" strokeWidth={1} maxBarSize={24} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : <p className="py-10 text-center text-sm text-gray-60">No events in this window.</p>}
        </figure>

        {all && (
          <section>
            <SectionTitle sub="Correlation rules evaluated over the audit log. Ship the NDJSON export to Wazuh, Elastic or Splunk to run them for real.">
              <span className="flex items-center gap-2"><Radar size={20} className="text-brand" /> SIEM detections</span>
            </SectionTitle>
            {det.isLoading && <Spinner />}
            {det.data && !det.data.findings.length && (
              <Callout tone="success" title="No detections in this window">
                Try a few wrong passwords on the login page, forge a token in the Token Lab, or hammer a denied dataset.
              </Callout>
            )}
            <div className="grid gap-4 lg:grid-cols-2">
              {det.data?.findings.map((f, i) => (
                <div key={i} className={clsx("card border-l-4 p-5", f.severity === "high" ? "border-l-[#d03b3b]" : "border-l-[#ec835a]")}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      {f.severity === "high" ? <ShieldAlert className="mt-0.5 shrink-0 text-[#d03b3b]" /> : <TriangleAlert className="mt-0.5 shrink-0 text-[#c46100]" />}
                      <div>
                        <p className="font-display font-bold">{f.title}</p>
                        <p className="text-sm text-ink-4">{f.explain}</p>
                      </div>
                    </div>
                    <Tag tone={f.severity === "high" ? "red" : "orange"}>{f.severity}</Tag>
                  </div>
                  <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-4">
                    <div><dt className="text-xs text-gray-60">{f.subject_type === "ip" ? "Source IP" : "Account"}</dt><dd className="font-mono">{f.subject}</dd></div>
                    <div><dt className="text-xs text-gray-60">Score</dt><dd className="font-mono">{fmt.format(f.value)}</dd></div>
                    <div><dt className="text-xs text-gray-60">Last seen</dt><dd>{relTime(f.last_seen)}</dd></div>
                    <div><dt className="text-xs text-gray-60">MITRE ATT&amp;CK</dt><dd className="text-xs">{f.mitre}</dd></div>
                  </dl>
                </div>
              ))}
            </div>
          </section>
        )}

        <section>
          <SectionTitle sub={`${fmt.format(logs.data?.total ?? 0)} events match. Click a row for its full record.`}>Events</SectionTitle>
          <div className="mb-3 flex flex-wrap gap-3">
            <select className="field w-auto text-sm" value={filters.outcome} onChange={(e) => setFilters({ ...filters, outcome: e.target.value })}>
              <option value="">All outcomes</option>
              {Object.keys(OUTCOME_TONE).map((o) => <option key={o}>{o}</option>)}
            </select>
            {all && <input className="field w-48 text-sm" placeholder="username" value={filters.username} onChange={(e) => setFilters({ ...filters, username: e.target.value })} />}
            <input className="field w-48 text-sm" placeholder="dataset" value={filters.dataset} onChange={(e) => setFilters({ ...filters, dataset: e.target.value })} />
          </div>
          {logs.isLoading ? <Spinner /> : logs.data?.results.length ? (
            <div className="scroll-thin max-h-[70vh] overflow-auto rounded border border-gray-30 bg-white">
              <table className="tbl">
                <thead><tr><th>Time</th><th>User</th><th>Role</th><th>Request</th><th>Status</th><th>Outcome</th><th>Dataset</th><th>Source</th><th className="text-right">ms</th></tr></thead>
                <tbody>
                  {logs.data.results.map((e) => (
                    <Fragment key={e.id}>
                      <tr className="cursor-pointer" onClick={() => setOpen(open === e.id ? null : e.id)}>
                        <td className="whitespace-nowrap font-mono text-xs">{clock(e.timestamp)}</td>
                        <td className="font-mono text-xs">{e.username || "—"}</td>
                        <td className="text-xs">{e.role || "—"}</td>
                        <td className="max-w-[320px] truncate font-mono text-xs">{e.method} {e.path}</td>
                        <td className="font-mono text-xs">{e.status_code}</td>
                        <td><OutcomeTag outcome={e.outcome} /></td>
                        <td className="font-mono text-xs">{e.dataset || "—"}</td>
                        <td className="font-mono text-xs">{e.ip}</td>
                        <td className="text-right font-mono text-xs">{e.duration_ms.toFixed(0)}</td>
                      </tr>
                      {open === e.id && (
                        <tr><td colSpan={9} className="bg-gray-10"><Code className="max-h-80">{JSON.stringify(e, null, 2)}</Code></td></tr>
                      )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <Empty title="No events match" />}
        </section>
      </Page>
    </>
  );
}
