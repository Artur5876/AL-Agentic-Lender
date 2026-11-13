"""FirestoreRepository against the Firestore EMULATOR (skipped when it is not running).

Run from firebase/:
  npx firebase emulators:exec --only firestore --project demo-al-group11 \
    "cd ../backend && .venv/bin/python -m pytest -q tests/test_firestore_repository.py"
"""

import os
from datetime import UTC, datetime

import pytest

from app.integrations import run_committee
from app.lifecycle import InvalidTransition

pytestmark = pytest.mark.skipif(not os.environ.get("FIRESTORE_EMULATOR_HOST"),
                                reason="needs the Firestore emulator")


@pytest.fixture
def repo():
    from app.repository import FirestoreRepository
    return FirestoreRepository("demo-al-group11")


def _new_app(repo):
    data = {"borrowerId": "b1", "brokerId": "broker-ciaran", "metrics": None,
            "property": {"county": "Cork", "propertyType": "detached", "askingPrice": 1}}
    return repo.create_application(data, "b1", datetime.now(UTC))


def test_record_deliberation_writes_everything_in_one_transaction(repo):
    app = _new_app(repo)
    result = run_committee(app)
    now = datetime.now(UTC)
    deliberation = {"applicationId": app["id"], "status": "completed", "startedAt": now,
                    "completedAt": now, "finalDecision": result["decision"],
                    "creditMemo": result["creditMemo"], "isStub": True}
    rec = {"decision": result["decision"], "deliberationId": app["id"], "completedAt": now}

    repo.record_deliberation(app["id"], deliberation, result["steps"], rec, now)

    stored = repo.get_application(app["id"])
    assert stored["status"] == "ai_deliberated"
    assert stored["statusHistory"][-1]["role"] == "system"
    assert stored["aiRecommendation"]["decision"] == result["decision"]
    d = repo.get_deliberation(app["id"])
    assert d["finalDecision"] == result["decision"] and d["isStub"] is True
    assert [s["id"] for s in d["steps"]] == ["01-affordability", "02-valuation",
                                             "03-market_research",
                                             "04-underwriting_strategist"]

    # A second run is refused by the state machine and changes nothing.
    with pytest.raises(InvalidTransition):
        repo.record_deliberation(app["id"], {**deliberation, "finalDecision": "decline"},
                                 result["steps"], rec, now)
    assert repo.get_deliberation(app["id"])["finalDecision"] == result["decision"]
    assert len(repo.get_application(app["id"])["statusHistory"]) == 2
