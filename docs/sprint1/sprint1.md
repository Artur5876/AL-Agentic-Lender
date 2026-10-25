# AL: Agentic Lender — Sprint 1 document (Group 11)

Sprint 1, weeks 3–5. Sprint goal (backlog section 5): *a borrower can register, get an ML
property valuation and submit an application that appears in the broker/underwriter pipeline;
data model, state machine, security rules and API running.* Planned: 19 stories, 67 points.

Status values are left as **TBC** until the Scrum Master confirms them with each owner at the
sprint review. Sections marked "To be written by …" are filled in by that owner.

## a) Sprint backlog

From `AL_Product_Backlog_v1.1`, section 8 (every story with Sprint = S1).

| ID | Title | Pts | Owner | Status |
|---|---|---|---|---|
| US-101 | Register with email and password | 3 | Mobile | TBC |
| US-102 | Log in and log out | 2 | Mobile | TBC |
| US-112 | Submit a loan application for a property | 5 | Mobile | TBC |
| US-121 | Enter property details and get a fair-value estimate | 5 | Mobile | TBC |
| US-201 | Portal login with a role-based view | 3 | Web | TBC |
| US-202 | Broker sees only own referred files | 3 | Web | TBC |
| US-203 | Underwriter has portfolio-wide access and sign-off | 2 | Web | TBC |
| US-211 | Queue of incoming applications | 5 | Web | TBC |
| US-212 | Group / filter the queue by status, LTV band and risk tier | 3 | Web | TBC |
| US-301 | Documented Firestore data model | 3 | Core | TBC |
| US-302 | Lifecycle enforced as a state machine | 5 | Core | TBC |
| US-303 | Role-based security rules | 5 | Core | TBC |
| US-311 | Documented REST API | 5 | Core | TBC |
| US-401 | Cleaned housing dataset | 3 | AI | TBC |
| US-402 | Valuation model that beats a baseline | 5 | AI | TBC |
| US-403 | Valuation endpoint | 3 | AI | TBC |
| US-410 | Tested calculation module (LTI, LTV, DTI, repayments) | 5 | AI | TBC |
| US-602 | Tests run automatically on GitHub | 2 | All | TBC |
| | **Total** | **67** | | |

US-341 (one-command local start) is a Sprint 0 story. Its test results are reported in
section c) because the Sprint 1 end-to-end test depends on it.

## b) Use cases

### UC-F1.1 Register / log in (US-101, US-102) — DRAFT - owner to check

| | |
|---|---|
| **Actor** | Borrower (Android app) |
| **Precondition** | App installed; Auth and Firestore reachable (emulators in local work) |
| **Main flow** | 1. Borrower opens M-01 and chooses Register. 2. Enters email and password (≥ 8 characters). 3. App creates the Firebase Auth account. 4. App writes `users/{uid}` with `uid`, `email`, `displayName`, `role: "borrower"`, `createdAt` (server time). 5. Borrower is signed in and stays signed in after restart until logout. |
| **Alternative flows** | A1 Invalid email or weak password: clear message, nothing created. A2 Wrong credentials at login: error message. A3 Profile write rejected by the security rules: error shown, borrower cannot continue. |
| **Postcondition** | Auth account and borrower profile exist |

### UC-F1.2 Submit a loan application (US-112) — DRAFT - owner to check

| | |
|---|---|
| **Actor** | Borrower |
| **Precondition** | Signed in; optionally has a `valuationId` from UC-F1.3 |
| **Main flow** | 1. Borrower fills M-03: buyer type, income, debts, deposit, loan amount, term. 2. App sends `POST /applications` with the ID token and the property from M-02. 3. API validates, stores the application with status Applied and returns its reference (e.g. `AL-2026-0122`). 4. App shows the reference and status. |
| **Alternative flows** | A1 Invalid field: API returns 422 with the field name; app highlights it. A2 Token missing/expired: 401, app asks the borrower to sign in again. A3 `valuationId` not the borrower's: 400 `bad_valuation`. |
| **Postcondition** | Application in Firestore with status `applied`; visible in the web pipeline (UC-F2.2) |

