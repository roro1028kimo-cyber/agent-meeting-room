from __future__ import annotations

from html import escape

from app.models import Meeting, SummarySnapshot


def build_markdown_report(meeting: Meeting, snapshot: SummarySnapshot, role_messages: list[dict]) -> str:
    lines = [
        f"# {meeting.topic}",
        "",
        f"- 會議模式：`{meeting.meeting_mode.value}`",
        f"- 目前狀態：`{meeting.current_state.value}`",
        f"- 輪次：`{snapshot.round_number}`",
        "",
        "## 主持人摘要",
        "",
        f"**目前結論**  {snapshot.conclusion}",
        "",
        "**已確認事項**",
        *[f"- {item}" for item in snapshot.confirmed_items],
        "",
        "**主要風險**",
        *[f"- {item}" for item in snapshot.risks],
        "",
        "**待決事項**",
        *[f"- {item}" for item in snapshot.pending_decisions],
        "",
        "**下一步**",
        *[
            f"- {action['task']} / {action['owner']} / {action['due']}"
            for action in snapshot.next_actions
        ],
        "",
        "## 角色摘要",
        "",
    ]

    for message in role_messages:
        lines.extend(
            [
                f"### {message['role_name']}",
                "",
                message["content"],
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def build_html_report(meeting: Meeting, snapshot: SummarySnapshot, role_messages: list[dict]) -> str:
    def list_items(items: list[str]) -> str:
        return "".join(f"<li>{escape(item)}</li>" for item in items)

    action_items = "".join(
        f"<li>{escape(action['task'])} / {escape(action['owner'])} / {escape(action['due'])}</li>"
        for action in snapshot.next_actions
    )
    role_sections = "".join(
        (
            f"<section class='role-card'>"
            f"<h3>{escape(message['role_name'])}</h3>"
            f"<pre>{escape(message['content'])}</pre>"
            f"</section>"
        )
        for message in role_messages
    )

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
  <head>
    <meta charset="utf-8" />
    <title>{escape(meeting.topic)} - 匯出報告</title>
    <style>
      body {{
        font-family: "Segoe UI", "Noto Sans TC", sans-serif;
        margin: 0;
        padding: 32px;
        background: #f4f1ea;
        color: #1b1a17;
      }}
      h1, h2, h3 {{
        margin-top: 0;
      }}
      .grid {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 20px;
        margin-bottom: 24px;
      }}
      .panel, .role-card {{
        background: white;
        border-radius: 18px;
        padding: 20px;
        box-shadow: 0 10px 30px rgba(32, 24, 16, 0.08);
      }}
      pre {{
        white-space: pre-wrap;
        font-family: inherit;
        line-height: 1.6;
      }}
    </style>
  </head>
  <body>
    <h1>{escape(meeting.topic)}</h1>
    <div class="grid">
      <section class="panel">
        <h2>主持人摘要</h2>
        <p><strong>目前結論：</strong> {escape(snapshot.conclusion)}</p>
        <p><strong>已確認事項</strong></p>
        <ul>{list_items(snapshot.confirmed_items)}</ul>
      </section>
      <section class="panel">
        <h2>風險與待決</h2>
        <p><strong>主要風險</strong></p>
        <ul>{list_items(snapshot.risks)}</ul>
        <p><strong>待決事項</strong></p>
        <ul>{list_items(snapshot.pending_decisions)}</ul>
        <p><strong>下一步</strong></p>
        <ul>{action_items}</ul>
      </section>
    </div>
    <section class="panel">
      <h2>角色摘要</h2>
      {role_sections}
    </section>
  </body>
</html>
"""

