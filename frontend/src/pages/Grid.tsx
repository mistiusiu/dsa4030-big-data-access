import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { Ban, Check, CheckCircle2, Sigma, X } from "lucide-react";
import { useAuth } from "@/auth/AuthContext";
import { Icon } from "@/components/Icon";
import { Callout, MODE_META, ModeTag, Page, PageHeader, RULE_META, RuleTag, SectionTitle, Spinner, Tag } from "@/components/ui";
import { api, errorMessage, errorStatus } from "@/lib/api";
import type { ColumnView, Mode, Role, Rule } from "@/lib/types";

interface GridData {
  roles: Role[];
  datasets: { slug: string; title: string; domain: string; icon: string }[];
  cells: Record<string, Record<string, { mode: Mode; cross_analyze: boolean; k: number; rules: Rule[] }>>;
  transforms: Record<Rule, string>;
  capabilities: Record<string, string>;
}

interface RolePolicy {
  dataset: string; title: string; mode: Mode; rationale: string; min_group_size: number;
  cross_analyze: boolean; columns: ColumnView[];
}

const CELL = {
  row: "bg-ok-bg text-ok hover:ring-[#3d7317]",
  aggregate: "bg-link-light text-link-dark hover:ring-link",
  deny: "bg-gray-10 text-gray-40 hover:ring-gray-50",
};
const CELL_ICON = { row: CheckCircle2, aggregate: Sigma, deny: Ban };

