import pytest
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.lake.generator import generate


@pytest.fixture(scope="session")
def lake_dir(tmp_path_factory):
    path = tmp_path_factory.mktemp("lake")
    generate(path, seed=7, scale=0.1)
    return path


@pytest.fixture(autouse=True)
def lab(db, settings, lake_dir, tmp_path):
    settings.LAKE_DIR = lake_dir
    settings.AUDIT_LOG_FILE = tmp_path / "audit.jsonl"
    call_command("seed_lab", verbosity=0)
    cache.clear()  # login throttle state


def login(username, password="SmartCity@4030"):
    resp = APIClient().post("/api/auth/token/", {"username": username, "password": password}, format="json")
    assert resp.status_code == 200, resp.content
    return resp.json()


@pytest.fixture
def as_role():
    def make(username):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {login(username)['access']}")
        return client

    return make
