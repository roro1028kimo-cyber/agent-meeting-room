from __future__ import annotations

import ast
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
    RoleProfile,
    RoleSource,
)


DEFAULT_SETTINGS = {
    "api_mode": "mock",
    "api_key": "",
    "base_url": "https://api.openai.com/v1",
    "model_name": "gpt-4.1-mini",
    "temperature": 0.7,
    "max_tokens": 700,
    "openclaw_enabled": False,
    "openclaw_gateway_url": "",
    "openclaw_notes": "",
}


BUILTIN_ROLES = [
    {
        "role_key": "chair",
        "display_name": "主持人",
        "description": "控場、指定順序、最後收斂結論。",
        "color": "#7dd3fc",
        "sort_order": 1,
        "system_prompt": """你是會議主持人。
你的任務是：
1. 控制討論節奏。
2. 幫大家收斂焦點。
3. 在最後給出短而清楚的本輪結論。

發言要求：
- 使用繁體中文。
- 先說結論，再補充。
- 盡量控制在 4 到 8 句。
- 不要假裝知道不存在的事實。
- 不要做 PM 流程式長篇報告。""",
    },
    {
        "role_key": "planner",
        "display_name": "規劃師",
        "description": "把主題拆成方向、步驟與可行方案。",
        "color": "#c4b5fd",
        "sort_order": 2,
        "system_prompt": """你是規劃師。
你的任務是把議題拆成具體方向、步驟與選項。

發言要求：
- 使用繁體中文。
- 先說最可行的方向。
- 盡量給 2 到 4 個步驟。
- 短句、清楚、可執行。""",
    },
    {
        "role_key": "skeptic",
        "display_name": "反方辯手",
        "description": "挑戰假設，避免過度樂觀。",
        "color": "#fca5a5",
        "sort_order": 3,
        "system_prompt": """你是反方辯手。
你的任務是挑戰討論中的假設，指出過度樂觀、模糊或風險。

發言要求：
- 使用繁體中文。
- 直接指出問題。
- 不要情緒化。
- 每次至少提出一個需要重想的點。""",
    },
    {
        "role_key": "risk_officer",
        "display_name": "風險官",
        "description": "指出風險、依賴與失敗點。",
        "color": "#fbbf24",
        "sort_order": 4,
        "system_prompt": """你是風險官。
你的任務是找出可能失敗的地方、依賴條件與需要先確認的因素。

發言要求：
- 使用繁體中文。
- 列出最重要的 2 到 3 個風險。
- 若有風險，盡量附簡短備案。""",
    },
    {
        "role_key": "executor",
        "display_name": "執行官",
        "description": "把討論轉成可落地動作。",
        "color": "#6ee7b7",
        "sort_order": 5,
        "system_prompt": """你是執行官。
你的任務是把目前討論轉成可以立刻採取的下一步。

發言要求：
- 使用繁體中文。
- 優先講可立刻做的事。
- 盡量整理成 3 到 5 個行動點。""",
    },
    {
        "role_key": "recorder",
        "display_name": "記錄員",
        "description": "整理關鍵觀點與本輪共識。",
        "color": "#fdba74",
        "sort_order": 6,
        "system_prompt": """你是記錄員。
你的任務是把目前會議內容整理成短摘要，保留共識、分歧與下一步。

發言要求：
- 使用繁體中文。
- 條列清楚。
- 避免加入你自己新的推論。""",
    },
    {
        "role_key": "researcher",
        "display_name": "研究員",
        "description": "指出背景知識缺口與需要查證的資訊。",
        "color": "#93c5fd",
        "sort_order": 7,
        "system_prompt": """你是研究員。
你的任務是指出目前資訊缺口，以及應該補查什麼資料才能讓討論更可靠。

發言要求：
- 使用繁體中文。
- 重點放在缺什麼資訊。
- 不要假裝你已經查證完成。""",
    },
    {
        "role_key": "product_advisor",
        "display_name": "產品顧問",
        "description": "從使用者價值與產品角度提出看法。",
        "color": "#f9a8d4",
        "sort_order": 8,
        "system_prompt": """你是產品顧問。
你的任務是從使用者價值、定位與體驗角度給建議。

發言要求：
- 使用繁體中文。
- 聚焦使用者會不會看懂、想用、持續使用。
- 用簡單的產品語言。""",
    },
]


@dataclass
class RuntimeSettings:
    api_mode: str
    api_key: str
    base_url: str
    model_name: str
    temperature: float
    max_tokens: int
    openclaw_enabled: bool
    openclaw_gateway_url: str
    openclaw_notes: str


def ensure_defaults(session: Session) -> None:
    for key, value in DEFAULT_SETTINGS.items():
        if session.get(AppSetting, key) is None:
            session.add(AppSetting(key=key, value=value))

    existing = {
        role.role_key: role
        for role in session.execute(select(RoleProfile)).scalars().all()
    }
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
                    enabled=True,
                    is_builtin=True,
                    sort_order=definition["sort_order"],
                )
            )
        elif role.is_builtin:
            role.display_name = definition["display_name"]
            role.description = definition["description"]
            role.system_prompt = definition["system_prompt"]
            role.color = definition["color"]
            role.sort_order = definition["sort_order"]
    session.commit()


