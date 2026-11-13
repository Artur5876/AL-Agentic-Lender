"""Web3Chain against a real local chain (skipped unless AL_TEST_CHAIN=1).

  cd contracts && npx hardhat node            # or: docker compose up anvil
  cd contracts && npm run deploy:local        # writes deployments/local.json
  cd backend && AL_TEST_CHAIN=1 .venv/bin/python -m pytest -q tests/test_chain_web3.py
"""

import os

import pytest

from app.audit import audit_hash
from app.chain import ChainError, Web3Chain, borrower_ref

pytestmark = pytest.mark.skipif(os.environ.get("AL_TEST_CHAIN") != "1",
                                reason="needs a local chain with LoanNote deployed")


@pytest.fixture
def chain():
    return Web3Chain(os.environ.get("AL_CHAIN_RPC_URL", "http://127.0.0.1:8545"),
                     "../contracts/deployments/local.json")


def test_mint_record_and_read_audit_hash(chain):
    minted = chain.mint_loan(33_500_000, 390, 30, borrower_ref("borrower-aoife", "test-salt"))
    assert minted["tokenId"] >= 1 and minted["txHash"].startswith("0x")
    h = audit_hash({"applicationId": "AL-TEST", "n": minted["tokenId"]})
    audit = chain.record_audit(minted["tokenId"], h)
    assert audit["txHash"].startswith("0x") and audit["txHash"] != minted["txHash"]
    assert chain.get_audit_hash(minted["tokenId"]) == h

    # write-once on the real contract: the revert becomes ChainError
    with pytest.raises(ChainError):
        chain.record_audit(minted["tokenId"], "ab" * 32)
    assert chain.get_audit_hash(minted["tokenId"]) == h


def test_unknown_token_raises_chain_error(chain):
    with pytest.raises(ChainError):
        chain.record_audit(999_999, "ab" * 32)


def test_missing_deployment_file_raises_chain_error():
    bad = Web3Chain("http://127.0.0.1:8545", "/nonexistent/local.json")
    with pytest.raises(ChainError, match="deploy:local"):
        bad.mint_loan(1, 390, 30, b"\x01" * 32)
