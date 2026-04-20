from __future__ import annotations

from app.models import Meeting


def build_meeting_brief(meeting: Meeting) -> dict:
    return {
        "title": meeting.title,
        "objective": meeting.objective,
        "status": meeting.status.value,
        "round_count": meeting.round_count,
        "latest_summary": meeting.temporary_memory.get("latest_summary", ""),
    }
