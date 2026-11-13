"""Automatic AI committee run after submission (US-313).

POST /applications schedules `deliberate()` as a FastAPI BackgroundTask, so the borrower
gets the 201 response straight away and the committee runs afterwards.

Success: the result is validated, saved to deliberations/{applicationId} (+ steps), copied
into application.aiRecommendation, and the status moves applied -> ai_deliberated as
Actor.SYSTEM through the state machine (one repository transaction).
Failure (committee raises, bad result, refused transition): the error is logged with the
application ID, nothing is written, and the status stays "applied". Never raises.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from . import integrations
from .repository import NotFound, Repository

log = logging.getLogger("al.deliberation")

Committee = Callable[[dict], dict]


def _now() -> datetime:
    return datetime.now(UTC)


def default_committee(application: dict) -> dict:
    """Looked up at call time, so switching integrations.run_committee needs no change here."""
    return integrations.run_committee(application)


def deliberate(app_id: str, repo: Repository, committee: Committee = default_committee,
               now: Callable[[], datetime] = _now) -> bool:
    """Run the committee for one application. Returns True if the result was stored."""
    started = now()
    try:
        application = repo.get_application(app_id)
        if application is None:
            raise NotFound(app_id)
        result = integrations.validate_committee_result(committee(dict(application)))
        completed = now()
        deliberation = {
            "applicationId": app_id,
            "status": "completed",
            "startedAt": started,
            "completedAt": completed,
            "finalDecision": result["decision"],
            "creditMemo": result["creditMemo"],
            "isStub": result["isStub"],
        }
        recommendation = {
            "decision": result["decision"],
            "deliberationId": app_id,
            "completedAt": completed,
        }
        repo.record_deliberation(app_id, deliberation, result["steps"], recommendation,
                                 completed)
    except Exception:
        log.exception("AI committee failed for application %s; status left unchanged.",
                      app_id)
        return False
    log.info("AI committee finished for application %s: %s", app_id, result["decision"])
    return True
