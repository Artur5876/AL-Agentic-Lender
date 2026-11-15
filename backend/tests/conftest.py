"""Backend tests always use the stub committee, whatever backend/.env says (US-414).

An environment variable beats the .env file in pydantic-settings, so this wins.
"""

import os

os.environ["AL_COMMITTEE_MODE"] = "stub"
