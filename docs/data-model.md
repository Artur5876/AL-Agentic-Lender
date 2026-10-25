# AL data model (US-301) — draft v0.1 for team agreement

Status: **draft, not yet agreed.**

## 1. Three rules that everything else follows

1. **Clients read Firestore directly; clients write through the API.**
   Mobile and web use Firestore listeners for live data (US-132, US-211). Anything that changes an
   application (create, status change, decision, payment) goes through the Python API (US-311).
   The API writes with the Firebase Admin SDK, which bypasses security rules, so the rules can simply
   say "clients may not write applications". This is what makes the state machine (US-302) impossible
   to skip.
   Exceptions (direct client writes, checked by security rules): the borrower's own `users` profile at
   registration (US-101), chat messages (US-141/255), support requests (US-161) and reviews (US-162).
2. **Roles live in the Firebase Auth token as a custom claim `role`.**
   Values: `broker`, `underwriter`. A user with no claim is a `borrower`. Claims can only be set with
   the Admin SDK (backend or seed script), so nobody can promote themselves. The `users/{uid}.role`
   field is a copy for display only; security decisions never use it.
3. **Field names are camelCase; money is in euro as numbers; timestamps are Firestore timestamps
   set by the server.** Percentages are stored as fractions (0.882 = 88.2%). Status values are the
   lowercase codes in section 3, never display text.

## 2. Collections

| Collection | Who writes | Who reads | Sprint |
|---|---|---|---|
| `users/{uid}` | Borrower creates own (rules); seed script for staff | Owner; underwriters | S1 |
| `applications/{applicationId}` | API only | Borrower (own), broker (assigned), underwriters | S1 |
| `applications/{id}/messages/{messageId}` | Borrower and staff of that application (rules) | Same | S3 |
| `valuations/{valuationId}` | API only | Requester; staff | S1 |
| `deliberations/{applicationId}` + `/steps/{stepId}` | API / AI engine only | Staff who can see the application | S2 |
| `decisions/{decisionId}` | API only | Staff who can see the application | S2 |
| `payments/{paymentId}` | API only (after Stripe confirms) | Owner; underwriters | S3 |
| `supportRequests/{id}` | Borrower creates own (rules) | Owner; staff | S3 |
| `reviews/{id}` | Borrower creates own (rules) | Owner; underwriters | S3 |
| `counters/{name}` | API only | Nobody | S1 |

Messages are a subcollection of the application (not a top-level `messages` collection as listed in
the backlog) so that they automatically have the same readers as the application.
`supportRequests` is added because US-161 needs it and the backlog list did not include it.

### 2.1 `users/{uid}` — S1

| Field | Type | Notes |
|---|---|---|
| `uid` | string | Same as the document ID and the Firebase Auth UID |
| `email` | string | Must equal the email in the sign-in token |
| `displayName` | string | Shown in the portal and messages |
| `role` | string | Display copy only. Borrowers must write `"borrower"` |
| `createdAt` | timestamp | Must be `FieldValue.serverTimestamp()` |

Borrower registration (US-101): create the Firebase Auth account, then create this document with the
user's own UID. The security rules reject any other role or extra fields.
Staff accounts (brokers, underwriters) are created only by `scripts/seed_emulator.py` (later an admin script).

### 2.2 `applications/{applicationId}` — S1

The document ID is the human reference, e.g. `AL-2026-0117` (matches the mock-up URLs).

| Field | Type | Set by | Notes |
|---|---|---|---|
| `reference` | string | API | Same as document ID |
| `borrowerId` | string | API | UID from the caller's token |
| `borrowerName` | string | API | Copied so the pipeline needs no extra read |
| `brokerId` | string or null | API | Assigned broker UID (US-304). S1: default broker from config, or null |
| `status` | string | API | Code from section 3 |
| `statusHistory` | array of map | API | `{status, at, by, role, reason}` appended on every change |
| `buyerType` | string | client input | `first_time` or `subsequent` |
| `limitedBy` | string | calculation module (US-410) | `lti` or `deposit` |
| `financials` | map | client input | `grossAnnualIncome`, `monthlyDebts`, `deposit`, `loanAmount`, `termYears` |
| `property` | map | client input | `county`, `floorAreaM2`, `bedrooms`, `propertyType`, `ber`, `askingPrice` |
| `valuation` | map or null | API | Copy of the valuation used: `valuationId`, `estimate`, `low`, `high`, `modelVersion` |
| `metrics` | map | API (US-410) | `lti`, `ltv`, `dti`, `stressedDti`, `monthlyRepayment`, and `checks` (`ltiOk`, `ltvOk`, `dtiOk`, `stressedDtiOk`). `lti`/`dti`/`stressedDti` are null when income is 0. Seed documents carry illustrative numbers marked `source: "seed-illustrative"` and no `checks` |
| `riskTier` | string or null | open decision | `low`, `medium`, `high`. Who sets it is not in the backlog — see section 5 |
| `aiRecommendation` | map or null | API (US-313/414) | `decision`, `deliberationId`, `completedAt` — S2 |
| `decision` | map or null | API (US-251/252) | `outcome`, `reason`, `by`, `at` — S2 |
| `loanNote` | map or null | API (US-251/331) | `tokenId`, `txHash`, `auditHash`, `auditTxHash`, `chainStatus` — S2 |
| `payment` | map or null | API (US-151) | `status`, `paymentId` — S3 |
| `createdAt`, `updatedAt` | timestamp | API | Server time |

