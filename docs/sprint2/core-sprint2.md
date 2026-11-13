# AL: Agentic Lender — Sprint 2, Core stories (Group 11)

Owner: Core lead (backend, database, blockchain). This file covers **only** the Core stories
US-312, US-313, US-321, US-322 and US-331. The other owners document their own stories.
Story points and the mock-up screen IDs for Sprint 2 screens are in `AL_Product_Backlog_v1.1` and
`AL_Mockup_Prototype_v1`; screen IDs below that are not certain are marked **TBC**.

All results below come from runs on **13 Nov 2026** on the Core branches
`core/us-313-auto-committee`, `core/us-321-loan-note`, `core/us-331-audit-hash`,
`core/us-251-mint-on-approval` and `core/us-312-auth-tests` (each built on the one before, apart
from US-313, which was merged in). Machine: Python 3.13, Node 20, Java 21. Docker was **not**
usable (the user is not in the `docker` group), so the anvil container was replaced by a local
Hardhat node (same chain ID 31337, same RPC port 8545) and the API was run with `uvicorn`.

## a) Status

| ID | Title | Status | Reason |
|---|---|---|---|
| US-312 | Firebase ID token verified on each request; role checked per endpoint | **Done** | Every endpoint tested (401/403/success); real emulator tokens verified; one bug found and fixed |
| US-313 | Application sent to the AI committee automatically after submission | **Done (Core side)** | Background run, validation, storage and status change all tested. The committee is a **stub** until the AI lead's agents (US-414) are connected |
| US-321 | ERC-721 loan note with principal, APR, term, pseudonymous borrower ID | **Done** | Contract + Hardhat tests; minted by the backend on approval, verified on a local chain |
| US-322 | AccessControl minter role | **Done** | Mint from an address without `MINTER_ROLE` reverts (tested) |
| US-331 | Canonical record hashed; hash on-chain; tx hash in Firestore | **Done** | Verified end to end: on-chain hash = Firestore hash = hash recomputed from Firestore |

"Done" here means the acceptance criteria pass in the tests below. Running the stack with
`docker compose` (anvil container) is **not verified** (see Known issues).

## b) Overall test results (13 Nov 2026)

| Suite | Command | Result |
|---|---|---|
| Backend unit + API | `cd backend && pytest -q` | **246 passed, 6 skipped** (skipped = emulator/chain tests, run separately below) |
| Backend vs Firestore + Auth emulators | `cd firebase && npx firebase emulators:exec --only auth,firestore --project demo-al-group11 "cd ../backend && .venv/bin/python -m pytest -q tests/test_firestore_repository.py tests/test_auth.py"` | **75 passed** |
| Backend vs local chain | Hardhat node + `npm run deploy:local`, then `AL_TEST_CHAIN=1 pytest -q tests/test_chain_web3.py` | **3 passed** |
| Contracts | `cd contracts && npx hardhat test` | **19 passing** |
| Firestore rules (regression) | `cd firebase && npm run test:rules` | **35 passed, 0 failed** |
| AI module (regression, not a Core story) | `cd ai && pytest -q` | 45 passed |

**End-to-end run** (real API process with `AL_REPOSITORY=firestore`, `AL_AUTH_MODE=firebase`,
`AL_CHAIN_MODE=web3`; Firestore + Auth emulators seeded with `scripts/seed_emulator.py`; LoanNote
deployed on a local Hardhat node; real ID tokens for `aoife@example.com` and `rachel@example.com`):

