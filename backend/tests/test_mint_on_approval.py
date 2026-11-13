"""Approval mints the loan note and records the audit hash (US-321, US-331, backend of US-251).

Uses FakeChain (same write-once rule as the contract) and the in-memory repository.
"""

import hashlib
import logging

import pytest
from fastapi.testclient import TestClient

from app.audit import audit_hash
from app.chain import FakeChain, borrower_ref
from app.config import Settings
from app.decisions import build_audit_record, principal_cents
from app.main import create_app
from app.repository import InMemoryRepository

BORROWER = {"Authorization": "Bearer dev:borrower-aoife:borrower"}
BROKER = {"Authorization": "Bearer dev:broker-ciaran:broker"}
UNDERWRITER = {"Authorization": "Bearer dev:uw-rachel:underwriter"}
APPLICATION = {
    "buyerType": "first_time",
    "financials": {"grossAnnualIncome": 95000, "monthlyDebts": 300, "deposit": 60000,
                   "loanAmount": 335000, "termYears": 30},
    "property": {"county": "Cork", "floorAreaM2": 110, "bedrooms": 3,
                 "propertyType": "semi_detached", "ber": "B2", "askingPrice": 395000},
}
SALT = "test-salt"


def make(chain=None, repo=None, salt=SALT, committee=None, raise_errors=True):
    repo = repo or InMemoryRepository()
    chain = chain or FakeChain()
    settings = Settings(repository="memory", auth_mode="dev", default_broker_uid="broker-ciaran",
                        borrower_ref_salt=salt)
    kwargs = {"committee": committee} if committee else {}
    client = TestClient(create_app(settings, repo, chain=chain, **kwargs),
                        raise_server_exceptions=raise_errors)
    return client, repo, chain


def submitted(client):
    """Submit; the stub committee moves it to ai_deliberated in the background."""
    app_id = client.post("/applications", json=APPLICATION, headers=BORROWER).json()["id"]
    assert client.get(f"/applications/{app_id}", headers=UNDERWRITER).json()["status"] == \
        "ai_deliberated"
    return app_id


def decide(client, app_id, to, reason=None, headers=UNDERWRITER):
    body = {"to": to} | ({"reason": reason} if reason else {})
    return client.post(f"/applications/{app_id}/status", json=body, headers=headers)


# ---------- approve mints ----------

def test_approve_mints_and_stores_loan_note():
    client, repo, chain = make()
    app_id = submitted(client)
    r = decide(client, app_id, "underwriter_approved")
    assert r.status_code == 200
    app = r.json()
    assert app["status"] == "underwriter_approved"
    note = app["loanNote"]
    assert note["tokenId"] == 1 and note["chainStatus"] == "minted"
    assert note["txHash"].startswith("0x") and len(note["txHash"]) == 66
    assert note["auditTxHash"].startswith("0x") and note["auditTxHash"] != note["txHash"]
    assert len(note["auditHash"]) == 64
    assert app["decision"]["outcome"] == "underwriter_approved"
    assert app["decision"]["by"] == "uw-rachel"

    # what went on-chain
    minted = chain.loans[1]
    assert minted["to"] == chain.bank_address
    assert minted["principalCents"] == 33_500_000
    assert minted["aprBps"] == 390 and minted["termYears"] == 30
    assert minted["borrowerRef"] == hashlib.sha256(b"borrower-aoifetest-salt").digest()
    assert b"aoife" not in minted["borrowerRef"]  # no personal data on-chain

    # decisions/{id}
    (d,) = repo.list_decisions(app_id)
    assert d["outcome"] == "underwriter_approved" and d["brokerId"] == "broker-ciaran"
    assert d["auditHash"] == note["auditHash"] and d["auditTxHash"] == note["auditTxHash"]


def test_stored_audit_hash_matches_recomputed_record_and_chain():
    client, repo, chain = make()
    app_id = submitted(client)
    decide(client, app_id, "underwriter_approved")
    stored, deliberation = repo.get_application(app_id), repo.get_deliberation(app_id)
    assert stored is not None and deliberation is not None
    memo = deliberation["creditMemo"]
    record = build_audit_record(stored, stored["decision"], memo)
    assert record["creditMemo"].startswith("[STUB")
    assert stored["loanNote"]["auditHash"] == audit_hash(record)
    assert chain.get_audit_hash(stored["loanNote"]["tokenId"]) == audit_hash(record)
    # One changed field (e.g. someone edits the stored memo) no longer matches.
    assert audit_hash({**record, "creditMemo": memo + "!"}) != stored["loanNote"]["auditHash"]


def test_conditional_then_approve_mints_once():
    client, _, chain = make()
    app_id = submitted(client)
    r = decide(client, app_id, "conditionally_approved", reason="Need payslips")
    assert r.status_code == 200 and r.json()["loanNote"] is None
    assert chain.loans == {}
    r = decide(client, app_id, "underwriter_approved")
    assert r.status_code == 200 and r.json()["loanNote"]["tokenId"] == 1
    assert len(chain.loans) == 1


