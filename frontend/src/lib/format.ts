export const fmt = new Intl.NumberFormat("en-KE");

export function cell(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (typeof v === "number") return Number.isInteger(v) ? fmt.format(v) : v.toLocaleString("en-KE", { maximumFractionDigits: 4 });
  const s = String(v);
  // ISO timestamps → readable local form.
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(s)) return s.replace("T", " ").slice(0, 19);
  return s;
}

export function relTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const s = Math.round((new Date(iso).getTime() - Date.now()) / 1000);
  const abs = Math.abs(s);
  const unit = abs < 60 ? [s, "second"] : abs < 3600 ? [Math.round(s / 60), "minute"] : abs < 86400 ? [Math.round(s / 3600), "hour"] : [Math.round(s / 86400), "day"];
  return new Intl.RelativeTimeFormat("en", { numeric: "auto" }).format(unit[0] as number, unit[1] as Intl.RelativeTimeFormatUnit);
}

export function clock(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-KE", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