| # | Step | Result |
|---|---|---|
| 1 | Borrower `POST /applications` | Pass: 201 `AL-2026-0122`, status `applied`, response in 0.09 s |
| 2 | Committee runs in the background | Pass: status `ai_deliberated`, `aiRecommendation.decision = approve`, last history entry `role: system`, `deliberations/AL-2026-0122` with `isStub: true` and 4 steps |
| 3 | Underwriter approves | Pass: 200 `underwriter_approved`, `loanNote` with `tokenId: 1`, `txHash`, `auditHash`, `auditTxHash`, `chainStatus: minted` |
| 4 | Firestore after approval | Pass: status `underwriter_approved`, one `decisions` document with the same `auditTxHash` |
| 5 | On-chain loan | Pass: `getLoan(1) = (33500000, 390, 30, Minted)`, both transactions status 1 |
| 6 | Audit hash | Pass: `getAuditHash(1)` = Firestore `auditHash` = hash recomputed from the Firestore record (`64f2bd31fc5256de…`) |
| 7 | Tamper check | Pass: changing one field of the record gives a different hash |
| 8 | Approve again | Pass: 409 `invalid_transition`, no second mint |
| 9 | Borrower sets `funded` | Pass: 403 `actor_not_allowed` |
| 10 | Read without token | Pass: 401, header `WWW-Authenticate: Bearer` |

## c) Per-story details

### US-313 AI committee runs automatically after submission (Core)

- **Wire frame:** not applicable (backend). Consumers: the web pipeline W-02 (status column moves
  to "AI Deliberated" live) and the portal's AI committee / application detail screen (W-xx, **TBC**
  by the Web lead); the borrower app's status view (M-xx, **TBC**).
- **Design:**
  - `POST /applications` stores the application and schedules a FastAPI `BackgroundTask`, so the
    response is sent before the committee runs.
  - The background worker (`backend/app/deliberation.py`) calls `run_committee(application)`,
    checks the result with `validate_committee_result`, and calls
    `repository.record_deliberation(...)`.
  - `record_deliberation` is **one transaction**. It re-checks the state machine
    (`applied → ai_deliberated`, actor `system`), then writes `deliberations/{id}`, the 4 `steps`
    and `applications/{id}.aiRecommendation`, and appends the status change.
  - Any exception or invalid result is logged with the application ID, nothing is written, and the
    status stays `applied`.
  - Contract with the AI lead (US-414): `run_committee(application: dict) -> dict` returning
    `{decision, creditMemo, isStub, steps[4]}`. Each step has
    `{agent, model, output, reasoning, timestamp}` (`docs/data-model.md` §2.4). The committee never
    uses Firebase.
- **Implementation notes:**
  - The stub (`backend/app/integrations.py`) copies figures from `application["metrics"]` (calc
    module) and decides from the calc module's own pass/fail checks, so it does no arithmetic.
    Its output is marked `isStub: true` and the memo starts with `[STUB`.
  - Switching to `ai/committee.py` is one import line, written in a comment in `integrations.py`.
  - Three Sprint 1 tests used to move `applied → ai_deliberated` by hand. That now happens
    automatically, so the manual step was removed from them.

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-313-01 | Borrower submits (`test_submit_runs_committee_in_background`) | 201 with status `applied` and `aiRecommendation: null`; afterwards status `ai_deliberated` | Pass (also end-to-end step 1–2, 0.09 s response) |
| TC-313-02 | Same test: check stored result | `aiRecommendation {decision, deliberationId, completedAt}`; 4 steps stored in agent order; last history entry `by: system`, `role: system` | Pass |
| TC-313-03 | Committee raises an exception (`test_committee_failure_leaves_status_applied[committee_raises]`) | Status stays `applied`, no deliberation stored, error logged with the application ID | Pass |
| TC-313-04 | Committee returns decision `"maybe"` (`…[invalid_decision]`) | As TC-313-03 | Pass |
| TC-313-05 | A step without `reasoning` (`…[step_missing_field]`) | As TC-313-03 | Pass |
| TC-313-06 | Run the committee twice (`test_deliberate_twice_does_not_move_status_again`) | Second run refused by the state machine, nothing changes | Pass |
| TC-313-07 | Validator: 15 bad results (wrong decision, wrong types, non-UTC timestamp, missing or duplicate agent…) (`test_validator_rejects_bad_results`) | All rejected | Pass |
| TC-313-08 | Stub copies figures from metrics, decision follows calc checks (`test_stub_*`) | Figures equal `metrics`; approve / conditional / decline as per checks | Pass |
| TC-313-09 | Firestore transaction against the emulator (`test_record_deliberation_writes_everything_in_one_transaction`) | Application, deliberation and 4 step documents written; second run refused and nothing overwritten | Pass |

