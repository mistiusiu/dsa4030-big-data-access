export type Mode = "row" | "aggregate" | "deny";
export type Rule = "clear" | "mask" | "pseudonym" | "fake" | "generalize" | "redact";

export interface Role {
  slug: string;
  name: string;
  description: string;
  icon: string;
  capabilities: string[];
}

export interface Me {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  role: Role;
  last_login: string | null;
  token_claims: Record<string, unknown>;
}

export interface PolicySummary {
  mode: Mode;
  rationale: string;
  cross_analyze: boolean;
  max_rows: number;
  min_group_size: number;
  dimensions: string[];
  measures: string[];
}

export interface DatasetCard extends PolicySummary {
  slug: string;
  title: string;
  domain: string;
  icon: string;
  description: string;
  rows: number | null;
  columns: number;
}

export interface ColumnView {
  name: string;
  type: string;
  kind: string;
  description: string;
  pii: boolean;
  rule: Rule;
  effect: string;
}

export interface DatasetDetail extends DatasetCard {
  schema: ColumnView[];
}

export interface RowResult {
  columns: string[];
  types?: string[];
  rows: unknown[][];
  total?: number;
  limit?: number;
  offset?: number;
  max_rows?: number;
  transforms?: Record<string, Rule | null>;
  truncated?: boolean;
  tables_used?: string[];
  elapsed_ms?: number;
}

export interface AggregateResult {
  columns: string[];
  rows: unknown[][];
  min_group_size: number;
  suppressed_groups: number;
  suppressed_rows: number;
}

export interface AuditEntry {
  id: number;
  timestamp: string;
  username: string;
  role: string;
  method: string;
  path: string;
  status_code: number;
  outcome: string;
  action: string;
  dataset: string;
  ip: string | null;
  user_agent: string;
  duration_ms: number;
  token_jti: string;
  detail: Record<string, unknown>;
}

export interface Finding {
  rule: string;
  title: string;
  mitre: string;
  severity: "high" | "medium";
  subject_type: string;
  subject: string;
  value: number;
  events: number;
  first_seen: string;
  last_seen: string;
  explain: string;
}
