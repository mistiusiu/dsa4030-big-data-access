from dataclasses import asdict
from functools import lru_cache

from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import capabilities as cap
from apps.accounts.permissions import require
from apps.audit.context import note
from apps.grid.models import Policy

from . import engine
from .catalog import BY_SLUG, DATASETS


@lru_cache(maxsize=None)
def row_count(slug: str) -> int | None:
    return engine.dataset_row_count(BY_SLUG[slug])


def run(request, fn, *args, action: str, dataset: str = ""):
    """Execute an engine call, translating its errors to HTTP and auditing the result."""
    note(request, action=action, dataset=dataset)
    try:
        result = fn(*args)
    except engine.AccessDenied as exc:
        note(request, denial=str(exc))
        raise PermissionDenied(str(exc)) from exc
    except engine.BadQuery as exc:
        raise ValidationError({"detail": str(exc)}) from exc
    note(request, rows=len(result["rows"]), columns=result["columns"][:40])
    return Response(result)


def policy_summary(ds, policy: Policy) -> dict:
    return {
        "mode": policy.mode,
        "rationale": policy.rationale,
        "cross_analyze": policy.cross_analyze and policy.mode == "row",
        "max_rows": policy.max_rows,
        "min_group_size": policy.min_group_size,
        "dimensions": engine.allowed_dimensions(ds, policy) if policy.mode != "deny" else [],
        "measures": engine.allowed_measures(ds, policy) if policy.mode != "deny" else [],
    }


class DatasetListView(APIView):
    def get(self, request):
        role = request.user.role_id
        policies = {p.dataset_id: p for p in Policy.objects.filter(role_id=role)}
        out = []
        for ds in DATASETS:
            policy = policies.get(ds.slug) or engine.get_policy(role, ds.slug)
            out.append({
                "slug": ds.slug, "title": ds.title, "domain": ds.domain, "icon": ds.icon,
                "description": ds.description, "rows": row_count(ds.slug), "columns": len(ds.columns),
                **policy_summary(ds, policy),
            })
        note(request, action="lake.catalog")
        return Response(out)


class DatasetDetailView(APIView):
    def get(self, request, slug):
        ds = BY_SLUG.get(slug)
        if not ds:
            raise NotFound("Unknown dataset.")
        policy = engine.get_policy(request.user.role_id, slug)
        note(request, action="lake.schema", dataset=slug)
        return Response({
            "slug": ds.slug, "title": ds.title, "domain": ds.domain, "icon": ds.icon,
            "description": ds.description, "rows": row_count(slug),
            "schema": [asdict(c) for c in engine.describe_columns(ds, policy)],
            **policy_summary(ds, policy),
        })


class QueryView(APIView):
    permission_classes = [require(cap.BROWSE)]

    def post(self, request, slug):
        note(request, spec={k: request.data.get(k) for k in ("columns", "filters", "order_by", "limit", "offset")})
        return run(request, engine.query_rows, request.user.role_id, slug, request.data,
                   action="lake.query", dataset=slug)


class AggregateView(APIView):
    permission_classes = [require(cap.AGGREGATE)]

    def post(self, request, slug):
        note(request, spec={k: request.data.get(k) for k in ("group_by", "metrics")})
        return run(request, engine.query_aggregate, request.user.role_id, slug, request.data,
                   action="lake.aggregate", dataset=slug)


class SQLTablesView(APIView):
    permission_classes = [require(cap.SQL)]

    def get(self, request):
        note(request, action="lake.sql_tables")
        return Response(engine.sql_tables(request.user.role_id))


class SQLView(APIView):
    permission_classes = [require(cap.SQL)]

    def post(self, request):
        sql = str(request.data.get("sql", ""))
        note(request, sql=sql[:2000])
        response = run(request, engine.run_sql, request.user.role_id, sql, action="lake.sql")
        note(request, tables=response.data.get("tables_used"))
        return response
