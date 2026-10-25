"""API tests (US-311) using the in-memory repository and fake "dev" tokens.

These prove the endpoints, validation, error format and access checks. They do
NOT talk to Firebase; the Firestore path is checked with the emulator (see README).
"""

import threading

import pytest
from fastapi.testclient import TestClient

from app import integrations
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

def valuate(client, **changes):
    r = client.post("/valuations", json={**PROPERTY, **changes}, headers=BORROWER)
    assert r.status_code == 201
    return r.json()


def test_valuation_uses_the_model(client):
    body = valuate(client)
    assert body["isStub"] is False and body["valuationId"]
    assert body["modelVersion"] == "gbr-1"
    assert 0 < body["low"] < body["estimate"] < body["high"]


def test_valuation_depends_on_the_property(client):
    dublin, donegal = valuate(client, county="Dublin"), valuate(client, county="Donegal")
    assert dublin["estimate"] > donegal["estimate"]
    big, small = valuate(client, floorAreaM2=180), valuate(client, floorAreaM2=70)
    assert big["estimate"] > small["estimate"]


def test_valuation_falls_back_to_stub_without_model(client, monkeypatch):
    monkeypatch.setattr(integrations, "_load_model", lambda: None)
    body = valuate(client)
    assert body["isStub"] is True and body["estimate"] == 380000


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
    assert set(app["metrics"]) == {"lti", "ltv", "dti", "stressedDti",
                                   "monthlyRepayment", "checks"}


def test_references_are_sequential(client):
    a, b = submit(client).json()["id"], submit(client).json()["id"]
    assert int(b[-4:]) == int(a[-4:]) + 1


def test_submit_with_valuation_copies_estimate(client):
    valuation = valuate(client)
    vid = valuation["valuationId"]
    app = submit(client, body={**APPLICATION, "valuationId": vid}).json()
    assert app["valuation"]["valuationId"] == vid
    assert app["valuation"]["estimate"] == valuation["estimate"]


# ---------- metrics (US-410) ----------

def test_metrics_use_asking_price_without_valuation(client):
    m = submit(client).json()["metrics"]
    assert m["ltv"] == pytest.approx(335000 / 395000, abs=1e-4)
    assert m["lti"] == pytest.approx(335000 / 95000, abs=1e-2)
    assert m["monthlyRepayment"] > 0
    assert m["checks"]["ltvOk"] is True


def test_metrics_use_lower_of_price_and_valuation(client):
    valuation = valuate(client)
    body = {**APPLICATION, "valuationId": valuation["valuationId"]}
    m = submit(client, body=body).json()["metrics"]
    assert m["ltv"] == pytest.approx(335000 / min(395000, valuation["estimate"]), abs=1e-4)


def test_metrics_with_zero_income_fail_checks(client):
    body = {**APPLICATION, "financials": {**APPLICATION["financials"], "grossAnnualIncome": 0}}
    r = submit(client, body=body)
    assert r.status_code == 201
    m = r.json()["metrics"]
    assert m["lti"] is None and m["dti"] is None and m["stressedDti"] is None
    assert not m["checks"]["ltiOk"] and not m["checks"]["dtiOk"]


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
