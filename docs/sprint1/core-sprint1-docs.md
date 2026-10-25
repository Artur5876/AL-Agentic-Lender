# Sprint 1 documentation — Core stories

Sprint 1 story notes reflect the implemented Android client and local emulator integration. Test
results below record the evidence currently reported for the local stack; repeat them in the
submission environment if formal test artefacts are required.

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

## US-101 Register

### Design

- Collect display name, email, password, and password confirmation.
- Create the Firebase Authentication account first, then write `users/{uid}` in Firestore.
- The profile contains only `uid`, `email`, `displayName`, `role: "borrower"`, and
  `createdAt: FieldValue.serverTimestamp()`. Firestore rules enforce ownership, token email,
  borrower role, allowed fields, and server timestamp.

### Implementation Notes

- Registration uses Firebase Authentication and Firestore Emulator in local development.
- Client validation checks required display name/email/password, email format, password strength
  (minimum eight characters), and confirmation match. Firebase duplicate-account errors are
  presented as registration failures.
- Successful profile creation completes registration and navigates into the app. Firestore profile
  creation failure is displayed to the user.

### Test Cases

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-101-01 | Register with a valid name, email, and matching strong password | Auth account is created and app continues | Verified against local Firebase Auth Emulator |
| TC-101-02 | Inspect `users/{uid}` in Firestore Emulator | Document ID and `uid` match; `email`, `displayName`, borrower `role`, and server `createdAt` are present | Profile creation and required fields verified |
| TC-101-03 | Submit blank/invalid email, weak password, or mismatched confirmation | Registration is blocked and a validation message is shown | Client validation implemented |
| TC-101-04 | Register an email already in use | Duplicate account is rejected with an error | Duplicate-account handling implemented |

## US-102 Login / Logout

### Design

- Authenticate borrowers with Firebase Authentication; local development routes Auth through the
  Firebase Auth Emulator.
- Keep the Firebase Auth session in the SDK and provide a logout action that signs out the current
  user.

### Implementation Notes

- Login validates required credentials and email format, calls
  `signInWithEmailAndPassword`, and reports invalid credentials separately from network failures.
- Logout calls `FirebaseAuth.signOut()`. Firebase Auth session persistence is provided by the SDK.
- The documented demo account `aoife@example.com` / `al-demo-pass` was used for local login
  verification.


### Test Cases

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-102-01 | Sign in with `aoife@example.com` / `al-demo-pass` against Auth Emulator | Sign-in succeeds and app enters the authenticated flow | Verified |
| TC-102-02 | Sign in with an invalid email/password pair | User remains signed out and sees an invalid-credentials message | Handling implemented |
| TC-102-03 | Restart the app after successful sign-in | Firebase Auth retains the session | Session persistence reported; authenticated-route restoration remains a navigation caveat |
| TC-102-04 | Use logout and inspect the Firebase Auth current user | `signOut()` clears the authenticated user | Sign-out call implemented; signed-in logout placement/route behavior needs confirmation |

## US-112 Submit Loan Application

### Design

- Require a successful Property Checker valuation before application submission.
- Carry the valuation and entered property details into the application form.
- Send borrower type, financials, property details, and the returned `valuationId` to
  `POST /applications`, authenticated with `Authorization: Bearer <Firebase ID token>`.
- Display the API-returned application reference, status, and status label.

### Implementation Notes

- `POST /applications` is integrated; this is no longer an unimplemented Sprint 1 item.
- The application client obtains a Firebase ID token before submission. The backend verifies the
  token, validates the payload, checks that an included valuation belongs to the borrower, persists
  the application, and returns the created record.
- The form validates buyer type and financial inputs, prevents repeat submission while loading, and
  displays API error messages and financial-field validation details.
- End-to-end testing confirmed successful authenticated submission using POST /applications. Docker logs 
  verified HTTP 201 Created responses and application creation with status "applied".

### Test Cases

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-112-01 | Sign in, obtain a valuation, enter valid financials, and submit | Authenticated `POST /applications` returns `201` | Verified in Docker logs |
| TC-112-02 | Inspect the response | Application reference, `status: "applied"`, and `statusLabel: "Applied"` are returned and shown | Successful response and applied status verified |
| TC-112-03 | Submit without required/valid input or with an invalid API constraint | Submission is blocked locally or API returns structured `422` details | Client and backend validation implemented |
| TC-112-04 | Submit a valuation ID not owned by the signed-in borrower | API rejects it with `400 bad_valuation` | Backend ownership validation implemented |

## US-121 Property Checker

### Design

- Collect county, floor area, bedrooms, property type, BER rating, and asking price.
- Validate the property details, then call authenticated `POST /valuations`.
- Retain the returned valuation ID and valuation figures with the entered property details for the
  subsequent application flow.

### Implementation Notes

- The Property Checker is integrated with the FastAPI `POST /valuations` endpoint; it does not
  submit placeholder valuation data.
- Client validation covers county, BER rating, floor area, bedrooms, and asking price. The API
  validates allowed counties/property types/BER ratings and numeric limits.
- The response fields are `valuationId`, `estimate`, `low`, `high`, `modelVersion`, and `isStub`.
  The mobile client displays the valuation figures and ID, and carries the result into US-112.
  `isStub` is returned by the API; the current Property Checker does not display that flag in its UI.
- Docker logs report `POST /valuations` returning `201 Created`. The verified local example returned
  estimate `380000`, low `360000`, high `400000`, model version `stub-0`, and `isStub: true`.
- The Property Checker integration is complete. The backend currently returns stub valuation values
  (isStub=true, modelVersion="stub-0") pending completion of US-403. 

### Test Cases

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-121-01 | Enter valid property details and request a valuation | Authenticated `POST /valuations` returns `201` and a valuation ID | Verified in Docker logs |
| TC-121-02 | Inspect/display the response | ID, estimate, low/high range, model version, and stub flag are available | Values verified; local result has `isStub: true` |
| TC-121-03 | Omit/enter invalid county, BER, floor area, bedroom count, or asking price | Client blocks invalid input or API returns a structured validation error | Client validation implemented; API validates its schema |
| TC-121-04 | Edit property input after receiving a valuation | Stale result is cleared; a new valuation is required before continuing | Implemented in Property Checker |

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

## Carried to Sprint 2

- **US-403 valuation model integration:** US-121 now calls `POST /valuations` and carries its
  response through the application flow, but the local API still reports `isStub: true` with model
  version `stub-0`. Replacing the stub estimate with the production model remains outstanding.
- **US-410 metrics calculation:** application metrics remain `null` until the calculation module is
  connected, as described in `docs/data-model.md`.
- **US-102 navigation follow-through:** confirm whether restored sessions should bypass the login
  route and whether logout should navigate to a signed-out screen. The SDK sign-out call exists, but
  the current navigation placement does not yet demonstrate that full UX.
