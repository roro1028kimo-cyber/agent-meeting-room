from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import BASE_DIR
from app.models import (
    AppSetting,
    Meeting,
    MeetingMessage,
    MeetingParticipant,
    MeetingStatus,
    MemoryArchive,
    MessageType,
    ModelProvider,
    ResponseMode,
    RoleProfile,
    RoleSource,
)


DEFAULT_SETTINGS = {
    "api_mode": "mock",
    "openai_api_key": "",
    "openai_base_url": "https://api.openai.com/v1",
    "openai_model": "gpt-4.1-mini",
    "anthropic_api_key": "",
    "anthropic_base_url": "https://api.anthropic.com",
    "anthropic_model": "claude-sonnet-4-20250514",
    "gemini_api_key": "",
    "gemini_base_url": "https://generativelanguage.googleapis.com/v1beta",
    "gemini_model": "gemini-2.5-flash",
    "temperature": 0.35,
    "short_reply_max_tokens": 48,
    "full_summary_max_tokens": 360,
    "openclaw_enabled": False,
    "openclaw_gateway_url": "",
    "openclaw_notes": "",
}


LEGACY_SETTING_MAP = {
    "api_key": "openai_api_key",
    "base_url": "openai_base_url",
    "model_name": "openai_model",
    "max_tokens": "short_reply_max_tokens",
}


BUILTIN_ROLES = [
    {
        "role_key": "chair",
        "display_name": "主持人",
        "description": "控場、指定順序、最後收斂結論。",
        "color": "#7dd3fc",
        "sort_order": 1,
        "provider": ModelProvider.MOCK,
        "response_mode": ResponseMode.FULL_SUMMARY,
        "max_output_tokens": 220,
        "system_prompt": (
            "你是主持人。"
            "平時發言只保留重點，不要客套，不要模仿人類聊天。"
            "請優先收斂討論、指出焦點與下一步。"
        ),
    },
    {
        "role_key": "planner",
        "display_name": "規劃師",
        "description": "把主題拆成方向、步驟與可行方案。",
        "color": "#c4b5fd",
        "sort_order": 2,
        "provider": ModelProvider.MOCK,
        "response_mode": ResponseMode.CONCISE,
        "max_output_tokens": 48,
        "system_prompt": "你是規劃師。只說結構、步驟、下一步，不要鋪陳。",
    },
    {
        "role_key": "skeptic",
        "display_name": "反方辯手",
        "description": "挑戰假設，避免過度樂觀。",
        "color": "#fca5a5",
        "sort_order": 3,
        "provider": ModelProvider.MOCK,
        "response_mode": ResponseMode.CONCISE,
        "max_output_tokens": 48,
        "system_prompt": "你是反方辯手。只指出最值得懷疑的一點與理由。",
    },
    {
        "role_key": "risk_officer",
        "display_name": "風險官",
        "description": "指出風險、依賴與失敗點。",
        "color": "#fbbf24",
        "sort_order": 4,
        "provider": ModelProvider.MOCK,
        "response_mode": ResponseMode.CONCISE,
        "max_output_tokens": 48,
        "system_prompt": "你是風險官。只列關鍵風險、依賴與備案。",
    },
    {
        "role_key": "executor",
        "display_name": "執行官",
        "description": "把討論轉成可落地動作。",
        "color": "#6ee7b7",
        "sort_order": 5,
        "provider": ModelProvider.MOCK,
        "response_mode": ResponseMode.FULL_SUMMARY,
        "max_output_tokens": 220,
        "system_prompt": "你是執行官。優先輸出可行動項，不要解釋太多背景。",
    },
    {
        "role_key": "recorder",
        "display_name": "記錄員",
        "description": "整理關鍵觀點與本輪共識。",
        "color": "#fdba74",
        "sort_order": 6,
        "provider": ModelProvider.MOCK,
        "response_mode": ResponseMode.FULL_SUMMARY,
        "max_output_tokens": 220,
        "system_prompt": "你是記錄員。負責把會議內容整理成可保存的結論。",
    },
    {
        "role_key": "researcher",
        "display_name": "研究員",
        "description": "指出背景知識缺口與需要查證的資訊。",
        "color": "#93c5fd",
        "sort_order": 7,
        "provider": ModelProvider.MOCK,
        "response_mode": ResponseMode.CONCISE,
        "max_output_tokens": 48,
        "system_prompt": "你是研究員。只指出缺口與要查什麼，不要假裝查完。",
    },
    {
        "role_key": "product_advisor",
        "display_name": "產品顧問",
        "description": "從使用者價值與產品角度提出看法。",
        "color": "#f9a8d4",
        "sort_order": 8,
        "provider": ModelProvider.MOCK,
        "response_mode": ResponseMode.CONCISE,
        "max_output_tokens": 48,
        "system_prompt": "你是產品顧問。只談使用者價值、理解門檻與採用意願。",
    },
]


