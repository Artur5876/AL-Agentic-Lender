"""US-312: the sign-in token is verified on every request and the role is checked per endpoint.

Part 1 runs every endpoint through the same matrix with "dev" tokens:
no token -> 401, malformed token -> 401, wrong role -> 403, right role -> success.
Part 2 checks the real Firebase verification path ("firebase" mode): with the Admin SDK
call replaced (unit), and against the Auth emulator with real ID tokens (skipped unless
FIREBASE_AUTH_EMULATOR_HOST is set).
"""

import os

import pytest
from fastapi.testclient import TestClient

from app.chain import FakeChain
from app.config import Settings
from app.main import create_app
from app.repository import InMemoryRepository


def tok(uid, role):
    return {"Authorization": f"Bearer dev:{uid}:{role}"}


BORROWER = tok("borrower-aoife", "borrower")
BROKER = tok("broker-ciaran", "broker")
UNDERWRITER = tok("uw-rachel", "underwriter")

PROPERTY = {"county": "Cork", "floorAreaM2": 110, "bedrooms": 3,
            "propertyType": "semi_detached", "ber": "B2"}
APPLICATION = {
    "buyerType": "first_time",
    "financials": {"grossAnnualIncome": 95000, "monthlyDebts": 300, "deposit": 60000,
                   "loanAmount": 335000, "termYears": 30},
    "property": {**PROPERTY, "askingPrice": 395000},
}

MALFORMED = [
    pytest.param({"Authorization": "dev:borrower-aoife:borrower"}, id="no_bearer_prefix"),
    pytest.param({"Authorization": "Basic dXNlcjpwYXNz"}, id="basic_scheme"),
    pytest.param({"Authorization": "Bearer"}, id="bearer_without_token"),
    pytest.param({"Authorization": "Bearer "}, id="bearer_empty_token"),
    pytest.param({"Authorization": "Bearer not-a-token"}, id="garbage"),
    pytest.param({"Authorization": "Bearer dev:borrower-aoife"}, id="dev_missing_role"),
    pytest.param({"Authorization": "Bearer dev::borrower"}, id="dev_empty_uid"),
    pytest.param({"Authorization": "Bearer dev:a:b:c"}, id="dev_too_many_parts"),
    pytest.param({"Authorization": "Bearer dev:x:admin"}, id="unknown_role"),
    pytest.param({"Authorization": "Bearer dev:x:system"}, id="system_role_in_user_token"),
    pytest.param({"Authorization": "Bearer eyJhbGciOiJSUzI1NiJ9.e30.sig"}, id="jwt_in_dev_mode"),
]


@pytest.fixture
def client():
    settings = Settings(repository="memory", auth_mode="dev", default_broker_uid="broker-ciaran",
                        borrower_ref_salt="test-salt")
    return TestClient(create_app(settings, InMemoryRepository(), chain=FakeChain()))


@pytest.fixture
def app_id(client):
    """An application already moved to ai_deliberated by the (stub) committee."""
    r = client.post("/applications", json=APPLICATION, headers=BORROWER)
    assert r.status_code == 201
    return r.json()["id"]


# Every endpoint that needs a token: (method, path, json body). {id} = app_id fixture.
PROTECTED = [
    pytest.param("POST", "/valuations", PROPERTY, id="POST /valuations"),
    pytest.param("POST", "/applications", APPLICATION, id="POST /applications"),
    pytest.param("GET", "/applications/{id}", None, id="GET /applications/{id}"),
    pytest.param("POST", "/applications/{id}/status", {"to": "underwriter_approved"},
                 id="POST /applications/{id}/status"),
]


def call(client, method, path, body, app_id, headers=None):
    return client.request(method, path.format(id=app_id), json=body, headers=headers or {})


def assert_unauthenticated(r):
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"
    assert r.headers.get("www-authenticate") == "Bearer"


# ---------- 401: no token / malformed token, on every protected endpoint ----------

@pytest.mark.parametrize("method,path,body", PROTECTED)
def test_no_token_is_401(client, app_id, method, path, body):
    assert_unauthenticated(call(client, method, path, body, app_id))


