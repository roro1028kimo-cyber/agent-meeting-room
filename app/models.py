from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RoleSource(str, enum.Enum):
    BUILTIN = "builtin"
    CUSTOM = "custom"
    OPENCLAW = "openclaw"


class ModelProvider(str, enum.Enum):
    MOCK = "mock"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class ResponseMode(str, enum.Enum):
    CONCISE = "concise"
    FULL_SUMMARY = "full_summary"


class MessageType(str, enum.Enum):
    SYSTEM = "system"
    USER = "user"
    AGENT = "agent"
    SUMMARY = "summary"


class MeetingStatus(str, enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"


class Base(DeclarativeBase):
    pass


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict | str | int | float | bool | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class RoleProfile(Base):
    __tablename__ = "role_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#6ee7b7")
    source: Mapped[RoleSource] = mapped_column(SAEnum(RoleSource), default=RoleSource.BUILTIN)
    provider: Mapped[ModelProvider] = mapped_column(SAEnum(ModelProvider), default=ModelProvider.MOCK)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    model_override: Mapped[str | None] = mapped_column(String(120), nullable=True)
    response_mode: Mapped[ResponseMode] = mapped_column(SAEnum(ResponseMode), default=ResponseMode.CONCISE)
    max_output_tokens: Mapped[int] = mapped_column(Integer, default=80)
    openclaw_agent_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    participants: Mapped[list["MeetingParticipant"]] = relationship(back_populates="role_profile")


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(Text, default="")
    context_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[MeetingStatus] = mapped_column(SAEnum(MeetingStatus), default=MeetingStatus.ACTIVE)
    round_count: Mapped[int] = mapped_column(Integer, default=0)
    temporary_memory: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    participants: Mapped[list["MeetingParticipant"]] = relationship(back_populates="meeting")
    messages: Mapped[list["MeetingMessage"]] = relationship(back_populates="meeting")
    archives: Mapped[list["MemoryArchive"]] = relationship(back_populates="meeting")


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    role_profile_id: Mapped[int] = mapped_column(ForeignKey("role_profiles.id"), nullable=False)
    seat_order: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    meeting: Mapped[Meeting] = relationship(back_populates="participants")
    role_profile: Mapped[RoleProfile] = relationship(back_populates="participants")


class MeetingMessage(Base):
    __tablename__ = "meeting_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    role_profile_id: Mapped[int | None] = mapped_column(ForeignKey("role_profiles.id"), nullable=True)
    role_name: Mapped[str] = mapped_column(String(120), nullable=False)
    message_type: Mapped[MessageType] = mapped_column(SAEnum(MessageType), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    meeting: Mapped[Meeting] = relationship(back_populates="messages")


class MemoryArchive(Base):
    __tablename__ = "memory_archives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    export_format: Mapped[str] = mapped_column(String(20), nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    meeting: Mapped[Meeting] = relationship(back_populates="archives")
