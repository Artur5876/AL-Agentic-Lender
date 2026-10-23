"""Data access for applications and valuations.

Two implementations with the same methods:
- InMemoryRepository: a dict guarded by a lock. Used by the unit tests.
- FirestoreRepository: Cloud Firestore (or the emulator). Uses transactions so that
  "read current status -> check -> write new status" cannot be interleaved by a
  second request (two underwriters clicking at the same moment).

Documents are stored in the Firestore format from docs/data-model.md (camelCase keys).
"""

from __future__ import annotations

import os
import threading
import uuid
from datetime import datetime
from typing import Protocol

from .lifecycle import INITIAL_STATUS, Actor, Status, check_transition, history_entry


class NotFound(Exception):
    pass


def make_reference(year: int, number: int) -> str:
    return f"AL-{year}-{number:04d}"


def new_application_doc(
    reference: str, data: dict, actor_uid: str, now: datetime
) -> dict:
    """Build the stored document for a new application (status = applied)."""
    first = history_entry(INITIAL_STATUS, now, actor_uid, Actor.BORROWER)
    return {
        **data,
        "reference": reference,
        "status": INITIAL_STATUS.value,
        "statusHistory": [first.to_dict()],
        "metrics": data.get("metrics"),
        "riskTier": None,
        "aiRecommendation": None,
        "decision": None,
        "loanNote": None,
        "payment": None,
        "createdAt": now,
        "updatedAt": now,
    }


class Repository(Protocol):
    def create_application(self, data: dict, actor_uid: str, now: datetime) -> dict: ...
    def get_application(self, app_id: str) -> dict | None: ...
    def change_status(
        self, app_id: str, target: Status, actor: Actor, actor_uid: str,
        reason: str | None, now: datetime,
    ) -> dict: ...
    def save_valuation(self, data: dict, now: datetime) -> dict: ...
    def get_valuation(self, valuation_id: str) -> dict | None: ...


class InMemoryRepository:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._apps: dict[str, dict] = {}
        self._valuations: dict[str, dict] = {}
        self._counters: dict[int, int] = {}

    def create_application(self, data: dict, actor_uid: str, now: datetime) -> dict:
        with self._lock:
            n = self._counters.get(now.year, 1)
            self._counters[now.year] = n + 1
            ref = make_reference(now.year, n)
            doc = new_application_doc(ref, data, actor_uid, now)
            self._apps[ref] = doc
            return {"id": ref, **doc}

    def get_application(self, app_id: str) -> dict | None:
        with self._lock:
            doc = self._apps.get(app_id)
            return {"id": app_id, **doc} if doc else None

    def change_status(self, app_id, target, actor, actor_uid, reason, now) -> dict:
        with self._lock:  # check + write happen as one step
            doc = self._apps.get(app_id)
            if doc is None:
                raise NotFound(app_id)
            check_transition(Status(doc["status"]), target, actor, reason)
            entry = history_entry(target, now, actor_uid, actor, reason).to_dict()
            doc["status"] = target.value
            doc["statusHistory"] = [*doc["statusHistory"], entry]
            doc["updatedAt"] = now
            return {"id": app_id, **doc}

    def save_valuation(self, data: dict, now: datetime) -> dict:
        vid = uuid.uuid4().hex
        doc = {**data, "createdAt": now}
        with self._lock:
            self._valuations[vid] = doc
        return {"id": vid, **doc}

    def get_valuation(self, valuation_id: str) -> dict | None:
        with self._lock:
            doc = self._valuations.get(valuation_id)
            return {"id": valuation_id, **doc} if doc else None


def firestore_client(project_id: str):
    """Return a Firestore client. With FIRESTORE_EMULATOR_HOST set it talks to the
    local emulator and needs no credentials; otherwise it uses the service account
    from GOOGLE_APPLICATION_CREDENTIALS (never commit that file)."""
    from google.cloud import firestore

    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        from google.auth.credentials import AnonymousCredentials

        return firestore.Client(project=project_id, credentials=AnonymousCredentials())
    return firestore.Client(project=project_id)


class FirestoreRepository:
    def __init__(self, project_id: str, client=None) -> None:
        from google.cloud import firestore

        self._fs = firestore
        self._db = client or firestore_client(project_id)

    def create_application(self, data: dict, actor_uid: str, now: datetime) -> dict:
        db, fs = self._db, self._fs
        counter_ref = db.collection("counters").document(f"applications-{now.year}")

        @fs.transactional
        def _create(tx) -> dict:
            snap = counter_ref.get(transaction=tx)
            n = snap.get("next") if snap.exists else 1
            ref = make_reference(now.year, n)
            doc = new_application_doc(ref, data, actor_uid, now)
            tx.set(counter_ref, {"next": n + 1})
            tx.create(db.collection("applications").document(ref), doc)
            return {"id": ref, **doc}

        return _create(db.transaction())

    def get_application(self, app_id: str) -> dict | None:
        snap = self._db.collection("applications").document(app_id).get()
        return {"id": snap.id, **snap.to_dict()} if snap.exists else None

    def change_status(self, app_id, target, actor, actor_uid, reason, now) -> dict:
        db, fs = self._db, self._fs
        ref = db.collection("applications").document(app_id)

        @fs.transactional
        def _change(tx) -> dict:
            snap = ref.get(transaction=tx)
            if not snap.exists:
                raise NotFound(app_id)
            doc = snap.to_dict()
            check_transition(Status(doc["status"]), target, actor, reason)
            entry = history_entry(target, now, actor_uid, actor, reason).to_dict()
            history = [*doc.get("statusHistory", []), entry]
            tx.update(ref, {"status": target.value, "statusHistory": history, "updatedAt": now})
            return {"id": app_id, **doc, "status": target.value,
                    "statusHistory": history, "updatedAt": now}

        return _change(db.transaction())

    def save_valuation(self, data: dict, now: datetime) -> dict:
        ref = self._db.collection("valuations").document()
        doc = {**data, "createdAt": now}
        ref.set(doc)
        return {"id": ref.id, **doc}

    def get_valuation(self, valuation_id: str) -> dict | None:
        snap = self._db.collection("valuations").document(valuation_id).get()
        return {"id": snap.id, **snap.to_dict()} if snap.exists else None
