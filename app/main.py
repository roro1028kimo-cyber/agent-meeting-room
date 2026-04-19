from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import DatabaseManager
from app.meeting_engine import (
    ROLE_LIBRARY,
    build_chair_output,
    build_meeting_bundle,
    build_context_payload,
    build_intake_message,
    build_role_outputs,
    chair_output_to_message,
    role_output_to_message,
    transition_meeting_state,
)
from app.models import (
    ActionItem,
    InteractionState,
    Meeting,
    MeetingMessage,
    MeetingStateLog,
    MessageType,
    QueueStatus,
    RiskItem,
    SummarySnapshot,
    UserInterruptQueue,
)
from app.reports import build_html_report, build_markdown_report
from app.schemas import (
    ChairSummaryResponse,
    DiscussionRequest,
    InterruptRequest,
    MeetingConfirmRequest,
    MeetingCreate,
    MeetingResponse,
    ReframeRequest,
)


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
logger = logging.getLogger(__name__)


def create_app(database_url: str | None = None) -> FastAPI:
    db_manager = DatabaseManager(database_url or settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.db = db_manager
        app.state.db.try_initialize()
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"title": settings.app_name},
        )

    @app.get("/api/health")
    def health(request: Request) -> dict[str, object]:
        db = request.app.state.db
        return {
            "status": "ok",
            "database_initialized": db.initialized,
            "database_configured": bool(db.database_url),
        }

    @app.get("/api/ready")
    def ready(request: Request) -> dict[str, object]:
        db = request.app.state.db
        if not db.initialized:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "degraded",
                    "message": "資料庫尚未完成初始化",
                    "database_url_present": bool(db.database_url),
                    "last_error": db.last_error,
                },
            )
        return {"status": "ready"}

    @app.post("/api/meetings", response_model=MeetingResponse)
    def create_meeting(payload: MeetingCreate, session: Session = Depends(get_session)) -> MeetingResponse:
        meeting = Meeting(
            topic=payload.topic,
            meeting_mode=payload.meeting_mode,
            current_state=InteractionState.INTAKE,
            background_text=payload.background,
            context_payload=build_context_payload(payload.model_dump()),
        )
        session.add(meeting)
        session.flush()

        session.add(
            MeetingStateLog(
                meeting_id=meeting.id,
                from_state=None,
                to_state=InteractionState.INTAKE,
                reason="meeting created",
            )
        )

        intake_message = build_intake_message(meeting)
        session.add(
            MeetingMessage(
                meeting_id=meeting.id,
                round_number=0,
                role_id="ideation_interviewer",
                role_name=ROLE_LIBRARY["ideation_interviewer"],
                message_type=MessageType.AGENT,
                content=intake_message["content"],
                structured_payload=intake_message["structured_payload"],
            )
        )
        session.commit()
        return build_meeting_response(session, meeting.id)

    @app.post("/api/meetings/{meeting_id}/confirm", response_model=MeetingResponse)
    def confirm_meeting(
        meeting_id: str,
        payload: MeetingConfirmRequest,
        session: Session = Depends(get_session),
    ) -> MeetingResponse:
        meeting = get_meeting(session, meeting_id)
        context_payload = dict(meeting.context_payload or {})
        if payload.note:
            context_payload.setdefault("confirmation_notes", []).append(payload.note)
            meeting.context_payload = context_payload

        state_log = transition_meeting_state(
            meeting, InteractionState.CONFIRMING, "premise confirmed by user"
        )
        session.add(state_log)
        session.add(
            MeetingMessage(
                meeting_id=meeting.id,
                round_number=0,
                role_id="chair",
                role_name=ROLE_LIBRARY["chair"],
                message_type=MessageType.SYSTEM,
                content="主持人已收到確認，接下來可進入正式會議。",
                structured_payload={"note": payload.note or ""},
            )
        )
        session.commit()
        return build_meeting_response(session, meeting.id)

    @app.post("/api/meetings/{meeting_id}/discussion", response_model=MeetingResponse)
    def run_discussion(
        meeting_id: str,
        payload: DiscussionRequest,
        session: Session = Depends(get_session),
    ) -> MeetingResponse:
        meeting = get_meeting(session, meeting_id)
        if meeting.current_state == InteractionState.PAUSED_FOR_USER_CORRECTION:
            raise HTTPException(status_code=409, detail="Meeting is paused. Reframe before continuing.")

        if meeting.current_state == InteractionState.INTAKE:
            if not payload.message.strip():
                raise HTTPException(status_code=400, detail="Provide intake input before moving forward.")
            meeting.background_text = (meeting.background_text + "\n" + payload.message).strip()
            session.add(
                MeetingMessage(
                    meeting_id=meeting.id,
                    round_number=0,
                    role_id="user",
                    role_name="使用者",
                    message_type=MessageType.USER,
                    content=payload.message,
                    structured_payload=None,
                )
            )
            session.add(
                transition_meeting_state(
                    meeting, InteractionState.CONFIRMING, "intake details updated"
                )
            )
            intake_message = build_intake_message(meeting)
            session.add(
                MeetingMessage(
                    meeting_id=meeting.id,
                    round_number=0,
                    role_id="ideation_interviewer",
                    role_name=ROLE_LIBRARY["ideation_interviewer"],
                    message_type=MessageType.AGENT,
                    content=intake_message["content"],
                    structured_payload=intake_message["structured_payload"],
                )
            )
            session.commit()
            return build_meeting_response(session, meeting.id)

        if meeting.current_state in {InteractionState.CONFIRMING, InteractionState.REFRAMING, InteractionState.USER_INPUT_QUEUED}:
            session.add(
                transition_meeting_state(
                    meeting, InteractionState.MEETING_LIVE, "meeting round started"
                )
            )

        round_number = get_next_round_number(session, meeting.id)
        applied_interrupts = apply_pending_interrupts(session, meeting, round_number)

        if payload.message.strip():
            session.add(
                MeetingMessage(
                    meeting_id=meeting.id,
                    round_number=round_number,
                    role_id="user",
                    role_name="使用者",
                    message_type=MessageType.USER,
                    content=payload.message,
                    structured_payload=None,
                )
            )

        role_outputs = build_role_outputs(
            meeting,
            user_message=payload.message,
            applied_interrupts=applied_interrupts,
        )
        bundle = build_meeting_bundle(meeting, payload.message, applied_interrupts)

        role_messages_for_report: list[dict] = []
        for output in role_outputs:
            rendered = role_output_to_message(output)
            role_messages_for_report.append(
                {"role_name": output.role_name, "content": rendered["content"]}
            )
            session.add(
                MeetingMessage(
                    meeting_id=meeting.id,
                    round_number=round_number,
                    role_id=output.role_id,
                    role_name=output.role_name,
                    message_type=MessageType.AGENT,
                    content=rendered["content"],
                    structured_payload=rendered["structured_payload"],
                )
            )

        chair_output = build_chair_output(meeting, role_outputs, bundle)
        chair_rendered = chair_output_to_message(chair_output)
        snapshot = SummarySnapshot(
            meeting_id=meeting.id,
            round_number=round_number,
            conclusion=chair_output.conclusion,
            confirmed_items=chair_output.confirmed_items,
            risks=chair_output.risks,
            pending_decisions=chair_output.pending_decisions,
            next_actions=chair_output.next_actions,
        )
        session.add(snapshot)
        session.flush()

        snapshot.markdown_report = build_markdown_report(meeting, snapshot, role_messages_for_report)
        snapshot.html_report = build_html_report(meeting, snapshot, role_messages_for_report)

        session.add(
            MeetingMessage(
                meeting_id=meeting.id,
                round_number=round_number,
                role_id="chair",
                role_name=ROLE_LIBRARY["chair"],
                message_type=MessageType.CHAIR_SUMMARY,
                content=chair_rendered["content"],
                structured_payload=chair_rendered["structured_payload"],
            )
        )

        for action in chair_output.next_actions:
            session.add(
                ActionItem(
                    meeting_id=meeting.id,
                    snapshot_id=snapshot.id,
                    task=action["task"],
                    owner=action["owner"],
                    due=action["due"],
                    source_role="chair",
                )
            )

        for risk in chair_output.risks:
            session.add(
                RiskItem(
                    meeting_id=meeting.id,
                    snapshot_id=snapshot.id,
                    summary=risk,
                    severity="medium",
                    mitigation="由主持人安排後續處理與備案確認。",
                )
            )

        session.commit()
        return build_meeting_response(session, meeting.id)

    @app.post("/api/meetings/{meeting_id}/interrupts", response_model=MeetingResponse)
    def queue_interrupt(
        meeting_id: str,
        payload: InterruptRequest,
        session: Session = Depends(get_session),
    ) -> MeetingResponse:
        meeting = get_meeting(session, meeting_id)
        queue_item = UserInterruptQueue(
            meeting_id=meeting.id,
            message=payload.message,
            priority=payload.priority,
            mode=payload.mode,
        )
        session.add(queue_item)

        if payload.priority.value == "high":
            session.add(
                transition_meeting_state(
                    meeting,
                    InteractionState.PAUSED_FOR_USER_CORRECTION,
                    "high-priority user interruption",
                )
            )
            session.add(
                MeetingMessage(
                    meeting_id=meeting.id,
                    round_number=get_latest_round_number(session, meeting.id),
                    role_id="chair",
                    role_name=ROLE_LIBRARY["chair"],
                    message_type=MessageType.SYSTEM,
                    content="收到高優先修正，會議已暫停，待重整前提後再繼續。",
                    structured_payload={"priority": payload.priority.value},
                )
            )
        else:
            session.add(
                transition_meeting_state(
                    meeting,
                    InteractionState.USER_INPUT_QUEUED,
                    "interrupt queued for next round",
                )
            )
        session.commit()
        return build_meeting_response(session, meeting.id)

    @app.post("/api/meetings/{meeting_id}/reframe", response_model=MeetingResponse)
    def reframe_meeting(
        meeting_id: str,
        payload: ReframeRequest,
        session: Session = Depends(get_session),
    ) -> MeetingResponse:
        meeting = get_meeting(session, meeting_id)
        context_payload = dict(meeting.context_payload or {})
        context_payload.setdefault("reframing_notes", []).append(payload.updated_context)
        meeting.context_payload = context_payload
        session.add(
            transition_meeting_state(meeting, InteractionState.REFRAMING, "meeting reframed by user")
        )
        session.add(
            MeetingMessage(
                meeting_id=meeting.id,
                round_number=get_latest_round_number(session, meeting.id),
                role_id="chair",
                role_name=ROLE_LIBRARY["chair"],
                message_type=MessageType.SYSTEM,
                content="\n".join(
                    [
                        "收到使用者補充，以下更新本輪前提：",
                        f"1. 新增或修正事項：{payload.updated_context}",
                        "2. 對目前討論的影響：主持人將以新前提重整接下來的討論順序。",
                        "3. 接下來將如何調整討論順序：下一輪先重新收斂前提，再進入角色回應。",
                    ]
                ),
                structured_payload={"updated_context": payload.updated_context},
            )
        )
        session.commit()
        return build_meeting_response(session, meeting.id)

    @app.post("/api/meetings/{meeting_id}/finalize", response_model=MeetingResponse)
    def finalize_meeting(meeting_id: str, session: Session = Depends(get_session)) -> MeetingResponse:
        meeting = get_meeting(session, meeting_id)
        session.add(
            transition_meeting_state(
                meeting, InteractionState.FINALIZING, "final summary requested"
            )
        )
        session.add(
            MeetingMessage(
                meeting_id=meeting.id,
                round_number=get_latest_round_number(session, meeting.id),
                role_id="chair",
                role_name=ROLE_LIBRARY["chair"],
                message_type=MessageType.SYSTEM,
                content="主持人正在整理最終摘要與可交辦項目。",
                structured_payload=None,
            )
        )
        session.commit()
        return build_meeting_response(session, meeting.id)

    @app.get("/api/meetings/{meeting_id}", response_model=MeetingResponse)
    def get_meeting_detail(meeting_id: str, session: Session = Depends(get_session)) -> MeetingResponse:
        return build_meeting_response(session, meeting_id)

    @app.get("/api/meetings/{meeting_id}/export")
    def export_meeting(
        meeting_id: str,
        format: str = Query(default="json", pattern="^(json|markdown|html)$"),
        session: Session = Depends(get_session),
    ):
        meeting = get_meeting(session, meeting_id)
        snapshot = get_latest_snapshot(session, meeting.id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="No summary snapshot available yet.")

        if format == "markdown":
            return PlainTextResponse(snapshot.markdown_report, media_type="text/markdown; charset=utf-8")
        if format == "html":
            return HTMLResponse(snapshot.html_report)
        return JSONResponse(build_meeting_response(session, meeting.id).model_dump(mode="json"))

    return app


