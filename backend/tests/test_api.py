"""API tests (US-311) using the in-memory repository and fake "dev" tokens.

These prove the endpoints, validation, error format and access checks. They do
NOT talk to Firebase; the Firestore path is checked with the emulator (see README).
"""

import threading

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.lifecycle import Actor, Status
from app.main import create_app
from app.repository import InMemoryRepository

BORROWER = {"Authorization": "Bearer dev:borrower-aoife:borrower"}
OTHER_BORROWER = {"Authorization": "Bearer dev:borrower-sean:borrower"}
BROKER = {"Authorization": "Bearer dev:broker-ciaran:broker"}
OTHER_BROKER = {"Authorization": "Bearer dev:broker-x:broker"}
UNDERWRITER = {"Authorization": "Bearer dev:uw-rachel:underwriter"}

PROPERTY = {"county": "Cork", "floorAreaM2": 110, "bedrooms": 3,
            "propertyType": "semi_detached", "ber": "B2"}
APPLICATION = {
    "buyerType": "first_time",
    "financials": {"grossAnnualIncome": 95000, "monthlyDebts": 300, "deposit": 60000,
                   "loanAmount": 335000, "termYears": 30},
    "property": {**PROPERTY, "askingPrice": 395000},
}


@pytest.fixture
def repo():
    return InMemoryRepository()


@pytest.fixture
def client(repo):
    settings = Settings(repository="memory", auth_mode="dev",
                        default_broker_uid="broker-ciaran")
    return TestClient(create_app(settings, repo))


def submit(client, headers=BORROWER, body=APPLICATION):
    return client.post("/applications", json=body, headers=headers)


# ---------- health and auth ----------

def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_missing_token_is_401_in_standard_format(client):
    r = client.post("/applications", json=APPLICATION)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"


def test_token_cannot_claim_system_role(client):
    r = submit(client, headers={"Authorization": "Bearer dev:evil:system"})
    assert r.status_code == 401


# ---------- valuations ----------

def test_valuation_returns_stub_flag(client):
    r = client.post("/valuations", json=PROPERTY, headers=BORROWER)
    assert r.status_code == 201
    body = r.json()
    assert body["isStub"] is True and body["valuationId"]


@pytest.mark.parametrize("field,value", [("county", "Atlantis"), ("ber", "Z9"),
                                         ("floorAreaM2", 0), ("bedrooms", -1)])
def test_valuation_rejects_invalid_input(client, field, value):
    r = client.post("/valuations", json={**PROPERTY, field: value}, headers=BORROWER)
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "validation_error"
    assert any(d["field"] == field for d in err["details"])


# ---------- applications ----------

def test_submit_creates_applied_application(client):
    r = submit(client)
    assert r.status_code == 201
    app = r.json()
    assert app["reference"] == app["id"] and app["id"].startswith("AL-")
    assert app["status"] == "applied" and app["statusLabel"] == "Applied"
    assert app["borrowerId"] == "borrower-aoife"
    assert app["brokerId"] == "broker-ciaran"
    assert app["statusHistory"][0]["status"] == "applied"
    assert app["metrics"] is None  # filled by US-410 later, never by Core


def test_references_are_sequential(client):
    a, b = submit(client).json()["id"], submit(client).json()["id"]
    assert int(b[-4:]) == int(a[-4:]) + 1


def test_submit_with_valuation_copies_estimate(client):
    vid = client.post("/valuations", json=PROPERTY, headers=BORROWER).json()["valuationId"]
    app = submit(client, body={**APPLICATION, "valuationId": vid}).json()
    assert app["valuation"]["valuationId"] == vid
    assert app["valuation"]["estimate"] == 380000


def test_cannot_use_someone_elses_valuation(client):
    vid = client.post("/valuations", json=PROPERTY, headers=OTHER_BORROWER).json()["valuationId"]
    r = submit(client, body={**APPLICATION, "valuationId": vid})
    assert r.status_code == 400


@pytest.mark.parametrize("headers", [BROKER, UNDERWRITER])
def test_only_borrowers_submit(client, headers):
    assert submit(client, headers=headers).status_code == 403


