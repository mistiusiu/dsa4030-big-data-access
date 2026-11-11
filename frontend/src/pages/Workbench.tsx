import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Lock, Play, Skull, Sparkles, Table2 } from "lucide-react";
import { useAuth } from "@/auth/AuthContext";
import { DataTable } from "@/components/DataTable";
import { Callout, Page, PageHeader, RULE_META, Spinner, Tag } from "@/components/ui";
import { api, errorMessage, errorStatus } from "@/lib/api";
import type { ColumnView, RowResult } from "@/lib/types";

interface SqlTable { name: string; title: string; columns: ColumnView[] }
interface Preset { label: string; sql: string; attack?: boolean }

const PRESETS: Record<string, Preset[]> = {
  medical: [
    { label: "Critical patients and how to reach them", sql: `SELECT c.first_name, c.last_name, m.diagnosis, m.severity, m.facility,\n       r.address, r.district, r.floor, r.access_notes\nFROM medical_records m\nJOIN citizens c USING (citizen_id)\nJOIN residences r USING (residence_id)\nWHERE m.severity = 'critical'\nORDER BY m.visit_at DESC\nLIMIT 50` },
    { label: "Does the patient have a record? (denied)", sql: `SELECT c.first_name, c.last_name, f.offence\nFROM felonies f JOIN citizens c USING (citizen_id)\nLIMIT 10`, attack: true },
  ],
  rapid_response: [
    { label: "Residents needing help to evacuate a district", sql: `SELECT c.first_name, c.last_name, c.disability, c.phone,\n       r.address, r.floor, r.access_notes, m.blood_type, m.allergies\nFROM citizens c\nJOIN residences r USING (residence_id)\nLEFT JOIN medical_records m USING (citizen_id)\nWHERE c.disability <> 'none' AND r.district = 'Mto Riverside'\nLIMIT 100` },
    { label: "Unsafe assets near active hazards", sql: `SELECT h.hazard_type, h.severity, h.district, i.asset_type, i.status, i.health_score\nFROM hazard_alerts h\nJOIN infrastructure i USING (district)\nWHERE i.status IN ('critical', 'maintenance_due')\nORDER BY h.issued_at DESC\nLIMIT 100` },
  ],
  law_enforcement: [
    { label: "Convicted suspects and their vehicle activity", sql: `SELECT c.first_name, c.last_name, f.offence, f.status, v.plate,\n       count(*) AS pings, round(max(v.speed_kph)) AS top_speed\nFROM felonies f\nJOIN citizens c USING (citizen_id)\nJOIN vehicle_tracking v ON v.owner_id = c.citizen_id\nGROUP BY ALL\nORDER BY pings DESC\nLIMIT 25` },
    { label: "Read medical records (denied)", sql: `SELECT * FROM medical_records LIMIT 10`, attack: true },
  ],
  sociologist: [
    { label: "Income homophily in friendships", sql: `SELECT a.income_band AS person, b.income_band AS friend, count(*) AS ties\nFROM relationships r\nJOIN citizens a ON a.citizen_id = r.citizen_a\nJOIN citizens b ON b.citizen_id = r.citizen_b\nWHERE r.relation_type = 'friend'\nGROUP BY ALL\nORDER BY ties DESC` },
    { label: "Ego network of pseudonymous subjects", sql: `SELECT a.first_name AS subject, a.citizen_id, r.relation_type,\n       b.first_name AS alter, b.occupation, r.strength\nFROM relationships r\nJOIN citizens a ON a.citizen_id = r.citizen_a\nJOIN citizens b ON b.citizen_id = r.citizen_b\nORDER BY r.strength DESC\nLIMIT 50` },
  ],
  transport_official: [
    { label: "Riders who requested boarding assistance", sql: `SELECT t.board_at, t.route_id, t.board_stop, t.alight_stop,\n       c.first_name, c.last_name, c.date_of_birth AS age_band, c.disability\nFROM transit_trips t\nJOIN citizens c USING (citizen_id)\nWHERE t.assistance_requested\nORDER BY t.board_at DESC\nLIMIT 100` },
    { label: "Peak-hour load per route", sql: `SELECT route_id, hour(board_at) AS hour, count(*) AS boardings\nFROM transit_trips\nGROUP BY ALL\nORDER BY boardings DESC\nLIMIT 30` },
  ],
  climatologist: [
    { label: "Urban heat island by district", sql: `SELECT district,\n       round(avg(temperature_c), 1) AS air_c,\n       round(avg(surface_temp_c), 1) AS surface_c,\n       round(avg(surface_temp_c - temperature_c), 2) AS heat_island_delta,\n       round(avg(pm25), 1) AS pm25\nFROM weather\nGROUP BY district\nORDER BY heat_island_delta DESC` },
    { label: "Rainfall vs flood alerts", sql: `SELECT w.district, round(sum(w.rainfall_mm)) AS rain_mm,\n       (SELECT count(*) FROM hazard_alerts h\n        WHERE h.district = w.district AND h.hazard_type = 'flood') AS flood_alerts\nFROM weather w\nGROUP BY w.district\nORDER BY rain_mm DESC` },
  ],
  administrator: [
    { label: "Prove every silo is reachable", sql: `SELECT 'citizens' AS silo, count(*) AS rows FROM citizens\nUNION ALL SELECT 'medical_records', count(*) FROM medical_records\nUNION ALL SELECT 'felonies', count(*) FROM felonies\nUNION ALL SELECT 'transit_trips', count(*) FROM transit_trips\nUNION ALL SELECT 'vehicle_tracking', count(*) FROM vehicle_tracking\nUNION ALL SELECT 'egov_logs', count(*) FROM egov_logs` },
    { label: "Pseudonymised citizen sample", sql: `SELECT * FROM citizens LIMIT 25` },
  ],
};