def get_session(request: Request):
    if not request.app.state.db.initialized:
        request.app.state.db.try_initialize()
    if not request.app.state.db.initialized:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "資料庫尚未就緒，請稍後再試",
                "last_error": request.app.state.db.last_error,
            },
        )
    with request.app.state.db.session() as session:
        yield session


def get_meeting(session: Session, meeting_id: str) -> Meeting:
    meeting = session.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return meeting


def get_latest_round_number(session: Session, meeting_id: str) -> int:
    snapshot = get_latest_snapshot(session, meeting_id)
    return snapshot.round_number if snapshot else 0


def get_next_round_number(session: Session, meeting_id: str) -> int:
    return get_latest_round_number(session, meeting_id) + 1


def get_latest_snapshot(session: Session, meeting_id: str) -> SummarySnapshot | None:
    statement = (
        select(SummarySnapshot)
        .where(SummarySnapshot.meeting_id == meeting_id)
        .order_by(SummarySnapshot.round_number.desc(), SummarySnapshot.id.desc())
    )
    return session.execute(statement).scalars().first()


def apply_pending_interrupts(session: Session, meeting: Meeting, round_number: int) -> list[str]:
    statement = (
        select(UserInterruptQueue)
        .where(
            UserInterruptQueue.meeting_id == meeting.id,
            UserInterruptQueue.status == QueueStatus.PENDING,
        )
        .order_by(UserInterruptQueue.created_at.asc(), UserInterruptQueue.id.asc())
    )
    pending_items = session.execute(statement).scalars().all()
    applied_messages: list[str] = []
    for item in pending_items:
        if item.priority.value == "high" and meeting.current_state != InteractionState.REFRAMING:
            continue
        item.status = QueueStatus.APPLIED
        item.applied_in_round = round_number
        applied_messages.append(item.message)
    return applied_messages


