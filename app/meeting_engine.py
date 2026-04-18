from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from app.models import InteractionState, Meeting, MeetingMode, MeetingStateLog


ROLE_LIBRARY = {
    "ideation_interviewer": "發想訪談官",
    "chair": "主持人",
    "project_staff": "專案幕僚",
    "execution_staff": "執行幕僚",
    "risk_staff": "風險幕僚",
    "retrospective_staff": "復盤幕僚",
}

MODE_ROLE_MAP = {
    MeetingMode.PRE_PROJECT: ["project_staff", "risk_staff"],
    MeetingMode.IN_PROGRESS: ["execution_staff", "risk_staff", "project_staff"],
    MeetingMode.POST_REVIEW: ["retrospective_staff", "execution_staff", "risk_staff"],
}


@dataclass
class RoleOutput:
    role_id: str
    role_name: str
    summary: str
    observations: list[str]
    risks: list[str]
    options: list[str]
    recommended_next_step: str


@dataclass
class ChairOutput:
    conclusion: str
    confirmed_items: list[str]
    risks: list[str]
    pending_decisions: list[str]
    next_actions: list[dict[str, str]]


def transition_meeting_state(
    meeting: Meeting, target_state: InteractionState, reason: str
) -> MeetingStateLog:
    previous = meeting.current_state
    meeting.current_state = target_state
    return MeetingStateLog(
        meeting_id=meeting.id,
        from_state=previous,
        to_state=target_state,
        reason=reason,
    )


def build_context_payload(data: dict) -> dict:
    return {
        "timeline": data.get("timeline", ""),
        "task_list": [item for item in data.get("task_list", []) if item],
        "blockers": [item for item in data.get("blockers", []) if item],
        "risks": [item for item in data.get("risks", []) if item],
        "acceptance_criteria": [item for item in data.get("acceptance_criteria", []) if item],
        "kpis": [item for item in data.get("kpis", []) if item],
        "confirmation_notes": [],
        "reframing_notes": [],
    }


def split_points(*texts: str) -> list[str]:
    points: list[str] = []
    for text in texts:
        if not text:
            continue
        for line in text.splitlines():
            cleaned = re.sub(r"^[\-\*\d\.\)\s]+", "", line).strip()
            if cleaned:
                points.append(cleaned)
        if not points and text.strip():
            fragments = re.split(r"[。；;!?！？]+", text)
            points.extend(fragment.strip() for fragment in fragments if fragment.strip())
    return dedupe(points)


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def build_meeting_bundle(
    meeting: Meeting, user_message: str = "", applied_interrupts: list[str] | None = None
) -> dict:
    payload = meeting.context_payload or {}
    applied_interrupts = applied_interrupts or []

    facts = split_points(
        meeting.background_text,
        payload.get("timeline", ""),
        "\n".join(payload.get("task_list", [])),
        "\n".join(payload.get("acceptance_criteria", [])),
        "\n".join(payload.get("kpis", [])),
        "\n".join(payload.get("confirmation_notes", [])),
        "\n".join(payload.get("reframing_notes", [])),
        user_message,
        "\n".join(applied_interrupts),
    )

    explicit_risks = dedupe(payload.get("risks", []) + payload.get("blockers", []))
    pending_decisions = infer_pending_decisions(meeting)

    risks = dedupe(
        explicit_risks
        + infer_generic_risks(meeting, pending_decisions)
        + [f"使用者插話待吸收：{item}" for item in applied_interrupts]
    )

    return {
        "facts": facts,
        "explicit_risks": explicit_risks,
        "risks": risks,
        "pending_decisions": pending_decisions,
        "applied_interrupts": applied_interrupts,
    }


def infer_pending_decisions(meeting: Meeting) -> list[str]:
    payload = meeting.context_payload or {}
    pending: list[str] = []

    if not payload.get("timeline"):
        pending.append("尚未確認主要里程碑與時程")
    if not payload.get("task_list"):
        pending.append("尚未整理任務拆解與優先順序")
    if not payload.get("acceptance_criteria"):
        pending.append("尚未確認驗收標準")

    if meeting.meeting_mode == MeetingMode.PRE_PROJECT:
        pending.append("尚未指定各關鍵任務的責任人")
    elif meeting.meeting_mode == MeetingMode.IN_PROGRESS:
        pending.append("尚未同步本輪最優先交付與阻塞排除順序")
    else:
        pending.append("尚未完成成果落差與根因對照")

    return dedupe(pending)


