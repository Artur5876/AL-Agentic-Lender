# Sprint 1 documentation — Core stories (DRAFT)

Paste-ready sections for the Sprint 1 document, keyed by story ID. **Draft:** fill the "Result"
columns only after the team has run the tests, and edit wording so it matches what was actually
built and by whom. Check the module's AI-use rules before this goes into a graded submission.

## Use cases

### UC-F3.1 Manage application lifecycle (US-301, US-302, US-303, US-304)

| | |
|---|---|
| **Actors** | Borrower, Broker, Underwriter, System (backend / AI committee) |
| **Precondition** | User signed in; role taken from the sign-in token |
| **Main flow** | 1. Borrower submits an application → status Applied. 2. System runs the AI committee → AI Deliberated. 3. Underwriter approves, conditionally approves or declines (reason required for the last two). 4. System/underwriter marks Funded, then Closed. Every change is appended to the status history. |
| **Alternative flows** | A1 Invalid move (e.g. Applied → Funded): rejected, status unchanged. A2 Actor not allowed (broker tries to decide): rejected. A3 Decline without reason: rejected. A4 Two underwriters act at once: exactly one change is applied. |
| **Postcondition** | Status and history stored in Firestore; all clients see the change live |

### UC-F3.2 Submit and read through the API (US-311, US-312)

| | |
|---|---|
| **Actors** | Borrower (mobile), Broker / Underwriter (web) |
| **Main flow** | 1. Client sends request with Firebase ID token. 2. API verifies token and role. 3. API validates input. 4. API writes to Firestore and returns the stored record. |
| **Alternative flows** | Missing/invalid token → 401. Wrong role → 403. Invalid input → 422 listing the fields. Not found / not yours → 404. |

### UC-F3.5 Start the local system (US-341)

| | |
|---|---|
| **Actor** | Developer |
| **Main flow** | 1. Clone repo. 2. `docker compose up --build`. 3. Run seed script. 4. Open emulator UI, API docs, chain RPC. |
| **Alternative flow** | Port in use → change the port mapping in `docker-compose.yml`. |

## US-301 Documented Firestore data model

- **Wire frame:** not applicable (no screen). Design artefact: `docs/data-model.md`.
- **Design:** clients read Firestore directly, write through the API; roles as custom claims;
  camelCase fields; messages as a subcollection of the application; status stored as codes.
- **Implementation notes:** agreed at team meeting on <date>; open decisions recorded in section 5.

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-301-01 | Each member reviews `data-model.md` against their stories | All fields their screens need exist; sign-off recorded in meeting notes | |
| TC-301-02 | Run seed script, open Emulator UI | Documents match the documented fields and types | |

## US-302 Lifecycle state machine

- **Wire frame:** not applicable. Design: transition table in `backend/app/lifecycle.py` (same as backlog §2.2).
- **Design:** `TRANSITIONS[current][target] = allowed actors`; `check_transition` checks move → actor → reason;
  repository applies check + write atomically (Firestore transaction / lock).
- **Implementation notes:** pure Python, no Firebase imports; 49-pair exhaustive test.

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-302-01 | Check every (current, target) pair (`test_every_pair_matches_backlog`) | Exactly the 8 moves in §2.2 allowed | |
| TC-302-02 | Applied → Funded | Rejected `invalid_transition` (409) | |
| TC-302-03 | Broker sets Declined | Rejected `actor_not_allowed` (403) | |
| TC-302-04 | Underwriter declines with empty reason | Rejected `reason_required` (422) | |
| TC-302-05 | Declined/Closed → any | Rejected (final states) | |
| TC-302-06 | Approve and Decline at the same moment | One succeeds, one `invalid_transition` | |

## US-303 Role-based security rules

- **Wire frame:** not applicable. Design: `firebase/firestore.rules`, role from custom claim, default deny.
- **Implementation notes:** tests in `firebase/tests/rules.test.mjs`, run with `npm run test:rules` (Firestore emulator).

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-303-01 | Anonymous reads an application | Denied | |
| TC-303-02 | Borrower reads own / another's application | Allowed / denied | |
| TC-303-03 | Broker reads assigned / unassigned application | Allowed / denied | |
| TC-303-04 | Broker lists applications with and without `where brokerId == uid` | Allowed / denied | |
| TC-303-05 | Underwriter lists all applications | Allowed | |
| TC-303-06 | Any client creates or updates an application | Denied | |
| TC-303-07 | Borrower registers with role "underwriter", or edits own role | Denied | |
| TC-303-08 | Message on own application / other application / spoofed sender | Allowed / denied / denied | |
| TC-303-09 | Review with rating 5 / 6 | Allowed / denied | |

## US-311 Documented REST API

- **Wire frame:** not applicable (API). Design: endpoint table in `docs/api.md`; live docs at `/docs`.
- **Design:** FastAPI + Pydantic validation; one error shape `{error:{code,message,details}}`;
  repository interface (memory for tests, Firestore for real).
- **Implementation notes:** valuation and metrics are placeholders in `backend/app/integrations.py`
  until US-403 and US-410 are connected.

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-311-01 | `GET /health` | 200 `{"status":"ok"}` | |
| TC-311-02 | Borrower submits valid application | 201, status `applied`, reference `AL-YYYY-NNNN` | |
| TC-311-03 | Submit with `termYears` 40 / deposit −1 / unknown field | 422 with the field named | |
| TC-311-04 | Submit with no token | 401 `unauthenticated` | |
| TC-311-05 | Broker or underwriter submits | 403 | |
| TC-311-06 | Other borrower / other broker reads application | 404 | |
| TC-311-07 | Valuation with county "Atlantis" or BER "Z9" | 422 | |
| TC-311-08 | Open `/docs` | Every endpoint listed with request/response schema | |

## US-341 One-command local start (Sprint 0)

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-341-01 | Fresh clone, `docker compose up --build` on each member's machine | Emulator UI :4000, API :8000/docs, chain :8545 respond | |
| TC-341-02 | `python scripts/seed_emulator.py` | 10 users and 7 applications visible in Emulator UI | |
| TC-341-03 | `curl -X POST localhost:8545 -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","method":"eth_chainId","id":1}'` | Result `0x7a69` (31337) | |
