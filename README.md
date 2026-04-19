# Agent Meeting Room

`Agent Meeting Room` 是依照 [agent.md](C:\codex\agent-meeting-room\agent.md:1) 規格實作的第一版會議代理系統 MVP。

如果你要看這次交付做了哪些內容、測試到哪裡、目前還缺什麼，請直接看 `REPORT.md`。

## 專案定位

這個專案的核心不是單純聊天，而是把會議流程做成可控、可追蹤、可匯出的系統，讓使用者能透過多角色代理完成：

- 會議前提整理
- 正式會議收斂
- 插話排隊與高優先修正
- 主持人摘要整合
- 待辦與風險輸出
- 多格式報告匯出

## 第一版技術組合

- 前端：HTML + CSS + 原生 JavaScript
- 後端：Python + FastAPI
- 資料存取：SQLAlchemy
- 正式資料庫：PostgreSQL
- 測試資料庫：SQLite
- API 主交換格式：JSON

## 第一版已完成能力

- 建立會議
- 進入訪談整理流程
- 進行前提確認
- 啟動正式會議回合
- 輸出多角色回應
- 產生主持人摘要
- 支援中低優先插話排隊
- 支援高優先插話暫停與重整
- 匯出 JSON、Markdown、HTML

## 專案結構

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
REPORT.md
requirements.txt
docker-compose.yml
```

## 本機啟動方式

### 1. 建立虛擬環境

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. 安裝相依套件

```powershell
pip install -r requirements.txt
```

### 3. 啟動 PostgreSQL

```powershell
docker compose up -d
```

### 4. 設定資料庫連線

```powershell
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/agent_meeting_room"
```

### 5. 啟動應用程式

```powershell
uvicorn app.main:create_app --factory --reload
```

啟動後可開啟：

- 首頁：[http://127.0.0.1:8000](http://127.0.0.1:8000)

## 測試方式

目前自動化測試使用 SQLite 作為測試資料庫，目的是讓測試更快、更穩定；正式開發與部署仍以 PostgreSQL 為主。

執行指令如下：

```powershell
python -m unittest discover -s tests -v
```

## 主要 API

- `POST /api/meetings`
- `POST /api/meetings/{meeting_id}/confirm`
- `POST /api/meetings/{meeting_id}/discussion`
- `POST /api/meetings/{meeting_id}/interrupts`
- `POST /api/meetings/{meeting_id}/reframe`
- `POST /api/meetings/{meeting_id}/finalize`
- `GET /api/meetings/{meeting_id}`
- `GET /api/meetings/{meeting_id}/export?format=json|markdown|html`

## 補充說明

- PostgreSQL 是本專案規格中的正式資料庫目標。
- SQLite 只保留給測試流程使用。
- 目前角色引擎為可測試的規則式版本，方便先把狀態機、資料流與輸出格式打通。
- 後續可以在不改動 API 契約的前提下，替換成真正的 LLM 驅動角色流程。