US-111 (affordability) belongs to this feature but is a Sprint 2 story.

### UC-F1.3 Fair-price property checker (US-121) — DRAFT - owner to check

| | |
|---|---|
| **Actor** | Borrower |
| **Main flow** | 1. Borrower enters county, floor area, bedrooms, property type, BER on M-02. 2. App validates the inputs (known counties, BER A1–G). 3. App calls `POST /valuations`. 4. App shows estimate, range and model version, with a loading state while waiting. |
| **Alternative flows** | A1 Invalid input: message, no call. A2 API error: error state with retry. A3 Response has `isStub: true`: app labels the numbers as placeholder values. |
| **Postcondition** | A `valuationId` the borrower can attach to the application |

US-122 (asking-price comparison) is a Sprint 2 story.

### UC-F2.1 Role-based portal access (US-201, US-202, US-203) — DRAFT - owner to check

| | |
|---|---|
| **Actors** | Broker, Underwriter |
| **Main flow** | 1. User signs in on W-01. 2. Portal reads the `role` custom claim from the ID token. 3. Broker is routed to a pipeline of only their assigned files; underwriter to the full pipeline with decision controls. |
| **Alternative flows** | A1 User has no role (a borrower): sent to a "no access" page. A2 Broker tries to read a file assigned to another broker: denied by the Firestore rules, not only hidden in the UI. |
| **Postcondition** | User sees only the tools and data for their role |

### UC-F2.2 Origination pipeline (US-211, US-212) — DRAFT - owner to check

| | |
|---|---|
| **Actors** | Broker, Underwriter |
| **Main flow** | 1. W-02 opens a live Firestore query (broker: `where brokerId == uid`). 2. Table shows applicant, property, amount, LTV, risk tier, status. 3. New or changed applications appear without a reload. 4. User filters by status, LTV band (≤ 80 %, 80–90 %, > 90 %) and risk tier. |
| **Alternative flows** | A1 `metrics` or `riskTier` still null: shown as "—" / "unknown" band. A2 Query rejected (missing index or rule): error message. |

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

### UC-F3.5 Start the local system (US-341, Sprint 0)

| | |
|---|---|
| **Actor** | Developer |
| **Main flow** | 1. Clone repo. 2. `docker compose up --build`. 3. Run seed script. 4. Open emulator UI, API docs, chain RPC. |
| **Alternative flow** | Port in use → change the port mapping in `docker-compose.yml`. |

### UC-F4.1 Property valuation (US-401, US-402, US-403) — DRAFT - owner to check

| | |
|---|---|
| **Actors** | AI developer (training); client app (prediction) |
| **Main flow** | 1. AI developer cleans the chosen housing dataset with a reproducible script. 2. Trains a regression model and compares it with the baseline (median price per county) on held-out data, reporting MAE for both. 3. The model is loaded by the backend; `POST /valuations` returns estimate, range and model version. |
| **Alternative flows** | A1 Invalid input (unknown county, BER "Z9"): 422. A2 Model not loaded: the endpoint returns the stub with `isStub: true`. |

### UC-F4.2 Calculation module (US-410) — DRAFT - owner to check

| | |
|---|---|
| **Actors** | Backend, AI agents, both front ends (through the API) |
| **Main flow** | 1. Backend passes the application to the calculation module. 2. Module returns LTI, LTV (against the lower of price and valuation), DTI, stressed DTI and monthly repayment, plus pass/fail checks against configurable Central Bank limits. 3. Backend stores them in `applications/{id}.metrics`. |
| **Alternative flows** | A1 Zero income: LTI and DTI are null and the checks fail. |

### UC-F6.1 Repository and automatic tests (US-601, US-602, US-603) — DRAFT - owner to check

