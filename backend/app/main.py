"""AL backend API (US-311). Run: uvicorn app.main:app --reload  (from backend/)

Interactive endpoint documentation is generated automatically at /docs.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import integrations
from .auth import CurrentUser, can_read_application, get_current_user, require_role
from .chain import ChainClient, make_chain
from .config import Settings, get_settings
from .decisions import UNDERWRITER_DECISIONS, MintFailed, apply_decision
from .deliberation import Committee, default_committee, deliberate
from .lifecycle import (
    LABELS,
    Actor,
    ActorNotAllowed,
    InvalidTransition,
    ReasonRequired,
    Status,
    TransitionError,
)
from .models import (
    AffordabilityOut,
    AffordabilityRequest,
    ApplicationCreate,
    ApplicationOut,
    ErrorResponse,
    PropertySpec,
    StatusChange,
    ValuationOut,
)
from .repository import FirestoreRepository, InMemoryRepository, NotFound, Repository

log = logging.getLogger("al")

ERRORS = {
    400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse},
    404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
}

_TRANSITION_STATUS = {
    InvalidTransition: status.HTTP_409_CONFLICT,
    ActorNotAllowed: status.HTTP_403_FORBIDDEN,
    ReasonRequired: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def _now() -> datetime:
    return datetime.now(UTC)


def _error(status_code: int, code: str, message: str, details=None,
           headers: dict[str, str] | None = None) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "details": details}}
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def _to_out(doc: dict) -> ApplicationOut:
    s = Status(doc["status"])
    return ApplicationOut.model_validate({**doc, "statusLabel": LABELS[s]})


def create_app(settings: Settings | None = None, repo: Repository | None = None,
               committee: Committee = default_committee,
               chain: ChainClient | None = None) -> FastAPI:
    """`committee` and `chain` can be replaced in tests. Production uses
    integrations.run_committee and the chain from AL_CHAIN_MODE."""
    settings = settings or get_settings()
    if chain is None:
        chain = make_chain(settings)
    if repo is None:
        repo = (FirestoreRepository(settings.firebase_project_id)
                if settings.repository == "firestore" else InMemoryRepository())
    if settings.auth_mode == "dev":
        log.warning("AL_AUTH_MODE=dev: fake tokens accepted. Never use this outside local tests.")

    app = FastAPI(
        title="AL: Agentic Lender API",
        version="0.1.0",
        description="Core API for AL-Mobile and AL-Web. Errors always use the ErrorResponse shape.",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # ----- one error format for everything (US-311 acceptance criterion) -----
    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]}
                   for e in exc.errors()]
        return _error(422, "validation_error", "Some fields are missing or invalid.", details)

    @app.exception_handler(HTTPException)
    async def _http(_: Request, exc: HTTPException):
        if isinstance(exc.detail, dict):
            return _error(exc.status_code, exc.detail.get("code", "error"),
                          exc.detail.get("message", ""), exc.detail.get("details"),
                          headers=exc.headers)  # keeps WWW-Authenticate on 401 (US-312)
        return _error(exc.status_code, "error", str(exc.detail), headers=exc.headers)

    @app.exception_handler(TransitionError)
    async def _transition(_: Request, exc: TransitionError):
        return _error(_TRANSITION_STATUS.get(type(exc), 409), exc.code, str(exc))

    @app.exception_handler(MintFailed)
    async def _mint_failed(_: Request, exc: MintFailed):
        return _error(502, exc.code, str(exc))

    @app.exception_handler(NotFound)
    async def _not_found(_: Request, exc: NotFound):
        return _error(404, "not_found", f"No application '{exc}'.")

    # ----- endpoints -----
    @app.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok", "repository": settings.repository, "authMode": settings.auth_mode}

    @app.post("/valuations", response_model=ValuationOut, status_code=201,
              tags=["valuations"], responses=ERRORS,
              summary="Fair-value estimate for a property (US-121, US-403)")
    def create_valuation(spec: PropertySpec, user: CurrentUser = Depends(get_current_user)):
        inputs = spec.model_dump(by_alias=True)
        result = integrations.estimate_value(inputs)
        saved = repo.save_valuation(
            {"inputs": inputs, **result, "requestedBy": user.uid}, _now())
        return ValuationOut(
            valuation_id=saved["id"], estimate=result["estimate"], low=result["low"],
            high=result["high"], model_version=result["modelVersion"],
            is_stub=result["modelVersion"] == integrations.STUB_MODEL_VERSION,
        )

    @app.post("/affordability", response_model=AffordabilityOut,
              tags=["applications"], responses=ERRORS,
              summary="Borrowing estimate from income, debts, deposit and term (US-111). "
                      "Saves nothing")
    def affordability(body: AffordabilityRequest,
                      user: CurrentUser = Depends(require_role(Actor.BORROWER))):
        result = integrations.affordability(
            body.buyer_type, body.gross_annual_income, body.monthly_debts, body.deposit,
            body.term_years)
        return AffordabilityOut.model_validate(result)

    @app.post("/applications", response_model=ApplicationOut, status_code=201,
              tags=["applications"], responses=ERRORS,
              summary="Borrower submits a loan application (US-112)")
    def create_application(
        body: ApplicationCreate,
        background: BackgroundTasks,
        user: CurrentUser = Depends(require_role(Actor.BORROWER)),
    ):
        data = body.model_dump(by_alias=True, exclude={"valuation_id"})
        data["valuation"] = None
        if body.valuation_id:
            v = repo.get_valuation(body.valuation_id)
            if v is None or v.get("requestedBy") != user.uid:
                raise HTTPException(400, {"code": "bad_valuation",
                                          "message": "valuationId not found for this user."})
            data["valuation"] = {k: v[k] for k in ("estimate", "low", "high", "modelVersion")}
            data["valuation"]["valuationId"] = v["id"]
        data |= {
            "borrowerId": user.uid,
            "borrowerName": user.name or user.email or user.uid,
            "brokerId": settings.default_broker_uid,
        }
        data["metrics"] = integrations.compute_metrics(data)
        doc = repo.create_application(data, user.uid, _now())
        # US-313: AI committee runs after the response is sent; status is still "applied" here.
        background.add_task(deliberate, doc["id"], repo, committee)
        return _to_out(doc)

    @app.get("/applications/{app_id}", response_model=ApplicationOut,
             tags=["applications"], responses=ERRORS,
             summary="Read one application (same access rule as Firestore)")
    def get_application(app_id: str, user: CurrentUser = Depends(get_current_user)):
        doc = repo.get_application(app_id)
        # 404 also when the caller may not see it, so IDs cannot be probed.
        if doc is None or not can_read_application(user, doc):
            raise NotFound(app_id)
        return _to_out(doc)

    @app.post("/applications/{app_id}/status", response_model=ApplicationOut,
              tags=["applications"], responses=ERRORS,
              summary="Change status through the state machine (US-302). "
                      "Approval mints the loan note (US-321, US-331)")
    def change_status(app_id: str, body: StatusChange,
                      user: CurrentUser = Depends(get_current_user)):
        doc = repo.get_application(app_id)
        if doc is None or not can_read_application(user, doc):
            raise NotFound(app_id)
        if body.to in UNDERWRITER_DECISIONS:
            updated = apply_decision(doc, body.to, user, body.reason, _now(), repo, chain,
                                     settings)
        else:
            updated = repo.change_status(app_id, body.to, user.role, user.uid, body.reason,
                                         _now())
        return _to_out(updated)

    return app


app = create_app()
