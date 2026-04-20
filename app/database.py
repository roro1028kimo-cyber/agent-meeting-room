from __future__ import annotations

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, database_url: str) -> None:
        connect_args: dict[str, object] = {}
        if database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        self.engine = create_engine(
            database_url,
            future=True,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            future=True,
        )
        self.database_url = database_url
        self.last_error: str | None = None
        self.initialized = False

    def create_all(self) -> None:
        Base.metadata.create_all(self.engine)
        self._migrate_schema()
        self.initialized = True
        self.last_error = None

    def _migrate_schema(self) -> None:
        inspector = inspect(self.engine)
        table_names = set(inspector.get_table_names())
        if "role_profiles" not in table_names:
            return

        columns = {column["name"] for column in inspector.get_columns("role_profiles")}
        statements: list[str] = []
        if "provider" not in columns:
            statements.append("ALTER TABLE role_profiles ADD COLUMN provider VARCHAR(20) DEFAULT 'mock'")
        if "response_mode" not in columns:
            statements.append("ALTER TABLE role_profiles ADD COLUMN response_mode VARCHAR(20) DEFAULT 'concise'")
        if "max_output_tokens" not in columns:
            statements.append("ALTER TABLE role_profiles ADD COLUMN max_output_tokens INTEGER DEFAULT 80")

        with self.engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))
            self._normalize_enum_values(connection, table_names)

    def _normalize_enum_values(self, connection, table_names: set[str]) -> None:
        updates = {
            "role_profiles": {
                "source": {
                    "BUILTIN": "builtin",
                    "CUSTOM": "custom",
                    "OPENCLAW": "openclaw",
                },
                "provider": {
                    "MOCK": "mock",
                    "OPENAI": "openai",
                    "ANTHROPIC": "anthropic",
                    "GEMINI": "gemini",
                },
                "response_mode": {
                    "CONCISE": "concise",
                    "FULL_SUMMARY": "full_summary",
                },
            },
            "meetings": {
                "status": {
                    "ACTIVE": "active",
                    "CLOSED": "closed",
                }
            },
            "meeting_messages": {
                "message_type": {
                    "SYSTEM": "system",
                    "USER": "user",
                    "AGENT": "agent",
                    "SUMMARY": "summary",
                }
            },
        }

        for table_name, columns in updates.items():
            if table_name not in table_names:
                continue
            existing_columns = {column["name"] for column in inspect(connection).get_columns(table_name)}
            for column_name, mapping in columns.items():
                if column_name not in existing_columns:
                    continue
                for old_value, new_value in mapping.items():
                    connection.execute(
                        text(f"UPDATE {table_name} SET {column_name} = :new_value WHERE {column_name} = :old_value"),
                        {"new_value": new_value, "old_value": old_value},
                    )

    def try_initialize(self) -> bool:
        try:
            self.create_all()
            return True
        except Exception as exc:
            self.initialized = False
            self.last_error = str(exc)
            logger.exception("資料庫初始化失敗")
            return False

    @contextmanager
    def session(self) -> Session:
        session = self.session_factory()
        try:
            yield session
        finally:
            session.close()