| | |
|---|---|
| **Actor** | Any team member |
| **Main flow** | 1. Member pushes a branch and opens a pull request. 2. GitHub Actions runs the backend, ai, Firestore rules and web jobs. 3. The PR shows a green tick per job, or a red cross naming the folder that broke. 4. Reviewer merges only when the checks pass. |
| **Alternative flow** | A job fails: the author fixes it on the same branch and the checks run again. |

## c) Per-story details

Mock-up screens: `AL_Mockup_Prototype_v1` — M-01 Login/register, M-02 Property checker,
M-03 Loan application, W-01 Portal login, W-02 Origination pipeline.

All Core results below come from runs on 25 Oct 2026 on branch `sprint1-core-finish`.

### US-301 Documented Firestore data model (Core)

- **Wire frame:** not applicable (no screen). Design artefact: `docs/data-model.md`.
- **Design:** clients read Firestore directly and write through the API; roles as custom claims;
  camelCase fields; messages as a subcollection of the application; status stored as codes.
- **Implementation notes:** `docs/data-model.md` is still marked "draft, not yet agreed". The
  team sign-off (acceptance criterion 2) is not recorded yet. Open decisions are in its section 5.

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-301-01 | Each member reviews `data-model.md` against their stories | All fields their screens need exist; sign-off recorded in meeting notes | Not done yet |
| TC-301-02 | Run seed script, read documents from the emulator | Documents match the documented fields and types | Pass for `applications/AL-2026-0122`: `status`, `borrowerId`, `brokerId`, `valuation.valuationId`, `metrics` present as documented. Other collections not checked field by field |

### US-302 Lifecycle state machine (Core)

- **Wire frame:** not applicable. Design: transition table in `backend/app/lifecycle.py` (same as backlog §2.2).
- **Design:** `TRANSITIONS[current][target] = allowed actors`; `check_transition` checks
  move → actor → reason; the repository applies check and write atomically (Firestore
  transaction / lock).