def infer_generic_risks(meeting: Meeting, pending_decisions: list[str]) -> list[str]:
    risks: list[str] = []
    if pending_decisions:
        risks.append("若前提未先收斂，後續討論容易失焦或重工")

    payload = meeting.context_payload or {}
    if not payload.get("blockers"):
        risks.append("目前尚未形成明確 blocker 清單，可能低估執行阻力")
    if not payload.get("risks"):
        risks.append("目前風險盤點仍偏初步，建議盡快排序處理優先級")
    if meeting.meeting_mode == MeetingMode.POST_REVIEW and not payload.get("kpis"):
        risks.append("缺少成效數據時，復盤結論容易停留在印象層級")

    return dedupe(risks)


def build_intake_message(meeting: Meeting) -> dict:
    bundle = build_meeting_bundle(meeting)
    known_items = bundle["facts"][:4] or ["已建立會議主題，待補齊背景資料"]
    pending = bundle["pending_decisions"][:4]

    content = "\n".join(
        [
            "結論：",
            "已收到這次會議需求，建議先確認會議前提，再進入正式多角色討論。",
            "",
            "已知資訊：",
            *[f"{index}. {item}" for index, item in enumerate(known_items, start=1)],
            "",
            "待確認：",
            *[f"{index}. {item}" for index, item in enumerate(pending, start=1)],
            "",
            "下一步：",
            "請補充或確認前提，完成後即可進入正式會議。",
        ]
    )

    return {
        "content": content,
        "structured_payload": {
            "summary": "先完成前提確認，再進入正式會議。",
            "known_items": known_items,
            "pending_items": pending,
        },
    }


def build_role_outputs(
    meeting: Meeting, user_message: str = "", applied_interrupts: list[str] | None = None
) -> list[RoleOutput]:
    bundle = build_meeting_bundle(meeting, user_message=user_message, applied_interrupts=applied_interrupts)
    role_ids = MODE_ROLE_MAP[meeting.meeting_mode]
    outputs: list[RoleOutput] = []

    for role_id in role_ids:
        outputs.append(generate_role_output(role_id, meeting.meeting_mode, bundle))

    return outputs


def generate_role_output(role_id: str, meeting_mode: MeetingMode, bundle: dict) -> RoleOutput:
    facts = bundle["facts"] or ["目前會議仍需更多具體背景資料支撐。"]
    risks = bundle["risks"] or ["目前未發現明確高風險，但建議持續盤點。"]
    pending = bundle["pending_decisions"]

    if role_id == "project_staff":
        summary = {
            MeetingMode.PRE_PROJECT: "建議先鎖定範圍、里程碑與責任人，再展開第一版執行。",
            MeetingMode.IN_PROGRESS: "目前應先收斂本輪最重要交付，避免排程持續分散。",
            MeetingMode.POST_REVIEW: "建議將原始目標、實際結果與差距並排整理，才能形成有效復盤。",
        }[meeting_mode]
        observations = facts[:3]
        role_risks = dedupe(risks[:2] + pending[:1])
        options = [
            "先整理本輪範圍與不做項目，避免討論持續擴張。",
            "先排出里程碑與前置依賴，再決定任務順序。",
            "先確認責任分工，再讓各角色回報進度。",
        ]
        next_step = "由專案幕僚整理範圍、時程與責任人草案，交由主持人收斂。"
    elif role_id == "execution_staff":
        summary = {
            MeetingMode.PRE_PROJECT: "執行前建議先把交付順序與前置條件排清楚。",
            MeetingMode.IN_PROGRESS: "目前最務實的做法是先處理阻塞，再保住本輪承諾交付。",
            MeetingMode.POST_REVIEW: "應先還原實際執行過程，才能判斷哪些偏差可避免。",
        }[meeting_mode]
        observations = (facts[:2] + pending[:1])[:3]
        role_risks = dedupe(risks[:2])
        options = [
            "先處理最卡的 blocker，再排其他事項。",
            "將未完成事項重排優先級，避免資源平均分散。",
            "同步可立即交付與需延後處理的項目。",
        ]
        next_step = "由執行幕僚更新完成、進行中與卡點清單，作為下一輪追蹤基準。"
    elif role_id == "retrospective_staff":
        summary = "建議先把做得好的地方、失誤點與根因拆開記錄，避免復盤流於印象。"
        observations = (facts[:2] + pending[:1])[:3]
        role_risks = dedupe(risks[:2] + ["若未明確對照根因，改善措施容易流於口號。"])
        options = [
            "先還原事件時間線，再討論責任與改善。",
            "區分偶發失誤與結構性問題，避免過度修正。",
            "先定下一次要保留與要修正的做法。",
        ]
        next_step = "由復盤幕僚整理結果、差距與根因對照表，主持人再收斂改善方案。"
    else:
        summary = {
            MeetingMode.PRE_PROJECT: "目前最大風險在於前提未完全收斂就直接進入執行。",
            MeetingMode.IN_PROGRESS: "目前最大風險在於 blocker 與決策延遲同步不足。",
            MeetingMode.POST_REVIEW: "目前最大風險在於缺少數據或事實基礎，導致復盤偏主觀。",
        }[meeting_mode]
        observations = risks[:3]
        role_risks = dedupe(risks[:3])
        options = [
            "先排序高風險項目，避免每個問題都同時處理。",
            "針對每個高風險項目指定一個備援方案。",
            "把需要主管決策的項目獨立拉出，縮短等待時間。",
        ]
        next_step = "由風險幕僚列出高、中、低風險與備案，主持人確認哪些需立即升級。"

    return RoleOutput(
        role_id=role_id,
        role_name=ROLE_LIBRARY[role_id],
        summary=summary,
        observations=dedupe(observations)[:3],
        risks=dedupe(role_risks)[:3],
        options=options[:3],
        recommended_next_step=next_step,
    )