# ---------- chain failures: status unchanged ----------

def test_mint_failure_leaves_status_unchanged(caplog):
    client, repo, chain = make(chain=FakeChain(fail_on="mint"))
    app_id = submitted(client)
    with caplog.at_level(logging.ERROR, logger="al.decisions"):
        r = decide(client, app_id, "underwriter_approved")
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "mint_failed"
    app = repo.get_application(app_id)
    assert app["status"] == "ai_deliberated"
    assert app["loanNote"] is None and app["decision"] is None
    assert repo.list_decisions(app_id) == []
    assert any(app_id in rec.getMessage() for rec in caplog.records)


def test_audit_failure_leaves_status_unchanged_and_logs_orphan(caplog):
    client, repo, chain = make(chain=FakeChain(fail_on="audit"))
    app_id = submitted(client)
    with caplog.at_level(logging.ERROR, logger="al.decisions"):
        r = decide(client, app_id, "underwriter_approved")
    assert r.status_code == 502 and r.json()["error"]["code"] == "mint_failed"
    assert repo.get_application(app_id)["status"] == "ai_deliberated"
    assert repo.get_application(app_id)["loanNote"] is None
    assert any("orphaned" in rec.getMessage() for rec in caplog.records)  # known issue


def test_missing_salt_refuses_to_mint():
    client, repo, chain = make(salt=None)
    app_id = submitted(client)
    r = decide(client, app_id, "underwriter_approved")
    assert r.status_code == 502 and r.json()["error"]["code"] == "mint_failed"
    assert chain.loans == {} and repo.get_application(app_id)["status"] == "ai_deliberated"


class FirestoreDown(InMemoryRepository):
    def record_decision(self, *args, **kwargs):
        raise RuntimeError("Firestore unavailable")


def test_firestore_failure_after_mint_is_logged(caplog):
    """KNOWN ISSUE (logged, not solved): the token exists, Firestore was not updated."""
    client, repo, chain = make(repo=FirestoreDown(), raise_errors=False)
    app_id = submitted(client)
    with caplog.at_level(logging.CRITICAL, logger="al.decisions"):
        r = decide(client, app_id, "underwriter_approved")
    assert r.status_code == 500
    assert repo.get_application(app_id)["status"] == "ai_deliberated"
    assert len(chain.loans) == 1
    msg = " ".join(rec.getMessage() for rec in caplog.records)
    assert app_id in msg and "tokenId=1" in msg


# ---------- no mint ----------

@pytest.mark.parametrize("to,reason", [("declined", "Income not verified"),
                                       ("conditionally_approved", "Need payslips")])
def test_decline_and_conditional_do_not_mint(to, reason):
    client, repo, chain = make()
    app_id = submitted(client)
    r = decide(client, app_id, to, reason)
    assert r.status_code == 200 and r.json()["status"] == to
    assert r.json()["loanNote"] is None
    assert r.json()["decision"] == {**r.json()["decision"], "outcome": to, "reason": reason}
    assert chain.loans == {}
    (d,) = repo.list_decisions(app_id)
    assert d["auditHash"] is None and d["auditTxHash"] is None


def _never_finishes(_application):
    raise RuntimeError("committee down")


@pytest.mark.parametrize("case", ["still_applied", "broker", "approve_twice", "no_reason"])
def test_refused_moves_never_touch_the_chain(case):
    if case == "still_applied":  # committee failed, so applied -> approved is not allowed
        client, _, chain = make(committee=_never_finishes)
        app_id = client.post("/applications", json=APPLICATION, headers=BORROWER).json()["id"]
        r, code = decide(client, app_id, "underwriter_approved"), 409
    elif case == "broker":
        client, _, chain = make()
        r, code = decide(client, submitted(client), "underwriter_approved", headers=BROKER), 403
    elif case == "approve_twice":
        client, _, chain = make()
        app_id = submitted(client)
        decide(client, app_id, "underwriter_approved")
        r, code = decide(client, app_id, "underwriter_approved"), 409
    else:
        client, _, chain = make()
        r, code = decide(client, submitted(client), "declined"), 422
    assert r.status_code == code
    assert len(chain.loans) == (1 if case == "approve_twice" else 0)


# ---------- helpers ----------

@pytest.mark.parametrize("euro,cents", [(335000, 33_500_000), (335000.0, 33_500_000),
                                        (0.29, 29), (1234.565, 123_457), (1, 100)])
def test_principal_cents(euro, cents):
    assert principal_cents(euro) == cents


def test_borrower_ref_depends_on_salt():
    assert borrower_ref("b1", "s1") != borrower_ref("b1", "s2")
    assert len(borrower_ref("b1", "s1")) == 32