- **Implementation notes:** pure Python, no Firebase imports; 49-pair exhaustive test.
  `cd backend && pytest -q` → **102 passed** (one deprecation warning from Starlette's test client).

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-302-01 | Check every (current, target) pair (`test_every_pair_matches_backlog`) | Exactly the 8 moves in §2.2 allowed | Pass |
| TC-302-02 | Applied → Funded (`test_skipping_a_stage_is_409`, `test_cannot_fund_before_approval`) | Rejected `invalid_transition` (409) | Pass |
| TC-302-03 | Broker sets Declined (`test_broker_cannot_decide`) | Rejected `actor_not_allowed` (403) | Pass |
| TC-302-04 | Underwriter declines with empty reason (`test_decline_without_reason_is_422`) | Rejected `reason_required` (422) | Pass |
| TC-302-05 | Declined/Closed → any (`test_final_states_have_no_exit`) | Rejected (final states) | Pass |
| TC-302-06 | Approve and Decline at the same moment (`test_concurrent_decisions_only_one_wins`) | One succeeds, one `invalid_transition` | Pass (in-memory repository; not yet run against the Firestore emulator) |

### US-303 Role-based security rules (Core)

- **Wire frame:** not applicable. Design: `firebase/firestore.rules`, role from custom claim, default deny.
- **Implementation notes:** tests in `firebase/tests/rules.test.mjs`, run with
  `npm run test:rules` (Firestore emulator, Java 21) → **35 passed, 0 failed**. Three tests were
  added this sprint for the borrower profile write: the current mobile registration map (no
  `displayName`, no `createdAt`) is rejected, a phone-clock `createdAt` is rejected, and an email
  that differs from the sign-in token is rejected.

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-303-01 | Anonymous reads an application | Denied | Pass |
| TC-303-02 | Borrower reads own / another's application | Allowed / denied | Pass |
| TC-303-03 | Broker reads assigned / unassigned application | Allowed / denied | Pass |
| TC-303-04 | Broker lists applications with and without `where brokerId == uid` | Allowed / denied | Pass |
| TC-303-05 | Underwriter lists all applications | Allowed | Pass |
| TC-303-06 | Any client creates or updates an application | Denied | Pass |
| TC-303-07 | Borrower registers with role "underwriter", or edits own role | Denied | Pass |
| TC-303-08 | Message on own application / other application / spoofed sender | Allowed / denied / denied | Pass |
| TC-303-09 | Review with rating 5 / 6 | Allowed / denied | Pass |
| TC-303-10 | Profile written without `displayName` and `createdAt` (current mobile registration) | Denied | Pass (denied: "Property displayName is undefined on object") |

### US-311 Documented REST API (Core)

- **Wire frame:** not applicable (API). Design: endpoint table and Mobile quick start in
  `docs/api.md`; live docs at `/docs`.
- **Design:** FastAPI + Pydantic validation; one error shape `{error:{code,message,details}}`;
  repository interface (memory for tests, Firestore for real).
- **Implementation notes:** valuation and metrics are still placeholders in
  `backend/app/integrations.py` (`estimate_value` returns fixed numbers with
  `modelVersion: "stub-0"`, `compute_metrics` returns `None`) until US-403 and US-410 are
  connected. End-to-end test against the emulators: signed in as `aoife@example.com` through
  the Auth emulator REST API, `POST /valuations` → 201 with `isStub: true`,
  `POST /applications` → 201 `AL-2026-0122`, status `applied`, valuation copied, `metrics: null`;
  the document was read back from the Firestore emulator with status `applied`, and the borrower
  could read it with rules on (200).

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-311-01 | `GET /health` | 200 `{"status":"ok"}` | Pass (`{"status":"ok","repository":"firestore","authMode":"firebase"}`) |
| TC-311-02 | Borrower submits valid application | 201, status `applied`, reference `AL-YYYY-NNNN` | Pass (unit test and live emulator run: `AL-2026-0122`) |
| TC-311-03 | Submit with `termYears` 40 / deposit −1 / unknown field | 422 with the field named | Pass (`test_submit_validation`, `test_unknown_fields_rejected`) |
| TC-311-04 | Submit with no token | 401 `unauthenticated` | Pass (`test_missing_token_is_401_in_standard_format`) |
| TC-311-05 | Broker or underwriter submits | 403 | Pass (`test_only_borrowers_submit`) |
| TC-311-06 | Other borrower / other broker reads application | 404 | Pass (`test_read_access`) |
| TC-311-07 | Valuation with county "Atlantis" or BER "Z9" | 422 | Pass (`test_valuation_rejects_invalid_input`) |
| TC-311-08 | Open `/docs` | Every endpoint listed with request/response schema | Not run this sprint |

### US-341 One-command local start (Core, Sprint 0)

- **Implementation notes:** `docker compose up --build` could not be run on the Core lead's
  machine in this test session (the user is not in the `docker` group). The same services were
  started without Docker (README Option B): Firebase emulators with `npm run emulators`, API with
  `uvicorn`. The seed script then ran successfully.

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-341-01 | Fresh clone, `docker compose up --build` on each member's machine | Emulator UI :4000, API :8000/docs, chain :8545 respond | Not run (Docker permission on test machine) |
| TC-341-02 | `python scripts/seed_emulator.py` | 10 users and 7 applications visible | Pass (seed output lists 10 users and applications AL-2026-0099 … AL-2026-0121) |
| TC-341-03 | `eth_chainId` call to :8545 | Result `0x7a69` (31337) | Not run (needs Docker) |

### US-602 Tests run automatically on GitHub (All)

- **Wire frame:** not applicable.
- **Design:** `.github/workflows/ci.yml`, triggered on every pull request and on pushes to `main`.
  One job per folder so a failure points straight at the subsystem: `backend` (Python 3.12,
  `pip install -r requirements-dev.txt`, `pytest -q`), `ai` (`pytest -q`), `firebase-rules`
  (Java 21 + Node 22, `npm ci`, `npm run test:rules`), `web` (Node 22, `npm ci`, `npm run build`).
- **Implementation notes:** every command was run locally before the workflow was added
  (Python 3.13, Node 20, Java 21): backend 102 passed; ai 27 passed; rules 35 passed;
  web build succeeded with a warning that the JS bundle is larger than 500 kB.

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-602-01 | Open a pull request | All four jobs run | See PR checks |
| TC-602-02 | All jobs on the Sprint 1 PR | Green | See PR checks |
| TC-602-03 | Push a commit that breaks a backend test | `backend` job fails, others still pass | Not run |

### US-101 Register — To be written by Mobile lead

- **Wire frame:** M-01
- **Test cases:**
- **Design:**
- **Implementation notes:**

### US-102 Log in / log out — To be written by Mobile lead

- **Wire frame:** M-01
- **Test cases:**
- **Design:**
- **Implementation notes:**

### US-112 Submit application — To be written by Mobile lead

- **Wire frame:** M-03
- **Test cases:**
- **Design:**
- **Implementation notes:**

### US-121 Property checker — To be written by Mobile lead

- **Wire frame:** M-02
- **Test cases:**
- **Design:**
- **Implementation notes:**

### US-201 Portal login — To be written by Web lead

- **Wire frame:** W-01
- **Test cases:**
- **Design:**
- **Implementation notes:**

### US-202 Broker sees own files only — To be written by Web lead

- **Wire frame:** W-01, W-02
- **Test cases:**
- **Design:**
- **Implementation notes:**

### US-203 Underwriter portfolio access — To be written by Web lead

- **Wire frame:** W-01, W-02
- **Test cases:**
- **Design:**
- **Implementation notes:**

### US-211 Application queue — To be written by Web lead

- **Wire frame:** W-02
- **Test cases:**
- **Design:**
- **Implementation notes:**

### US-212 Queue filters — To be written by Web lead

- **Wire frame:** W-02
- **Test cases:**
- **Design:**
- **Implementation notes:**

### US-401 Cleaned dataset — To be written by AI lead

- **Wire frame:** not applicable
- **Test cases:**
- **Design:**
- **Implementation notes:**

### US-402 Valuation model — To be written by AI lead

- **Wire frame:** not applicable
- **Test cases:**
- **Design:**
- **Implementation notes:**

### US-403 Valuation endpoint — To be written by AI lead

- **Wire frame:** M-02 (consumer)
- **Test cases:**
- **Design:**
- **Implementation notes:**

### US-410 Calculation module — To be written by AI lead

- **Wire frame:** M-03, W-02 (consumers)
- **Test cases:**
- **Design:**
- **Implementation notes:**

## d) Carried to Sprint 2

Based on the code in `develop` on 25 Oct 2026. The Scrum Master confirms the final list at the
sprint review.

| ID | Reason |
|---|---|
| US-101 | Mobile registration writes `users/{uid}` without `displayName` and `createdAt`, so the security rules reject it (TC-303-10). |
| US-112 | Mobile submit is a placeholder (`TODO US-112`, fixed reference `AL-2026-0122`); it does not call `POST /applications` yet. The backend endpoint works. |
| US-121 | Mobile property checker shows fixed numbers and does not call `POST /valuations`; the endpoint itself still returns the stub (depends on US-403). |
| US-401 | No dataset or cleaning script in the repository. |
| US-402 | No trained model or baseline comparison in the repository. |
| US-403 | `estimate_value` in `backend/app/integrations.py` returns fixed numbers (`modelVersion: "stub-0"`). |
| US-410 | Calculation functions, tests and configurable limits are done (`ai/calc`, 27 tests pass), but "exposed through the API" is not: `compute_metrics` returns `None`. |
| US-301 | `docs/data-model.md` still says "draft, not yet agreed"; team sign-off not recorded. |
| US-211 / US-212 | The LTV column and LTV-band filter need `metrics.ltv`, which stays null for new applications until US-410 is connected; `riskTier` is an open decision (data model §5). Web part itself: owner to confirm. |

Not decided from code (owner to confirm at the review): US-102, US-201, US-202, US-203.
US-602 counts as done once the CI checks pass on GitHub.

## e) Retrospective

### What went well

### What didn't go well

### Actions for Sprint 2
