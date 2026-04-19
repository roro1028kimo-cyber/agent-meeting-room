from __future__ import annotations

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine
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
        self.initialized = True
        self.last_error = None

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
