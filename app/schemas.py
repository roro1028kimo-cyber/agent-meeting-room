from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import InteractionState, InterruptPriority, MeetingMode, MessageType, QueueStatus


class MeetingCreate(BaseModel):
    topic: str = Field(min_length=1, max_length=255)
    meeting_mode: MeetingMode
    background: str = ""
    timeline: str = ""
    task_list: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    kpis: list[str] = Field(default_factory=list)


class MeetingConfirmRequest(BaseModel):
    note: str | None = None


class DiscussionRequest(BaseModel):
    message: str = ""


class InterruptRequest(BaseModel):
    message: str = Field(min_length=1)
    priority: InterruptPriority
    mode: str = "meeting"


class ReframeRequest(BaseModel):
    updated_context: str = Field(min_length=1)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    round_number: int
    role_id: str
    role_name: str
    message_type: MessageType
    content: str
    structured_payload: dict | None = None
    created_at: datetime


class InterruptQueueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message: str
    priority: InterruptPriority
    mode: str
    status: QueueStatus
    applied_in_round: int | None = None
    created_at: datetime


class ChairSummaryResponse(BaseModel):
    conclusion: str = ""
    confirmed_items: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    pending_decisions: list[str] = Field(default_factory=list)
    next_actions: list[dict[str, str]] = Field(default_factory=list)
    round_number: int | None = None


class MeetingResponse(BaseModel):
    id: str
    topic: str
    meeting_mode: MeetingMode
    current_state: InteractionState
    background_text: str
    context_payload: dict
    chair_summary: ChairSummaryResponse
    messages: list[MessageResponse]
    interrupts: list[InterruptQueueResponse]
    created_at: datetime
    updated_at: datetime

