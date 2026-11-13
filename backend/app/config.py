"""Settings read from environment variables (prefix AL_) or backend/.env.

Never put real keys in this file or in .env.example.
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AL_", env_file=".env", extra="ignore")

    # "memory" = in-process store for unit tests and quick demos (data lost on restart).
    # "firestore" = Cloud Firestore, or the emulator when FIRESTORE_EMULATOR_HOST is set.
    repository: Literal["memory", "firestore"] = "memory"

    # "firebase" = verify real Firebase ID tokens (also works with the Auth emulator).
    # "dev" = accept fake tokens "dev:<uid>:<role>". FOR LOCAL TESTS ONLY, never deploy with it.
    auth_mode: Literal["firebase", "dev"] = "firebase"

    # Projects whose ID starts with "demo-" can only ever talk to the emulators.
    firebase_project_id: str = "demo-al-group11"

    # S1 stand-in for US-304 (broker assignment): every new application goes to this broker.
    default_broker_uid: str | None = None

    # Origins allowed to call the API from a browser (the React dev server).
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ----- loan note on the local chain (US-321, US-331; minted on approval) -----
    # "web3" = the real LoanNote contract on the anvil node (docker-compose).
    # "fake" = in-process FakeChain with made-up hashes, for demos without a chain.
    chain_mode: Literal["web3", "fake"] = "web3"
    chain_rpc_url: str = "http://127.0.0.1:8545"
    # Written by `npm run deploy:local` in contracts/ (address + ABI). Relative to backend/.
    chain_deployment_file: str = "../contracts/deployments/local.json"
    # Private key that signs mint/audit transactions; it needs MINTER_ROLE. Only in .env.
    # Unset = use the node's first unlocked dev account (anvil only).
    chain_signer_key: SecretStr | None = None
    # The bank's own address that receives every loan note. Unset = the signer's address.
    chain_bank_address: str | None = None
    # Secret salt for borrowerRef = SHA-256(borrowerId + salt). Only in .env. Required to mint.
    borrower_ref_salt: SecretStr | None = None
    # S2 default APR for the loan note, in basis points (390 = 3.90 %).
    default_apr_bps: int = 390


@lru_cache
def get_settings() -> Settings:
    return Settings()
