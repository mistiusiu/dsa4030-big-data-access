"""Policy engine: turns a permission-grid cell into DuckDB SQL.

A row-mode policy compiles to a SELECT over the Parquet file in which every
column is either passed through, rewritten by a transform, or left out. Callers
only ever query *that* view, so filters and sorts operate on transformed values
and a masked column cannot be used to probe the original.
"""

import re
import threading
import time
from dataclasses import asdict, dataclass

import duckdb
from django.conf import settings

from apps.grid.models import Policy

from .catalog import BY_SLUG, Column, Dataset
from .generator import FIRST_NAMES, LAST_NAMES


class AccessDenied(Exception):
    pass


class BadQuery(Exception):
    pass


def lit(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def parquet(ds: Dataset) -> str:
    return f"read_parquet({lit(str(settings.LAKE_DIR / ds.filename))})"


def _list(values: list[str]) -> str:
    return "[" + ", ".join(lit(v) for v in values) + "]"


AGE_BAND = (
    "CAST(floor(date_diff('year', {c}, current_date) / 10) * 10 AS INTEGER) || '–' || "
    "CAST(floor(date_diff('year', {c}, current_date) / 10) * 10 + 9 AS INTEGER)"
)
TAIL4 = "repeat('•', greatest(length({c}) - 4, 0)) || right({c}, 4)"


def _pseudonym(c: str, salt: str) -> str:
    return f"'PSN-' || substr(sha256({lit(salt)} || CAST({c} AS VARCHAR)), 1, 12)"


def _pick(pool: list[str], c: str, salt: str) -> str:
    return f"list_extract({_list(pool)}, CAST(hash({lit(salt)} || CAST({c} AS VARCHAR)) % {len(pool)} AS INTEGER) + 1)"


def column_expr(col: Column, rule: str, role: str) -> str | None:
    """SQL expression for ``col`` under ``rule``, or None when it is redacted."""
    if rule == "redact":
        return None
    c = ident(col.name)
    if rule == "clear":
        return c
    # The secret is per role: one role's pseudonyms cannot be matched to another's.
    salt = f"{settings.PSEUDONYM_SECRET}:{role}:"
    k = col.kind

    if rule == "pseudonym":
        expr = _pseudonym(c, salt)
    elif rule == "fake":
        if k == "first_name":
            expr = _pick(FIRST_NAMES, c, salt)
        elif k == "last_name":
            expr = _pick(LAST_NAMES, c, salt)
        elif k == "full_name":
            expr = f"{_pick(FIRST_NAMES, c, salt + 'f')} || ' ' || {_pick(LAST_NAMES, c, salt + 'l')}"
        else:
            expr = _pseudonym(c, salt)
    elif rule == "generalize":
        expr = {
            "dob": AGE_BAND,
            "date": "strftime({c}, '%Y-%m')",
            "datetime": "strftime({c}, '%Y-%m')",
            "geo": "round({c}, 2)",
            "money": "CAST(round({c} / 1000.0) * 1000 AS INTEGER)",
            "number": "round({c}, 0)",
            "address": r"regexp_replace({c}, '^[0-9]+\s+', '')",
            "ip": r"regexp_replace({c}, '\.[0-9]+\.[0-9]+$', '.0.0/16')",
            "category": "{c}",
            "bool": "{c}",
        }.get(k, "'[generalized]'").format(c=c)
    elif rule == "mask":
        expr = {
            "national_id": TAIL4, "ssn": TAIL4, "card": TAIL4, "plate": TAIL4, "phone": TAIL4,
            "email": "left({c}, 1) || '•••@' || split_part({c}, '@', 2)",
            "first_name": "left({c}, 1) || '.'",
            "last_name": "left({c}, 1) || '.'",
            "full_name": "left({c}, 1) || '.'",
            "address": "regexp_replace({c}, '[0-9]+', '##', 'g')",
            "ip": r"regexp_replace({c}, '\.[0-9]+$', '.•••')",
            "id": "left({c}, 4) || '•••' || right({c}, 2)",
            "ref": "left({c}, 4) || '•••' || right({c}, 2)",
            "dob": "CAST(year({c}) AS VARCHAR)",
            "date": "CAST(year({c}) AS VARCHAR)",
            "datetime": "CAST(year({c}) AS VARCHAR)",
            "geo": "round({c}, 2)",
            "money": "CAST(round({c} / 1000.0) * 1000 AS INTEGER)",
            "number": "round({c}, 0)",
        }.get(k, "'[masked]'").format(c=c)
    else:
        raise ValueError(f"Unknown transform {rule!r}")
    return f"CASE WHEN {c} IS NULL THEN NULL ELSE {expr} END"


EXPLAIN = {
    ("mask", "national_id"): "last 4 digits kept",
    ("mask", "ssn"): "last 4 digits kept",
    ("mask", "phone"): "last 4 digits kept",
    ("mask", "card"): "last 4 digits kept",
    ("mask", "plate"): "last 4 characters kept",
    ("mask", "email"): "initial and domain kept",
    ("mask", "first_name"): "initial only",
    ("mask", "last_name"): "initial only",
    ("mask", "full_name"): "initial only",
    ("mask", "address"): "house numbers hidden",
    ("mask", "ip"): "last octet hidden",
    ("generalize", "dob"): "10-year age band",
    ("generalize", "date"): "month only",
    ("generalize", "datetime"): "month only",
    ("generalize", "geo"): "rounded to ~1 km",
    ("generalize", "money"): "rounded to nearest 1,000",
    ("generalize", "address"): "street name only",
    ("generalize", "ip"): "/16 network only",
    ("fake", "first_name"): "pseudorandom stand-in name",
    ("fake", "last_name"): "pseudorandom stand-in name",
    ("fake", "full_name"): "pseudorandom stand-in name",
    ("pseudonym", None): "keyed SHA-256, stable within your role",
    ("clear", None): "as stored",
    ("redact", None): "removed",
}


def explain(rule: str, kind: str) -> str:
    return EXPLAIN.get((rule, kind)) or EXPLAIN.get((rule, None)) or rule


@dataclass
class ColumnView:
    name: str
    type: str
    kind: str
    description: str
    pii: bool
    rule: str
    effect: str


def get_policy(role_slug: str, slug: str) -> Policy:
    if slug not in BY_SLUG:
        raise BadQuery(f"Unknown dataset '{slug}'.")
    policy = Policy.objects.filter(role_id=role_slug, dataset_id=slug).first()
    if policy is None:
        # Deny by default: a dataset with no grid cell for this role is invisible.
        policy = Policy(role_id=role_slug, dataset_id=slug, mode=Policy.Mode.DENY,
                        rationale="No policy defined for this role (deny by default).")
    return policy


def describe_columns(ds: Dataset, policy: Policy) -> list[ColumnView]:
    out = []
    for col in ds.columns:
        rule = policy.column_rules.get(col.name, "redact") if policy.mode == "row" else "redact"
        out.append(ColumnView(col.name, col.type, col.kind, col.description, col.pii, rule, explain(rule, col.kind)))
    return out


def compile_view(ds: Dataset, policy: Policy) -> tuple[str, list[str]]:
    """SELECT statement exposing ``ds`` through ``policy``, and its visible columns."""
    parts, visible = [], []
    for col in ds.columns:
        expr = column_expr(col, policy.column_rules.get(col.name, "redact"), policy.role_id)
        if expr is not None:
            parts.append(f"{expr} AS {ident(col.name)}")
            visible.append(col.name)
    if not parts:
        raise AccessDenied("Every column of this dataset is redacted for your role.")
    return f"SELECT {', '.join(parts)} FROM {parquet(ds)}", visible


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    con.execute("SET threads = 2; SET memory_limit = '512MB'")
    return con


def _jsonable(rows):
    return [list(r) for r in rows]


# ── record-level query ──────────────────────────────────────

OPS = {
    "eq": "{c} = ?", "neq": "{c} <> ?", "lt": "{c} < ?", "lte": "{c} <= ?", "gt": "{c} > ?",
    "gte": "{c} >= ?", "contains": "CAST({c} AS VARCHAR) ILIKE ?", "is_null": "{c} IS NULL",
    "not_null": "{c} IS NOT NULL",
}


def query_rows(role: str, slug: str, spec: dict) -> dict:
    ds = BY_SLUG.get(slug)
    policy = get_policy(role, slug)
    if policy.mode != "row":
        raise AccessDenied(f"{ds.title}: {policy.get_mode_display().lower()} for your role. {policy.rationale}")
    view, visible = compile_view(ds, policy)
    con = connect()
    types = {name: typ for name, typ, *_ in con.execute(f"DESCRIBE SELECT * FROM ({view}) v LIMIT 0").fetchall()}

    columns = spec.get("columns") or visible
    hidden = [c for c in columns if c not in visible]
    if hidden:
        raise AccessDenied(f"Columns not visible to your role: {', '.join(hidden)}")

    where, params = [], []
    for f in spec.get("filters") or []:
        col, op = f.get("column"), f.get("op", "eq")
        if col not in visible:
            raise AccessDenied(f"Cannot filter on '{col}': not visible to your role.")
        if op not in OPS:
            raise BadQuery(f"Unsupported operator '{op}'.")
        clause = OPS[op].format(c=ident(col))
        if "?" in clause:
            if op == "contains":
                params.append(f"%{f.get('value', '')}%")
            else:
                clause = clause.replace("?", f"CAST(? AS {types[col]})")
                params.append(str(f.get("value")))
        where.append(clause)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    order = spec.get("order_by")
    order_sql = ""
    if order:
        if order not in visible:
            raise AccessDenied(f"Cannot sort on '{order}'.")
        order_sql = f"ORDER BY {ident(order)} {'DESC' if spec.get('desc') else 'ASC'} NULLS LAST"

    limit = max(1, min(int(spec.get("limit") or 50), policy.max_rows))
    offset = max(0, int(spec.get("offset") or 0))
    select = ", ".join(ident(c) for c in columns)
    try:
        total = con.execute(f"SELECT count(*) FROM ({view}) v {where_sql}", params).fetchone()[0]
        rows = con.execute(
            f"SELECT {select} FROM ({view}) v {where_sql} {order_sql} LIMIT {limit} OFFSET {offset}", params
        ).fetchall()
    except duckdb.Error as exc:
        raise BadQuery(str(exc).split("\n")[0]) from exc
    return {
        "columns": columns,
        "types": [types[c] for c in columns],
        "rows": _jsonable(rows),
        "total": total,
        "limit": limit,
        "offset": offset,
        "max_rows": policy.max_rows,
        "transforms": {c: policy.column_rules.get(c) for c in columns},
    }


# ── aggregate query ─────────────────────────────────────────

AGG_FNS = {"avg", "min", "max", "sum", "median", "stddev"}


def allowed_dimensions(ds: Dataset, policy: Policy) -> list[str]:
    return list(policy.group_by) or list(ds.dimensions)


def allowed_measures(ds: Dataset, policy: Policy) -> list[str]:
    return list(policy.metrics) or list(ds.measures)


def query_aggregate(role: str, slug: str, spec: dict) -> dict:
    ds = BY_SLUG.get(slug)
    policy = get_policy(role, slug)
    if policy.mode == "deny":
        raise AccessDenied(f"{ds.title}: denied for your role. {policy.rationale}")
    dims_ok, measures_ok = allowed_dimensions(ds, policy), allowed_measures(ds, policy)

    group_by = spec.get("group_by") or []
    if not 1 <= len(group_by) <= 3:
        raise BadQuery("Choose between one and three dimensions.")
    bad = [d for d in group_by if d not in dims_ok]
    if bad:
        raise AccessDenied(f"Dimensions not allowed for your role: {', '.join(bad)}")

    metric_sql, metric_names = [], []
    for m in (spec.get("metrics") or [])[:4]:
        fn, measure = m.get("fn"), m.get("measure")
        if fn not in AGG_FNS:
            raise BadQuery(f"Unsupported function '{fn}'.")
        if measure not in measures_ok:
            raise AccessDenied(f"Measure '{measure}' not allowed for your role.")
        name = f"{fn}_{measure}"
        metric_sql.append(f"round({fn}({ds.measures[measure]}), 2) AS {ident(name)}")
        metric_names.append(name)

    k = max(1, policy.min_group_size)
    dims_sql = ", ".join(f"{ds.dimensions[d]} AS {ident(d)}" for d in group_by)
    cols_sql = ", ".join([dims_sql, "count(*) AS n", *metric_sql])
    base = f"WITH g AS (SELECT {cols_sql} FROM {parquet(ds)} GROUP BY ALL)"
    con = connect()
    try:
        rows = con.execute(f"{base} SELECT * FROM g WHERE n >= {k} ORDER BY n DESC LIMIT 500").fetchall()
        suppressed_groups, suppressed_rows = con.execute(
            f"{base} SELECT count(*), coalesce(sum(n), 0) FROM g WHERE n < {k}"
        ).fetchone()
    except duckdb.Error as exc:
        raise BadQuery(str(exc).split("\n")[0]) from exc
    return {
        "columns": [*group_by, "n", *metric_names],
        "rows": _jsonable(rows),
        "min_group_size": k,
        "suppressed_groups": suppressed_groups,
        "suppressed_rows": int(suppressed_rows),
    }


# ── SQL workbench ───────────────────────────────────────────


def sql_tables(role: str) -> list[dict]:
    out = []
    for policy in Policy.objects.filter(role_id=role, mode="row", cross_analyze=True).select_related("dataset"):
        ds = BY_SLUG.get(policy.dataset_id)
        if not ds:
            continue
        cols = [asdict(c) for c in describe_columns(ds, policy) if c.rule != "redact"]
        out.append({"name": ds.slug, "title": ds.title, "columns": cols})
    return out


def run_sql(role: str, sql: str) -> dict:
    """Run one read-only SELECT against this role's views only.

    The role's views are materialised into an in-memory database, then external
    access is switched off and the configuration locked, so the statement can
    reach neither the raw Parquet files nor the filesystem nor extensions.
    """
    sql = (sql or "").strip().rstrip(";")
    if not sql:
        raise BadQuery("Empty query.")
    if len(sql) > 10_000:
        raise BadQuery("Query too long.")

    con = connect()
    try:
        statements = con.extract_statements(sql)
    except duckdb.Error as exc:
        raise BadQuery(str(exc).split("\n")[0]) from exc
    if len(statements) != 1 or statements[0].type != duckdb.StatementType.SELECT:
        raise AccessDenied("Only a single read-only SELECT statement is allowed.")

    usable = {
        p.dataset_id: p
        for p in Policy.objects.filter(role_id=role, mode="row", cross_analyze=True)
    }
    loaded = []
    for slug, policy in usable.items():
        if re.search(rf"\b{re.escape(slug)}\b", sql, re.IGNORECASE):
            view, _ = compile_view(BY_SLUG[slug], policy)
            con.execute(f"CREATE TABLE {ident(slug)} AS {view}")
            loaded.append(slug)
    con.execute("SET autoinstall_known_extensions = false")
    con.execute("SET autoload_known_extensions = false")
    con.execute("SET enable_external_access = false")
    con.execute("SET lock_configuration = true")

    timer = threading.Timer(settings.SQL_TIMEOUT_SECONDS, con.interrupt)
    started = time.monotonic()
    timer.start()
    try:
        cur = con.execute(sql)
        names = [d[0] for d in cur.description]
        types = [str(d[1]) for d in cur.description]
        rows = cur.fetchmany(settings.SQL_MAX_ROWS + 1)
    except duckdb.CatalogException as exc:
        missing = re.search(r"Table with name (\w+) does not exist", str(exc))
        if missing and missing.group(1).lower() in BY_SLUG:
            name = missing.group(1).lower()
            policy = get_policy(role, name)
            reason = policy.rationale if policy.mode != "row" else "not enabled for cross-analysis."
            raise AccessDenied(
                f"'{name}' is not available to your role in the workbench "
                f"({policy.get_mode_display().lower()}): {reason}"
            ) from exc
        raise BadQuery(str(exc).split("\n")[0]) from exc
    except duckdb.InterruptException as exc:
        raise BadQuery(f"Query exceeded {settings.SQL_TIMEOUT_SECONDS:.0f}s and was cancelled.") from exc
    except duckdb.Error as exc:
        raise BadQuery(str(exc).split("\n")[0]) from exc
    finally:
        timer.cancel()

    truncated = len(rows) > settings.SQL_MAX_ROWS
    return {
        "columns": names,
        "types": types,
        "rows": _jsonable(rows[: settings.SQL_MAX_ROWS]),
        "truncated": truncated,
        "tables_used": loaded,
        "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
    }


def dataset_row_count(ds: Dataset) -> int | None:
    path = settings.LAKE_DIR / ds.filename
    if not path.exists():
        return None
    return connect().execute(f"SELECT count(*) FROM {parquet(ds)}").fetchone()[0]
