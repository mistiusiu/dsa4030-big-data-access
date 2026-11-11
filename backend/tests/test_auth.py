import json

from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from conftest import login


def b64(obj) -> str:
    import base64

    return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()


def unb64(part: str) -> dict:
    import base64

    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


def test_token_carries_role_and_is_rs256():
    data = login("medic")
    header = unb64(data["access"].split(".")[0])
    payload = unb64(data["access"].split(".")[1])
    assert header["alg"] == "RS256"
    assert payload["role"] == "medical"
    assert data["access_expires"] and data["refresh_expires"]


def test_tampered_payload_is_rejected_and_audited():
    h, p, s = login("medic")["access"].split(".")
    payload = unb64(p)
    payload["role"] = "administrator"
    forged = f"{h}.{b64(payload)}.{s}"
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {forged}")
    resp = client.get("/api/auth/me/")
    assert resp.status_code == 401
    entry = AuditLog.objects.filter(path="/api/auth/me/").latest("timestamp")
    assert entry.outcome == "unauthenticated"
    assert entry.detail["reason"] == "token_invalid"


def test_alg_none_is_rejected():
    _, p, _ = login("medic")["access"].split(".")
    forged = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{p}."
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {forged}")
    assert client.get("/api/auth/me/").status_code == 401


def test_role_change_invalidates_existing_tokens():
    access = login("medic")["access"]
    User.objects.filter(username="medic").update(role_id="law_enforcement")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert client.get("/api/auth/me/").status_code == 401


def test_refresh_rotation_blacklists_old_token():
    refresh = login("medic")["refresh"]
    client = APIClient()
    first = client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
    assert first.status_code == 200 and "access_expires" in first.json()
    assert client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json").status_code == 401


def test_superadmin_without_role_cannot_get_api_token(django_user_model):
    django_user_model.objects.create_superuser("root", "", "pw-123456789")
    resp = APIClient().post("/api/auth/token/", {"username": "root", "password": "pw-123456789"}, format="json")
    assert resp.status_code == 400


def test_failed_login_records_username_not_password():
    APIClient().post("/api/auth/token/", {"username": "medic", "password": "wrong-pass"}, format="json")
    entry = AuditLog.objects.latest("timestamp")
    assert entry.outcome == "login_failed" and entry.username == "medic"
    assert "wrong-pass" not in json.dumps(entry.as_event())