@pytest.mark.parametrize("headers", MALFORMED)
@pytest.mark.parametrize("method,path,body", PROTECTED)
def test_malformed_token_is_401(client, app_id, method, path, body, headers):
    assert_unauthenticated(call(client, method, path, body, app_id, headers))


def test_401_happens_before_validation(client):
    """An unauthenticated caller learns nothing about the body format."""
    assert_unauthenticated(client.post("/applications", json={"junk": 1}))


def test_health_needs_no_token(client):
    assert client.get("/health").status_code == 200


# ---------- 403: wrong role ----------

@pytest.mark.parametrize("headers", [BROKER, UNDERWRITER], ids=["broker", "underwriter"])
def test_only_borrowers_submit_applications(client, headers):
    r = client.post("/applications", json=APPLICATION, headers=headers)
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize("headers", [BORROWER, BROKER], ids=["borrower", "broker"])
@pytest.mark.parametrize("to,reason", [("underwriter_approved", None),
                                       ("conditionally_approved", "x"), ("declined", "x")])
def test_only_underwriters_decide(client, app_id, headers, to, reason):
    """The owner borrower and the assigned broker can see the file but may not decide."""
    r = client.post(f"/applications/{app_id}/status", json={"to": to, "reason": reason},
                    headers=headers)
    assert r.status_code == 403 and r.json()["error"]["code"] == "actor_not_allowed"
    after = client.get(f"/applications/{app_id}", headers=UNDERWRITER).json()
    assert after["status"] == "ai_deliberated"


def test_borrower_cannot_mark_funded(client, app_id):
    client.post(f"/applications/{app_id}/status", json={"to": "underwriter_approved"},
                headers=UNDERWRITER)
    r = client.post(f"/applications/{app_id}/status", json={"to": "funded"}, headers=BORROWER)
    assert r.status_code == 403 and r.json()["error"]["code"] == "actor_not_allowed"


@pytest.mark.parametrize("headers", [tok("borrower-sean", "borrower"), tok("broker-x", "broker")],
                         ids=["other_borrower", "other_broker"])
def test_not_your_application_is_404_not_403(client, app_id, headers):
    """Read and status change both hide other people's files (IDs cannot be probed)."""
    assert client.get(f"/applications/{app_id}", headers=headers).status_code == 404
    r = client.post(f"/applications/{app_id}/status", json={"to": "declined", "reason": "x"},
                    headers=headers)
    assert r.status_code == 404


# ---------- right role -> success ----------

@pytest.mark.parametrize("headers", [BORROWER, BROKER, UNDERWRITER],
                         ids=["borrower", "broker", "underwriter"])
def test_any_signed_in_user_gets_a_valuation(client, headers):
    assert client.post("/valuations", json=PROPERTY, headers=headers).status_code == 201


def test_borrower_submits(client):
    assert client.post("/applications", json=APPLICATION, headers=BORROWER).status_code == 201


@pytest.mark.parametrize("headers", [BORROWER, BROKER, UNDERWRITER],
                         ids=["owner", "assigned_broker", "underwriter"])
def test_allowed_readers_get_the_application(client, app_id, headers):
    assert client.get(f"/applications/{app_id}", headers=headers).status_code == 200


def test_underwriter_decides(client, app_id):
    r = client.post(f"/applications/{app_id}/status", json={"to": "underwriter_approved"},
                    headers=UNDERWRITER)
    assert r.status_code == 200 and r.json()["status"] == "underwriter_approved"


# ---------- firebase mode: verification path with the Admin SDK call replaced ----------

@pytest.fixture
def fb_client(monkeypatch):
    """auth_mode=firebase; verify_id_token is replaced by a fake that knows two tokens."""
    import firebase_admin
    from firebase_admin import auth as fb_auth

    valid = {
        "good-borrower": {"uid": "borrower-aoife", "email": "aoife@example.com"},  # no claim
        "good-underwriter": {"uid": "uw-rachel", "role": "underwriter", "name": "Rachel"},
        "bad-role": {"uid": "x", "role": "system"},
    }

    def fake_verify(token, *args, **kwargs):
        if token not in valid:
            raise fb_auth.InvalidIdTokenError("bad token")
        return valid[token]

    monkeypatch.setattr(fb_auth, "verify_id_token", fake_verify)
    monkeypatch.setattr(firebase_admin, "_apps", {"[DEFAULT]": object()})  # skip init
    settings = Settings(repository="memory", auth_mode="firebase",
                        default_broker_uid="broker-ciaran", borrower_ref_salt="test-salt")
    return TestClient(create_app(settings, InMemoryRepository(), chain=FakeChain()))