export default function Grid() {
  const { me } = useAuth();
  const grid = useQuery({ queryKey: ["grid"], queryFn: async () => (await api.get<GridData>("/grid/")).data });
  const [sel, setSel] = useState<{ role: string; dataset: string } | null>(null);
  const g = grid.data;

  return (
    <>
      <PageHeader eyebrow="Authorisation" title="The permission grid">
        Rows are roles, columns are datasets. Each cell is a policy: deny, aggregate-only (with a k-anonymity
        floor), or record-level with a rule for every column. Click a cell to see its column rules. Only the
        super-admin can change the grid, from the Django console.
      </PageHeader>
      <Page className="space-y-10">
        {grid.isLoading && <Spinner />}
        {g && (
          <>
            <div className="flex flex-wrap items-center gap-3 text-sm">
              {(Object.keys(MODE_META) as Mode[]).map((m) => <ModeTag key={m} mode={m} />)}
              <span className="text-gray-60">· <Tag tone="purple">SQL</Tag> = joinable in the workbench · k = minimum group size</span>
            </div>
            <div className="scroll-thin overflow-x-auto rounded-md border border-gray-30 bg-white">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr>
                    <th className="sticky left-0 z-20 min-w-[220px] border-b-2 border-ink bg-white px-4 py-3 text-left font-display">Role \ Dataset</th>
                    {g.datasets.map((d) => (
                      <th key={d.slug} className="h-40 w-16 min-w-[64px] border-b-2 border-ink px-1 align-bottom">
                        <div className="flex flex-col items-center gap-2">
                          <span className="whitespace-nowrap font-display text-xs font-medium [writing-mode:vertical-rl] rotate-180">{d.title}</span>
                          <Icon name={d.icon} size={15} className="text-gray-50" />
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {g.roles.map((r) => (
                    <tr key={r.slug} className={clsx(r.slug === me?.role.slug && "bg-brand-light/40")}>
                      <th className={clsx("sticky left-0 z-10 border-b border-gray-20 px-4 py-2 text-left font-normal", r.slug === me?.role.slug ? "bg-[#fdf1f1]" : "bg-white")}>
                        <span className="flex items-center gap-2">
                          <Icon name={r.icon} size={16} className="text-brand" />
                          <span className="font-display font-bold">{r.name}</span>
                          {r.slug === me?.role.slug && <Tag tone="red">you</Tag>}
                        </span>
                      </th>
                      {g.datasets.map((d) => {
                        const c = g.cells[r.slug]?.[d.slug] ?? { mode: "deny" as Mode, cross_analyze: false, k: 1, rules: [] };
                        const I = CELL_ICON[c.mode];
                        const active = sel?.role === r.slug && sel.dataset === d.slug;
                        return (
                          <td key={d.slug} className="border-b border-l border-gray-20 p-1 text-center">
                            <button
                              onClick={() => setSel({ role: r.slug, dataset: d.slug })}
                              title={`${r.name} → ${d.title}: ${MODE_META[c.mode].label}`}
                              className={clsx("flex h-12 w-full flex-col items-center justify-center rounded transition hover:ring-2", CELL[c.mode], active && "ring-2 ring-ink")}
                            >
                              <I size={16} />
                              <span className="mt-0.5 text-[10px] font-medium">
                                {c.mode === "aggregate" && c.k > 1 ? `k≥${c.k}` : c.cross_analyze ? "SQL" : MODE_META[c.mode].short}
                              </span>
                            </button>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {sel && <CellDetail role={sel.role} dataset={sel.dataset} roleName={g.roles.find((r) => r.slug === sel.role)?.name ?? sel.role} onClose={() => setSel(null)} />}

            <section className="grid gap-8 lg:grid-cols-2">
              <div>
                <SectionTitle sub="How a record-level policy can rewrite each column.">Column transforms</SectionTitle>
                <ul className="card divide-y divide-gray-20">
                  {(Object.keys(RULE_META) as Rule[]).map((r) => (
                    <li key={r} className="flex items-start gap-3 px-4 py-3 text-sm">
                      <span className="w-28 shrink-0"><RuleTag rule={r} /></span>
                      <span className="text-ink-4">{g.transforms[r]}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <SectionTitle sub="Which endpoints each role may call at all.">API capabilities</SectionTitle>
                <div className="scroll-thin overflow-x-auto rounded-md border border-gray-30 bg-white">
                  <table className="tbl">
                    <thead><tr><th>Role</th>{Object.keys(g.capabilities).map((c) => <th key={c} className="text-center font-mono text-[11px]" title={g.capabilities[c]}>{c}</th>)}</tr></thead>
                    <tbody>
                      {g.roles.map((r) => (
                        <tr key={r.slug}>
                          <td className="whitespace-nowrap font-medium">{r.name}</td>
                          {Object.keys(g.capabilities).map((c) => (
                            <td key={c} className="text-center">
                              {r.capabilities.includes(c) ? <Check size={16} className="mx-auto text-ok" aria-label="granted" /> : <X size={14} className="mx-auto text-gray-30" aria-label="not granted" />}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>
          </>
        )}
      </Page>
    </>
  );
}

function CellDetail({ role, dataset, roleName, onClose }: { role: string; dataset: string; roleName: string; onClose: () => void }) {
  const q = useQuery({
    queryKey: ["role-policy", role],
    queryFn: async () => (await api.get<RolePolicy[]>(`/grid/policies/${role}/`)).data,
  });
  const p = q.data?.find((x) => x.dataset === dataset);
  return (
    <section className="card relative overflow-hidden">
      <span className="absolute inset-x-0 top-0 h-1 bg-brand" />
      <div className="flex items-start justify-between gap-4 border-b border-gray-20 p-5">
        <div>
          <p className="eyebrow">{roleName}</p>
          <h3 className="mt-1 text-xl font-bold">{p?.title ?? dataset}</h3>
          {p && <p className="mt-1 text-sm text-ink-4">{p.rationale}</p>}
        </div>
        <div className="flex items-center gap-2">
          {p && <ModeTag mode={p.mode} />}
          <button className="btn-link btn-sm" onClick={onClose} aria-label="Close"><X size={16} /></button>
        </div>
      </div>
      <div className="p-5">
        {q.isLoading && <Spinner />}
        {q.isError && (
          <Callout tone="danger" title={`HTTP ${errorStatus(q.error)} — column rules hidden`}>
            {errorMessage(q.error)} The matrix above is public to every role; column-level detail for other roles needs <code>grid.view_all</code>.
          </Callout>
        )}
        {p && p.mode !== "row" && <p className="text-sm text-gray-60">{p.mode === "deny" ? "No columns are exposed." : `Only aggregates, with groups smaller than ${p.min_group_size} suppressed.`}</p>}
        {p && p.mode === "row" && (
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {p.columns.map((c) => (
              <div key={c.name} className={clsx("flex items-center justify-between gap-2 rounded border px-3 py-2", c.rule === "redact" ? "border-dashed border-gray-30 text-gray-50" : "border-gray-30")}>
                <span className="min-w-0">
                  <span className={clsx("block truncate font-mono text-[13px]", c.rule === "redact" && "line-through")}>{c.name}</span>
                  <span className="block truncate text-xs text-gray-60">{c.effect}</span>
                </span>
                <RuleTag rule={c.rule} />
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
