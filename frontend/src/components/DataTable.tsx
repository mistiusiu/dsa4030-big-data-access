import clsx from "clsx";
import { cell } from "@/lib/format";
import type { Rule } from "@/lib/types";

const RULE_CELL: Partial<Record<Rule, string>> = {
  mask: "text-warn bg-warn-bg/40",
  pseudonym: "text-purple bg-purple-bg/40 font-mono text-[12px]",
  fake: "text-teal bg-teal-bg/40",
  generalize: "text-link-dark bg-link-light/40",
};

export function DataTable({ columns, rows, transforms, maxHeight = "60vh" }: {
  columns: string[];
  rows: unknown[][];
  transforms?: Record<string, Rule | null | undefined>;
  maxHeight?: string;
}) {
  return (
    <div className="scroll-thin overflow-auto rounded border border-gray-30 bg-white" style={{ maxHeight }}>
      <table className="tbl">
        <thead>
          <tr>
            <th className="w-10 text-right text-gray-50">#</th>
            {columns.map((c) => (
              <th key={c}>
                {c}
                {transforms?.[c] && transforms[c] !== "clear" && (
                  <span className="ml-1.5 align-middle text-[10px] font-medium uppercase tracking-wide text-gray-50">
                    {transforms[c]}
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td className="text-right font-mono text-xs text-gray-50">{i + 1}</td>
              {r.map((v, j) => (
                <td key={j} className={clsx("max-w-[340px] truncate", transforms && RULE_CELL[transforms[columns[j]] as Rule])} title={String(v ?? "")}>
                  {cell(v)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