Allowed input values:
- `county`: the 26 counties of Ireland, spelled as in `backend/app/models.py` (e.g. `Cork`, `Dublin`).
- `propertyType`: `apartment`, `terraced`, `semi_detached`, `detached`, `bungalow`.
- `ber`: `A1 A2 A3 B1 B2 B3 C1 C2 C3 D1 D2 E1 E2 F G`.
- `termYears`: 5–35. All money amounts ≥ 0; `loanAmount` and `askingPrice` > 0.

### 2.3 `valuations/{valuationId}` — S1

`inputs` (the property map without asking price), `estimate`, `low`, `high`, `modelVersion`,
`requestedBy` (UID), `createdAt`. The mobile app sends the `valuationId` with the application, and the
API copies the result into `applications/{id}.valuation`.

### 2.4 Later sprints (shape only, owners fill in details)

- `deliberations/{applicationId}`: `status`, `startedAt`, `completedAt`, `finalDecision`, `creditMemo`.
  `steps/{stepId}`: `agent`, `model`, `promptVersion`, `input`, `output`, `reasoning`, `verdict`, `at`
  (US-415, AI lead).
- `decisions/{decisionId}`: `applicationId`, `brokerId` (copied, for the rules), `outcome`, `reason`, `by`, `at`, `auditHash`, `auditTxHash` (US-251–253, US-331).
- `applications/{id}/messages/{messageId}`: `senderId`, `senderRole`, `text` (1–2000 chars), `sentAt` (server time).
- `supportRequests/{id}`: `borrowerId`, `applicationId` (optional), `category`, `description`, `status: "open"`, `createdAt`.
  The reference shown to the user (US-161) is the document ID.
- `reviews/{id}`: `borrowerId`, `rating` (1–5), `comment` (optional, ≤ 1000 chars), `createdAt`.
- `payments/{paymentId}`: `applicationId`, `borrowerId`, `amount`, `currency`, `stripePaymentIntentId`, `status`, `createdAt`. Test mode only.

## 3. Status codes (lifecycle from backlog section 2.2)

| Code (stored) | Label (shown) | Allowed next | Who may move it there |
|---|---|---|---|
| `applied` | Applied | `ai_deliberated` | system (AI committee via backend) |
| `ai_deliberated` | AI Deliberated | `underwriter_approved`, `conditionally_approved`, `declined` | underwriter |
| `conditionally_approved` | Conditionally Approved | `underwriter_approved`, `declined` | underwriter |
| `underwriter_approved` | Underwriter Approved | `funded` | system or underwriter |
| `funded` | Funded | `closed` | system or underwriter |
| `declined` | Declined | — final | — |
| `closed` | Closed | — final | — |

Declining or conditionally approving requires a written reason (US-252). The single source of this
table in code is `backend/app/lifecycle.py`.

## 4. Queries the clients will run (must match the security rules)

Firestore rejects a query that *could* return a document the user may not read. So:

| Who | Query |
|---|---|
| Borrower | `applications where borrowerId == myUid orderBy createdAt desc` |
| Broker | `applications where brokerId == myUid orderBy updatedAt desc` (the `where` is required) |
| Underwriter | `applications orderBy updatedAt desc` (optionally `where status == ...`) |

Composite indexes for these are in `firebase/firestore.indexes.json`.

## 5. Open decisions for the team call

1. Who sets `riskTier`, and from what? Not defined in the backlog. Proposal: the AI committee result (S2);
   null until then, shown as "—".
2. How a broker gets assigned in S1 (US-304 is S3). Proposal: `AL_DEFAULT_BROKER_UID` config, so every
   new application goes to the one demo broker.
3. Are the 26 counties enough, or does Dublin need splitting for the valuation model? (AI lead)
   S1: kept at 26 counties, because the Property Price Register gives county, not district,
   for the price levels the model is built on.
4. Does the valuation response also return the asking-price comparison (US-122), so the 10% threshold
   lives in one place? Proposal: yes, from the calculation module (US-410).