### US-321 Loan note ERC-721 (Core)

- **Wire frame:** not applicable (contract). Consumer: the portal shows `loanNote` after approval
  (W-xx, **TBC**).
- **Design:**
  - `contracts/contracts/LoanNote.sol`: OpenZeppelin 5.6 `ERC721` + `AccessControl`, Solidity
    0.8.28, Hardhat 2.29.
  - Each token stores `principalCents` (uint256), `aprBps` (uint16), `termYears` (uint8), `status`
    (enum Minted/Funded/Closed; only Minted is used in Sprint 2) and `borrowerRef` (bytes32).
  - `mint(to, …)` returns the token ID (from 1) and emits `LoanMinted`. `getLoan(tokenId)` reverts
    `ERC721NonexistentToken` for unknown IDs.
  - `scripts/deploy.js` refuses any chain whose ID is not 31337 and writes the git-ignored
    `contracts/deployments/local.json` (address + ABI) for the backend.
- **No personal data on-chain:** `borrowerRef = SHA-256(borrowerId + salt)`. The salt is only in a
  git-ignored `.env` (placeholder in `.env.example`), and the API refuses to mint without it.
- **Implementation notes (backend side):** an underwriter's approval mints the note to the bank's
  address with `principalCents = loanAmount × 100` (Decimal, no float error), `aprBps = 390`
  (config) and the application's `termYears`, before the status changes (`backend/app/decisions.py`).

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-321-01 | Mint and read every field (`stores every field and reads it back`) | principal, APR, term, status Minted, borrowerRef, owner all as minted | Pass |
| TC-321-02 | `LoanMinted` event, sequential IDs | Event with all arguments; IDs 1, 2 | Pass |
| TC-321-03 | Maximum values (uint256 / uint16 / uint8) | Stored without overflow | Pass |
| TC-321-04 | Zero principal / zero term / empty borrowerRef | Revert `InvalidLoanTerms` | Pass |
| TC-321-05 | `getLoan(99)` | Revert `ERC721NonexistentToken(99)` | Pass |
| TC-321-06 | `supportsInterface` ERC-721 / AccessControl / ERC-165 / `0xffffffff` | true / true / true / false | Pass |
| TC-321-07 | Approval through the API mints with the right terms (`test_approve_mints_and_stores_loan_note`) | principal 33,500,000 cents, 390 bps, 30 years, to the bank; borrowerRef = SHA-256(id+salt), does not contain the ID | Pass (FakeChain), and on the real contract in end-to-end step 5 |
| TC-321-08 | Deploy script against a local node | Contract deployed, `MINTER_ROLE` granted, `local.json` written | Pass (Hardhat node); **anvil not verified** |

### US-322 Minter role (Core)

- **Wire frame:** not applicable.
- **Design:** `MINTER_ROLE = keccak256("MINTER_ROLE")`; the deployer is `DEFAULT_ADMIN_ROLE` and
  grants `MINTER_ROLE` to the backend signer (`AL_CHAIN_MINTER_ADDRESS`, default the deployer).
  `mint` and `recordAudit` are `onlyRole(MINTER_ROLE)`.
- **Implementation notes:** the backend signs with `AL_CHAIN_SIGNER_KEY` from `.env`, or uses
  anvil's unlocked dev account when it is empty. Both paths were run against the local node.

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-322-01 | Mint from an address without the role | Revert `AccessControlUnauthorizedAccount(stranger, MINTER_ROLE)` | Pass |
| TC-322-02 | Admin mints without the role | Reverts as well | Pass |
| TC-322-03 | Admin grants the role; new minter mints | `RoleGranted` emitted; mint succeeds | Pass |
| TC-322-04 | Non-admin grants the role | Revert `AccessControlUnauthorizedAccount(…, DEFAULT_ADMIN_ROLE)` | Pass |
| TC-322-05 | Revoked minter mints | Reverts | Pass |

