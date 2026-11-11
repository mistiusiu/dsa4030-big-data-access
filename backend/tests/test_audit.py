from rest_framework.test import APIClient

from apps.audit import detections
from apps.audit.models import AuditLog


def test_everything_is_logged_and_scoped(as_role):
    medic = as_role("medic")
    medic.get("/api/lake/datasets/")
    as_role("officer").get("/api/lake/datasets/")
    own = medic.get("/api/audit/logs/").json()
    assert own["scope"] == "own" and {e["username"] for e in own["results"]} == {"medic"}
    everyone = as_role("admin").get("/api/audit/logs/").json()
    assert {"medic", "officer"} <= {e["username"] for e in everyone["results"]}
    assert medic.get("/api/audit/detections/").status_code == 403


def test_brute_force_and_forgery_are_detected(as_role):
    anon = APIClient()
    for _ in range(6):
        anon.post("/api/auth/token/", {"username": "admin", "password": "guess"}, format="json")
    anon.credentials(HTTP_AUTHORIZATION="Bearer aaa.bbb.ccc")
    anon.get("/api/auth/me/")
    rules = {f["rule"] for f in detections.run(60)}
    assert {"brute_force_account", "token_forgery"} <= rules
    assert AuditLog.objects.filter(outcome="login_failed").count() == 6


def test_privilege_probing_detected(as_role):
    medic = as_role("medic")
    for slug in ["felonies", "infractions", "vehicle_tracking", "transit_trips", "egov_logs"]:
        medic.post(f"/api/lake/datasets/{slug}/query/", {}, format="json")
    findings = [f for f in detections.run(60) if f["rule"] == "privilege_probing"]
    assert findings and findings[0]["subject"] == "medic"


def test_export_is_ndjson(as_role):
    as_role("medic").get("/api/lake/datasets/")
    resp = as_role("admin").get("/api/audit/export/")
    body = b"".join(resp.streaming_content).decode()
    assert resp["Content-Type"] == "application/x-ndjson" and '"event.outcome"' in body