def load_runtime_settings(session: Session) -> RuntimeSettings:
    settings = {key: value for key, value in DEFAULT_SETTINGS.items()}
    for item in session.execute(select(AppSetting)).scalars().all():
        settings[item.key] = item.value
    return RuntimeSettings(**settings)


def settings_to_dict(settings: RuntimeSettings) -> dict:
    return {
        "api_mode": settings.api_mode,
        "api_key": settings.api_key,
        "base_url": settings.base_url,
        "model_name": settings.model_name,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "openclaw_enabled": settings.openclaw_enabled,
        "openclaw_gateway_url": settings.openclaw_gateway_url,
        "openclaw_notes": settings.openclaw_notes,
    }


def update_settings(session: Session, payload: dict) -> dict:
    for key, value in payload.items():
        row = session.get(AppSetting, key)
        if row is None:
            row = AppSetting(key=key, value=value)
            session.add(row)
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
        temporary_memory={"notes": [], "latest_summary": "", "latest_user_input": ""},
    )
    session.add(meeting)
    session.flush()

    seat = 1
    for role in available_roles:
        if role.id not in selected_role_ids:
            continue
        session.add(
            MeetingParticipant(
                meeting_id=meeting.id,
                role_profile_id=role.id,
                seat_order=seat,
                enabled=True,
            )
        )
        seat += 1

    session.add(
        MeetingMessage(
            meeting_id=meeting.id,
            role_profile_id=None,
            role_name="系統",
            message_type=MessageType.SYSTEM,
            round_number=0,
            content="會議已建立，請輸入主題補充後開始第一輪討論。",
            meta_payload=None,
        )
    )
    session.commit()
    session.expire_all()
    return get_meeting(session, meeting.id)


def list_recent_meetings(session: Session) -> list[Meeting]:
    statement = select(Meeting).order_by(Meeting.updated_at.desc()).limit(20)
    return session.execute(statement).scalars().all()


def list_archives(session: Session) -> list[MemoryArchive]:
    statement = select(MemoryArchive).order_by(MemoryArchive.created_at.desc()).limit(50)
    return session.execute(statement).scalars().all()


def run_meeting_round(session: Session, meeting_id: str, user_input: str) -> Meeting:
    meeting = get_meeting(session, meeting_id)
    if meeting is None:
        raise ValueError("Meeting not found.")
    if meeting.status == MeetingStatus.CLOSED:
        raise ValueError("Meeting is already closed.")

    runtime = load_runtime_settings(session)
    round_number = meeting.round_count + 1
    trimmed_input = user_input.strip()

    memory = dict(meeting.temporary_memory or {})
    memory.setdefault("notes", [])

    if trimmed_input:
        memory["latest_user_input"] = trimmed_input
        memory["notes"].append(f"使用者補充：{trimmed_input}")
        session.add(
            MeetingMessage(
                meeting_id=meeting.id,
                role_profile_id=None,
                role_name="使用者",
                message_type=MessageType.USER,
                round_number=round_number,
                content=trimmed_input,
                meta_payload=None,
            )
        )

    transcript = build_transcript(meeting)
    participant_roles = [participant.role_profile for participant in sorted(meeting.participants, key=lambda item: item.seat_order) if participant.enabled]

    generated_messages: list[tuple[RoleProfile, str]] = []
    for role in participant_roles:
        reply = generate_role_reply(runtime, role, meeting, transcript, trimmed_input)
        generated_messages.append((role, reply))
        transcript.append({"role": role.display_name, "content": reply})
        session.add(
            MeetingMessage(
                meeting_id=meeting.id,
                role_profile_id=role.id,
                role_name=role.display_name,
                message_type=MessageType.AGENT,
                round_number=round_number,
                content=reply,
                meta_payload={"source": role.source.value},
            )
        )

    summary_text = build_round_summary(meeting, generated_messages, trimmed_input)
    meeting.round_count = round_number
    memory["latest_summary"] = summary_text
    memory["notes"].append(f"第 {round_number} 輪摘要：{summary_text}")
    meeting.temporary_memory = memory

    session.add(
        MeetingMessage(
            meeting_id=meeting.id,
            role_profile_id=None,
            role_name="會議室",
            message_type=MessageType.SUMMARY,
            round_number=round_number,
            content=summary_text,
            meta_payload={"kind": "round_summary"},
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
                summary=meeting.temporary_memory.get("latest_summary", ""),
            )
        )
        memory = dict(meeting.temporary_memory or {})
        memory.setdefault("notes", [])
        memory["notes"].append(f"已匯出 {export_format} 檔案：{file_path}")
        meeting.temporary_memory = memory
        session.commit()

    return {
        "meeting_id": meeting.id,
        "export_format": export_format,
        "file_path": file_path,
        "content": content,
        "archived": archive,
    }


