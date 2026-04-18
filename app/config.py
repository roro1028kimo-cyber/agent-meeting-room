from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    app_name = "Agent Meeting Room"
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/agent_meeting_room",
    )
    secret_key = os.getenv("SECRET_KEY", "agent-meeting-room-dev")


settings = Settings()

