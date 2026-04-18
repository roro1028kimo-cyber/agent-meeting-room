from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MeetingMode(str, enum.Enum):
    PRE_PROJECT = "pre_project"
    IN_PROGRESS = "in_progress"
    POST_REVIEW = "post_review"


class InteractionState(str, enum.Enum):
    INTAKE = "intake"
    CONFIRMING = "confirming"
    MEETING_LIVE = "meeting_live"
    USER_INPUT_QUEUED = "user_input_queued"
    PAUSED_FOR_USER_CORRECTION = "paused_for_user_correction"
    REFRAMING = "reframing"
    FINALIZING = "finalizing"


class InterruptPriority(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class QueueStatus(str, enum.Enum):
    PENDING = "pending"
    APPLIED = "applied"


class MessageType(str, enum.Enum):
    SYSTEM = "system"
    USER = "user"
    AGENT = "agent"
    CHAIR_SUMMARY = "chair_summary"


class Base(DeclarativeBase):
    pass


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    meeting_mode: Mapped[MeetingMode] = mapped_column(SAEnum(MeetingMode), nullable=False)
    current_state: Mapped[InteractionState] = mapped_column(
        SAEnum(InteractionState), nullable=False, default=InteractionState.INTAKE
    )
    background_text: Mapped[str] = mapped_column(Text, default="")
    context_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    state_logs: Mapped[list["MeetingStateLog"]] = relationship(back_populates="meeting")
    messages: Mapped[list["MeetingMessage"]] = relationship(back_populates="meeting")
    queue_items: Mapped[list["UserInterruptQueue"]] = relationship(back_populates="meeting")
    summary_snapshots: Mapped[list["SummarySnapshot"]] = relationship(back_populates="meeting")
    action_items: Mapped[list["ActionItem"]] = relationship(back_populates="meeting")
    risk_items: Mapped[list["RiskItem"]] = relationship(back_populates="meeting")


class MeetingStateLog(Base):
    __tablename__ = "meeting_state_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    from_state: Mapped[InteractionState | None] = mapped_column(SAEnum(InteractionState), nullable=True)
    to_state: Mapped[InteractionState] = mapped_column(SAEnum(InteractionState), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    meeting: Mapped[Meeting] = relationship(back_populates="state_logs")


class MeetingMessage(Base):
    __tablename__ = "meeting_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, default=0)
    role_id: Mapped[str] = mapped_column(String(64), nullable=False)
    role_name: Mapped[str] = mapped_column(String(128), nullable=False)
    message_type: Mapped[MessageType] = mapped_column(SAEnum(MessageType), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    structured_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    meeting: Mapped[Meeting] = relationship(back_populates="messages")


class UserInterruptQueue(Base):
    __tablename__ = "user_interrupt_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[InterruptPriority] = mapped_column(SAEnum(InterruptPriority), nullable=False)
    mode: Mapped[str] = mapped_column(String(64), default="meeting")
    status: Mapped[QueueStatus] = mapped_column(SAEnum(QueueStatus), default=QueueStatus.PENDING)
    applied_in_round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    meeting: Mapped[Meeting] = relationship(back_populates="queue_items")


class SummarySnapshot(Base):
    __tablename__ = "summary_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    conclusion: Mapped[str] = mapped_column(Text, default="")
    confirmed_items: Mapped[list] = mapped_column(JSON, default=list)
    risks: Mapped[list] = mapped_column(JSON, default=list)
    pending_decisions: Mapped[list] = mapped_column(JSON, default=list)
    next_actions: Mapped[list] = mapped_column(JSON, default=list)
    markdown_report: Mapped[str] = mapped_column(Text, default="")
    html_report: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    meeting: Mapped[Meeting] = relationship(back_populates="summary_snapshots")


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("summary_snapshots.id"), nullable=True)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    due: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="open")
    source_role: Mapped[str] = mapped_column(String(64), default="chair")

    meeting: Mapped[Meeting] = relationship(back_populates="action_items")


class RiskItem(Base):
    __tablename__ = "risk_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("summary_snapshots.id"), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(64), default="medium")
    mitigation: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(64), default="open")

    meeting: Mapped[Meeting] = relationship(back_populates="risk_items")