@pytest.mark.parametrize("path,value", [(("financials", "termYears"), 40),
                                        (("financials", "deposit"), -1),
                                        (("financials", "loanAmount"), 0),
                                        (("property", "askingPrice"), 0)])
def test_submit_validation(client, path, value):
    body = {**APPLICATION, path[0]: {**APPLICATION[path[0]], path[1]: value}}
    r = submit(client, body=body)
    assert r.status_code == 422


def test_unknown_fields_rejected(client):
    r = submit(client, body={**APPLICATION, "status": "funded"})
    assert r.status_code == 422


# ---------- read access mirrors the security rules ----------

@pytest.mark.parametrize("headers,visible", [
    (BORROWER, True), (OTHER_BORROWER, False),
    (BROKER, True), (OTHER_BROKER, False), (UNDERWRITER, True),
])
def test_read_access(client, headers, visible):
    app_id = submit(client).json()["id"]
    r = client.get(f"/applications/{app_id}", headers=headers)
    assert r.status_code == (200 if visible else 404)


# ---------- status changes through the state machine ----------

def test_full_happy_path(client, repo):
    from datetime import UTC, datetime
    app_id = submit(client).json()["id"]
    # applied -> ai_deliberated is a SYSTEM move (US-313, Sprint 2); simulate it directly.
    repo.change_status(app_id, Status.AI_DELIBERATED, Actor.SYSTEM, "system", None,
                       datetime.now(UTC))
    r = client.post(f"/applications/{app_id}/status",
                    json={"to": "underwriter_approved"}, headers=UNDERWRITER)
    assert r.status_code == 200 and r.json()["status"] == "underwriter_approved"
    assert [h["status"] for h in r.json()["statusHistory"]] == [
        "applied", "ai_deliberated", "underwriter_approved"]


def test_skipping_a_stage_is_409(client):
    app_id = submit(client).json()["id"]
    r = client.post(f"/applications/{app_id}/status", json={"to": "funded"},
                    headers=UNDERWRITER)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "invalid_transition"


def test_broker_cannot_decide(client, repo):
    from datetime import UTC, datetime
    app_id = submit(client).json()["id"]
    repo.change_status(app_id, Status.AI_DELIBERATED, Actor.SYSTEM, "system", None,
                       datetime.now(UTC))
    r = client.post(f"/applications/{app_id}/status", json={"to": "declined", "reason": "x"},
                    headers=BROKER)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "actor_not_allowed"


def test_decline_without_reason_is_422(client, repo):
    from datetime import UTC, datetime
    app_id = submit(client).json()["id"]
    repo.change_status(app_id, Status.AI_DELIBERATED, Actor.SYSTEM, "system", None,
                       datetime.now(UTC))
    r = client.post(f"/applications/{app_id}/status", json={"to": "declined"},
                    headers=UNDERWRITER)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "reason_required"


def test_unknown_application_is_404(client):
    r = client.post("/applications/AL-2026-9999/status", json={"to": "funded"},
                    headers=UNDERWRITER)
    assert r.status_code == 404


def test_concurrent_decisions_only_one_wins(repo):
    """Two underwriters act at the same moment: exactly one change may succeed.
    The repository does check + write as one atomic step (a lock here, a
    transaction in Firestore)."""
    from datetime import UTC, datetime
    now = datetime.now(UTC)
    doc = repo.create_application({"borrowerId": "b"}, "b", now)
    repo.change_status(doc["id"], Status.AI_DELIBERATED, Actor.SYSTEM, "system", None, now)

    results: list[str] = []
    barrier = threading.Barrier(2)

    def decide(target, reason):
        barrier.wait()
        try:
            repo.change_status(doc["id"], target, Actor.UNDERWRITER, "uw", reason, now)
            results.append("ok")
        except Exception as exc:
            results.append(type(exc).__name__)

    threads = [threading.Thread(target=decide, args=(Status.UNDERWRITER_APPROVED, None)),
               threading.Thread(target=decide, args=(Status.DECLINED, "too risky"))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == ["InvalidTransition", "ok"]
