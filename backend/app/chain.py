"""Talking to the LoanNote contract (US-321, US-331; used when an underwriter approves).

ChainClient is the small interface the API needs. Two implementations:
- Web3Chain: the real contract on the local anvil chain (address + ABI from
  contracts/deployments/local.json, written by `npm run deploy:local`).
- FakeChain: in memory, for unit tests and demos without a chain (AL_CHAIN_MODE=fake).

Any failure is raised as ChainError, which the API turns into the "mint_failed" error.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from pathlib import Path
from typing import Protocol

log = logging.getLogger("al.chain")

LOCAL_CHAIN_ID = 31337
RECEIPT_TIMEOUT_S = 30


class ChainError(Exception):
    """Mint or audit transaction could not be completed."""


def borrower_ref(borrower_id: str, salt: str) -> bytes:
    """Pseudonymous on-chain borrower ID: SHA-256(borrowerId + salt), 32 bytes.
    Without the salt (kept in .env) the chain value cannot be linked to the borrower."""
    if not salt:
        raise ChainError("AL_BORROWER_REF_SALT is not set; refusing to mint.")
    return hashlib.sha256((borrower_id + salt).encode("utf-8")).digest()


def _hash_to_bytes32(audit_hash_hex: str) -> bytes:
    h = audit_hash_hex.removeprefix("0x")
    if len(h) != 64:
        raise ChainError("Audit hash must be 32 bytes (64 hex characters).")
    return bytes.fromhex(h)


class ChainClient(Protocol):
    bank_address: str

    def mint_loan(self, principal_cents: int, apr_bps: int, term_years: int,
                  borrower_ref: bytes) -> dict:
        """Mint to the bank's address. Returns {"tokenId": int, "txHash": "0x..."}."""
        ...

    def record_audit(self, token_id: int, audit_hash_hex: str) -> dict:
        """Store the audit hash on-chain (write-once). Returns {"txHash": "0x..."}."""
        ...

    def get_audit_hash(self, token_id: int) -> str:
        """Read the stored audit hash as 64 hex characters (no 0x)."""
        ...


class FakeChain:
    """In-memory stand-in with the same rules as the contract (write-once audit).
    `fail_on` = "mint" or "audit" makes that call raise ChainError (for tests)."""

    def __init__(self, bank_address: str = "0x" + "b4" * 20, fail_on: str | None = None):
        self.bank_address = bank_address
        self.fail_on = fail_on
        self._lock = threading.Lock()
        self.loans: dict[int, dict] = {}
        self.audits: dict[int, str] = {}
        self._tx = 0

    def _tx_hash(self) -> str:
        self._tx += 1
        return "0x" + hashlib.sha256(f"fake-tx-{self._tx}".encode()).hexdigest()

    def mint_loan(self, principal_cents, apr_bps, term_years, borrower_ref) -> dict:
        if self.fail_on == "mint":
            raise ChainError("FakeChain: mint failed (test).")
        with self._lock:
            token_id = len(self.loans) + 1
            self.loans[token_id] = {"to": self.bank_address, "principalCents": principal_cents,
                                    "aprBps": apr_bps, "termYears": term_years,
                                    "borrowerRef": borrower_ref}
            return {"tokenId": token_id, "txHash": self._tx_hash()}

    def record_audit(self, token_id, audit_hash_hex) -> dict:
        if self.fail_on == "audit":
            raise ChainError("FakeChain: recordAudit failed (test).")
        h = _hash_to_bytes32(audit_hash_hex).hex()
        with self._lock:
            if token_id not in self.loans:
                raise ChainError(f"Token {token_id} does not exist.")
            if token_id in self.audits:
                raise ChainError(f"Audit already recorded for token {token_id}.")
            self.audits[token_id] = h
            return {"txHash": self._tx_hash()}

    def get_audit_hash(self, token_id) -> str:
        return self.audits.get(token_id, "00" * 32)