@dataclass
class RuntimeSettings:
    api_mode: str
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    anthropic_api_key: str
    anthropic_base_url: str
    anthropic_model: str
    gemini_api_key: str
    gemini_base_url: str
    gemini_model: str
    temperature: float
    short_reply_max_tokens: int
    full_summary_max_tokens: int
    openclaw_enabled: bool
    openclaw_gateway_url: str
    openclaw_notes: str


def ensure_defaults(session: Session) -> None:
    for key, value in DEFAULT_SETTINGS.items():
        if session.get(AppSetting, key) is None:
            session.add(AppSetting(key=key, value=value))

    existing = {role.role_key: role for role in session.execute(select(RoleProfile)).scalars().all()}
    for definition in BUILTIN_ROLES:
        role = existing.get(definition["role_key"])
        if role is None:
            session.add(
                RoleProfile(
                    role_key=definition["role_key"],
                    display_name=definition["display_name"],
                    description=definition["description"],
                    system_prompt=definition["system_prompt"],
                    color=definition["color"],
                    source=RoleSource.BUILTIN,
                    provider=definition["provider"],
                    enabled=True,
                    is_builtin=True,
                    model_override=None,
                    response_mode=definition["response_mode"],
                    max_output_tokens=definition["max_output_tokens"],
                    sort_order=definition["sort_order"],
                )
            )
        elif role.is_builtin:
            role.display_name = definition["display_name"]
            role.description = definition["description"]
            role.system_prompt = definition["system_prompt"]
            role.color = definition["color"]
            role.provider = definition["provider"]
            role.response_mode = definition["response_mode"]
            role.max_output_tokens = definition["max_output_tokens"]
            role.sort_order = definition["sort_order"]
    session.commit()


def load_runtime_settings(session: Session) -> RuntimeSettings:
    values = dict(DEFAULT_SETTINGS)
    for item in session.execute(select(AppSetting)).scalars().all():
        if item.key in values:
            values[item.key] = item.value
        elif item.key in LEGACY_SETTING_MAP:
            values[LEGACY_SETTING_MAP[item.key]] = item.value
    return RuntimeSettings(**values)


def settings_to_dict(settings: RuntimeSettings) -> dict:
    return {
        "api_mode": settings.api_mode,
        "openai_api_key": settings.openai_api_key,
        "openai_base_url": settings.openai_base_url,
        "openai_model": settings.openai_model,
        "anthropic_api_key": settings.anthropic_api_key,
        "anthropic_base_url": settings.anthropic_base_url,
        "anthropic_model": settings.anthropic_model,
        "gemini_api_key": settings.gemini_api_key,
        "gemini_base_url": settings.gemini_base_url,
        "gemini_model": settings.gemini_model,
        "temperature": settings.temperature,
        "short_reply_max_tokens": settings.short_reply_max_tokens,
        "full_summary_max_tokens": settings.full_summary_max_tokens,
        "openclaw_enabled": settings.openclaw_enabled,
        "openclaw_gateway_url": settings.openclaw_gateway_url,
        "openclaw_notes": settings.openclaw_notes,
    }


