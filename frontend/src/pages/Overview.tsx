import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { ArrowRight, Check, X } from "lucide-react";
import { useAuth } from "@/auth/AuthContext";
import { Countdown } from "@/components/Countdown";
import { Icon } from "@/components/Icon";
import { ModeTag, Page, PageHeader, SectionTitle, Spinner, Stat } from "@/components/ui";
import { api } from "@/lib/api";
import { clock } from "@/lib/format";
import { useTokens } from "@/lib/tokens";
import type { AuditEntry, DatasetCard } from "@/lib/types";
import { OutcomeTag } from "./Audit";

const CAPS: Record<string, string> = {
  "lake.browse": "Read record-level rows",
  "lake.aggregate": "Run k-anonymous aggregates",
  "lake.sql": "Cross-analyse in SQL",
  "audit.view_own": "See own audit trail",
  "audit.view_all": "See all audit logs + SIEM",
  "grid.view_all": "Inspect every role's rules",
};

export default function Overview() {
  const { me } = useAuth();
  const { accessExpires, refreshExpires } = useTokens();
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: async () => (await api.get<DatasetCard[]>("/lake/datasets/")).data });
  const activity = useQuery({
    queryKey: ["audit", "mine"],
    queryFn: async () => (await api.get<{ results: AuditEntry[] }>("/audit/logs/", { params: { username: me?.username, limit: 8 } })).data,
  });
  if (!me) return null;

  const count = (m: string) => datasets.data?.filter((d) => d.mode === m).length ?? 0;

  return (
    <>
      <PageHeader eyebrow={me.role.name} title={<>Habari, {me.first_name}.</>}
        actions={<Link to="/lake" className="btn-primary">Explore your data <ArrowRight size={16} /></Link>}>
        {me.role.description}
      </PageHeader>

      <Page className="space-y-10">
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Record-level datasets" value={count("row")} hint="Rows, through your column rules" accent="bg-[#3d7317]" />
          <Stat label="Aggregate-only datasets" value={count("aggregate")} hint="Group-bys with small groups suppressed" accent="bg-link" />
          <Stat label="Denied datasets" value={count("deny")} hint="Invisible to your role" accent="bg-gray-40" />
          <Stat label="Access token" value={<Countdown until={accessExpires} compact />} hint={<>Refresh token: <Countdown until={refreshExpires} compact /></>} />
        </section>

        <section className="grid gap-8 lg:grid-cols-[1.4fr_1fr]">
          <div>
            <SectionTitle sub="What the permission grid lets your role see, per dataset.">Your lens on the lake</SectionTitle>
            {datasets.isLoading ? <Spinner /> : (
              <div className="card divide-y divide-gray-20">
                {datasets.data?.map((d) => (
                  <Link key={d.slug} to={`/lake/${d.slug}`} className="flex items-center gap-4 px-4 py-3 text-ink no-underline hover:bg-gray-10 hover:no-underline">
                    <span className={clsx("flex h-9 w-9 shrink-0 items-center justify-center rounded", d.mode === "deny" ? "bg-gray-10 text-gray-40" : "bg-ink text-white")}>
                      <Icon name={d.icon} size={17} />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className={clsx("block font-display font-bold", d.mode === "deny" && "text-gray-50")}>{d.title}</span>
                      <span className="block truncate text-xs text-gray-60">{d.rationale}</span>
                    </span>
                    <ModeTag mode={d.mode} />
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-8">
            <div>
              <SectionTitle sub="API capabilities granted to your role.">What you can do</SectionTitle>
              <ul className="card divide-y divide-gray-20">
                {Object.entries(CAPS).map(([c, label]) => {
                  const ok = me.role.capabilities.includes(c);
                  return (
                    <li key={c} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                      {ok ? <Check size={16} className="text-ok" /> : <X size={16} className="text-gray-40" />}
                      <span className={clsx("flex-1", !ok && "text-gray-50 line-through")}>{label}</span>
                      <code className="font-mono text-xs text-gray-50">{c}</code>
                    </li>
                  );
                })}
              </ul>
            </div>

            <div>
              <SectionTitle sub="Your last requests, as the audit log recorded them.">Recent activity</SectionTitle>
              <div className="card divide-y divide-gray-20">
                {activity.data?.results.map((e) => (
                  <div key={e.id} className="flex items-center gap-3 px-4 py-2 text-sm">
                    <span className="font-mono text-xs text-gray-50">{clock(e.timestamp)}</span>
                    <span className="min-w-0 flex-1 truncate font-mono text-xs">{e.method} {e.path}</span>
                    <OutcomeTag outcome={e.outcome} />
                  </div>
                ))}
                {activity.data && !activity.data.results.length && <p className="p-4 text-sm text-gray-60">Nothing yet.</p>}
              </div>
              <Link to="/audit" className="mt-2 inline-flex items-center gap-1 text-sm">Open audit trail <ArrowRight size={14} /></Link>
            </div>
          </div>
        </section>
      </Page>
    </>
  );
}
