# Contracts (Solidity / Hardhat)

Owner: Core lead. Loan note ERC-721 (US-321), minter role (US-322), audit hash (US-331).
Hardhat 2.29 (runs on Node 20+), Solidity 0.8.28, OpenZeppelin Contracts 5.6.
The local chain runs as the `anvil` service in `docker-compose.yml` (chainId 31337).

## `LoanNote` (contracts/LoanNote.sol)

ERC-721 + AccessControl. One token per approved loan, minted to the bank's own address.

| Per token | Type | Notes |
|---|---|---|
| `principalCents` | uint256 | Loan amount in euro cents (no decimals on-chain) |
| `aprBps` | uint16 | APR in basis points, `390` = 3.90 % |
| `termYears` | uint8 | |
| `status` | enum | `0 Minted`, `1 Funded`, `2 Closed`. Only `Minted` is set in Sprint 2 (US-323 updates it) |
| `borrowerRef` | bytes32 | **Pseudonymous**: SHA-256 of `borrowerId + secret salt`, computed by the backend |

**No personal data on-chain.** No names, emails or addresses. The salt stays in the backend's
git-ignored `.env`, so `borrowerRef` cannot be linked to a borrower from the chain alone.

| Function | Who | What |
|---|---|---|
| `mint(to, principalCents, aprBps, termYears, borrowerRef) → tokenId` | `MINTER_ROLE` | Token IDs start at 1. Emits `LoanMinted`. Reverts `InvalidLoanTerms` for zero principal, zero term or empty `borrowerRef` |
| `getLoan(tokenId) → Loan` | anyone | Reverts `ERC721NonexistentToken` for unknown IDs |
| `grantRole(MINTER_ROLE, account)` / `revokeRole` | `DEFAULT_ADMIN_ROLE` | Admin = the deployer |
| `recordAudit(tokenId, auditHash)` | `MINTER_ROLE` | US-331. Token must exist, hash non-zero, **write-once** (second call reverts `AuditAlreadyRecorded`). Emits `AuditRecorded` |
| `getAuditHash(tokenId) → bytes32` | anyone | `0x00…0` until recorded. Reverts `ERC721NonexistentToken` for unknown IDs |

A call to `mint` from an account without `MINTER_ROLE` reverts with
`AccessControlUnauthorizedAccount(account, MINTER_ROLE)`, and that includes the admin.

## Commands

```bash
cd contracts
npm ci                 # first time
npx hardhat test       # unit tests on the in-process Hardhat network (no node needed)
```

## Deploy to the local chain

```bash
docker compose up anvil          # or the whole stack; RPC on http://127.0.0.1:8545
cd contracts && npm run deploy:local
```

The script refuses any chain whose ID is not 31337. It writes **`deployments/local.json`**:

```json
{ "contract": "LoanNote", "network": "anvil", "chainId": 31337, "address": "0x…",
  "deployer": "0x…", "minter": "0x…", "blockNumber": 1, "deployedAt": "…", "abi": [ … ] }
```

The backend (`backend/app/chain.py`) reads the address and ABI from this file. It is **git-ignored**
because every fresh anvil chain gives a new address, so run the deploy again after restarting anvil.

Optional environment variables (put them in your shell or a git-ignored `.env`, never in code):

| Variable | Default | Meaning |
|---|---|---|
| `AL_CHAIN_RPC_URL` | `http://127.0.0.1:8545` | Chain RPC |
| `AL_CHAIN_DEPLOYER_KEY` | none: the node's first unlocked dev account | Deployer private key |
| `AL_CHAIN_MINTER_ADDRESS` | the deployer | Account that gets `MINTER_ROLE` (the backend signer) |

## Audit hash (US-331)

`auditHash` is the SHA-256 of the decision record serialised by `backend/app/audit.py`
(`canonical_json`: sorted keys, no spaces, UTF-8, datetimes as ISO 8601 UTC). Anyone with the
Firestore record can recompute it and compare with `getAuditHash(tokenId)`: a single changed
field gives a different hash. The record itself (memo, metrics) stays off-chain.
