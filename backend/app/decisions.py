"""Underwriter decisions (US-251/252 backend side) and minting on approval (US-321, US-331).

Order for an approval (target underwriter_approved):
 1. check the state machine first (nothing touches the chain if the move is not allowed),
 2. build the audit record and hash it (backend/app/audit.py),
 3. mint the loan note, 4. record the audit hash on-chain,
 5. THEN, in one repository transaction: status change + application.decision +
    application.loanNote + decisions/{id}.
A chain failure raises MintFailed ("mint_failed"); the status is not changed.
Conditional approval and decline do steps 1 and 5 only (no chain).
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from .audit import audit_hash
from .auth import CurrentUser
from .chain import ChainClient, ChainError, borrower_ref
from .config import Settings
from .lifecycle import Status, check_transition
from .repository import Repository

log = logging.getLogger("al.decisions")

UNDERWRITER_DECISIONS = frozenset(
    {Status.UNDERWRITER_APPROVED, Status.CONDITIONALLY_APPROVED, Status.DECLINED})


class MintFailed(Exception):
    """Loan note could not be minted or its audit hash not recorded. Status unchanged."""

    code = "mint_failed"


def principal_cents(loan_amount: float) -> int:
    """Euro amount -> integer cents for the contract (Decimal, so 0.1 + 0.2 issues cannot occur).
    A unit conversion done by backend code, not a lending calculation."""
    return int((Decimal(str(loan_amount)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def build_audit_record(application: dict, decision: dict, credit_memo: str | None) -> dict:
    """The record whose SHA-256 goes on-chain. Everything in it is also stored in Firestore
    (application + deliberation), so the hash can be recomputed later and compared."""
    return {
        "applicationId": application["id"],
        "decision": decision,
        "creditMemo": credit_memo,
        "valuation": application.get("valuation"),
        "metrics": application.get("metrics"),
    }


def apply_decision(application: dict, target: Status, user: CurrentUser, reason: str | None,
                   now: datetime, repo: Repository, chain: ChainClient,
                   settings: Settings) -> dict:
    app_id = application["id"]
    check_transition(Status(application["status"]), target, user.role, reason)

    cleaned = reason.strip() if reason and reason.strip() else None
    decision = {"outcome": target.value, "reason": cleaned, "by": user.uid, "at": now}
    loan_note = None
    hash_hex = audit_tx = None

    if target == Status.UNDERWRITER_APPROVED:
        deliberation = repo.get_deliberation(app_id)
        record = build_audit_record(application, decision,
                                    deliberation.get("creditMemo") if deliberation else None)
        hash_hex = audit_hash(record)
        salt = settings.borrower_ref_salt.get_secret_value() if settings.borrower_ref_salt else ""
        fin = application["financials"]
        try:
            minted = chain.mint_loan(principal_cents(fin["loanAmount"]), settings.default_apr_bps,
                                     int(fin["termYears"]),
                                     borrower_ref(application["borrowerId"], salt))
        except ChainError as exc:
            log.error("Mint failed for application %s: %s", app_id, exc)
            raise MintFailed(f"The loan note could not be minted: {exc}") from exc
        try:
            audit_tx = chain.record_audit(minted["tokenId"], hash_hex)["txHash"]
        except ChainError as exc:
            # KNOWN ISSUE: the token exists on-chain without an audit hash and without a
            # Firestore record. Logged for manual follow-up; not repaired automatically.
            log.error("Audit hash NOT recorded for application %s: token %s (tx %s) is "
                      "orphaned on-chain: %s", app_id, minted["tokenId"], minted["txHash"], exc)
            raise MintFailed(f"The audit hash could not be recorded: {exc}") from exc
        loan_note = {"tokenId": minted["tokenId"], "txHash": minted["txHash"],
                     "auditHash": hash_hex, "auditTxHash": audit_tx, "chainStatus": "minted"}

    decision_doc = {"applicationId": app_id, "brokerId": application.get("brokerId"),
                    **decision, "auditHash": hash_hex, "auditTxHash": audit_tx}
    try:
        return repo.record_decision(app_id, target, user.role, user.uid, reason, now,
                                    decision, decision_doc, loan_note)
    except Exception:
        if loan_note:
            # KNOWN ISSUE: minted + audited on-chain, but Firestore was not updated
            # (e.g. Firestore down, or another underwriter changed the status meanwhile).
            log.critical("Loan note minted for application %s but the Firestore write "
                         "failed: tokenId=%s txHash=%s auditHash=%s auditTxHash=%s",
                         app_id, loan_note["tokenId"], loan_note["txHash"], hash_hex, audit_tx)
        raise
