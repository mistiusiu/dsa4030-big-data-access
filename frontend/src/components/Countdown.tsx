import { useEffect, useState } from "react";
import clsx from "clsx";

export function useNow(intervalMs = 1000) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(t);
  }, [intervalMs]);
  return now;
}

export function remaining(until: string | null | undefined, now: number) {
  if (!until) return null;
  return Math.max(0, Math.floor((new Date(until).getTime() - now) / 1000));
}

export function fmtDuration(s: number) {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return h ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}:${String(sec).padStart(2, "0")}`;
}

export function Countdown({ until, compact }: { until: string | null | undefined; compact?: boolean }) {
  const now = useNow();
  const s = remaining(until, now);
  if (s === null) return <span>—</span>;
  return (
    <span className={clsx("font-mono tabular-nums", s === 0 ? "text-[#f56e6e]" : s < 60 && "text-[#ffcc17]")}>
      {s === 0 ? "expired" : compact ? fmtDuration(s) : `${fmtDuration(s)} left`}
    </span>
  );
}

export function ExpiryBar({ issued, until }: { issued?: number; until: string | null | undefined }) {
  const now = useNow();
  if (!until || !issued) return null;
  const end = new Date(until).getTime();
  const total = end - issued * 1000;
  const pct = Math.max(0, Math.min(100, ((end - now) / total) * 100));
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-20" role="progressbar" aria-valuenow={Math.round(pct)}>
      <div className={clsx("h-full transition-all", pct < 15 ? "bg-brand" : pct < 40 ? "bg-[#dca614]" : "bg-[#3d7317]")} style={{ width: `${pct}%` }} />
    </div>
  );
}
