# README｜Agent Meeting Room 使用說明

> Agent Meeting Room 是一個單機優先、輕量化的多 agent 會議室。
> 它不是重型 PM 平台，而是一個讓多個 AI 角色能穩定討論、收斂、匯出的會議介面。

---

## 一、產品定位

| 欄位 | 內容 |
|------|------|
| **產品名稱** | Agent Meeting Room |
| **核心定位** | 一個畫面、多個 agent、單機優先的會議室 |
| **主要目的** | 讓使用者在同一個介面裡與多個 AI 角色持續開會 |
| **MVP 範圍** | 角色會議、暫存記憶、會後匯出、長期記憶存檔 |
| **不做的事** | 重 PM 流程、任務編排引擎、OpenClaw Gateway 重做 |
| **規格基準** | [agent.md](C:\codex\agent-meeting-room\agent.md:1) |

---

## 二、目前已完成能力

### 核心能力

1. 建立新會議
2. 選擇多個與會角色
3. 分開輸入「正式會議內容」與「使用者插話 / 補充」
4. 讓多個 agent 逐輪發言
5. 一般角色以短輸出模式回覆
6. 主持人 / 執行官 / 記錄員可執行完整整理
7. 保留暫存記憶
8. 匯出 `text`
9. 匯出 `python`
10. 匯出後建立長期記憶存檔
11. 終端機式單頁會議室 UI

### 角色能力

- 內建角色
- 自訂角色
- OpenClaw 預留角色來源
- 可編輯角色提示詞、顏色、定位與啟用狀態
- 每個角色可綁定 `provider`
- 每個角色可覆寫 `model`
- 每個角色可設定 `response_mode`
- 每個角色可設定輸出 token 上限

### 模型能力

- `mock`
- `openai`
- `anthropic`
- `gemini`

---

## 三、技術組成

| 層級 | 技術 |
|------|------|
| 前端 | HTML + CSS + 原生 JavaScript |
| 後端 | FastAPI |
| ORM | SQLAlchemy |
| 模板 | Jinja2 |
| 預設資料庫 | SQLite |
| 可切換資料庫 | PostgreSQL |
| 匯出格式 | `text` / `python` |

---

## 四、專案結構

```text
app/
  main.py
  config.py
  database.py
  models.py
  schemas.py
  meeting_engine.py
  reports.py
  templates/
    index.html
  static/
    style.css
    app.js
tests/
agent.md
README.md
REPORT.md
.codex/
  standards/
    AGENT_MD_STANDARD.md
```

---

## 五、本地啟動方式

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

啟動後打開：

- [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 六、資料庫策略

### 預設模式

MVP 預設使用 SQLite。

原因：

- 本地啟動成本低
- 不需要先配置外部服務
- 方便快速測試會議流程

### PostgreSQL 切換方式

```powershell
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/agent_meeting_room"
```

之後再啟動 FastAPI 即可。

---

## 七、設定頁可配置內容

| 欄位 | 說明 |
|------|------|
| `API Mode` | `mock` 或 `live` |
| `OpenAI API Key / Base URL / Model` | OpenAI 供應商設定 |
| `Anthropic API Key / Base URL / Model` | Claude 供應商設定 |
| `Gemini API Key / Base URL / Model` | Gemini 供應商設定 |
| `Temperature` | 回應發散程度 |
| `Short Reply Max Tokens` | 一般角色短輸出上限 |
| `Full Summary Max Tokens` | 完整整理上限 |
| `OpenClaw Gateway URL` | 預留 OpenClaw 接入位址 |
| `OpenClaw Notes` | 預留整合備註 |

角色編輯區可另外配置：

- `provider`
- `model_override`
- `response_mode`
- `max_output_tokens`
- `openclaw_agent_id`

---

## 八、主要 API

| 方法 | 路徑 | 用途 |
|------|------|------|
| `GET` | `/api/health` | 健康檢查 |
| `GET` | `/api/bootstrap` | 前端初始化 |
| `GET` | `/api/settings` | 讀取設定 |
| `PUT` | `/api/settings` | 儲存設定 |
| `GET` | `/api/roles` | 讀取角色 |
| `POST` | `/api/roles` | 建立角色 |
| `PUT` | `/api/roles/{role_id}` | 更新角色 |
| `GET` | `/api/meetings` | 讀取最近會議 |
| `POST` | `/api/meetings` | 建立會議 |
| `GET` | `/api/meetings/{meeting_id}` | 讀取單場會議 |
| `POST` | `/api/meetings/{meeting_id}/rounds` | 執行一輪討論 |
| `POST` | `/api/meetings/{meeting_id}/full-summary` | 產生完整整理 |
| `POST` | `/api/meetings/{meeting_id}/close` | 關閉會議 |
| `POST` | `/api/meetings/{meeting_id}/export` | 匯出會議 |
| `GET` | `/api/memories` | 讀取長期記憶 |

---

## 九、測試方式

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

目前測試覆蓋：

1. 首頁渲染
2. bootstrap 初始化
3. 建立會議並執行一輪
4. 匯出與記憶存檔

---

## 十、與 OpenClaw 的關係

### 本專案會做

- 預留 OpenClaw 角色來源
- 預留 Gateway URL 欄位
- 預留 Agent ID 映射欄位

### 本專案不做

- 重做 OpenClaw Gateway
- 重做 OpenClaw Skills 系統
- 重做 OpenClaw agent 管理體系

---

## 十一、文件同步規則

本專案所有核心 Markdown 文件都應與 [agent.md](C:\codex\agent-meeting-room\agent.md:1) 保持一致，包括：

- [README.md](C:\codex\agent-meeting-room\README.md:1)
- [REPORT.md](C:\codex\agent-meeting-room\REPORT.md:1)
- [AGENT_MD_STANDARD.md](C:\codex\agent-meeting-room\.codex\standards\AGENT_MD_STANDARD.md:1)

若規格有重大變更，以上文件必須一起更新。