def update_settings(session: Session, payload: dict) -> dict:
    for key, value in payload.items():
        row = session.get(AppSetting, key)
        if row is None:
            session.add(AppSetting(key=key, value=value))
        else:
            row.value = value
    session.commit()
    return settings_to_dict(load_runtime_settings(session))


def get_roles(session: Session) -> list[RoleProfile]:
    return session.execute(select(RoleProfile).order_by(RoleProfile.sort_order.asc(), RoleProfile.id.asc())).scalars().all()


def get_meeting(session: Session, meeting_id: str) -> Meeting | None:
    statement = (
        select(Meeting)
        .where(Meeting.id == meeting_id)
        .options(
            selectinload(Meeting.participants).selectinload(MeetingParticipant.role_profile),
            selectinload(Meeting.messages),
            selectinload(Meeting.archives),
        )
    )
    return session.execute(statement).scalars().first()


def create_meeting(session: Session, title: str, objective: str, context_text: str, selected_role_ids: list[int]) -> Meeting:
    available_roles = get_roles(session)
    if not selected_role_ids:
        selected_role_ids = [role.id for role in available_roles if role.enabled][:4]

    meeting = Meeting(
        title=title,
        objective=objective,
        context_text=context_text,
        status=MeetingStatus.ACTIVE,
        temporary_memory={
            "notes": [],
            "latest_summary": "",
            "latest_formal_input": "",
            "latest_note_input": "",
            "active_speaker": None,
        },
    )
    session.add(meeting)
    session.flush()

    seat_order = 1
    for role in available_roles:
        if role.id not in selected_role_ids:
            continue
        session.add(
            MeetingParticipant(
                meeting_id=meeting.id,
                role_profile_id=role.id,
                seat_order=seat_order,
                enabled=True,
            )
        )
        seat_order += 1

    session.add(
        MeetingMessage(
            meeting_id=meeting.id,
            role_profile_id=None,
            role_name="系統",
            message_type=MessageType.SYSTEM,
            round_number=0,
            content="會議已建立。請輸入正式討論內容後開始下一輪。",
            meta_payload={"kind": "system_bootstrap"},
        )
    )
    session.commit()
    session.expire_all()
    return get_meeting(session, meeting.id)


def list_recent_meetings(session: Session) -> list[Meeting]:
    return session.execute(select(Meeting).order_by(Meeting.updated_at.desc()).limit(20)).scalars().all()


def list_archives(session: Session) -> list[MemoryArchive]:
    return session.execute(select(MemoryArchive).order_by(MemoryArchive.created_at.desc()).limit(50)).scalars().all()


