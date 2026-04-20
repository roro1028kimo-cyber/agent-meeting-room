from __future__ import annotations

import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app
from app.meeting_engine import parse_python_archive


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

    def test_homepage_renders_successfully(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Agent Meeting Room", response.text)

    def test_bootstrap_returns_settings_and_roles(self) -> None:
        response = self.client.get("/api/bootstrap")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["settings"]["api_mode"], "mock")
        self.assertGreaterEqual(len(payload["roles"]), 6)

    def test_create_meeting_and_run_round(self) -> None:
        bootstrap = self.client.get("/api/bootstrap").json()
        role_ids = [role["id"] for role in bootstrap["roles"][:3]]
        meeting = self.client.post(
            "/api/meetings",
            json={
                "title": "輕量會議室測試",
                "objective": "確認多 agent 可逐輪發言",
                "context_text": "本版先以 mock 模式測試會議流程。",
                "selected_role_ids": role_ids,
            },
        ).json()

        round_response = self.client.post(
            f"/api/meetings/{meeting['id']}/rounds",
            json={
                "formal_input": "請收斂一版會議室 MVP 的功能邊界。",
                "note_input": "插話：請不要做成重型 PM 系統。",
            },
        )
        self.assertEqual(round_response.status_code, 200)
        payload = round_response.json()
        self.assertEqual(payload["round_count"], 1)
        self.assertTrue(payload["active_speaker"])
        self.assertTrue(any(message["message_type"] == "agent" for message in payload["messages"]))
        self.assertTrue(any(message["message_type"] == "summary" for message in payload["messages"]))
        self.assertTrue(payload["temporary_memory"]["latest_summary"])
        self.assertTrue(payload["temporary_memory"]["latest_formal_input"])
        self.assertTrue(payload["temporary_memory"]["latest_note_input"])

    def test_export_creates_archive_and_python_payload(self) -> None:
        bootstrap = self.client.get("/api/bootstrap").json()
        role_ids = [role["id"] for role in bootstrap["roles"][:2]]
        meeting = self.client.post(
            "/api/meetings",
            json={
                "title": "匯出測試",
                "objective": "確認文字與 Python 匯出正常",
                "context_text": "測試長期記憶存檔。",
                "selected_role_ids": role_ids,
            },
        ).json()
        self.client.post(
            f"/api/meetings/{meeting['id']}/rounds",
            json={"formal_input": "請給我一個簡單會議結論。", "note_input": ""},
        )

        exported = self.client.post(
            f"/api/meetings/{meeting['id']}/export",
            json={"export_format": "python", "archive": True},
        )
        self.assertEqual(exported.status_code, 200)
        payload = exported.json()
        self.assertTrue(payload["archived"])
        parsed = parse_python_archive(payload["content"])
        self.assertEqual(parsed["title"], "匯出測試")

        memories = self.client.get("/api/memories").json()
        self.assertGreaterEqual(len(memories), 1)


if __name__ == "__main__":
    unittest.main()