const COMMON: Preset[] = [
  { label: "Escape the sandbox: read raw Parquet", sql: `SELECT * FROM read_parquet('/data/lake/citizens.parquet') LIMIT 5`, attack: true },
  { label: "Write something", sql: `DROP TABLE citizens`, attack: true },
];

export default function Workbench() {
  const { me, can } = useAuth();
  const allowed = can("lake.sql");
  const tables = useQuery({
    queryKey: ["sql-tables"],
    enabled: allowed,
    queryFn: async () => (await api.get<SqlTable[]>("/lake/sql/tables/")).data,
  });
  const presets = [...(PRESETS[me?.role.slug ?? ""] ?? []), ...COMMON];
  const [sql, setSql] = useState(presets[0]?.sql ?? "SELECT 1");
  const [open, setOpen] = useState<string | null>(null);

  const run = useMutation({
    mutationFn: async (text: string) => (await api.post<RowResult>("/lake/sql/", { sql: text })).data,
  });

  return (
    <>
      <PageHeader eyebrow="Cross-analysis" title="SQL Workbench">
        Join datasets with DuckDB SQL. Each table you reference is your role's <em>policy view</em> — already
        masked and pseudonymised — loaded into a sandbox with file access, extensions and configuration locked.
      </PageHeader>
      <Page>
        {!allowed && (
          <div className="mb-6">
            <Callout tone="danger" title="Your role lacks the lake.sql capability">
              The workbench is closed to {me?.role.name}. You can still press Run to watch the API refuse — and the audit log record it.
            </Callout>
          </div>
        )}
        <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
          <aside className="space-y-4">
            <div className="card">
              <p className="flex items-center gap-2 border-b border-gray-20 px-4 py-3 font-display font-bold"><Table2 size={16} /> Your tables</p>
              {tables.isLoading && <div className="px-4"><Spinner /></div>}
              {!allowed && <p className="flex items-center gap-2 px-4 py-3 text-sm text-gray-60"><Lock size={14} /> None</p>}
              <ul className="scroll-thin max-h-[55vh] overflow-auto">
                {tables.data?.map((t) => (
                  <li key={t.name} className="border-b border-gray-20 last:border-0">
                    <button className="flex w-full items-center gap-2 px-4 py-2 text-left font-mono text-sm hover:bg-gray-10" onClick={() => setOpen(open === t.name ? null : t.name)}>
                      {open === t.name ? <ChevronDown size={14} /> : <ChevronRight size={14} />} {t.name}
                      <span className="ml-auto text-xs text-gray-50">{t.columns.length}</span>
                    </button>
                    {open === t.name && (
                      <ul className="bg-gray-10 px-4 py-2">
                        {t.columns.map((c) => (
                          <li key={c.name} className="flex items-center justify-between gap-2 py-0.5">
                            <button className="truncate font-mono text-xs text-link hover:underline" onClick={() => setSql((s) => `${s} ${c.name}`)}>{c.name}</button>
                            {c.rule !== "clear" && <Tag tone={RULE_META[c.rule].tone}>{RULE_META[c.rule].label}</Tag>}
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            </div>
            <div className="card">
              <p className="flex items-center gap-2 border-b border-gray-20 px-4 py-3 font-display font-bold"><Sparkles size={16} /> Try these</p>
              <ul>
                {presets.map((p) => (
                  <li key={p.label} className="border-b border-gray-20 last:border-0">
                    <button className="flex w-full items-start gap-2 px-4 py-2.5 text-left text-sm hover:bg-gray-10" onClick={() => { setSql(p.sql); run.reset(); }}>
                      {p.attack ? <Skull size={15} className="mt-0.5 shrink-0 text-brand" /> : <Play size={15} className="mt-0.5 shrink-0 text-gray-50" />}
                      {p.label}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </aside>

          <section className="min-w-0 space-y-4">
            <div className="overflow-hidden rounded-md border border-ink bg-ink-2">
              <div className="flex items-center justify-between border-b border-ink-4 px-4 py-2 text-xs text-gray-40">
                <span className="font-mono">duckdb · sandboxed · read-only</span>
                <span>Ctrl + Enter to run</span>
              </div>
              <textarea
                value={sql}
                onChange={(e) => setSql(e.target.value)}
                onKeyDown={(e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") run.mutate(sql); }}
                spellCheck={false}
                className="block h-64 w-full resize-y bg-transparent p-4 font-mono text-[13px] leading-relaxed text-gray-10 outline-none"
              />
              <div className="flex justify-end border-t border-ink-4 px-4 py-2">
                <button className="btn-primary btn-sm" onClick={() => run.mutate(sql)} disabled={run.isPending}><Play size={15} /> Run</button>
              </div>
            </div>

            {run.isPending && <Spinner label="Materialising policy views and running…" />}
            {run.isError && (
              <Callout tone={errorStatus(run.error) === 403 ? "danger" : "warning"} title={`HTTP ${errorStatus(run.error)} — ${errorStatus(run.error) === 403 ? "refused by the permission grid" : "query rejected"}`}>
                {errorMessage(run.error)}
              </Callout>
            )}
            {run.data && (
              <>
                <div className="flex flex-wrap items-center gap-2 text-sm text-gray-60">
                  <b className="text-ink">{run.data.rows.length}</b> rows{run.data.truncated && " (truncated)"} · {run.data.elapsed_ms} ms ·
                  tables: {run.data.tables_used?.map((t) => <Tag key={t}>{t}</Tag>)}
                </div>
                <DataTable columns={run.data.columns} rows={run.data.rows} />
              </>
            )}
          </section>
        </div>
      </Page>
    </>
  );
}
