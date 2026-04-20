# Agent Meeting Room

`Agent Meeting Room` 是一個單機優先、輕量化的多 agent 會議室。這一版不再走重 PM 流程，而是專注在一個穩定的會議介面，讓多個 AI 角色能圍繞同一個主題持續討論、保留暫存記憶，並在會後匯出成文字或 Python 檔案，再進一步存入長期記憶。

目前產品方向以 [agent.md](C:\codex\agent-meeting-room\agent.md:1) 為準，`OpenClaw` 被視為未來整合對象，而不是在此專案內重做它的 Gateway 或 Skills 系統。

## MVP 目標

- 一個介面，多個 agent 開會
- 單機優先，可直接用 SQLite 啟動
- 設定頁可填 API、模型、角色與系統提示詞
- 會議中使用暫存記憶，不做複雜工作流
- 會後可匯出 `text` 與 `python` 格式並寫入本地檔案
- 預留 OpenClaw 角色來源與整合欄位，但不重做 OpenClaw 本體

## 技術組成

- 前端：HTML、CSS、原生 JavaScript
- 後端：Python、FastAPI
- ORM：SQLAlchemy
- 預設資料庫：SQLite
- 可切換資料庫：PostgreSQL
- 模型呼叫：OpenAI compatible API 或 mock 模式

## 目前功能

- 建立會議並選擇參與角色
- 內建多種會議角色
- 可新增自訂角色與自訂提示詞
- 逐輪輸入討論內容，產生多 agent 回覆
- 顯示暫存記憶、最新摘要與長期記憶列表
- 匯出會議為純文字或 Python 檔案
- 匯出後自動建立記憶存檔紀錄

## 專案結構

```text
app/
  main.py
  config.py
  database.py
  meeting_engine.py
  models.py
  reports.py
  schemas.py
  static/
    app.js
    style.css
  templates/
    index.html
tests/
agent.md
README.md
REPORT.md
requirements.txt
railway.json
```

## 本地啟動

### 1. 建立虛擬環境

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. 安裝依賴

```powershell
pip install -r requirements.txt
```

### 3. 啟動服務

如果沒有設定 `DATABASE_URL`，系統會自動使用本地 SQLite。

```powershell
uvicorn app.main:create_app --factory --reload
```

啟動後開啟：

- [http://127.0.0.1:8000](http://127.0.0.1:8000)

## PostgreSQL 設定

如果你要改用 PostgreSQL，可以先設定環境變數：

```powershell
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/agent_meeting_room"
```

之後再啟動 FastAPI 即可。

## API / 模型設定

進入介面後的「設定」可以填入：

- `API Mode`
- `API Key`
- `Base URL`
- `Model Name`
- `Temperature`
- `Max Tokens`
- `OpenClaw Gateway URL`
- `OpenClaw Notes`

其中：

- `mock` 模式不需要 API Key，方便本地驗證流程
- `openai_compatible` 模式可接 OpenAI 相容端點

## 測試

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

目前測試覆蓋：

- 首頁可正常載入
- Bootstrap 可回傳設定、角色、會議與記憶
- 建立會議後可執行一輪討論
- 匯出 Python 檔案後可寫入記憶存檔

## 主要 API

- `GET /api/health`
- `GET /api/bootstrap`
- `GET /api/settings`
- `PUT /api/settings`
- `GET /api/roles`
- `POST /api/roles`
- `PUT /api/roles/{role_id}`
- `GET /api/meetings`
- `POST /api/meetings`
- `GET /api/meetings/{meeting_id}`
- `POST /api/meetings/{meeting_id}/rounds`
- `POST /api/meetings/{meeting_id}/close`
- `POST /api/meetings/{meeting_id}/export`
- `GET /api/memories`

## 後續方向

- 強化前端閱讀性與會議臨場感
- 將 OpenClaw 角色載入流程接到既有 Gateway
- 支援更完整的本地長期記憶策略
- 補上角色技能包與角色匯入機制
