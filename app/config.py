from __future__ import annotations

import os
from urllib.parse import quote_plus
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    app_name = "Agent Meeting Room"
    database_url = ""
    secret_key = os.getenv("SECRET_KEY", "agent-meeting-room-dev")

    def __init__(self) -> None:
        self.database_url = self._resolve_database_url()

    def _resolve_database_url(self) -> str:
        direct_url = os.getenv("DATABASE_URL")
        if direct_url:
            return direct_url

        pg_host = os.getenv("PGHOST")
        pg_port = os.getenv("PGPORT")
        pg_user = os.getenv("PGUSER")
        pg_password = os.getenv("PGPASSWORD")
        pg_database = os.getenv("PGDATABASE")

        if all([pg_host, pg_port, pg_user, pg_password, pg_database]):
            encoded_password = quote_plus(pg_password)
            return (
                f"postgresql+psycopg://{pg_user}:{encoded_password}"
                f"@{pg_host}:{pg_port}/{pg_database}"
            )

        return "sqlite:///./agent_meeting_room.db"


settings = Settings()
