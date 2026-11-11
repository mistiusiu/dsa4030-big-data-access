import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowLeft, Ban, ChevronLeft, ChevronRight, Play, Plus, ShieldAlert, Trash2 } from "lucide-react";
import { useAuth } from "@/auth/AuthContext";
import { DataTable } from "@/components/DataTable";
import { Icon } from "@/components/Icon";
import { Callout, Empty, ModeTag, Page, PageHeader, RuleTag, Spinner, Tabs, Tag } from "@/components/ui";
import { api, errorMessage, errorStatus } from "@/lib/api";
import { fmt } from "@/lib/format";
import type { AggregateResult, DatasetDetail, RowResult } from "@/lib/types";

type Tab = "schema" | "records" | "aggregate";

export default function DatasetExplorer() {
  const { slug = "" } = useParams();
  const { data: ds, isLoading } = useQuery({
    queryKey: ["dataset", slug],
    queryFn: async () => (await api.get<DatasetDetail>(`/lake/datasets/${slug}/`)).data,
  });
  const [tab, setTab] = useState<Tab>("schema");
  useEffect(() => setTab("schema"), [slug]);

  if (isLoading || !ds) return <Page><Spinner /></Page>;

  return (
    <>
      <PageHeader
        eyebrow={ds.domain}
        title={<span className="flex items-center gap-4"><Icon name={ds.icon} size={36} className="text-brand" /> {ds.title}</span>}
        actions={<Link to="/lake" className="btn-dark"><ArrowLeft size={16} /> All datasets</Link>}
      >
        {ds.description}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <ModeTag mode={ds.mode} />
          {ds.rows != null && <Tag tone="dark">{fmt.format(ds.rows)} rows</Tag>}
          {ds.mode === "row" && <Tag tone="dark">max {ds.max_rows} rows / request</Tag>}
          {ds.mode !== "deny" && ds.min_group_size > 1 && <Tag tone="dark">k-anonymity ≥ {ds.min_group_size}</Tag>}
        </div>
      </PageHeader>
      <Page className="space-y-6">
        <Callout tone={ds.mode === "deny" ? "danger" : ds.mode === "aggregate" ? "info" : "success"} title="Why your role gets this view">
          {ds.rationale}
        </Callout>
        <Tabs<Tab>
          value={tab}
          onChange={setTab}
          items={[
            { value: "schema", label: "Schema & column rules" },
            { value: "records", label: "Records" },
            { value: "aggregate", label: "Aggregate" },
          ]}
        />
        {tab === "schema" && <Schema ds={ds} />}
        {tab === "records" && (ds.mode === "row" ? <Records ds={ds} /> : <Blocked slug={slug} ds={ds} kind="query" />)}
        {tab === "aggregate" && (ds.mode !== "deny" ? <Aggregate ds={ds} /> : <Blocked slug={slug} ds={ds} kind="aggregate" />)}
      </Page>
    </>
  );
}

