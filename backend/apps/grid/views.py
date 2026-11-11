from dataclasses import asdict

from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import capabilities as cap
from apps.accounts.models import Role
from apps.accounts.serializers import RoleSerializer
from apps.audit.context import note
from apps.lake import engine
from apps.lake.catalog import BY_SLUG, DATASETS

from .models import TRANSFORMS, Policy


class GridView(APIView):
    """The whole matrix at a glance: which role sees which dataset, and how."""

    def get(self, request):
        cells = {}
        for p in Policy.objects.all():
            cells.setdefault(p.role_id, {})[p.dataset_id] = {
                "mode": p.mode, "cross_analyze": p.cross_analyze, "k": p.min_group_size,
                "rules": sorted(set(p.column_rules.values())) if p.mode == "row" else [],
            }
        note(request, action="grid.matrix")
        return Response({
            "roles": RoleSerializer(Role.objects.all(), many=True).data,
            "datasets": [{"slug": d.slug, "title": d.title, "domain": d.domain, "icon": d.icon} for d in DATASETS],
            "cells": cells,
            "transforms": TRANSFORMS,
            "capabilities": cap.ALL,
        })


class RolePolicyView(APIView):
    """Column-level rules for one role. Own role always; others need grid.view_all."""

    def get(self, request, role):
        if role != request.user.role_id and not request.user.can(cap.GRID_ALL):
            note(request, action="grid.policy", denial=f"tried to read {role}")
            raise PermissionDenied("You can only inspect your own role's column rules.")
        if not Role.objects.filter(slug=role).exists():
            raise NotFound("Unknown role.")
        out = []
        for ds in DATASETS:
            policy = engine.get_policy(role, ds.slug)
            out.append({
                "dataset": ds.slug, "title": ds.title, "mode": policy.mode, "rationale": policy.rationale,
                "min_group_size": policy.min_group_size, "cross_analyze": policy.cross_analyze,
                "columns": [asdict(c) for c in engine.describe_columns(BY_SLUG[ds.slug], policy)],
            })
        note(request, action="grid.policy", role_inspected=role)
        return Response(out)
