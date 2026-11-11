import re

from apps.audit.models import AuditLog
from apps.lake.catalog import BY_SLUG
from apps.lake.engine import connect, parquet
from apps.lake.generator import FIRST_NAMES


def rows(resp):
    body = resp.json()
    return [dict(zip(body["columns"], r)) for r in body["rows"]]


def test_medical_sees_identity_but_not_crime(as_role):
    medic = as_role("medic")
    people = rows(medic.post("/api/lake/datasets/citizens/query/", {"limit": 5}, format="json"))
    assert people and people[0]["citizen_id"].startswith("CIT-")
    assert "ssn" not in people[0] and "income_band" not in people[0]
    assert re.fullmatch(r"•+\d{4}", people[0]["national_id"])

    denied = medic.post("/api/lake/datasets/felonies/query/", {}, format="json")
    assert denied.status_code == 403
    assert AuditLog.objects.filter(outcome="denied", dataset="felonies", username="medic").exists()
    assert medic.post("/api/lake/datasets/amenities/aggregate/", {"group_by": ["district"]}, format="json").status_code == 403


def test_sociologist_sees_pseudonyms_and_fake_names(as_role):
    people = rows(as_role("sociologist").post("/api/lake/datasets/citizens/query/", {"limit": 20}, format="json"))
    for p in people:
        assert p["citizen_id"].startswith("PSN-") and p["national_id"].startswith("PSN-")
        assert p["first_name"] in FIRST_NAMES
        assert re.fullmatch(r"\d+–\d+", p["date_of_birth"])
        assert "phone" not in p and "email" not in p


def test_pseudonyms_differ_between_roles(as_role):
    soc = rows(as_role("sociologist").post("/api/lake/datasets/citizens/query/", {"limit": 3, "order_by": "sex"}, format="json"))
    adm = rows(as_role("admin").post("/api/lake/datasets/citizens/query/", {"limit": 3, "order_by": "sex"}, format="json"))
    assert {p["citizen_id"] for p in soc}.isdisjoint({p["citizen_id"] for p in adm})


def test_pseudonymous_joins_still_work(as_role):
    resp = as_role("sociologist").post("/api/lake/sql/", {"sql": (
        "SELECT a.income_band, b.income_band AS friend_band, count(*) n FROM relationships r "
        "JOIN citizens a ON a.citizen_id = r.citizen_a JOIN citizens b ON b.citizen_id = r.citizen_b GROUP BY ALL"
    )}, format="json")
    assert resp.status_code == 200, resp.content
    assert sum(r[2] for r in resp.json()["rows"]) > 0


def test_policy_maker_feedback_is_deidentified(as_role):
    fb = as_role("policymaker").post("/api/lake/datasets/feedback/query/", {"limit": 5}, format="json").json()
    assert set(fb["columns"]) == {"feedback_id", "submitted_at", "topic", "message", "sentiment"}
    agg = as_role("policymaker").post("/api/lake/datasets/feedback/aggregate/", {"group_by": ["district"]}, format="json")
    assert agg.status_code == 403


def test_transport_gets_thin_citizen_slice(as_role):
    body = as_role("transport").post("/api/lake/datasets/citizens/query/", {"limit": 1}, format="json").json()
    assert set(body["columns"]) == {"citizen_id", "first_name", "last_name", "date_of_birth", "sex", "disability"}


def test_civil_engineer_aggregates_suppress_small_groups(as_role):
    eng = as_role("engineer")
    assert eng.post("/api/lake/datasets/citizens/query/", {}, format="json").status_code == 403
    resp = eng.post("/api/lake/datasets/citizens/aggregate/", {
        "group_by": ["district", "age_band", "disability"], "metrics": [{"fn": "avg", "measure": "age"}],
    }, format="json")
    assert resp.status_code == 200
    body = resp.json()
    assert body["min_group_size"] == 10
    assert all(r[body["columns"].index("n")] >= 10 for r in body["rows"])
    assert body["suppressed_groups"] > 0
    # occupation is a valid dimension in the catalog but not in this policy
    assert eng.post("/api/lake/datasets/citizens/aggregate/", {"group_by": ["occupation"]}, format="json").status_code == 403


def test_filtering_a_masked_column_cannot_probe_the_original(as_role):
    officer = as_role("officer")
    real_ssn = connect().execute(f"SELECT ssn FROM {parquet(BY_SLUG['citizens'])} LIMIT 1").fetchone()[0]
    resp = officer.post("/api/lake/datasets/citizens/query/", {
        "filters": [{"column": "ssn", "op": "eq", "value": real_ssn}],
    }, format="json")
    assert resp.status_code == 200 and resp.json()["total"] == 0


def test_capability_gates_sql(as_role):
    assert as_role("engineer").post("/api/lake/sql/", {"sql": "SELECT 1"}, format="json").status_code == 403
    assert as_role("policymaker").get("/api/lake/sql/tables/").status_code == 403


def test_sql_sandbox(as_role):
    medic = as_role("medic")
    ok = medic.post("/api/lake/sql/", {"sql": "SELECT count(*) FROM medical_records JOIN citizens USING (citizen_id)"}, format="json")
    assert ok.status_code == 200
    for sql, status in [
        ("SELECT * FROM felonies", 403),
        ("DROP TABLE citizens", 403),
        ("SELECT 1; SELECT 2", 403),
        ("SELECT * FROM read_parquet('/etc/passwd')", 400),
        ("COPY (SELECT 1) TO '/tmp/x.csv'", 403),
        ("SELECT * FROM read_csv_auto('/etc/hostname')", 400),
    ]:
        resp = medic.post("/api/lake/sql/", {"sql": sql}, format="json")
        assert resp.status_code == status, (sql, resp.content)


def test_grid_detail_requires_capability(as_role):
    assert as_role("medic").get("/api/grid/policies/medical/").status_code == 200
    assert as_role("medic").get("/api/grid/policies/law_enforcement/").status_code == 403
    assert as_role("admin").get("/api/grid/policies/law_enforcement/").status_code == 200
