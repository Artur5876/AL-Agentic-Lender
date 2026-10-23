# AL: Agentic Lender — Group 11

MTU Year 3 Group Project 2026. Academic prototype: synthetic data, test-mode payments, local
blockchain. Not a real lending service. Plan and story IDs: `AL_Product_Backlog_v1.1`.

## Repository layout

| Folder | What | Owner |
|---|---|---|
| `backend/` | FastAPI service: API, state machine, Firestore access | Core lead |
| `firebase/` | Firestore security rules, indexes, emulator config, rules tests | Core lead |
| `scripts/` | Demo-data seed script for the emulators | Core lead |
| `contracts/` | Solidity loan note + audit registry (Sprint 2) | Core lead |
| `ai/` | Valuation model, calculation module, agents | AI lead |
| `mobile/` | Android / Kotlin borrower app | Mobile lead |
| `web/` | React portal for brokers and underwriters | Web lead |
| `docs/` | Data model, API guide, sprint documentation | All |

## Run it locally

### Option A — everything with Docker (US-341)

```bash
docker compose up --build
```

Emulator UI http://localhost:4000 · API docs http://localhost:8000/docs · chain http://localhost:8545

### Option B — without Docker

Needs Python 3.12+, Node 22+, Java 21+.

```bash
# 1. Firebase emulators (terminal 1)
cd firebase && npm install && npm run emulators

# 2. Backend API (terminal 2)
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
export AL_REPOSITORY=firestore AL_DEFAULT_BROKER_UID=broker-ciaran
export FIRESTORE_EMULATOR_HOST=localhost:8080 FIREBASE_AUTH_EMULATOR_HOST=localhost:9099
uvicorn app.main:app --reload
```

### Seed demo data (after the emulators are running)

```bash
export FIRESTORE_EMULATOR_HOST=localhost:8080 FIREBASE_AUTH_EMULATOR_HOST=localhost:9099
python scripts/seed_emulator.py
```

Creates fictional users (password `al-demo-pass`, emulator only) and the 7 applications from mock-up W-02:

| Login | Role |
|---|---|
| rachel@example.com | underwriter |
| ciaran@example.com, orla@example.com | broker |
| aoife@example.com, sean@example.com, … | borrower |

## Tests

```bash
cd backend && pytest -q            # state machine + API (no Firebase needed)
cd firebase && npm run test:rules  # security rules against the Firestore emulator (needs Java 21+)
```

GitHub Actions runs both on every pull request (`.github/workflows/ci.yml`).

## Rules for everyone

- Work on a branch, open a pull request, get one review before merging to `main` (Definition of Done).
- Never commit `.env`, service-account JSON files, API keys or wallet keys. Copy `.env.example`.
- Synthetic data only. Stripe test mode only.
- Read `docs/data-model.md` before writing to Firestore, and `docs/api.md` before calling the API.