def run_meeting_round(session: Session, meeting_id: str, formal_input: str, note_input: str) -> Meeting:
    meeting = get_meeting(session, meeting_id)
    if meeting is None:
        raise ValueError("Meeting not found.")
    if meeting.status == MeetingStatus.CLOSED:
        raise ValueError("Meeting is already closed.")

    runtime = load_runtime_settings(session)
    round_number = meeting.round_count + 1
    trimmed_formal = formal_input.strip()
    trimmed_note = note_input.strip()

    if not trimmed_formal and not trimmed_note:
        raise ValueError("Please provide formal input or note input.")

    memory = dict(meeting.temporary_memory or {})
    memory.setdefault("notes", [])
    memory["active_speaker"] = None

    if trimmed_formal:
        memory["latest_formal_input"] = trimmed_formal
        memory["notes"].append(f"正式輸入｜{trimmed_formal}")
        session.add(
            MeetingMessage(
                meeting_id=meeting.id,
                role_profile_id=None,
                role_name="正式輸入",
                message_type=MessageType.USER,
                round_number=round_number,
                content=trimmed_formal,
                meta_payload={"kind": "formal_input"},
            )
        )

    if trimmed_note:
        memory["latest_note_input"] = trimmed_note
        memory["notes"].append(f"插話｜{trimmed_note}")
        session.add(
            MeetingMessage(
                meeting_id=meeting.id,
                role_profile_id=None,
                role_name="使用者插話",
                message_type=MessageType.USER,
                round_number=round_number,
                content=trimmed_note,
                meta_payload={"kind": "note_input"},
            )
        )

    transcript = build_transcript(meeting)
    user_context = build_user_context(trimmed_formal, trimmed_note)
    participant_roles = [
        participant.role_profile
        for participant in sorted(meeting.participants, key=lambda item: item.seat_order)
        if participant.enabled
    ]

    generated_messages: list[tuple[RoleProfile, str]] = []
    for role in participant_roles:
        reply = generate_role_reply(runtime, role, meeting, transcript, user_context, concise=True)
        generated_messages.append((role, reply))
        transcript.append({"role": role.display_name, "content": reply})
        memory["active_speaker"] = role.display_name
        session.add(
            MeetingMessage(
                meeting_id=meeting.id,
                role_profile_id=role.id,
                role_name=role.display_name,
                message_type=MessageType.AGENT,
                round_number=round_number,
                content=reply,
                meta_payload={"source": role.source.value, "provider": role.provider.value, "mode": "concise"},
            )
        )

    summary_text = build_round_summary(meeting, generated_messages, trimmed_formal, trimmed_note)
    memory["latest_summary"] = summary_text
    memory["notes"].append(f"摘要｜{extract_first_sentence(summary_text)}")
    meeting.round_count = round_number
    meeting.temporary_memory = memory

    session.add(
        MeetingMessage(
            meeting_id=meeting.id,
            role_profile_id=None,
            role_name="會議室摘要",
            message_type=MessageType.SUMMARY,
            round_number=round_number,
            content=summary_text,
            meta_payload={"kind": "round_summary"},
        )
    )
    session.commit()
    session.expire_all()
    return get_meeting(session, meeting.id)


def generate_full_summary(session: Session, meeting_id: str, force_provider: ModelProvider | None = None) -> Meeting:
    meeting = get_meeting(session, meeting_id)
    if meeting is None:
        raise ValueError("Meeting not found.")

    runtime = load_runtime_settings(session)
    summary_role = select_summary_role(meeting, force_provider)
    transcript = build_transcript(meeting)
    content = generate_role_reply(runtime, summary_role, meeting, transcript, "請整理完整會議內容。", concise=False)

    memory = dict(meeting.temporary_memory or {})
    memory.setdefault("notes", [])
    memory["active_speaker"] = summary_role.display_name
    memory["latest_summary"] = content
    memory["notes"].append(f"完整整理｜{extract_first_sentence(content)}")
    meeting.temporary_memory = memory

    session.add(
        MeetingMessage(
            meeting_id=meeting.id,
            role_profile_id=summary_role.id,
            role_name=f"{summary_role.display_name}完整整理",
            message_type=MessageType.SUMMARY,
            round_number=meeting.round_count,
            content=content,
            meta_payload={"kind": "full_summary", "provider": summary_role.provider.value},
        )
    )
    session.commit()
    session.expire_all()
    return get_meeting(session, meeting.id)


def close_meeting(session: Session, meeting_id: str) -> Meeting:
    meeting = get_meeting(session, meeting_id)
    if meeting is None:
        raise ValueError("Meeting not found.")
    meeting.status = MeetingStatus.CLOSED
    session.commit()
    session.expire_all()
    return get_meeting(session, meeting_id)


