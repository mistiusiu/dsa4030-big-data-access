import clsx from "clsx";
import type { ReactNode } from "react";
import { Ban, CheckCircle2, CircleAlert, Eye, EyeOff, Fingerprint, Shapes, Sigma, Shuffle, Asterisk, Info } from "lucide-react";
import type { Mode, Rule } from "@/lib/types";

export function PageHeader({ eyebrow, title, children, actions }: {
  eyebrow?: string; title: ReactNode; children?: ReactNode; actions?: ReactNode;
}) {
  return (
    <header className="relative overflow-hidden bg-ink text-white">
      <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full border-[40px] border-white/[0.04]" />
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-end justify-between gap-6 px-6 py-10 lg:px-10">
        <div className="max-w-3xl">
          {eyebrow && <p className="eyebrow mb-3 text-[#f56e6e]">{eyebrow}</p>}
          <h1 className="font-display text-3xl font-bold leading-tight text-white md:text-[2.5rem]">{title}</h1>
          {children && <div className="mt-3 text-[17px] leading-relaxed text-gray-30">{children}</div>}
        </div>
        {actions && <div className="flex flex-wrap gap-3">{actions}</div>}
      </div>
    </header>
  );
}

export function Page({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx("mx-auto max-w-[1400px] px-6 py-8 lg:px-10", className)}>{children}</div>;
}

export function SectionTitle({ children, sub }: { children: ReactNode; sub?: ReactNode }) {
  return (
    <div className="mb-4">
      <h2 className="text-xl font-bold">{children}</h2>
      {sub && <p className="mt-1 text-sm text-gray-60">{sub}</p>}
    </div>
  );
}

type Tone = "gray" | "green" | "red" | "blue" | "teal" | "purple" | "orange" | "yellow" | "dark";
const TONES: Record<Tone, string> = {
  gray: "bg-gray-10 text-ink-4 border-gray-30",
  green: "bg-ok-bg text-ok border-[#87bb62]",
  red: "bg-bad-bg text-bad border-[#f9a8a8]",
  blue: "bg-link-light text-link-dark border-[#92c5f9]",
  teal: "bg-teal-bg text-teal border-[#9ad8d8]",
  purple: "bg-purple-bg text-purple border-[#b6a6e9]",
  orange: "bg-orange-bg text-orange border-[#fccb8f]",
  yellow: "bg-warn-bg text-warn border-[#ffe072]",
  dark: "bg-ink text-white border-ink",
};

export function Tag({ tone = "gray", children, icon, className, title }: {
  tone?: Tone; children: ReactNode; icon?: ReactNode; className?: string; title?: string;
}) {
  return (
    <span title={title} className={clsx("inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium", TONES[tone], className)}>
      {icon}
      {children}
    </span>
  );
}

export const MODE_META: Record<Mode, { label: string; tone: Tone; icon: ReactNode; short: string }> = {
  row: { label: "Record level", short: "Rows", tone: "green", icon: <CheckCircle2 size={12} /> },
  aggregate: { label: "Aggregate only", short: "Agg", tone: "blue", icon: <Sigma size={12} /> },
  deny: { label: "Denied", short: "Deny", tone: "gray", icon: <Ban size={12} /> },
};

export function ModeTag({ mode }: { mode: Mode }) {
  const m = MODE_META[mode];
  return <Tag tone={m.tone} icon={m.icon}>{m.label}</Tag>;
}

export const RULE_META: Record<Rule, { label: string; tone: Tone; icon: ReactNode }> = {
  clear: { label: "Clear", tone: "green", icon: <Eye size={12} /> },
  mask: { label: "Masked", tone: "yellow", icon: <Asterisk size={12} /> },
  pseudonym: { label: "Pseudonym", tone: "purple", icon: <Fingerprint size={12} /> },
  fake: { label: "Fake", tone: "teal", icon: <Shuffle size={12} /> },
  generalize: { label: "Generalised", tone: "blue", icon: <Shapes size={12} /> },
  redact: { label: "Redacted", tone: "gray", icon: <EyeOff size={12} /> },
};

export function RuleTag({ rule }: { rule: Rule }) {
  const m = RULE_META[rule];
  return <Tag tone={m.tone} icon={m.icon}>{m.label}</Tag>;
}

export function Callout({ tone = "info", title, children }: {
  tone?: "info" | "danger" | "warning" | "success"; title?: ReactNode; children?: ReactNode;
}) {
  const styles = {
    info: "border-link bg-link-light/60",
    danger: "border-brand bg-bad-bg/70",
    warning: "border-[#dca614] bg-warn-bg/70",
    success: "border-[#3d7317] bg-ok-bg/70",
  }[tone];
  const icon = {
    info: <Info size={18} className="text-link" />,
    danger: <Ban size={18} className="text-brand" />,
    warning: <CircleAlert size={18} className="text-warn" />,
    success: <CheckCircle2 size={18} className="text-ok" />,
  }[tone];
  return (
    <div className={clsx("flex gap-3 rounded border-l-4 p-4", styles)}>
      <div className="mt-0.5 shrink-0">{icon}</div>
      <div className="min-w-0 text-sm">
        {title && <p className="font-display font-bold text-ink">{title}</p>}
        {children && <div className="mt-0.5 text-ink-4">{children}</div>}
      </div>
    </div>
  );
}

export function Stat({ label, value, hint, accent }: { label: string; value: ReactNode; hint?: ReactNode; accent?: string }) {
  return (
    <div className="card relative overflow-hidden p-5">
      <span className={clsx("absolute inset-x-0 top-0 h-1", accent ?? "bg-brand")} />
      <p className="text-sm font-medium text-gray-60">{label}</p>
      <p className="mt-1 font-display text-3xl font-bold tabular-nums">{value}</p>
      {hint && <p className="mt-1 text-xs text-gray-60">{hint}</p>}
    </div>
  );
}

export function Tabs<T extends string>({ value, onChange, items }: {
  value: T; onChange: (v: T) => void; items: { value: T; label: ReactNode; disabled?: boolean }[];
}) {
  return (
    <div role="tablist" className="flex gap-1 border-b border-gray-30">
      {items.map((it) => (
        <button
          key={it.value}
          role="tab"
          aria-selected={value === it.value}
          disabled={it.disabled}
          onClick={() => onChange(it.value)}
          className={clsx(
            "-mb-px flex items-center gap-2 border-b-[3px] px-4 py-2.5 font-display text-[15px] font-medium transition-colors disabled:opacity-40",
            value === it.value ? "border-brand text-ink" : "border-transparent text-gray-60 hover:border-gray-40 hover:text-ink",
          )}
        >
          {it.label}
        </button>
      ))}
    </div>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-8 text-sm text-gray-60">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-gray-30 border-t-brand" />
      {label}
    </div>
  );
}

export function Empty({ icon, title, children }: { icon?: ReactNode; title: ReactNode; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-md border border-dashed border-gray-30 bg-white px-6 py-14 text-center">
      {icon && <div className="mb-3 text-gray-40">{icon}</div>}
      <p className="font-display text-lg font-bold">{title}</p>
      {children && <div className="mt-1 max-w-md text-sm text-gray-60">{children}</div>}
    </div>
  );
}

export function Code({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <pre className={clsx("scroll-thin overflow-auto rounded bg-ink-2 p-4 font-mono text-[13px] leading-relaxed text-gray-20", className)}>
      {children}
    </pre>
  );
}
