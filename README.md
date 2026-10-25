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
export PYTHONPATH=../ai          # calculation module + valuation model; Windows: $env:PYTHONPATH="../ai"
uvicorn app.main:app --reload
```

### Rebuild the valuation data and model (AI, optional)

The trained model (`ai/valuation/model.joblib`) and its data are committed, so this is only
needed to change them. Download `PPR-2025.csv` from propertypriceregister.ie into
`ai/valuation/data/raw/` (not committed), then:

```bash
cd ai && pip install -r requirements.txt
python -m valuation.ppr        # clean PPR -> data/county_medians.csv
python -m valuation.generate   # synthetic listings -> data/listings.csv
python -m valuation.train      # model.joblib + data/metrics.json (MAE vs county baseline)
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
cd ai && pytest -q                 # calculation module, PPR cleaning, synthetic data, model
cd firebase && npm run test:rules  # security rules against the Firestore emulator (needs Java 21+)
```

Run each from its own folder: the import paths are set in that folder's `pyproject.toml`.
GitHub Actions runs all of them, plus the web build, on every pull request (`.github/workflows/ci.yml`).

## Rules for everyone

- Work on a branch, open a pull request, get one review before merging to `main` (Definition of Done).
- Never commit `.env`, service-account JSON files, API keys or wallet keys. Copy `.env.example`.
- Synthetic data only. Stripe test mode only.
- Read `docs/data-model.md` before writing to Firestore, and `docs/api.md` before calling the API.

## AI assistance

Parts of this project were written with Claude Code. All AI-assisted code and documents were
reviewed, tested and approved by the team member who committed them.