def build_meeting_response(session: Session, meeting_id: str) -> MeetingResponse:
    meeting = get_meeting(session, meeting_id)
    messages = session.execute(
        select(MeetingMessage)
        .where(MeetingMessage.meeting_id == meeting_id)
        .order_by(MeetingMessage.created_at.asc(), MeetingMessage.id.asc())
    ).scalars().all()
    interrupts = session.execute(
        select(UserInterruptQueue)
        .where(UserInterruptQueue.meeting_id == meeting_id)
        .order_by(UserInterruptQueue.created_at.asc(), UserInterruptQueue.id.asc())
    ).scalars().all()
    snapshot = get_latest_snapshot(session, meeting_id)
    chair_summary = ChairSummaryResponse(
        conclusion=snapshot.conclusion if snapshot else "",
        confirmed_items=snapshot.confirmed_items if snapshot else [],
        risks=snapshot.risks if snapshot else [],
        pending_decisions=snapshot.pending_decisions if snapshot else [],
        next_actions=snapshot.next_actions if snapshot else [],
        round_number=snapshot.round_number if snapshot else None,
    )
    return MeetingResponse(
        id=meeting.id,
        topic=meeting.topic,
        meeting_mode=meeting.meeting_mode,
        current_state=meeting.current_state,
        background_text=meeting.background_text,
        context_payload=meeting.context_payload or {},
        chair_summary=chair_summary,
        messages=messages,
        interrupts=interrupts,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
    )
