from __future__ import annotations

import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


class AgentMeetingRoomTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db_path = Path.cwd() / f"test-agent-meeting-room-{uuid4().hex}.db"
        self.database_url = f"sqlite:///{self.db_path.as_posix()}"
        self.app = create_app(self.database_url)
        self.client = TestClient(self.app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.app.state.db.engine.dispose()
        if self.db_path.exists():
            self.db_path.unlink()

    def create_meeting(self) -> dict:
        response = self.client.post(
            "/api/meetings",
            json={
                "topic": "Agent Meeting Room MVP",
                "meeting_mode": "pre_project",
                "background": "要完成第一版可測試的多角色會議系統。",
                "timeline": "兩週內完成 MVP",
                "task_list": ["建立 FastAPI API", "完成 HTML 介面"],
                "blockers": ["尚未確認正式部署方式"],
                "risks": ["需求持續變動造成重工"],
                "acceptance_criteria": ["可建立會議", "可輸出主持人摘要"],
                "kpis": [],
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_homepage_renders_successfully(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Agent Meeting Room", response.text)

    def test_create_meeting_generates_intake_message(self) -> None:
        meeting = self.create_meeting()
        self.assertEqual(meeting["current_state"], "intake")
        self.assertTrue(meeting["messages"])
        self.assertEqual(meeting["messages"][0]["role_id"], "ideation_interviewer")

    def test_confirm_and_discuss_generates_summary(self) -> None:
        meeting = self.create_meeting()
        meeting_id = meeting["id"]

        confirm_response = self.client.post(
            f"/api/meetings/{meeting_id}/confirm",
            json={"note": "可以開始正式會議。"},
        )
        self.assertEqual(confirm_response.status_code, 200)
        self.assertEqual(confirm_response.json()["current_state"], "confirming")

        discussion_response = self.client.post(
            f"/api/meetings/{meeting_id}/discussion",
            json={"message": "請整理 MVP 範圍、主要風險與下一步。"},
        )
        self.assertEqual(discussion_response.status_code, 200)
        payload = discussion_response.json()
        self.assertEqual(payload["current_state"], "meeting_live")
        self.assertTrue(payload["chair_summary"]["conclusion"])
        self.assertGreaterEqual(len(payload["chair_summary"]["next_actions"]), 1)

    def test_interrupt_and_reframe_flow(self) -> None:
        meeting = self.create_meeting()
        meeting_id = meeting["id"]
        self.client.post(f"/api/meetings/{meeting_id}/confirm", json={"note": "開始會議"})
        self.client.post(
            f"/api/meetings/{meeting_id}/discussion",
            json={"message": "先做第一輪收斂"},
        )

        interrupt_response = self.client.post(
            f"/api/meetings/{meeting_id}/interrupts",
            json={"message": "關鍵限制改成一週內完成", "priority": "high", "mode": "meeting"},
        )
        self.assertEqual(interrupt_response.status_code, 200)
        self.assertEqual(
            interrupt_response.json()["current_state"], "paused_for_user_correction"
        )

        reframe_response = self.client.post(
            f"/api/meetings/{meeting_id}/reframe",
            json={"updated_context": "排程修正為一週內可交付的 MVP"},
        )
        self.assertEqual(reframe_response.status_code, 200)
        self.assertEqual(reframe_response.json()["current_state"], "reframing")

        resumed_response = self.client.post(
            f"/api/meetings/{meeting_id}/discussion",
            json={"message": "請依新時程重排任務。"},
        )
        self.assertEqual(resumed_response.status_code, 200)
        self.assertEqual(resumed_response.json()["current_state"], "meeting_live")

    def test_exports_work_after_discussion(self) -> None:
        meeting = self.create_meeting()
        meeting_id = meeting["id"]
        self.client.post(f"/api/meetings/{meeting_id}/confirm", json={"note": "開始會議"})
        self.client.post(
            f"/api/meetings/{meeting_id}/discussion",
            json={"message": "請整理結論與下一步。"},
        )

        json_response = self.client.get(f"/api/meetings/{meeting_id}/export?format=json")
        markdown_response = self.client.get(
            f"/api/meetings/{meeting_id}/export?format=markdown"
        )
        html_response = self.client.get(f"/api/meetings/{meeting_id}/export?format=html")

        self.assertEqual(json_response.status_code, 200)
        self.assertEqual(markdown_response.status_code, 200)
        self.assertEqual(html_response.status_code, 200)
        self.assertIn("# Agent Meeting Room MVP", markdown_response.text)
        self.assertIn("<html", html_response.text.lower())


if __name__ == "__main__":
    unittest.main()