def build_transcript(meeting: Meeting) -> list[dict[str, str]]:
    items = [
        {"role": "會議主題", "content": meeting.title},
        {"role": "會議目標", "content": meeting.objective or "未指定"},
        {"role": "背景", "content": meeting.context_text or "未提供"},
    ]
    for message in sorted(meeting.messages, key=lambda item: (item.round_number, item.id))[-12:]:
        items.append({"role": message.role_name, "content": message.content})
    return items


def generate_role_reply(runtime: RuntimeSettings, role: RoleProfile, meeting: Meeting, transcript: list[dict], user_input: str) -> str:
    if runtime.api_mode == "openai_compatible" and runtime.api_key:
        try:
            return call_openai_compatible(runtime, role, meeting, transcript, user_input)
        except Exception as exc:
            return build_fallback_reply(role, meeting, user_input, transcript, reason=f"模型呼叫失敗：{exc}")
    return build_fallback_reply(role, meeting, user_input, transcript)


def call_openai_compatible(runtime: RuntimeSettings, role: RoleProfile, meeting: Meeting, transcript: list[dict], user_input: str) -> str:
    messages = [
        {"role": "system", "content": role.system_prompt},
        {
            "role": "user",
            "content": "\n".join(
                [
                    f"會議主題：{meeting.title}",
                    f"會議目標：{meeting.objective or '未指定'}",
                    f"背景：{meeting.context_text or '未提供'}",
                    f"本輪使用者輸入：{user_input or '無'}",
                    "最近討論：",
                    *[f"- {item['role']}：{item['content']}" for item in transcript[-10:]],
                    "",
                    "請你以你的角色定位發言，使用繁體中文，控制在 4 到 8 句。",
                ]
            ),
        },
    ]

    response = httpx.post(
        f"{runtime.base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {runtime.api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": role.model_override or runtime.model_name,
            "messages": messages,
            "temperature": runtime.temperature,
            "max_tokens": runtime.max_tokens,
            "stream": False,
        },
        timeout=60.0,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def build_fallback_reply(role: RoleProfile, meeting: Meeting, user_input: str, transcript: list[dict], reason: str | None = None) -> str:
    latest_points = [item["content"] for item in transcript[-3:]]
    context_hint = "；".join(latest_points) if latest_points else "目前討論剛開始。"

    style_map = {
        "chair": f"結論：本輪建議先聚焦在「{meeting.title}」，避免討論擴散。觀察：{context_hint}。下一步：請每位角色只補最重要的一點。",
        "planner": f"我建議先把「{meeting.title}」拆成目標、限制、下一步三塊。依目前內容看，先處理：{user_input or '補齊背景'}。",
        "skeptic": f"我想挑戰一個假設：我們可能把議題講得太快。若不先確認背景與限制，後面容易各說各話。",
        "risk_officer": f"目前最值得先注意的是資訊不足、範圍過大與執行落差。若不先收斂，這場會議很容易失焦。",
        "executor": f"如果要讓這輪討論往前走，我建議先做三件事：定義目標、確認參與角色、產出一版短結論。",
        "recorder": f"目前可先記下三個重點：會議主題是「{meeting.title}」、使用者最新補充是「{user_input or '尚無'}」、本輪需要收斂下一步。",
        "researcher": "目前最大的問題不是答案不夠，而是缺少背景資訊。建議先補：定義、限制、使用情境、成功標準。",
        "product_advisor": f"從產品角度看，這場會議要先確認使用者真的在意什麼。若主題是「{meeting.title}」，那最需要先講清楚的是價值。",
    }
    reply = style_map.get(role.role_key, f"我會以「{role.display_name}」的角度回應這個主題，先聚焦於最重要的一點，再補充下一步。")
    if role.source == RoleSource.OPENCLAW:
        reply = f"此席位目前標記為 OpenClaw 預留角色。本版尚未直接橋接 OpenClaw Gateway，因此先以保留席位方式參與討論。"
    if reason:
        reply = f"{reply}\n\n備註：{reason}"
    return reply


def build_round_summary(meeting: Meeting, generated_messages: list[tuple[RoleProfile, str]], user_input: str) -> str:
    key_lines = [f"- {role.display_name}：{extract_first_sentence(content)}" for role, content in generated_messages[:4]]
    return "\n".join(
        [
            f"第 {meeting.round_count + 1} 輪摘要",
            f"主題：{meeting.title}",
            f"使用者補充：{user_input or '本輪未新增補充'}",
            "本輪重點：",
            *key_lines,
            "建議下一步：由使用者決定是否再開下一輪，或直接匯出為長期記憶。",
        ]
    )


def extract_first_sentence(content: str) -> str:
    line = content.strip().splitlines()[0] if content.strip() else ""
    if len(line) > 80:
        return line[:77] + "..."
    return line


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
        lines.extend(
            [
                f"[Round {item['round']}] {item['speaker']} ({item['type']})",
                item["content"],
                "",
            ]
        )
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
