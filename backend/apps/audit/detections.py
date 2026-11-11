"""Toy SIEM correlation rules over the audit log.

Each rule groups recent events by a subject (account or source IP) and fires
when a count crosses a threshold. Real deployments ship the NDJSON export to a
SIEM (Wazuh, Elastic, Splunk) and run equivalent rules there.
"""

from datetime import timedelta

from django.db.models import Count, IntegerField, Max, Min, Sum
from django.db.models.functions import Cast
from django.db.models.fields.json import KT
from django.utils import timezone

from .models import AuditLog

RULES = [
    {
        "id": "brute_force_account",
        "title": "Brute force against an account",
        "mitre": "T1110.001 Password Guessing",
        "filter": {"outcome": "login_failed"},
        "group": "username",
        "medium": 5,
        "high": 10,
        "explain": "Repeated failed logins for one username.",
    },
    {
        "id": "password_spray",
        "title": "Password spraying / credential stuffing from one source",
        "mitre": "T1110.003 Password Spraying",
        "filter": {"outcome": "login_failed"},
        "group": "ip",
        "distinct": "username",
        "medium": 3,
        "high": 6,
        "explain": "Failed logins for several different usernames from the same IP.",
    },
    {
        "id": "token_forgery",
        "title": "Forged or tampered JWT presented",
        "mitre": "T1606 Forge Web Credentials",
        "filter": {"outcome": "unauthenticated", "reason": "token_invalid"},
        "group": "ip",
        "medium": 1,
        "high": 3,
        "explain": "Tokens whose RS256 signature does not verify: someone edited a token.",
    },
    {
        "id": "privilege_probing",
        "title": "Privilege probing by an authenticated account",
        "mitre": "T1078 Valid Accounts",
        "filter": {"outcome": "denied"},
        "group": "username",
        "medium": 5,
        "high": 15,
        "explain": "A logged-in account repeatedly requesting data its role is denied — "
        "typical of a compromised account exploring what it can reach.",
    },
    {
        "id": "bulk_extraction",
        "title": "Unusually large data extraction",
        "mitre": "T1530 Data from Cloud Storage",
        "filter": {"outcome": "allowed"},
        "group": "username",
        "sum": "rows",
        "medium": 2000,
        "high": 10000,
        "explain": "High volume of records returned to one account.",
    },
    {
        "id": "throttling",
        "title": "Rate limit triggered",
        "mitre": "T1110 Brute Force",
        "filter": {"outcome": "throttled"},
        "group": "ip",
        "medium": 1,
        "high": 5,
        "explain": "Login throttle engaged for a source.",
    },
]


def run(minutes: int = 60) -> list[dict]:
    since = timezone.now() - timedelta(minutes=minutes)
    findings = []
    for rule in RULES:
        qs = AuditLog.objects.filter(timestamp__gte=since, outcome=rule["filter"]["outcome"])
        if "reason" in rule["filter"]:
            qs = qs.filter(detail__reason=rule["filter"]["reason"])
        # GenericIPAddressField turns "" into None, and `ip = NULL` never matches,
        # so blank-excluding the ip column would silently drop every row.
        if rule["group"] == "ip":
            qs = qs.exclude(ip__isnull=True)
        else:
            qs = qs.exclude(**{rule["group"]: ""})
        if "sum" in rule:
            qs = qs.filter(detail__has_key="rows")
            groups = qs.values(rule["group"]).annotate(
                value=Sum(Cast(KT("detail__rows"), IntegerField())), first=Min("timestamp"), last=Max("timestamp"), events=Count("id")
            )
        elif "distinct" in rule:
            groups = qs.values(rule["group"]).annotate(
                value=Count(rule["distinct"], distinct=True), first=Min("timestamp"), last=Max("timestamp"),
                events=Count("id"),
            )
        else:
            groups = qs.values(rule["group"]).annotate(
                value=Count("id"), first=Min("timestamp"), last=Max("timestamp"), events=Count("id")
            )
        for g in groups:
            value = int(g["value"] or 0)
            if value < rule["medium"]:
                continue
            findings.append({
                "rule": rule["id"],
                "title": rule["title"],
                "mitre": rule["mitre"],
                "severity": "high" if value >= rule["high"] else "medium",
                "subject_type": rule["group"],
                "subject": g[rule["group"]],
                "value": value,
                "events": g["events"],
                "first_seen": g["first"],
                "last_seen": g["last"],
                "explain": rule["explain"],
            })
    order = {"high": 0, "medium": 1}
    return sorted(findings, key=lambda f: (order[f["severity"]], -f["value"]))
