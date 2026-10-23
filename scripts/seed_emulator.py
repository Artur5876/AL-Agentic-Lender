"""Fill the LOCAL Firebase emulators with fictional demo data.

Creates: 7 borrowers, 2 brokers, 1 underwriter (with role custom claims), the 7
applications shown on mock-up screen W-02 (one in every lifecycle state), and the
M-05 message thread. All names, emails and figures are fictional.

Usage (emulators must be running, see README):
    export FIRESTORE_EMULATOR_HOST=localhost:8080
    export FIREBASE_AUTH_EMULATOR_HOST=localhost:9099
    python scripts/seed_emulator.py

It REFUSES to run unless both emulator variables are set and the project ID starts
with "demo-", so it can never write to a real Firebase project. It wipes the
emulators first, so running it twice gives the same result.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.lifecycle import Actor, Status, check_transition, history_entry  # noqa: E402

PROJECT_ID = os.environ.get("AL_FIREBASE_PROJECT_ID", "demo-al-group11")
PASSWORD = "al-demo-pass"  # emulator-only demo password, not a real secret

USERS = [
    # uid, display name, role
    ("uw-rachel", "Rachel O'Connor", "underwriter"),
    ("broker-ciaran", "Ciarán Walsh", "broker"),
    ("broker-orla", "Orla Hayes", "broker"),
    ("borrower-aoife", "Aoife Byrne", "borrower"),
    ("borrower-sean", "Seán Doyle", "borrower"),
    ("borrower-niamh", "Niamh Kelly", "borrower"),
    ("borrower-darragh", "Darragh Quinn", "borrower"),
    ("borrower-emma", "Emma Nolan", "borrower"),
    ("borrower-patrick", "Patrick Ward", "borrower"),
    ("borrower-lucy", "Lucy Brennan", "borrower"),
]

# Mock-up W-02. Metrics are ILLUSTRATIVE values for building the UI, not output of
# the calculation module (US-410). Only AL-2026-0117 has the full set from W-03.
APPLICATIONS = [
    dict(ref="AL-2026-0121", borrower="borrower-sean", broker="broker-ciaran",
         status=Status.APPLIED, county="Dublin", ptype="apartment", beds=2, area=68,
         ber="C1", asking=345000, loan=310000, income=82000, debts=250, deposit=35000,
         ltv=0.899, risk="medium", days_ago=0),
    dict(ref="AL-2026-0117", borrower="borrower-aoife", broker="broker-ciaran",
         status=Status.AI_DELIBERATED, county="Cork", ptype="semi_detached", beds=3, area=110,
         ber="B2", asking=395000, loan=335000, income=95000, debts=300, deposit=60000,
         ltv=0.882, risk="low", days_ago=0,
         full_metrics=dict(lti=3.53, ltv=0.882, dti=0.237, stressedDti=0.289,
                           monthlyRepayment=1580),
         valuation=dict(estimate=380000, low=360000, high=400000, modelVersion="seed")),
    dict(ref="AL-2026-0115", borrower="borrower-niamh", broker="broker-ciaran",
         status=Status.UNDERWRITER_APPROVED, county="Galway", ptype="terraced", beds=3,
         area=95, ber="C2", asking=320000, loan=240000, income=78000, debts=0,
         deposit=80000, ltv=0.75, risk="low", days_ago=1),
    dict(ref="AL-2026-0112", borrower="borrower-darragh", broker="broker-orla",
         status=Status.CONDITIONALLY_APPROVED, county="Kildare", ptype="detached", beds=4,
         area=180, ber="B3", asking=563000, loan=520000, income=140000, debts=650,
         deposit=43000, ltv=0.924, risk="high", days_ago=1),
    dict(ref="AL-2026-0108", borrower="borrower-emma", broker="broker-ciaran",
         status=Status.FUNDED, county="Limerick", ptype="bungalow", beds=3, area=120,
         ber="C3", asking=300000, loan=210000, income=70000, debts=0, deposit=90000,
         ltv=0.70, risk="low", days_ago=2),
    dict(ref="AL-2026-0104", borrower="borrower-patrick", broker="broker-orla",
         status=Status.DECLINED, county="Cork", ptype="apartment", beds=2, area=72,
         ber="D1", asking=313500, loan=295000, income=68000, debts=900, deposit=18500,
         ltv=0.941, risk="high", days_ago=2),
    dict(ref="AL-2026-0099", borrower="borrower-lucy", broker="broker-orla",
         status=Status.CLOSED, county="Waterford", ptype="semi_detached", beds=3, area=105,
         ber="B3", asking=325000, loan=260000, income=88000, debts=200, deposit=65000,
         ltv=0.80, risk="low", days_ago=24),
]

# Path from Applied to each target, with who makes each move (checked by US-302 code).
PATHS = {
    Status.APPLIED: [],
    Status.AI_DELIBERATED: [(Status.AI_DELIBERATED, Actor.SYSTEM, None)],
    Status.UNDERWRITER_APPROVED: [(Status.AI_DELIBERATED, Actor.SYSTEM, None),
                                  (Status.UNDERWRITER_APPROVED, Actor.UNDERWRITER, None)],
    Status.CONDITIONALLY_APPROVED: [(Status.AI_DELIBERATED, Actor.SYSTEM, None),
                                    (Status.CONDITIONALLY_APPROVED, Actor.UNDERWRITER,
                                     "Approve subject to two more payslips.")],
    Status.FUNDED: [(Status.AI_DELIBERATED, Actor.SYSTEM, None),
                    (Status.UNDERWRITER_APPROVED, Actor.UNDERWRITER, None),
                    (Status.FUNDED, Actor.SYSTEM, None)],
    Status.DECLINED: [(Status.AI_DELIBERATED, Actor.SYSTEM, None),
                      (Status.DECLINED, Actor.UNDERWRITER, "LTV above the 90% limit.")],
    Status.CLOSED: [(Status.AI_DELIBERATED, Actor.SYSTEM, None),
                    (Status.UNDERWRITER_APPROVED, Actor.UNDERWRITER, None),
                    (Status.FUNDED, Actor.SYSTEM, None),
                    (Status.CLOSED, Actor.SYSTEM, None)],
}


def _guard() -> tuple[str, str]:
    fs_host = os.environ.get("FIRESTORE_EMULATOR_HOST")
    auth_host = os.environ.get("FIREBASE_AUTH_EMULATOR_HOST")
    if not fs_host or not auth_host or not PROJECT_ID.startswith("demo-"):
        sys.exit("Refusing to run: set FIRESTORE_EMULATOR_HOST and FIREBASE_AUTH_EMULATOR_HOST, "
                 "and use a demo-* project ID. This script only writes to local emulators.")
    return fs_host, auth_host


def _wipe(fs_host: str, auth_host: str) -> None:
    for url in (
        f"http://{fs_host}/emulator/v1/projects/{PROJECT_ID}/databases/(default)/documents",
        f"http://{auth_host}/emulator/v1/projects/{PROJECT_ID}/accounts",
    ):
        urllib.request.urlopen(urllib.request.Request(url, method="DELETE"), timeout=10)


def _history(target: Status, start: datetime, borrower_uid: str) -> list[dict]:
    entries = [history_entry(Status.APPLIED, start, borrower_uid, Actor.BORROWER).to_dict()]
    current, t = Status.APPLIED, start
    for nxt, actor, reason in PATHS[target]:
        check_transition(current, nxt, actor, reason)  # seed data must obey the state machine
        t += timedelta(hours=3)
        by = "uw-rachel" if actor == Actor.UNDERWRITER else "system"
        entries.append(history_entry(nxt, t, by, actor, reason).to_dict())
        current = nxt
    return entries


def main() -> None:
    fs_host, auth_host = _guard()
    import firebase_admin
    from firebase_admin import auth
    from google.auth.credentials import AnonymousCredentials
    from google.cloud import firestore

    _wipe(fs_host, auth_host)
    firebase_admin.initialize_app(options={"projectId": PROJECT_ID})
    db = firestore.Client(project=PROJECT_ID, credentials=AnonymousCredentials())
    now = datetime.now(UTC).replace(microsecond=0)
    names = {}

    for uid, name, role in USERS:
        email = f"{uid.split('-', 1)[1]}@example.com"
        auth.create_user(uid=uid, email=email, password=PASSWORD, display_name=name)
        if role != "borrower":
            auth.set_custom_user_claims(uid, {"role": role})
        db.document(f"users/{uid}").set({"uid": uid, "email": email, "displayName": name,
                                         "role": role, "createdAt": now})
        names[uid] = name

    for a in APPLICATIONS:
        start = now - timedelta(days=a["days_ago"], hours=12)
        history = _history(a["status"], start, a["borrower"])
        metrics = a.get("full_metrics") or {"ltv": a["ltv"], "lti": None, "dti": None,
                                            "stressedDti": None, "monthlyRepayment": None}
        db.document(f"applications/{a['ref']}").set({
            "reference": a["ref"],
            "borrowerId": a["borrower"], "borrowerName": names[a["borrower"]],
            "brokerId": a["broker"],
            "status": a["status"].value, "statusHistory": history,
            "buyerType": "first_time",
            "financials": {"grossAnnualIncome": a["income"], "monthlyDebts": a["debts"],
                           "deposit": a["deposit"], "loanAmount": a["loan"], "termYears": 30},
            "property": {"county": a["county"], "floorAreaM2": a["area"], "bedrooms": a["beds"],
                         "propertyType": a["ptype"], "ber": a["ber"], "askingPrice": a["asking"]},
            "valuation": a.get("valuation"),
            "metrics": {**metrics, "source": "seed-illustrative"},
            "riskTier": a["risk"],
            "aiRecommendation": None, "decision": None, "loanNote": None, "payment": None,
            "createdAt": start, "updatedAt": history[-1]["at"],
        })

    db.document("counters/applications-2026").set({"next": 122})

    thread = db.collection("applications/AL-2026-0117/messages")
    messages = [
        ("broker-ciaran", "broker",
         "Hi Aoife, I'm handling your application. Let me know if you have questions."),
        ("borrower-aoife", "borrower",
         "Thanks! How long does the underwriter review usually take?"),
        ("broker-ciaran", "broker",
         "Usually 1-2 working days. You'll see the status change in the app."),
    ]
    for i, (sender, role, text) in enumerate(messages):
        thread.add({"senderId": sender, "senderRole": role, "text": text,
                    "sentAt": now - timedelta(minutes=30 - 10 * i)})

    print(json.dumps({
        "project": PROJECT_ID,
        "password_for_all_demo_users": PASSWORD,
        "logins": {f"{u.split('-', 1)[1]}@example.com": r for u, _, r in USERS},
        "applications": [a["ref"] for a in APPLICATIONS],
    }, indent=2))


if __name__ == "__main__":
    main()
