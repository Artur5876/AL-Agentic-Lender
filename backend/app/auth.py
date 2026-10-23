"""Who is calling? (groundwork for US-312, used by US-311 endpoints)

Clients send `Authorization: Bearer <Firebase ID token>`. In "firebase" mode the
token is verified with the Firebase Admin SDK (works against the Auth emulator
when FIREBASE_AUTH_EMULATOR_HOST is set). The role comes from the custom claim
`role`; no claim means borrower.

In "dev" mode (unit tests only) the token is "dev:<uid>:<role>".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from .config import Settings, get_settings
from .lifecycle import Actor

log = logging.getLogger(__name__)

USER_ROLES = {Actor.BORROWER, Actor.BROKER, Actor.UNDERWRITER}  # never SYSTEM


@dataclass(frozen=True)
class CurrentUser:
    uid: str
    role: Actor
    name: str = ""
    email: str = ""


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "unauthenticated", "message": message},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _role_from(value: str | None) -> Actor:
    try:
        role = Actor(value or "borrower")
    except ValueError:
        raise _unauthorized("Unknown role in token.") from None
    if role not in USER_ROLES:
        raise _unauthorized("Role not allowed in a user token.")
    return role


def _verify_dev(token: str) -> CurrentUser:
    parts = token.split(":")
    if len(parts) != 3 or parts[0] != "dev" or not parts[1]:
        raise _unauthorized("Dev token must look like dev:<uid>:<role>.")
    return CurrentUser(uid=parts[1], role=_role_from(parts[2]), name=parts[1])


_firebase_ready = False


def _verify_firebase(token: str, settings: Settings) -> CurrentUser:
    global _firebase_ready
    import firebase_admin
    from firebase_admin import auth as fb_auth

    if not _firebase_ready:
        if not firebase_admin._apps:
            firebase_admin.initialize_app(options={"projectId": settings.firebase_project_id})
        _firebase_ready = True
    try:
        claims = fb_auth.verify_id_token(token)
    except Exception as exc:  # expired, wrong project, malformed...
        log.info("Token rejected: %s", type(exc).__name__)
        raise _unauthorized("Invalid or expired sign-in token.") from None
    return CurrentUser(
        uid=claims["uid"],
        role=_role_from(claims.get("role")),
        name=claims.get("name") or claims.get("email", ""),
        email=claims.get("email", ""),
    )


def get_current_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized("Missing 'Authorization: Bearer <token>' header.")
    token = authorization.removeprefix("Bearer ").strip()
    if settings.auth_mode == "dev":
        return _verify_dev(token)
    return _verify_firebase(token, settings)


def require_role(*roles: Actor):
    """Dependency factory: 403 unless the caller has one of `roles`."""

    def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "forbidden",
                        "message": f"This action needs role: {', '.join(r.value for r in roles)}."},
            )
        return user

    return _check


def can_read_application(user: CurrentUser, app: dict) -> bool:
    """Same rule as firestore.rules (canReadApp). Keep the two in step."""
    if user.role == Actor.UNDERWRITER:
        return True
    if user.role == Actor.BROKER:
        return app.get("brokerId") == user.uid
    return app.get("borrowerId") == user.uid