class Web3Chain:
    """The real LoanNote contract. Connects lazily, so the API starts without a chain."""

    def __init__(self, rpc_url: str, deployment_file: str, signer_key: str | None = None,
                 bank_address: str | None = None):
        self._rpc_url = rpc_url
        self._deployment_file = Path(deployment_file)
        self._signer_key = signer_key
        self._bank_address = bank_address
        self._send_lock = threading.Lock()  # one tx at a time, so nonces never collide
        self._ready = False

    # ----- setup -----
    def _connect(self) -> None:
        if self._ready:
            return
        from web3 import Web3

        try:
            dep = json.loads(self._deployment_file.read_text())
        except (OSError, ValueError) as exc:
            raise ChainError(
                f"Cannot read deployment file {self._deployment_file}: "
                f"{type(exc).__name__}. Run `npm run deploy:local` in contracts/.") from exc
        w3 = Web3(Web3.HTTPProvider(self._rpc_url, request_kwargs={"timeout": 10}))
        try:
            chain_id = w3.eth.chain_id
        except Exception as exc:
            raise ChainError(
                f"Chain not reachable at {self._rpc_url}: {type(exc).__name__}.") from exc
        if chain_id != dep.get("chainId") or chain_id != LOCAL_CHAIN_ID:
            raise ChainError(f"Chain ID {chain_id} does not match the deployment "
                             f"({dep.get('chainId')}) / local chain ({LOCAL_CHAIN_ID}).")
        if not w3.eth.get_code(dep["address"]):
            raise ChainError("No contract at the deployed address (was anvil restarted? "
                             "Run `npm run deploy:local` again).")
        if self._signer_key:
            self._account = w3.eth.account.from_key(self._signer_key)
            self._sender = self._account.address
        else:  # anvil's unlocked dev account
            self._account = None
            self._sender = w3.eth.accounts[0]
        self._w3 = w3
        self._contract = w3.eth.contract(address=dep["address"], abi=dep["abi"])
        self.bank_address = Web3.to_checksum_address(self._bank_address or self._sender)
        self._ready = True

    # ----- sending -----
    def _send(self, fn) -> dict:
        """Send a contract call, wait for the receipt, raise ChainError on revert."""
        try:
            self._connect()
            with self._send_lock:
                if self._account is None:
                    tx_hash = fn.transact({"from": self._sender})
                else:
                    tx = fn.build_transaction({
                        "from": self._sender,
                        "nonce": self._w3.eth.get_transaction_count(self._sender, "pending"),
                        "chainId": LOCAL_CHAIN_ID,
                    })
                    signed = self._account.sign_transaction(tx)
                    tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
                receipt = self._w3.eth.wait_for_transaction_receipt(
                    tx_hash, timeout=RECEIPT_TIMEOUT_S)
        except ChainError:
            raise
        except Exception as exc:  # revert, timeout, connection error...
            raise ChainError(f"{type(exc).__name__}: {exc}") from exc
        if receipt["status"] != 1:
            raise ChainError(f"Transaction {receipt['transactionHash'].hex()} reverted.")
        return receipt

    @staticmethod
    def _hex(b) -> str:
        return "0x" + bytes(b).hex()

    def mint_loan(self, principal_cents, apr_bps, term_years, borrower_ref) -> dict:
        self._connect()
        receipt = self._send(self._contract.functions.mint(
            self.bank_address, principal_cents, apr_bps, term_years, borrower_ref))
        events = self._contract.events.LoanMinted().process_receipt(receipt)
        if not events:
            raise ChainError("Mint succeeded but no LoanMinted event was found.")
        return {"tokenId": int(events[0]["args"]["tokenId"]),
                "txHash": self._hex(receipt["transactionHash"])}

    def record_audit(self, token_id, audit_hash_hex) -> dict:
        self._connect()
        receipt = self._send(self._contract.functions.recordAudit(
            token_id, _hash_to_bytes32(audit_hash_hex)))
        return {"txHash": self._hex(receipt["transactionHash"])}

    def get_audit_hash(self, token_id) -> str:
        self._connect()
        try:
            return bytes(self._contract.functions.getAuditHash(token_id).call()).hex()
        except Exception as exc:
            raise ChainError(f"{type(exc).__name__}: {exc}") from exc


def make_chain(settings) -> ChainClient:
    if settings.chain_mode == "fake":
        log.warning("AL_CHAIN_MODE=fake: loan notes are NOT on a real chain.")
        return FakeChain()
    # Empty strings (e.g. unset ${VAR:-} in docker-compose) count as "not set".
    key = settings.chain_signer_key.get_secret_value() if settings.chain_signer_key else ""
    return Web3Chain(settings.chain_rpc_url, settings.chain_deployment_file, key or None,
                     settings.chain_bank_address or None)
