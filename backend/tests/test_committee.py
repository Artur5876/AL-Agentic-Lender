"""US-313: AI committee runs automatically after submission.

TestClient runs BackgroundTasks after the response has been built, so the POST response
still shows "applied" (the API answered before the committee ran) and a following GET
shows the committee's effect.
"""

import copy
import logging
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app import integrations
from app.config import Settings
from app.deliberation import deliberate
from app.integrations import (
    COMMITTEE_AGENTS,
    CommitteeResultError,
    run_committee,
    validate_committee_result,
)
from app.main import create_app
from app.repository import InMemoryRepository

BORROWER = {"Authorization": "Bearer dev:borrower-aoife:borrower"}
UNDERWRITER = {"Authorization": "Bearer dev:uw-rachel:underwriter"}
APPLICATION = {
    "buyerType": "first_time",
    "financials": {"grossAnnualIncome": 95000, "monthlyDebts": 300, "deposit": 60000,
                   "loanAmount": 335000, "termYears": 30},
    "property": {"county": "Cork", "floorAreaM2": 110, "bedrooms": 3,
                 "propertyType": "semi_detached", "ber": "B2", "askingPrice": 395000},
}
SETTINGS = Settings(repository="memory", auth_mode="dev", default_broker_uid="broker-ciaran")


def make_client(repo, committee=None):
    kwargs = {"committee": committee} if committee else {}
    return TestClient(create_app(SETTINGS, repo, **kwargs))


def submit_and_read(client):
    r = client.post("/applications", json=APPLICATION, headers=BORROWER)
    assert r.status_code == 201
    created = r.json()
    after = client.get(f"/applications/{created['id']}", headers=UNDERWRITER).json()
    return created, after


# ---------- success path ----------

def test_submit_runs_committee_in_background():
    repo = InMemoryRepository()
    created, after = submit_and_read(make_client(repo))

    # The API answered before the committee ran.
    assert created["status"] == "applied" and created["aiRecommendation"] is None

    assert after["status"] == "ai_deliberated"
    assert after["statusLabel"] == "AI Deliberated"
    last = after["statusHistory"][-1]
    assert last["status"] == "ai_deliberated" and last["role"] == "system"
    assert last["by"] == "system"

    rec = after["aiRecommendation"]
    assert rec["decision"] == "approve"  # sample passes every calc-module check
    assert rec["deliberationId"] == created["id"] and rec["completedAt"]

    d = repo.get_deliberation(created["id"])
    assert d is not None
    assert d["status"] == "completed" and d["finalDecision"] == "approve"
    assert d["isStub"] is True and d["creditMemo"].startswith("[STUB")
    assert d["startedAt"] <= d["completedAt"]
    assert [s["agent"] for s in d["steps"]] == list(COMMITTEE_AGENTS)
    assert [s["id"] for s in d["steps"]][0] == "01-affordability"
    for s in d["steps"]:
        assert set(integrations.STEP_FIELDS) <= set(s)


# ---------- failure paths: status stays "applied", error logged ----------

def _boom(_application):
    raise RuntimeError("model server down")


def _bad_decision(application):
    return {**run_committee(application), "decision": "maybe"}


def _missing_step_field(application):
    result = run_committee(application)
    del result["steps"][2]["reasoning"]
    return result


@pytest.mark.parametrize("committee", [_boom, _bad_decision, _missing_step_field],
                         ids=["committee_raises", "invalid_decision", "step_missing_field"])
def test_committee_failure_leaves_status_applied(committee, caplog):
    repo = InMemoryRepository()
    with caplog.at_level(logging.ERROR, logger="al.deliberation"):
        created, after = submit_and_read(make_client(repo, committee))

    assert after["status"] == "applied"
    assert after["aiRecommendation"] is None
    assert len(after["statusHistory"]) == 1
    assert repo.get_deliberation(created["id"]) is None
    assert any(created["id"] in rec.getMessage() for rec in caplog.records)


def test_deliberate_twice_does_not_move_status_again():
    repo = InMemoryRepository()
    app_id = submit_and_read(make_client(repo))[0]["id"]
    assert deliberate(app_id, repo) is False  # ai_deliberated -> ai_deliberated is refused
    assert len(repo.get_application(app_id)["statusHistory"]) == 2


def test_deliberate_unknown_application_returns_false():
    assert deliberate("AL-2026-9999", InMemoryRepository()) is False


# ---------- stub committee ----------

METRICS = {"lti": 3.5263, "ltv": 0.8481, "dti": 0.2399, "stressedDti": 0.2915,
           "monthlyRepayment": 1599.36,
           "checks": {"ltiOk": True, "ltvOk": True, "dtiOk": True, "stressedDtiOk": True}}


def _app(checks=None, metrics=True):
    m = copy.deepcopy(METRICS)
    if checks:
        m["checks"].update(checks)
    return {**APPLICATION, "valuation": None, "metrics": m if metrics else None}


def test_stub_copies_figures_from_metrics():
    result = run_committee(_app())
    assert result["isStub"] is True
    affordability = result["steps"][0]["output"]
    assert affordability == {k: METRICS[k] for k in ("lti", "dti", "stressedDti",
                                                     "monthlyRepayment")}
    assert result["steps"][1]["output"]["ltv"] == METRICS["ltv"]
    validate_committee_result(result)


@pytest.mark.parametrize("app,expected", [
    (_app(), "approve"),
    (_app({"stressedDtiOk": False}), "conditionally_approve"),
    (_app({"ltvOk": False}), "decline"),
    (_app({"ltiOk": False, "stressedDtiOk": False}), "decline"),
    (_app(metrics=False), "conditionally_approve"),
])
def test_stub_decision_follows_calc_checks(app, expected):
    assert run_committee(app)["decision"] == expected


# ---------- validator ----------

def _valid():
    return run_committee(_app())


def _mutate(fn):
    r = _valid()
    fn(r)
    return r


@pytest.mark.parametrize("result", [
    "not a dict",
    _mutate(lambda r: r.update(decision="maybe")),
    _mutate(lambda r: r.update(decision="APPROVE")),
    _mutate(lambda r: r.pop("creditMemo")),
    _mutate(lambda r: r.update(isStub="yes")),
    _mutate(lambda r: r.update(steps="none")),
    _mutate(lambda r: r["steps"][0].pop("model")),
    _mutate(lambda r: r["steps"][1].update(output="text")),
    _mutate(lambda r: r["steps"][1].update(reasoning=None)),
    _mutate(lambda r: r["steps"][0].update(timestamp="yesterday")),
    _mutate(lambda r: r["steps"][0].update(timestamp="2026-11-13T10:00:00")),        # naive
    _mutate(lambda r: r["steps"][0].update(timestamp="2026-11-13T10:00:00+01:00")),  # not UTC
    _mutate(lambda r: r["steps"].pop()),                                             # 3 agents
    _mutate(lambda r: r["steps"].append(copy.deepcopy(r["steps"][0]))),              # duplicate
    _mutate(lambda r: r["steps"][2].update(agent="astrologer")),
], ids=lambda r: "bad")
def test_validator_rejects_bad_results(result):
    with pytest.raises(CommitteeResultError):
        validate_committee_result(result)


def test_validator_accepts_z_suffix_and_extra_fields():
    r = _valid()
    r["steps"][0]["timestamp"] = datetime(2026, 11, 13, tzinfo=UTC).isoformat().replace(
        "+00:00", "Z")
    r["steps"][0]["promptVersion"] = "v1"
    assert validate_committee_result(r) is r