def export_meeting(session: Session, meeting_id: str, export_format: str, archive: bool) -> dict:
    meeting = get_meeting(session, meeting_id)
    if meeting is None:
        raise ValueError("Meeting not found.")

    transcript = [
        {
            "round": message.round_number,
            "speaker": message.role_name,
            "type": message.message_type.value,
            "content": message.content,
        }
        for message in sorted(meeting.messages, key=lambda item: (item.round_number, item.id))
    ]

    if export_format == "text":
        content = build_text_export(meeting, transcript)
        suffix = "txt"
    else:
        content = build_python_export(meeting, transcript)
        suffix = "py"

    file_path = None
    if archive:
        export_dir = BASE_DIR / "exports"
        export_dir.mkdir(exist_ok=True)
        safe_name = "".join(ch if ch.isalnum() else "_" for ch in meeting.title)[:40].strip("_") or "meeting"
        file_name = f"{meeting.id}_{safe_name}.{suffix}"
        file_path = str(export_dir / file_name)
        Path(file_path).write_text(content, encoding="utf-8")
        session.add(
            MemoryArchive(
                meeting_id=meeting.id,
                export_format=export_format,
                file_path=file_path,
                summary=(meeting.temporary_memory or {}).get("latest_summary", ""),
            )
        )
        memory = dict(meeting.temporary_memory or {})
        notes = list(memory.get("notes", []))
        notes.append(f"匯出｜{export_format} -> {file_path}")
        memory["notes"] = notes
        meeting.temporary_memory = memory
        session.commit()

    return {
        "meeting_id": meeting.id,
        "export_format": export_format,
        "file_path": file_path,
        "content": content,
        "archived": archive,
    }


def select_summary_role(meeting: Meeting, force_provider: ModelProvider | None = None) -> RoleProfile:
    roles = [
        participant.role_profile
        for participant in sorted(meeting.participants, key=lambda item: item.seat_order)
        if participant.enabled
    ]
    summary_roles = [role for role in roles if role.response_mode == ResponseMode.FULL_SUMMARY]
    if force_provider is not None:
        summary_roles = [role for role in summary_roles if role.provider == force_provider] or summary_roles
    if summary_roles:
        return summary_roles[0]
    return roles[0]


def build_transcript(meeting: Meeting) -> list[dict[str, str]]:
    items = [
        {"role": "會議主題", "content": meeting.title},
        {"role": "會議目標", "content": meeting.objective or "未指定"},
        {"role": "背景", "content": meeting.context_text or "未提供"},
    ]
    for message in sorted(meeting.messages, key=lambda item: (item.round_number, item.id))[-10:]:
        items.append({"role": message.role_name, "content": message.content})
    return items


def build_user_context(formal_input: str, note_input: str) -> str:
    parts = []
    if formal_input:
        parts.append(f"正式輸入：{formal_input}")
    if note_input:
        parts.append(f"使用者插話：{note_input}")
    return "\n".join(parts)


def generate_role_reply(
    runtime: RuntimeSettings,
    role: RoleProfile,
    meeting: Meeting,
    transcript: list[dict],
    user_input: str,
    concise: bool,
) -> str:
    if runtime.api_mode != "mock":
        try:
            text = call_provider(runtime, role, meeting, transcript, user_input, concise)
            return post_process_reply(text, concise)
        except Exception as exc:
            return build_fallback_reply(role, meeting, user_input, transcript, concise, reason=f"模型呼叫失敗：{exc}")
    return build_fallback_reply(role, meeting, user_input, transcript, concise)


def call_provider(
    runtime: RuntimeSettings,
    role: RoleProfile,
    meeting: Meeting,
    transcript: list[dict],
    user_input: str,
    concise: bool,
) -> str:
    if role.provider == ModelProvider.OPENAI:
        return call_openai(runtime, role, meeting, transcript, user_input, concise)
    if role.provider == ModelProvider.ANTHROPIC:
        return call_anthropic(runtime, role, meeting, transcript, user_input, concise)
    if role.provider == ModelProvider.GEMINI:
        return call_gemini(runtime, role, meeting, transcript, user_input, concise)
    raise ValueError(f"Unsupported provider: {role.provider.value}")


