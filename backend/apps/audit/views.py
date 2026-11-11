import json
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncMinute
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import capabilities as cap
from apps.accounts.permissions import require

from . import detections
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        exclude = ["user"]


def scoped(request):
    """Everyone may read their own trail; only audit.view_all sees everybody's."""
    qs = AuditLog.objects.all()
    if not request.user.can(cap.AUDIT_ALL):
        qs = qs.filter(username=request.user.username)
    return qs


class LogListView(APIView):
    permission_classes = [require(cap.AUDIT_OWN)]

    def get(self, request):
        qs = scoped(request)
        p = request.query_params
        for field in ("outcome", "role", "dataset", "username", "method"):
            if p.get(field):
                qs = qs.filter(**{field: p[field]})
        if p.get("q"):
            qs = qs.filter(path__icontains=p["q"])
        if p.get("ip"):
            qs = qs.filter(ip=p["ip"])
        total = qs.count()
        limit = min(int(p.get("limit", 50)), 200)
        offset = int(p.get("offset", 0))
        rows = AuditLogSerializer(qs[offset : offset + limit], many=True).data
        return Response({"total": total, "limit": limit, "offset": offset, "results": rows,
                         "scope": "all" if request.user.can(cap.AUDIT_ALL) else "own"})


class StatsView(APIView):
    permission_classes = [require(cap.AUDIT_OWN)]

    def get(self, request):
        minutes = min(int(request.query_params.get("minutes", 60)), 24 * 60)
        since = timezone.now() - timedelta(minutes=minutes)
        qs = scoped(request).filter(timestamp__gte=since)
        by_outcome = dict(qs.values_list("outcome").annotate(n=Count("id")).values_list("outcome", "n"))
        by_role = list(qs.exclude(role="").values("role").annotate(n=Count("id")).order_by("-n"))
        timeline = (
            qs.annotate(t=TruncMinute("timestamp"))
            .values("t", "outcome")
            .annotate(n=Count("id"))
            .order_by("t")
        )
        return Response({"minutes": minutes, "total": qs.count(), "by_outcome": by_outcome,
                         "by_role": by_role, "timeline": list(timeline)})


class DetectionsView(APIView):
    permission_classes = [require(cap.AUDIT_ALL)]

    def get(self, request):
        minutes = min(int(request.query_params.get("minutes", 60)), 7 * 24 * 60)
        return Response({"minutes": minutes, "findings": detections.run(minutes),
                         "rules": [{k: r[k] for k in ("id", "title", "mitre", "medium", "high", "explain")}
                                   for r in detections.RULES]})


class ExportView(APIView):
    """NDJSON stream of audit events, ready for a SIEM forwarder."""

    permission_classes = [require(cap.AUDIT_ALL)]

    def get(self, request):
        qs = AuditLog.objects.order_by("timestamp").iterator(chunk_size=500)
        stream = (json.dumps(e.as_event(), default=str) + "\n" for e in qs)
        response = StreamingHttpResponse(stream, content_type="application/x-ndjson")
        response["Content-Disposition"] = 'attachment; filename="audit.ndjson"'
        return response