### US-331 Audit hash on-chain, tx hash in Firestore (Core)

- **Wire frame:** not applicable. Consumer: the portal can show `loanNote.auditHash` /
  `auditTxHash` (W-xx, **TBC**).
- **Design:**
  - `backend/app/audit.py`: `canonical_json` uses `json.dumps(sort_keys=True,
    separators=(",", ":"), ensure_ascii=False, allow_nan=False)` with datetimes as ISO 8601 UTC.
    It rejects naive datetimes, NaN, sets and non-string keys, so one record cannot have two
    hashes. `audit_hash` is the SHA-256 hex digest of that string.
  - Audit record = `{applicationId, decision {outcome, reason, by, at}, creditMemo (from the
    deliberation), valuation, metrics}`.
  - Contract: `recordAudit(tokenId, hash)` (minter only, token must exist, non-zero, write-once,
    emits `AuditRecorded`) and `getAuditHash(tokenId)`.
  - On approval the order is: state-machine check → hash → mint → `recordAudit` → one Firestore
    transaction (status, `decision`, `loanNote {tokenId, txHash, auditHash, auditTxHash,
    chainStatus}`, `decisions/{id}`). A chain failure returns `502 mint_failed`, and the status is
    unchanged.
- **Implementation notes:** `backend/app/chain.py` has a `ChainClient` interface with `Web3Chain`
  (web3 7.16) and `FakeChain`. `AL_CHAIN_MODE=fake` lets teammates demo without a chain.
  Conditional approval and decline record a decision but never mint.

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-331-01 | Same record twice (`test_same_record_same_hash`) | Same 64-char hash | Pass |
| TC-331-02 | Keys inserted in reverse order at every level | Same canonical JSON and hash | Pass |
| TC-331-03 | One changed field: top-level, nested 2 deep, 1 µs time change, trailing space, added / removed key (8 cases) | Different hash each time | Pass |
| TC-331-04 | Exact canonical string; datetime in UTC+1 and Firestore timestamp type | Expected string; same hash as UTC | Pass |
| TC-331-05 | Naive datetime / NaN / Infinity / set / int key | Rejected | Pass |
| TC-331-06 | Contract: record, read back, `AuditRecorded` event | Hash stored and returned | Pass |
| TC-331-07 | Contract: second `recordAudit` on the same token | Revert `AuditAlreadyRecorded`, hash unchanged | Pass |
| TC-331-08 | Contract: non-minter / missing token / zero hash | Reverts (role, `ERC721NonexistentToken`, `EmptyAuditHash`) | Pass |
| TC-331-09 | Approve: stored `auditHash` = hash of the record rebuilt from storage; equals the chain value (`test_stored_audit_hash_matches_recomputed_record_and_chain`) | Equal | Pass (FakeChain), and on the real contract in end-to-end step 6 |
| TC-331-10 | Tx hashes in Firestore | `loanNote.txHash`, `loanNote.auditTxHash`, `decisions/{id}.auditTxHash` set | Pass (unit test, Firestore emulator test, end-to-end step 4) |
| TC-331-11 | Mint fails / `recordAudit` fails / salt missing | 502 `mint_failed`, status unchanged, no decision stored | Pass |
| TC-331-12 | Decline and conditional approval | No mint, `decision` stored, `auditHash: null` | Pass |
| TC-331-13 | Not allowed (still `applied`, broker, approve twice, decline without reason) | 409 / 403 / 409 / 422 and the chain is never called | Pass |

### US-312 Authenticated requests (Core)

- **Wire frame:** not applicable. Affects every client screen that calls the API (M-02, M-03,
  W-01, W-02, and the Sprint 2 decision screens).
- **Design:** `backend/app/auth.py` (unchanged this sprint) verifies the Firebase ID token with
  the Admin SDK and reads the role from the `role` custom claim (no claim = borrower; `system` is
  never accepted from a token). `require_role` checks the role per endpoint, and the state machine
  checks it per status move. The role-per-endpoint table is in `docs/api.md` ("Who may call what").