def resolve_provider_model(runtime: RuntimeSettings, role: RoleProfile) -> tuple[str, str, str]:
    if role.provider == ModelProvider.OPENAI:
        return runtime.openai_base_url.rstrip("/"), runtime.openai_api_key, role.model_override or runtime.openai_model
    if role.provider == ModelProvider.ANTHROPIC:
        return runtime.anthropic_base_url.rstrip("/"), runtime.anthropic_api_key, role.model_override or runtime.anthropic_model
    if role.provider == ModelProvider.GEMINI:
        return runtime.gemini_base_url.rstrip("/"), runtime.gemini_api_key, role.model_override or runtime.gemini_model
    return "", "", role.model_override or "mock"


def resolve_token_budget(runtime: RuntimeSettings, role: RoleProfile, concise: bool) -> int:
    if concise:
        role_cap = role.max_output_tokens or runtime.short_reply_max_tokens
        return min(role_cap, runtime.short_reply_max_tokens)
    role_cap = role.max_output_tokens or runtime.full_summary_max_tokens
    return max(role_cap, runtime.full_summary_max_tokens)


def clip_prompt_text(value: str, limit: int) -> str:
    compact = re.sub(r"\s+", " ", (value or "").strip())
    return compact[:limit]


def build_role_request_prompt(role: RoleProfile, meeting: Meeting, transcript: list[dict], user_input: str, concise: bool) -> str:
    recent = "\n".join(
        [f"- {clip_prompt_text(item['role'], 10)}：{clip_prompt_text(item['content'], 24)}" for item in transcript[-6:]]
    )
    if concise:
        output_rule = (
            "請用繁體中文。禁止寒暄、禁止鋪陳、禁止模仿人類聊天。"
            "你不是在寫文章，而是在終端機會議中回報。"
            "只輸出三行：重點｜...、邏輯｜...、結論｜..."
            "每行 12 字內，寧短勿長，避免重複背景。"
        )
    else:
        output_rule = (
            "請用繁體中文輸出完整會議整理。"
            "請使用五行：主題｜...、共識｜...、分歧｜...、風險｜...、下一步｜..."
            "保持精簡，但要可保存。"
        )
    return "\n".join(
        [
            f"角色：{role.display_name}",
            f"會議主題：{clip_prompt_text(meeting.title, 30)}",
            f"會議目標：{clip_prompt_text(meeting.objective or '未指定', 30)}",
            f"背景：{clip_prompt_text(meeting.context_text or '未提供', 60)}",
            f"本輪輸入：{clip_prompt_text(user_input or '無', 60)}",
            "最近討論：",
            recent or "- 尚無",
            "",
            output_rule,
        ]
    )


def call_openai(
    runtime: RuntimeSettings,
    role: RoleProfile,
    meeting: Meeting,
    transcript: list[dict],
    user_input: str,
    concise: bool,
) -> str:
    base_url, api_key, model_name = resolve_provider_model(runtime, role)
    if not api_key:
        raise ValueError("OpenAI API key is missing.")

    response = httpx.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model_name,
            "messages": [
                {"role": "system", "content": role.system_prompt},
                {"role": "user", "content": build_role_request_prompt(role, meeting, transcript, user_input, concise)},
            ],
            "temperature": runtime.temperature,
            "max_tokens": resolve_token_budget(runtime, role, concise),
        },
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def call_anthropic(
    runtime: RuntimeSettings,
    role: RoleProfile,
    meeting: Meeting,
    transcript: list[dict],
    user_input: str,
    concise: bool,
) -> str:
    base_url, api_key, model_name = resolve_provider_model(runtime, role)
    if not api_key:
        raise ValueError("Anthropic API key is missing.")

    response = httpx.post(
        f"{base_url}/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model_name,
            "system": role.system_prompt,
            "max_tokens": resolve_token_budget(runtime, role, concise),
            "messages": [
                {
                    "role": "user",
                    "content": build_role_request_prompt(role, meeting, transcript, user_input, concise),
                }
            ],
        },
        timeout=60.0,
    )
    response.raise_for_status()
    data = response.json()
    return "".join(item.get("text", "") for item in data.get("content", []) if item.get("type") == "text").strip()


