from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.database import DatabaseManager
from app.meeting_engine import (
    close_meeting,
    create_meeting,
    ensure_defaults,
    export_meeting,
    generate_full_summary,
    get_meeting,
    get_roles,
    list_archives,
    list_recent_meetings,
    load_runtime_settings,
    run_meeting_round,
    settings_to_dict,
    update_settings,
)
from app.models import MemoryArchive, RoleProfile
from app.schemas import (
    AppSettingsPayload,
    ExportResponse,
    MeetingCreate,
    MeetingFullSummaryRequest,
    MeetingResponse,
    MeetingRoundRequest,
    MemoryArchiveResponse,
    RoleProfileCreate,
    RoleProfileResponse,
    RoleProfileUpdate,
    MeetingExportRequest,
)


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def create_app(database_url: str | None = None) -> FastAPI:
    db_manager = DatabaseManager(database_url or settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.db = db_manager
        app.state.db.try_initialize()
        with app.state.db.session() as session:
            ensure_defaults(session)
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
            "app_name": settings.app_name,
        }

    @app.get("/api/bootstrap")
    def bootstrap(session: Session = Depends(get_session)) -> dict[str, object]:
        runtime = load_runtime_settings(session)
        return {
            "settings": settings_to_dict(runtime),
            "roles": [serialize_role(role) for role in get_roles(session)],
            "meetings": [serialize_meeting_summary(meeting) for meeting in list_recent_meetings(session)],
            "memories": [MemoryArchiveResponse.model_validate(memory).model_dump(mode="json") for memory in list_archives(session)],
        }

    @app.get("/api/settings")
    def get_settings(session: Session = Depends(get_session)) -> dict[str, object]:
        return settings_to_dict(load_runtime_settings(session))

    @app.put("/api/settings")
    def put_settings(payload: AppSettingsPayload, session: Session = Depends(get_session)) -> dict[str, object]:
        return update_settings(session, payload.model_dump())

    @app.get("/api/roles")
    def roles(session: Session = Depends(get_session)) -> list[dict]:
        return [serialize_role(role) for role in get_roles(session)]

    @app.post("/api/roles")
    def create_role(payload: RoleProfileCreate, session: Session = Depends(get_session)) -> dict:
        role = RoleProfile(
            role_key=f"custom_{payload.display_name.strip().lower().replace(' ', '_')}_{len(get_roles(session)) + 1}",
            display_name=payload.display_name,
            description=payload.description,
            system_prompt=payload.system_prompt,
            color=payload.color,
            source=payload.source,
            provider=payload.provider,
            enabled=payload.enabled,
            is_builtin=False,
            model_override=payload.model_override,
            response_mode=payload.response_mode,
            max_output_tokens=payload.max_output_tokens,
            openclaw_agent_id=payload.openclaw_agent_id,
            sort_order=len(get_roles(session)) + 1,
        )
        session.add(role)
        session.commit()
        session.refresh(role)
        return serialize_role(role)

    @app.put("/api/roles/{role_id}")
    def update_role(role_id: int, payload: RoleProfileUpdate, session: Session = Depends(get_session)) -> dict:
        role = session.get(RoleProfile, role_id)
        if role is None:
            raise HTTPException(status_code=404, detail="Role not found.")

        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(role, key, value)
        session.commit()
        session.refresh(role)
        return serialize_role(role)

    @app.get("/api/meetings")
    def meetings(session: Session = Depends(get_session)) -> list[dict]:
        return [serialize_meeting_summary(meeting) for meeting in list_recent_meetings(session)]

    @app.post("/api/meetings", response_model=MeetingResponse)
    def post_meeting(payload: MeetingCreate, session: Session = Depends(get_session)) -> MeetingResponse:
        meeting = create_meeting(
            session,
            title=payload.title,
            objective=payload.objective,
            context_text=payload.context_text,
            selected_role_ids=payload.selected_role_ids,
        )
        return serialize_meeting(meeting)

    @app.get("/api/meetings/{meeting_id}", response_model=MeetingResponse)
    def get_meeting_detail(meeting_id: str, session: Session = Depends(get_session)) -> MeetingResponse:
        meeting = get_meeting(session, meeting_id)
        if meeting is None:
            raise HTTPException(status_code=404, detail="Meeting not found.")
        return serialize_meeting(meeting)

    @app.post("/api/meetings/{meeting_id}/rounds", response_model=MeetingResponse)
    def post_round(meeting_id: str, payload: MeetingRoundRequest, session: Session = Depends(get_session)) -> MeetingResponse:
        try:
            meeting = run_meeting_round(session, meeting_id, payload.formal_input, payload.note_input)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return serialize_meeting(meeting)

    @app.post("/api/meetings/{meeting_id}/close", response_model=MeetingResponse)
    def post_close(meeting_id: str, session: Session = Depends(get_session)) -> MeetingResponse:
        try:
            meeting = close_meeting(session, meeting_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return serialize_meeting(meeting)

    @app.post("/api/meetings/{meeting_id}/export", response_model=ExportResponse)
    def post_export(meeting_id: str, payload: MeetingExportRequest, session: Session = Depends(get_session)) -> ExportResponse:
        try:
            exported = export_meeting(session, meeting_id, payload.export_format, payload.archive)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return ExportResponse(**exported)

    @app.post("/api/meetings/{meeting_id}/full-summary", response_model=MeetingResponse)
    def post_full_summary(
        meeting_id: str,
        payload: MeetingFullSummaryRequest,
        session: Session = Depends(get_session),
    ) -> MeetingResponse:
        try:
            meeting = generate_full_summary(session, meeting_id, payload.force_provider)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return serialize_meeting(meeting)

    @app.get("/api/memories")
    def memories(session: Session = Depends(get_session)) -> list[dict]:
        return [MemoryArchiveResponse.model_validate(item).model_dump(mode="json") for item in list_archives(session)]

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
        ensure_defaults(session)
        yield session


def serialize_role(role: RoleProfile) -> dict:
    return RoleProfileResponse.model_validate(role).model_dump(mode="json")


def serialize_meeting(meeting) -> MeetingResponse:
    participants = [
        {
            "id": participant.id,
            "seat_order": participant.seat_order,
            "enabled": participant.enabled,
            "role": RoleProfileResponse.model_validate(participant.role_profile).model_dump(mode="json"),
        }
        for participant in sorted(meeting.participants, key=lambda item: item.seat_order)
    ]
    messages = sorted(meeting.messages, key=lambda item: (item.round_number, item.id))
    archives = sorted(meeting.archives, key=lambda item: item.created_at)
    return MeetingResponse(
        id=meeting.id,
        title=meeting.title,
        objective=meeting.objective,
        context_text=meeting.context_text,
        status=meeting.status,
        round_count=meeting.round_count,
        active_speaker=(meeting.temporary_memory or {}).get("active_speaker"),
        temporary_memory=meeting.temporary_memory or {},
        participants=participants,
        messages=messages,
        archives=archives,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
    )


def serialize_meeting_summary(meeting) -> dict:
    return {
        "id": meeting.id,
        "title": meeting.title,
        "status": meeting.status.value,
        "round_count": meeting.round_count,
        "updated_at": meeting.updated_at.isoformat(),
    }
