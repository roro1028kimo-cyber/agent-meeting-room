from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import MeetingStatus, MessageType, RoleSource


class AppSettingsPayload(BaseModel):
    api_mode: str = "mock"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4.1-mini"
    temperature: float = 0.7
    max_tokens: int = 700
    openclaw_enabled: bool = False
    openclaw_gateway_url: str = ""
    openclaw_notes: str = ""


class RoleProfileCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
    description: str = ""
    system_prompt: str = Field(min_length=1)
    color: str = "#6ee7b7"
    source: RoleSource = RoleSource.CUSTOM
    enabled: bool = True
    model_override: str | None = None
    openclaw_agent_id: str | None = None


class RoleProfileUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    color: str | None = None
    source: RoleSource | None = None
    enabled: bool | None = None
    model_override: str | None = None
    openclaw_agent_id: str | None = None
    sort_order: int | None = None


class MeetingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    objective: str = ""
    context_text: str = ""
    selected_role_ids: list[int] = Field(default_factory=list)


class MeetingRoundRequest(BaseModel):
    user_input: str = ""


class MeetingExportRequest(BaseModel):
    export_format: str = Field(pattern="^(text|python)$")
    archive: bool = True


class RoleProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role_key: str
    display_name: str
    description: str
    system_prompt: str
    color: str
    source: RoleSource
    enabled: bool
    is_builtin: bool
    model_override: str | None
    openclaw_agent_id: str | None
    sort_order: int


class MeetingParticipantResponse(BaseModel):
    id: int
    seat_order: int
    enabled: bool
    role: RoleProfileResponse


class MeetingMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role_profile_id: int | None
    role_name: str
    message_type: MessageType
    round_number: int
    content: str
    meta_payload: dict | None = None
    created_at: datetime


class MemoryArchiveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    export_format: str
    file_path: str
    summary: str
    created_at: datetime


class MeetingResponse(BaseModel):
    id: str
    title: str
    objective: str
    context_text: str
    status: MeetingStatus
    round_count: int
    temporary_memory: dict
    participants: list[MeetingParticipantResponse]
    messages: list[MeetingMessageResponse]
    archives: list[MemoryArchiveResponse]
    created_at: datetime
    updated_at: datetime


class ExportResponse(BaseModel):
    meeting_id: str
    export_format: str
    file_path: str | None = None
    content: str
    archived: bool
