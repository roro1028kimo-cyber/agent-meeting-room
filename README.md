# Agent Meeting Room

Agent Meeting Room is a first-version meeting orchestration MVP based on the specification in `agent.md`.

This build follows the agreed stack:

- Frontend: HTML + CSS + vanilla JavaScript
- Backend: Python + FastAPI
- Database: PostgreSQL via SQLAlchemy
- API contract: JSON

## What The MVP Can Do

- create a meeting with background context
- guide the user through intake and confirming states
- run a structured multi-role meeting round
- queue low/medium interruptions
- pause on high-priority corrections
- reframe the premise and continue the meeting
- produce chair summaries, risks, pending decisions, and action items
- export the latest result as JSON, Markdown, or HTML

## Project Structure

```text
app/
  main.py
  config.py
  database.py
  models.py
  schemas.py
  meeting_engine.py
  reports.py
  static/
    app.js
    style.css
  templates/
    index.html
tests/
agent.md
requirements.txt
docker-compose.yml
```

## Local Setup

1. Create and activate a virtual environment.
2. Install dependencies.
3. Start PostgreSQL.
4. Run the FastAPI app.

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
docker compose up -d
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/agent_meeting_room"
uvicorn app.main:create_app --factory --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Test

The automated tests run against SQLite for speed, while the application is designed to use PostgreSQL in development and production.

```powershell
python -m unittest discover -s tests -v
```

## Main Endpoints

- `POST /api/meetings`
- `POST /api/meetings/{meeting_id}/confirm`
- `POST /api/meetings/{meeting_id}/discussion`
- `POST /api/meetings/{meeting_id}/interrupts`
- `POST /api/meetings/{meeting_id}/reframe`
- `POST /api/meetings/{meeting_id}/finalize`
- `GET /api/meetings/{meeting_id}`
- `GET /api/meetings/{meeting_id}/export?format=json|markdown|html`

## Notes

- PostgreSQL is the primary database target for the product spec.
- SQLite is kept only as a test fallback.
- The current role engine is deterministic and template-based so the first version is testable end-to-end.
- A future iteration can replace the role engine with LLM-backed prompting without changing the API contract.