function Schema({ ds }: { ds: DatasetDetail }) {
  const visible = ds.schema.filter((c) => c.rule !== "redact").length;
  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-60">
        {ds.mode === "row"
          ? <>You see <b className="text-ink">{visible}</b> of {ds.schema.length} columns. Filters and sorting apply to the transformed values, never the originals.</>
          : ds.mode === "aggregate"
            ? <>No column is readable row-by-row. You may group by <b className="text-ink">{ds.dimensions.join(", ")}</b>{ds.measures.length > 0 && <> and summarise <b className="text-ink">{ds.measures.join(", ")}</b></>}.</>
            : <>This dataset is closed to your role.</>}
      </p>
      <div className="overflow-hidden rounded border border-gray-30 bg-white">
        <table className="tbl">
          <thead><tr><th>Column</th><th>Type</th><th>Description</th><th>PII</th><th>Your rule</th><th>Effect</th></tr></thead>
          <tbody>
            {ds.schema.map((c) => (
              <tr key={c.name} className={c.rule === "redact" ? "text-gray-50" : ""}>
                <td className={`font-mono text-[13px] ${c.rule === "redact" ? "line-through" : "font-medium"}`}>{c.name}</td>
                <td className="font-mono text-xs text-gray-60">{c.type}</td>
                <td>{c.description}</td>
                <td>{c.pii && <Tag tone="red">PII</Tag>}</td>
                <td><RuleTag rule={c.rule} /></td>
                <td className="text-xs text-gray-60">{c.effect}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** A denied view still offers the request, so the 403 and its audit entry can be observed. */
function Blocked({ slug, ds, kind }: { slug: string; ds: DatasetDetail; kind: "query" | "aggregate" }) {
  const attempt = useMutation({
    mutationFn: async () =>
      (await api.post(`/lake/datasets/${slug}/${kind}/`, kind === "query" ? { limit: 10 } : { group_by: [ds.schema[0]?.name] })).data,
  });
  const err = attempt.error;
  return (
    <Empty icon={<Ban size={40} />} title={kind === "query" ? "Record-level access is not granted" : "Aggregates are not granted"}>
      <p>{ds.rationale}</p>
      <button className="btn-secondary mt-5" onClick={() => attempt.mutate()} disabled={attempt.isPending}>
        <ShieldAlert size={16} /> Send the request anyway
      </button>
      {err && (
        <div className="mt-4 text-left">
          <Callout tone="danger" title={`HTTP ${errorStatus(err)} — refused by the backend`}>
            {errorMessage(err)} <br />Logged as <b>denied</b>. Repeated attempts trip the privilege-probing rule in the SIEM.
          </Callout>
        </div>
      )}
    </Empty>
  );
}

const OPS = [
  ["eq", "="], ["neq", "≠"], ["contains", "contains"], ["gt", ">"], ["gte", "≥"], ["lt", "<"], ["lte", "≤"],
  ["is_null", "is empty"], ["not_null", "is not empty"],
] as const;

interface Filter { column: string; op: string; value: string }

function Records({ ds }: { ds: DatasetDetail }) {
  const { can } = useAuth();
  const visible = useMemo(() => ds.schema.filter((c) => c.rule !== "redact").map((c) => c.name), [ds]);
  const [filters, setFilters] = useState<Filter[]>([]);
  const [orderBy, setOrderBy] = useState("");
  const [desc, setDesc] = useState(false);
  const [limit, setLimit] = useState(Math.min(50, ds.max_rows));
  const [offset, setOffset] = useState(0);

  const q = useMutation({
    mutationFn: async (o: number) =>
      (await api.post<RowResult>(`/lake/datasets/${ds.slug}/query/`, {
        filters: filters.filter((f) => f.column), order_by: orderBy || undefined, desc, limit, offset: o,
      })).data,
  });
  const run = (o = 0) => { setOffset(o); q.mutate(o); };
  useEffect(() => { if (can("lake.browse")) run(0); }, [ds.slug]);

  if (!can("lake.browse")) return <Callout tone="danger" title="Missing capability lake.browse">Your role cannot read records.</Callout>;

  const res = q.data;
  return (
    <div className="space-y-4">
      <div className="card space-y-3 p-4">
        {filters.map((f, i) => (
          <div key={i} className="flex flex-wrap items-center gap-2">
            <select className="field w-auto font-mono text-sm" value={f.column} onChange={(e) => setFilters(filters.map((x, j) => j === i ? { ...x, column: e.target.value } : x))}>
              {visible.map((c) => <option key={c}>{c}</option>)}
            </select>
            <select className="field w-auto text-sm" value={f.op} onChange={(e) => setFilters(filters.map((x, j) => j === i ? { ...x, op: e.target.value } : x))}>
              {OPS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            {!f.op.includes("null") && (
              <input className="field w-56 text-sm" placeholder="value" value={f.value} onChange={(e) => setFilters(filters.map((x, j) => j === i ? { ...x, value: e.target.value } : x))} />
            )}
            <button className="btn-link btn-sm" onClick={() => setFilters(filters.filter((_, j) => j !== i))} aria-label="Remove filter"><Trash2 size={15} /></button>
          </div>
        ))}
        <div className="flex flex-wrap items-end gap-3">
          <button className="btn-tertiary btn-sm" onClick={() => setFilters([...filters, { column: visible[0], op: "eq", value: "" }])}>
            <Plus size={15} /> Add filter
          </button>
          <div>
            <label className="label text-xs">Sort by</label>
            <select className="field w-auto py-1 text-sm" value={orderBy} onChange={(e) => setOrderBy(e.target.value)}>
              <option value="">—</option>
              {visible.map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <label className="flex items-center gap-2 pb-1.5 text-sm"><input type="checkbox" checked={desc} onChange={(e) => setDesc(e.target.checked)} /> descending</label>
          <div>
            <label className="label text-xs">Page size (max {ds.max_rows})</label>
            <input type="number" min={1} max={ds.max_rows} className="field w-24 py-1 text-sm" value={limit} onChange={(e) => setLimit(Number(e.target.value))} />
          </div>
          <button className="btn-primary btn-sm ml-auto" onClick={() => run(0)} disabled={q.isPending}><Play size={15} /> Run query</button>
        </div>
      </div>

      {q.isError && <Callout tone={errorStatus(q.error) === 403 ? "danger" : "warning"} title={`HTTP ${errorStatus(q.error)}`}>{errorMessage(q.error)}</Callout>}
      {q.isPending && <Spinner label="DuckDB is scanning Parquet…" />}
      {res && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
            <p className="text-gray-60">
              <b className="text-ink">{fmt.format(res.total ?? 0)}</b> matching rows · showing {fmt.format(res.offset! + 1)}–{fmt.format(res.offset! + res.rows.length)}
            </p>
            <div className="flex gap-2">
              <button className="btn-tertiary btn-sm" disabled={!offset} onClick={() => run(Math.max(0, offset - limit))}><ChevronLeft size={15} /> Prev</button>
              <button className="btn-tertiary btn-sm" disabled={offset + limit >= (res.total ?? 0)} onClick={() => run(offset + limit)}>Next <ChevronRight size={15} /></button>
            </div>
          </div>
          <DataTable columns={res.columns} rows={res.rows} transforms={res.transforms} />
        </>
      )}
    </div>
  );
}

const FNS = ["avg", "min", "max", "sum", "median", "stddev"];
const BAR = "#0066cc";

function Aggregate({ ds }: { ds: DatasetDetail }) {
  const [groupBy, setGroupBy] = useState<string[]>([ds.dimensions[0]]);
  const [metrics, setMetrics] = useState<{ fn: string; measure: string }[]>(
    ds.measures.length ? [{ fn: "avg", measure: ds.measures[0] }] : [],
  );
  const q = useMutation({
    mutationFn: async () => (await api.post<AggregateResult>(`/lake/datasets/${ds.slug}/aggregate/`, { group_by: groupBy, metrics })).data,
  });
  useEffect(() => { q.mutate(); }, [ds.slug]);

  const toggle = (d: string) =>
    setGroupBy(groupBy.includes(d) ? groupBy.filter((x) => x !== d) : groupBy.length < 3 ? [...groupBy, d] : groupBy);

  const res = q.data;
  const chart = useMemo(() => {
    if (!res) return [];
    const nIdx = res.columns.indexOf("n");
    const dimCount = nIdx;
    return res.rows.slice(0, 20).map((r) => ({ label: r.slice(0, dimCount).map(String).join(" · "), n: r[nIdx] as number }));
  }, [res]);

  return (
    <div className="space-y-4">
      <div className="card space-y-4 p-4">
        <div>
          <p className="label">Group by (up to 3)</p>
          <div className="flex flex-wrap gap-2">
            {ds.dimensions.map((d) => (
              <button key={d} onClick={() => toggle(d)} className={`rounded-full border px-3 py-1 font-mono text-xs transition-colors ${groupBy.includes(d) ? "border-ink bg-ink text-white" : "border-gray-30 bg-white hover:border-ink"}`}>
                {d}
              </button>
            ))}
          </div>
        </div>
        {ds.measures.length > 0 && (
          <div>
            <p className="label">Measures</p>
            <div className="space-y-2">
              {metrics.map((m, i) => (
                <div key={i} className="flex flex-wrap items-center gap-2">
                  <select className="field w-auto py-1 text-sm" value={m.fn} onChange={(e) => setMetrics(metrics.map((x, j) => j === i ? { ...x, fn: e.target.value } : x))}>
                    {FNS.map((f) => <option key={f}>{f}</option>)}
                  </select>
                  <span className="text-sm text-gray-60">of</span>
                  <select className="field w-auto py-1 font-mono text-sm" value={m.measure} onChange={(e) => setMetrics(metrics.map((x, j) => j === i ? { ...x, measure: e.target.value } : x))}>
                    {ds.measures.map((x) => <option key={x}>{x}</option>)}
                  </select>
                  <button className="btn-link btn-sm" onClick={() => setMetrics(metrics.filter((_, j) => j !== i))} aria-label="Remove measure"><Trash2 size={15} /></button>
                </div>
              ))}
              {metrics.length < 4 && (
                <button className="btn-tertiary btn-sm" onClick={() => setMetrics([...metrics, { fn: "avg", measure: ds.measures[0] }])}><Plus size={15} /> Add measure</button>
              )}
            </div>
          </div>
        )}
        <div className="flex justify-end">
          <button className="btn-primary btn-sm" disabled={!groupBy.length || q.isPending} onClick={() => q.mutate()}><Play size={15} /> Summarise</button>
        </div>
      </div>

      {q.isError && <Callout tone="danger" title={`HTTP ${errorStatus(q.error)}`}>{errorMessage(q.error)}</Callout>}
      {q.isPending && <Spinner label="Aggregating…" />}
      {res && (
        <>
          {res.min_group_size > 1 && (
            <Callout tone={res.suppressed_groups ? "warning" : "info"} title={`k-anonymity threshold: ${res.min_group_size}`}>
              {res.suppressed_groups
                ? <>{fmt.format(res.suppressed_groups)} groups covering {fmt.format(res.suppressed_rows)} records were smaller than {res.min_group_size} and have been suppressed so no individual can be singled out.</>
                : <>No group fell below the threshold.</>}
            </Callout>
          )}
          <div className="grid gap-4 xl:grid-cols-[1fr_1.1fr]">
            <figure className="card p-4">
              <figcaption className="mb-2 font-display text-sm font-bold">Records per group <span className="font-normal text-gray-60">(top {chart.length})</span></figcaption>
              <div style={{ height: Math.max(220, chart.length * 30) }}>
                <ResponsiveContainer>
                  <BarChart data={chart} layout="vertical" margin={{ left: 8, right: 24 }} barCategoryGap={4}>
                    <CartesianGrid horizontal={false} stroke="#e0e0e0" />
                    <XAxis type="number" tick={{ fontSize: 12, fill: "#4d4d4d" }} axisLine={false} tickLine={false}
                      tickFormatter={(v: number) => (v >= 1000 ? `${Math.round(v / 100) / 10}K` : String(v))} />
                    <YAxis type="category" dataKey="label" width={170} tick={{ fontSize: 12, fill: "#151515" }} axisLine={{ stroke: "#c7c7c7" }} tickLine={false} />
                    <Tooltip cursor={{ fill: "#f2f2f2" }} formatter={(v: number) => [fmt.format(v), "records"]}
                      contentStyle={{ borderRadius: 3, border: "1px solid #c7c7c7", fontSize: 13 }} />
                    <Bar dataKey="n" fill={BAR} radius={[0, 4, 4, 0]} maxBarSize={24} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </figure>
            <DataTable columns={res.columns} rows={res.rows} maxHeight="520px" />
          </div>
        </>
      )}
    </div>
  );
}
