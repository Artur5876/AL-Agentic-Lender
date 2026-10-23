"""Settings read from environment variables (prefix AL_) or backend/.env.

Never put real keys in this file or in .env.example.
"""

from functools import lru_cache
from typing import Literal

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
