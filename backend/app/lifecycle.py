"""Application lifecycle state machine (US-302).

This module is the ONE place where the allowed status changes are defined
(backlog section 2.2). Every endpoint that changes an application's status
must call `check_transition` before writing. It has no Firebase or FastAPI
imports, so it can be unit-tested on its own.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum


class Status(StrEnum):
    """Status codes stored in Firestore. Display text is in LABELS."""

    APPLIED = "applied"
    AI_DELIBERATED = "ai_deliberated"
    CONDITIONALLY_APPROVED = "conditionally_approved"
    UNDERWRITER_APPROVED = "underwriter_approved"
    FUNDED = "funded"
    DECLINED = "declined"
    CLOSED = "closed"


class Actor(StrEnum):
    """Who is asking for the change. SYSTEM is the backend itself (never a user token)."""

    BORROWER = "borrower"
    BROKER = "broker"
    UNDERWRITER = "underwriter"
    SYSTEM = "system"


LABELS: dict[Status, str] = {
    Status.APPLIED: "Applied",
    Status.AI_DELIBERATED: "AI Deliberated",
    Status.CONDITIONALLY_APPROVED: "Conditionally Approved",
    Status.UNDERWRITER_APPROVED: "Underwriter Approved",
    Status.FUNDED: "Funded",
    Status.DECLINED: "Declined",
    Status.CLOSED: "Closed",
}

INITIAL_STATUS = Status.APPLIED

_SYSTEM = frozenset({Actor.SYSTEM})
_UNDERWRITER = frozenset({Actor.UNDERWRITER})
_SYSTEM_OR_UNDERWRITER = frozenset({Actor.SYSTEM, Actor.UNDERWRITER})

# current status -> {allowed next status -> actors allowed to make that move}
TRANSITIONS: dict[Status, dict[Status, frozenset[Actor]]] = {
    Status.APPLIED: {
        Status.AI_DELIBERATED: _SYSTEM,
    },
    Status.AI_DELIBERATED: {
        Status.UNDERWRITER_APPROVED: _UNDERWRITER,
        Status.CONDITIONALLY_APPROVED: _UNDERWRITER,
        Status.DECLINED: _UNDERWRITER,
    },
    Status.CONDITIONALLY_APPROVED: {
        Status.UNDERWRITER_APPROVED: _UNDERWRITER,
        Status.DECLINED: _UNDERWRITER,
    },
    Status.UNDERWRITER_APPROVED: {
        Status.FUNDED: _SYSTEM_OR_UNDERWRITER,
    },
    Status.FUNDED: {
        Status.CLOSED: _SYSTEM_OR_UNDERWRITER,
    },
    Status.DECLINED: {},
    Status.CLOSED: {},
}

# US-252: declining or conditionally approving needs a written reason.
REASON_REQUIRED: frozenset[Status] = frozenset(
    {Status.CONDITIONALLY_APPROVED, Status.DECLINED}
)


class TransitionError(Exception):
    """Base class. `code` is the machine-readable error code returned by the API."""

    code = "transition_error"


class InvalidTransition(TransitionError):
    """The move is not in the table at all (e.g. applied -> funded)."""

    code = "invalid_transition"


class ActorNotAllowed(TransitionError):
    """The move exists, but this actor may not make it (e.g. a broker approving)."""

    code = "actor_not_allowed"


class ReasonRequired(TransitionError):
    """Decline / conditional approval without a reason."""

    code = "reason_required"


def allowed_next(current: Status) -> frozenset[Status]:
    return frozenset(TRANSITIONS[current])


def is_final(status: Status) -> bool:
    return not TRANSITIONS[status]


def check_transition(
    current: Status, target: Status, actor: Actor, reason: str | None = None
) -> None:
    """Raise a TransitionError if `actor` may not move an application from
    `current` to `target`. Returns None if the move is allowed.

    Order of checks matters for clear error messages:
    1. is the move possible at all, 2. may this actor do it, 3. is a reason given.
    """
    allowed = TRANSITIONS[current]
    if target not in allowed:
        nxt = ", ".join(sorted(s.value for s in allowed)) or "none (final state)"
        raise InvalidTransition(
            f"Cannot move from '{current.value}' to '{target.value}'. Allowed next: {nxt}."
        )
    if actor not in allowed[target]:
        raise ActorNotAllowed(
            f"A {actor.value} may not move an application from "
            f"'{current.value}' to '{target.value}'."
        )
    if target in REASON_REQUIRED and not (reason and reason.strip()):
        raise ReasonRequired(f"A reason is required to set status '{target.value}'.")


@dataclass(frozen=True)
class HistoryEntry:
    """One row of applications/{id}.statusHistory."""

    status: str
    at: datetime
    by: str  # UID of the user, or "system"
    role: str
    reason: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def history_entry(
    status: Status, at: datetime, by: str, actor: Actor, reason: str | None = None
) -> HistoryEntry:
    cleaned = reason.strip() if reason and reason.strip() else None
    return HistoryEntry(status=status.value, at=at, by=by, role=actor.value, reason=cleaned)