def bearer(t):
    return {"Authorization": f"Bearer {t}"}


def test_firebase_mode_rejects_invalid_and_dev_tokens(fb_client):
    for t in ("expired-or-forged", "dev:borrower-aoife:borrower"):
        assert_unauthenticated(fb_client.post("/valuations", json=PROPERTY, headers=bearer(t)))


def test_firebase_mode_no_claim_means_borrower(fb_client):
    r = fb_client.post("/applications", json=APPLICATION, headers=bearer("good-borrower"))
    assert r.status_code == 201 and r.json()["borrowerId"] == "borrower-aoife"
    r = fb_client.post("/applications", json=APPLICATION, headers=bearer("good-underwriter"))
    assert r.status_code == 403


def test_firebase_mode_system_claim_is_rejected(fb_client):
    assert_unauthenticated(fb_client.post("/valuations", json=PROPERTY, headers=bearer("bad-role")))


# ---------- firebase mode against the real Auth emulator ----------

emulator = pytest.mark.skipif(not os.environ.get("FIREBASE_AUTH_EMULATOR_HOST"),
                              reason="needs the Firebase Auth emulator")


def _emulator_user(email, role=None):
    """Create a user in the Auth emulator, optionally with a role claim; return an ID token."""
    import firebase_admin
    import httpx
    from firebase_admin import auth as fb_auth

    if not firebase_admin._apps:
        firebase_admin.initialize_app(options={"projectId": "demo-al-group11"})
    host = os.environ["FIREBASE_AUTH_EMULATOR_HOST"]
    base = f"http://{host}/identitytoolkit.googleapis.com/v1/accounts"
    creds = {"email": email, "password": "test-pass-123", "returnSecureToken": True}
    r = httpx.post(f"{base}:signUp?key=any", json=creds)
    if r.status_code != 200:  # already exists from an earlier run
        r = httpx.post(f"{base}:signInWithPassword?key=any", json=creds)
    uid = r.json()["localId"]
    if role:
        fb_auth.set_custom_user_claims(uid, {"role": role})
        r = httpx.post(f"{base}:signInWithPassword?key=any", json=creds)  # token with claim
    return uid, r.json()["idToken"]


@pytest.fixture
def emu_client():
    settings = Settings(repository="memory", auth_mode="firebase",
                        firebase_project_id="demo-al-group11",
                        default_broker_uid="broker-ciaran", borrower_ref_salt="test-salt")
    return TestClient(create_app(settings, InMemoryRepository(), chain=FakeChain()))


@emulator
def test_emulator_real_tokens_and_roles(emu_client):
    b_uid, b_tok = _emulator_user("us312-borrower@example.com")
    _, u_tok = _emulator_user("us312-underwriter@example.com", "underwriter")
    _, k_tok = _emulator_user("us312-broker@example.com", "broker")

    r = emu_client.post("/applications", json=APPLICATION, headers=bearer(b_tok))
    assert r.status_code == 201 and r.json()["borrowerId"] == b_uid
    app_id = r.json()["id"]
    assert emu_client.post("/applications", json=APPLICATION,
                           headers=bearer(k_tok)).status_code == 403
    r = emu_client.post(f"/applications/{app_id}/status", json={"to": "underwriter_approved"},
                        headers=bearer(b_tok))
    assert r.status_code == 403
    r = emu_client.post(f"/applications/{app_id}/status", json={"to": "underwriter_approved"},
                        headers=bearer(u_tok))
    assert r.status_code == 200

    tampered = b_tok[:-4] + ("AAAA" if not b_tok.endswith("AAAA") else "BBBB")
    for bad in (tampered, "not-a-jwt", "dev:x:borrower"):
        assert_unauthenticated(emu_client.post("/valuations", json=PROPERTY, headers=bearer(bad)))