- **Implementation notes:**
  - **Bug found by the new tests and fixed:** the global `HTTPException` handler in `main.py`
    dropped the `WWW-Authenticate: Bearer` header that `auth.py` sets on every 401. `_error()` now
    passes the exception's headers through; `auth.py` was not changed.
  - Before the fix, 51 of 72 auth tests failed, all on this header only. After it, all pass.

| TC | Steps | Expected | Result |
|---|---|---|---|
| TC-312-01 | Each of the 4 protected endpoints with no token | 401 `unauthenticated` + `WWW-Authenticate: Bearer` | Pass |
| TC-312-02 | Each protected endpoint × 11 malformed tokens (no Bearer, Basic, empty, garbage, bad dev formats, unknown role, `system` role, JWT in dev mode) | 401 | Pass (44 cases) |
| TC-312-03 | No token and an invalid body | 401 before any validation | Pass |
| TC-312-04 | Broker / underwriter submits an application | 403 `forbidden` | Pass |
| TC-312-05 | Owner borrower / assigned broker approves, conditionally approves, declines | 403 `actor_not_allowed`, status unchanged | Pass |
| TC-312-06 | Borrower marks an approved loan `funded` | 403 `actor_not_allowed` | Pass |
| TC-312-07 | Another borrower / broker reads or changes the status | 404 (IDs cannot be probed) | Pass |
| TC-312-08 | Right roles: valuation (all roles), submit (borrower), read (owner, assigned broker, underwriter), decide (underwriter) | 201 / 201 / 200 / 200 | Pass |
| TC-312-09 | Firebase mode with the Admin SDK call replaced: invalid token, dev token, no claim, `system` claim | 401 / 401 / borrower / 401 | Pass |
| TC-312-10 | Firebase mode against the **Auth emulator** with real ID tokens: borrower submits, broker submits, borrower approves, underwriter approves, tampered / non-JWT / dev token | 201 / 403 / 403 / 200 / 401 | Pass |

## d) Depends on teammate

| What | Owner | Status |
|---|---|---|
| Real AI committee `ai/committee.py` → `run_committee(application) -> dict` in the documented shape (replaces the stub with one import line) | AI lead (US-414/415) | Stub in use (`isStub: true`) |
| Approve button: spinner while minting, handle `502 mint_failed`, show `loanNote` | Web lead (US-251) | Message drafted (Step 4 report); backend ready |
| Show stub committee output as placeholder advice | Web + Mobile leads | Message drafted (Step 1 report) |

## e) Known issues

1. **Mint succeeds, then the Firestore write fails** (Firestore down, or another underwriter
   changed the status between the check and the write). The token exists on-chain but is not linked
   in Firestore. It is logged at CRITICAL with application ID, `tokenId`, both tx hashes and the
   `auditHash`; it is not repaired automatically. Tested (`test_firestore_failure_after_mint_is_logged`).
2. **Mint succeeds, `recordAudit` fails:** the token is left without an audit hash. It is logged as
   "orphaned"; the status is unchanged. Tested.
3. **Two approvals at exactly the same moment** could both mint; only one status change wins (Firestore
   transaction), so the other token becomes case 1.
4. **Docker not verified on the Core machine:** `docker compose up` (anvil container, API image
   with web3 on `python:3.12-slim`) was not run because the user is not in the `docker` group. The
   same flow passed against a local Hardhat node (chain ID 31337) and the emulators.
5. **Auth:** the `Bearer` prefix is case-sensitive (`bearer x` → 401), and revoked or disabled
   Firebase users are only rejected when their token expires (`check_revoked` is off).
6. **CI does not run the contract tests yet:** a `contracts` job in `.github/workflows/ci.yml`
   is needed (pending team approval).
7. **Root `.gitignore` has no `__pycache__/` entry**, so test runs leave untracked `ai/*/__pycache__`
   folders. Stage files by name, never with `git add -A`.
8. **The committee is a stub** until US-414; its decision is a placeholder, not AI advice.