def role_output_to_message(output: RoleOutput) -> dict:
    content = "\n".join(
        [
            "結論：",
            output.summary,
            "",
            "觀察：",
            *[f"{index}. {item}" for index, item in enumerate(output.observations, start=1)],
            "",
            "風險：",
            *[f"{index}. {item}" for index, item in enumerate(output.risks, start=1)],
            "",
            "方案：",
            *[f"{index}. {item}" for index, item in enumerate(output.options, start=1)],
            "",
            "下一步：",
            output.recommended_next_step,
        ]
    )
    return {"content": content, "structured_payload": asdict(output)}


def build_chair_output(meeting: Meeting, role_outputs: list[RoleOutput], bundle: dict) -> ChairOutput:
    confirmed_items = bundle["facts"][:4] or ["目前已有基本背景資料可供討論。"]
    risks = dedupe([risk for output in role_outputs for risk in output.risks])[:4]
    pending_decisions = bundle["pending_decisions"][:4]
    next_actions = build_next_actions(meeting.meeting_mode, pending_decisions)

    if meeting.meeting_mode == MeetingMode.PRE_PROJECT:
        conclusion = "目前可先以 MVP 方式啟動，但本輪後應優先補齊範圍、時程與驗收標準。"
    elif meeting.meeting_mode == MeetingMode.IN_PROGRESS:
        conclusion = "目前建議先保住本輪關鍵交付，並把阻塞與決策需求集中處理。"
    else:
        conclusion = "目前可先完成復盤初稿，但仍需用結果與根因對照來支撐改善決策。"

    return ChairOutput(
        conclusion=conclusion,
        confirmed_items=confirmed_items,
        risks=risks,
        pending_decisions=pending_decisions,
        next_actions=next_actions,
    )


def build_next_actions(meeting_mode: MeetingMode, pending_decisions: list[str]) -> list[dict[str, str]]:
    if meeting_mode == MeetingMode.PRE_PROJECT:
        actions = [
            {"task": "整理範圍與不做清單", "owner": "專案幕僚", "due": "本輪後"},
            {"task": "確認主要風險與備案", "owner": "風險幕僚", "due": "本週"},
            {"task": "補齊驗收標準", "owner": "主持人", "due": "開始執行前"},
        ]
    elif meeting_mode == MeetingMode.IN_PROGRESS:
        actions = [
            {"task": "更新完成與進行中清單", "owner": "執行幕僚", "due": "今日"},
            {"task": "排定 blocker 解法與責任人", "owner": "風險幕僚", "due": "今日"},
            {"task": "確認下一個里程碑", "owner": "主持人", "due": "本輪後"},
        ]
    else:
        actions = [
            {"task": "整理成果與落差對照表", "owner": "復盤幕僚", "due": "本輪後"},
            {"task": "補齊根因與改善方案", "owner": "主持人", "due": "本週"},
            {"task": "指定改善方案責任人", "owner": "專案幕僚", "due": "本週"},
        ]

    if pending_decisions:
        actions.insert(
            0,
            {
                "task": f"先處理待決事項：{pending_decisions[0]}",
                "owner": "主持人",
                "due": "立即",
            },
        )

    return actions[:4]


def chair_output_to_message(output: ChairOutput) -> dict:
    content = "\n".join(
        [
            "目前結論：",
            output.conclusion,
            "",
            "已確認事項：",
            *[f"{index}. {item}" for index, item in enumerate(output.confirmed_items, start=1)],
            "",
            "主要風險：",
            *[f"{index}. {item}" for index, item in enumerate(output.risks, start=1)],
            "",
            "待決事項：",
            *[f"{index}. {item}" for index, item in enumerate(output.pending_decisions, start=1)],
            "",
            "下一步：",
            *[
                f"{index}. {action['task']} / {action['owner']} / {action['due']}"
                for index, action in enumerate(output.next_actions, start=1)
            ],
        ]
    )
    return {"content": content, "structured_payload": asdict(output)}