def call_gemini(
    runtime: RuntimeSettings,
    role: RoleProfile,
    meeting: Meeting,
    transcript: list[dict],
    user_input: str,
    concise: bool,
) -> str:
    base_url, api_key, model_name = resolve_provider_model(runtime, role)
    if not api_key:
        raise ValueError("Gemini API key is missing.")

    response = httpx.post(
        f"{base_url}/models/{model_name}:generateContent",
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "systemInstruction": {"parts": [{"text": role.system_prompt}]},
            "contents": [
                {
                    "parts": [
                        {"text": build_role_request_prompt(role, meeting, transcript, user_input, concise)}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": runtime.temperature,
                "maxOutputTokens": resolve_token_budget(runtime, role, concise),
            },
        },
        timeout=60.0,
    )
    response.raise_for_status()
    data = response.json()
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "".join(part.get("text", "") for part in parts).strip()


def post_process_reply(text: str, concise: bool) -> str:
    cleaned = re.sub(r"\n{3,}", "\n\n", text.strip())
    if concise:
        return compress_concise_output(cleaned)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    trimmed = lines[:5]
    if len(trimmed) < 5:
        return compress_full_summary(cleaned)
    return "\n".join(line[:80] for line in trimmed)


def compress_concise_output(text: str) -> str:
    lines = [line.strip("-• ").strip() for line in text.splitlines() if line.strip()]
    labels = ["重點", "邏輯", "結論"]
    normalized: list[str] = []

    if len(lines) >= 3 and all("｜" in line for line in lines[:3]):
        for label, line in zip(labels, lines[:3]):
            content = line.split("｜", 1)[1].strip() if "｜" in line else line
            normalized.append(f"{label}｜{content[:12]}")
        return "\n".join(normalized)

    fragments = [fragment.strip() for fragment in re.split(r"[。！？\n]+", text) if fragment.strip()]
    while len(fragments) < 3:
        fragments.append("無")
    return "\n".join(
        [
            f"重點｜{fragments[0][:12]}",
            f"邏輯｜{fragments[1][:12]}",
            f"結論｜{fragments[2][:12]}",
        ]
    )


def compress_full_summary(text: str) -> str:
    fragments = [fragment.strip() for fragment in re.split(r"[。！？\n]+", text) if fragment.strip()]
    while len(fragments) < 5:
        fragments.append("無")
    labels = ["主題", "共識", "分歧", "風險", "下一步"]
    return "\n".join(f"{label}｜{fragment[:60]}" for label, fragment in zip(labels, fragments[:5]))


def build_fallback_reply(
    role: RoleProfile,
    meeting: Meeting,
    user_input: str,
    transcript: list[dict],
    concise: bool,
    reason: str | None = None,
) -> str:
    latest_points = [item["content"] for item in transcript[-3:]]
    context_hint = "；".join(latest_points) if latest_points else "討論剛開始"
    topic_hint = user_input or "先根據目前脈絡往前推進"

    concise_map = {
        "chair": f"重點｜先收斂主題\n邏輯｜焦點={topic_hint[:16]}\n結論｜每人只補一點",
        "planner": f"重點｜先拆結構\n邏輯｜目標/限制/下一步\n結論｜先解 {topic_hint[:16]}",
        "skeptic": f"重點｜前提未明\n邏輯｜脈絡={context_hint[:16]}\n結論｜先釐清",
        "risk_officer": "重點｜風險偏高\n邏輯｜資訊少/範圍大/結論快\n結論｜先縮題",
        "executor": "重點｜先出動作\n邏輯｜定義→補充→收斂\n結論｜先做短版決議",
        "recorder": f"重點｜已記錄\n邏輯｜主題={meeting.title[:12]}\n結論｜可整理摘要",
        "researcher": "重點｜資訊缺口大\n邏輯｜缺情境/限制/標準\n結論｜先補資料",
        "product_advisor": "重點｜先問價值\n邏輯｜使用者是否在意\n結論｜不清楚別擴做",
    }
    full_map = {
        "chair": "\n".join(
            [
                f"主題｜{meeting.title}",
                f"共識｜本輪先聚焦在 {topic_hint[:48]}",
                "分歧｜部分意見仍停在背景與範圍定義",
                "風險｜若再延伸題，會議會失焦且成本上升",
                "下一步｜保留一條主線，其餘議題延後",
            ]
        ),
        "executor": "\n".join(
            [
                f"主題｜{meeting.title}",
                "共識｜需要短輸出、清楚角色分工、可保存結論",
                "分歧｜是否立刻擴功能仍未定",
                "風險｜多供應商與 UI 同時擴張會升高維護成本",
                "下一步｜先固定主流程，再逐步接供應商",
            ]
        ),
        "recorder": "\n".join(
            [
                f"主題｜{meeting.title}",
                f"共識｜本輪輸入聚焦 {topic_hint[:52]}",
                "分歧｜仍有部分背景需再確認",
                "風險｜若摘要過長，閱讀與 token 成本都會上升",
                "下一步｜保留短句討論，最後再整理完整版",
            ]
        ),
    }

    reply = (concise_map if concise else full_map).get(
        role.role_key,
        "重點｜先收斂\n邏輯｜避免廢話與重複\n結論｜只保留可執行內容" if concise else "主題｜未指定\n共識｜先收斂\n分歧｜待釐清\n風險｜待確認\n下一步｜繼續整理",
    )
    if role.source == RoleSource.OPENCLAW:
        reply = "重點｜OpenClaw 預留席位\n邏輯｜目前尚未直接橋接 Gateway\n結論｜先以保留角色參與"
    return reply


def build_round_summary(
    meeting: Meeting,
    generated_messages: list[tuple[RoleProfile, str]],
    formal_input: str,
    note_input: str,
) -> str:
    highlights = [f"{role.display_name}:{extract_first_sentence(content)}" for role, content in generated_messages[:2]]
    return "\n".join(
        [
            f"焦點｜{meeting.title[:18]}",
            f"輸入｜{(formal_input or note_input or '無')[:18]}",
            f"共識｜{' / '.join(highlights)[:36]}",
            "下一步｜續談或整理",
        ]
    )


def extract_first_sentence(content: str) -> str:
    first = content.strip().splitlines()[0] if content.strip() else ""
    return first[:32]


def build_text_export(meeting: Meeting, transcript: list[dict]) -> str:
    lines = [
        f"會議標題：{meeting.title}",
        f"會議目標：{meeting.objective or '未指定'}",
        f"會議狀態：{meeting.status.value}",
        f"總輪次：{meeting.round_count}",
        "",
        "=== 會議逐字內容 ===",
        "",
    ]
    for item in transcript:
        lines.extend([f"[Round {item['round']}] {item['speaker']} ({item['type']})", item["content"], ""])
    return "\n".join(lines).strip() + "\n"


def build_python_export(meeting: Meeting, transcript: list[dict]) -> str:
    payload = {
        "title": meeting.title,
        "objective": meeting.objective,
        "status": meeting.status.value,
        "round_count": meeting.round_count,
        "temporary_memory": meeting.temporary_memory,
        "messages": transcript,
    }
    return "MEETING_ARCHIVE = " + repr(payload) + "\n"


def parse_python_archive(content: str) -> dict:
    prefix = "MEETING_ARCHIVE = "
    raw = content[len(prefix):] if content.startswith(prefix) else content
    return ast.literal_eval(raw)
