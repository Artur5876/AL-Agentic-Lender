"""Unit tests for the state machine (US-302).

The first test checks EVERY pair of statuses (7 x 7 = 49 cases), so a mistake
anywhere in the transition table is caught, not only the cases we thought of.
"""

import itertools
from datetime import UTC, datetime

import pytest

from app.lifecycle import (
    LABELS,
    TRANSITIONS,
    Actor,
    ActorNotAllowed,
    InvalidTransition,
    ReasonRequired,
    Status,
    allowed_next,
    check_transition,
    history_entry,
    is_final,
)

# Backlog section 2.2, written out independently of the code under test.
EXPECTED = {
    ("applied", "ai_deliberated"),
    ("ai_deliberated", "underwriter_approved"),
    ("ai_deliberated", "conditionally_approved"),
    ("ai_deliberated", "declined"),
    ("conditionally_approved", "underwriter_approved"),
    ("conditionally_approved", "declined"),
    ("underwriter_approved", "funded"),
    ("funded", "closed"),
}


def _any_allowed_actor(current: Status, target: Status) -> Actor:
    return next(iter(TRANSITIONS[current][target]))


@pytest.mark.parametrize("current,target", list(itertools.product(Status, Status)))
def test_every_pair_matches_backlog(current, target):
    allowed = (current.value, target.value) in EXPECTED
    if allowed:
        actor = _any_allowed_actor(current, target)
        check_transition(current, target, actor, reason="test reason")
    else:
        with pytest.raises(InvalidTransition):
            check_transition(current, target, Actor.UNDERWRITER, reason="test reason")


def test_every_status_has_a_row_and_a_label():
    assert set(TRANSITIONS) == set(Status)
    assert set(LABELS) == set(Status)


def test_cannot_fund_before_approval():  # the example in the US-302 story
    with pytest.raises(InvalidTransition):
        check_transition(Status.APPLIED, Status.FUNDED, Actor.SYSTEM)
    with pytest.raises(InvalidTransition):
        check_transition(Status.AI_DELIBERATED, Status.FUNDED, Actor.UNDERWRITER)


@pytest.mark.parametrize("final", [Status.DECLINED, Status.CLOSED])
def test_final_states_have_no_exit(final):
    assert is_final(final)
    assert allowed_next(final) == frozenset()
    for target in Status:
        with pytest.raises(InvalidTransition):
            check_transition(final, target, Actor.UNDERWRITER, reason="x")


@pytest.mark.parametrize("actor", [Actor.BORROWER, Actor.BROKER])
def test_only_underwriter_can_decide(actor):
    with pytest.raises(ActorNotAllowed):
        check_transition(Status.AI_DELIBERATED, Status.UNDERWRITER_APPROVED, actor)


def test_only_system_marks_ai_deliberated():
    check_transition(Status.APPLIED, Status.AI_DELIBERATED, Actor.SYSTEM)
    with pytest.raises(ActorNotAllowed):
        check_transition(Status.APPLIED, Status.AI_DELIBERATED, Actor.UNDERWRITER)


@pytest.mark.parametrize("target", [Status.DECLINED, Status.CONDITIONALLY_APPROVED])
@pytest.mark.parametrize("reason", [None, "", "   "])
def test_reason_required_for_decline_and_conditional(target, reason):
    with pytest.raises(ReasonRequired):
        check_transition(Status.AI_DELIBERATED, target, Actor.UNDERWRITER, reason)


def test_approve_needs_no_reason():
    check_transition(Status.AI_DELIBERATED, Status.UNDERWRITER_APPROVED, Actor.UNDERWRITER)


def test_history_entry_trims_reason():
    now = datetime(2026, 10, 2, 10, 16, tzinfo=UTC)
    e = history_entry(Status.DECLINED, now, "uw-1", Actor.UNDERWRITER, "  DTI too high ")
    assert e.to_dict() == {"status": "declined", "at": now, "by": "uw-1",
                           "role": "underwriter", "reason": "DTI too high"}
