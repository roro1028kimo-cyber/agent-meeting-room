# agent.md｜Agent Meeting Room 產品規格書

> 這不是重型專案管理系統，也不是 OpenClaw 的替代品。
> 這是一個單機優先、穩定可運行、讓多個 AI agent 在同一個會議室內協作討論的輕量化會議產品。

---

## 一、角色定義

| 欄位 | 內容 |
|------|------|
| **產品名稱** | Agent Meeting Room |
| **產品類型** | 輕量化多 agent 會議室 |
| **核心定位** | 單機優先、穩定運行、低心智負擔的 AI 協作會議介面 |
| **一句話描述** | 用最少功能，讓多個 AI 角色能在一個畫面中穩定開會、保留暫存記憶，並在會後匯出成果 |
| **主要使用情境** | 提案討論、方案比較、風險檢視、角色分工、想法收斂 |
| **部署策略** | 本地單機優先，可再延伸到雲端部署 |
| **與 OpenClaw 關係** | 整合對象，不重做其 Gateway、Skills、Agent 管理體系 |
| **文件版本** | v2.1 |
| **最後更新** | 2026-04-20 |

---

## 二、產品原則

### 設計原則

1. **單機優先**
   預設應能直接在本機啟動，不依賴雲端服務才可使用。

2. **會議優先**
   核心是「多 agent 開會」，不是任務看板、流程編排器或重 PM 平台。

3. **穩定優先**
   優先保證建立會議、發言、摘要、匯出這條主流程穩定，次要功能一律延後。

4. **一畫面完成**
   使用者應在一個主介面內完成大部分會議操作，不需要跳多個子頁面。

5. **暫存記憶先行**
   開會中先用暫存記憶維持上下文，會後再匯出、存檔、進入長期記憶。

6. **OpenClaw 不重做**
   若要接 OpenClaw，只處理角色接入、模型接入與顯示層整合，不重複建 Gateway / Skills。

7. **制式文件可複製**
   這份 `agent.md` 不只是本專案規格，也要能當作其他專案撰寫規格的標準樣板。

### 這一版刻意不做

- 重型 PM 流程
- 任務卡片流轉
- blocker / risk / milestone 專屬系統
- 複雜權限控管
- 工作流編排引擎
- OpenClaw Gateway 重做
- OpenClaw Skills 系統重做
- 跨團隊 SaaS 化需求

---

## 三、產品問題定義

目前常見的 AI 協作工具大多落在以下兩種極端：

- 太偏聊天介面，沒有角色協作結構
- 太偏流程平台，導致操作負擔過重

使用者真正需要的是：

- 一個畫面
- 可以放多個 agent
- 可以看出誰正在發話
- 可以持續收斂討論
- 會後可以把內容帶走

因此，Agent Meeting Room 的任務不是做最完整的平台，而是做最穩的會議室。

---

## 四、與 OpenClaw 的關係

### 明確定位

OpenClaw 是整合對象，不是重做對象。

本專案**會使用**或**預留接入**的 OpenClaw 能力：

- OpenClaw agent 資訊
- OpenClaw 模型接入能力
- OpenClaw 角色來源
- 未來可能的 Gateway URL / Agent ID 映射

本專案**不重做**的內容：

- OpenClaw Gateway
- OpenClaw Skills 系統
- OpenClaw 內部 agent lifecycle
- OpenClaw 的完整設定中心

### 整合原則

1. Agent Meeting Room 專注在會議體驗與會議資料結構。
2. OpenClaw 專注在 agent 能力、外部工具、技能體系。
3. 兩者之間以「角色接入」與「模型接入」為主要接點。

### MVP 階段的整合深度

MVP 只做到：

- 可標記角色來源為 `builtin` / `custom` / `openclaw`
- 可在設定中保留 OpenClaw Gateway URL
- 可在角色設定中保留 OpenClaw Agent ID

MVP 不做到：

- 即時同步 OpenClaw 角色列表
- OpenClaw Skills 編輯
- OpenClaw 任務編排

---

## 五、開發環境

| 欄位 | 規格 |
|------|------|
| 作業系統 | Windows 優先，macOS / Linux 可支援 |
| Python | 3.11+ |
| 前端 | HTML + CSS + 原生 JavaScript |
| 後端 | FastAPI |
| 資料庫 | SQLite 預設，PostgreSQL 可切換 |
| 套件管理 | pip |
| 產品模式 | 本地啟動優先 |

### 為什麼不用重型前端框架

這個產品目前不是複雜 SaaS 後台，而是單一會議室介面。

因此 MVP 階段採用：

- HTML
- CSS
- 原生 JavaScript

原因是：

- 啟動快
- 結構單純
- 部署負擔低
- 修改成本低
- 不需要先引入額外建置鏈才能完成主流程

---

## 六、技術選型

### 後端

```text
框架：FastAPI
資料模型：SQLAlchemy
HTTP：REST API
模板：Jinja2
啟動：uvicorn
```

### 前端

```text
結構：單頁式會議室
樣式：客製 CSS
互動：原生 JavaScript
渲染：伺服器模板 + 前端 API 更新
```

### 模型呼叫

```text
模式一：mock
模式二：OpenAI
模式三：Anthropic / Claude
模式四：Gemini
模式五：未來可接 OpenClaw 代理層
```

### 資料庫策略

| 階段 | 資料庫策略 |
|------|------------|
| MVP | SQLite 預設 |
| 進階部署 | PostgreSQL |
| 長期方向 | 匯出檔案 + 記憶檔案 + 可擴充外部記憶層 |

---

## 七、模組結構

```text
agent-meeting-room/
├─ agent.md
├─ README.md
├─ REPORT.md
├─ requirements.txt
├─ railway.json
├─ app/
│  ├─ main.py
│  ├─ config.py
│  ├─ database.py
│  ├─ models.py
│  ├─ schemas.py
│  ├─ meeting_engine.py
│  ├─ reports.py
│  ├─ templates/
│  │  └─ index.html
│  └─ static/
│     ├─ style.css
│     └─ app.js
├─ tests/
│  └─ test_app.py
└─ .codex/
   └─ standards/
      └─ AGENT_MD_STANDARD.md
```

---

## 八、核心資料結構

### 資料實體

| 實體 | 用途 |
|------|------|
| `AppSetting` | 儲存系統設定、API 與模型設定 |
| `RoleProfile` | 儲存角色定義、顏色、提示詞、來源 |
| `Meeting` | 儲存單場會議主體 |
| `MeetingParticipant` | 儲存會議參與角色 |
| `MeetingMessage` | 儲存每輪對話與摘要 |
| `MemoryArchive` | 儲存會後歸檔結果 |

### 角色來源

| 類型 | 說明 |
|------|------|
| `builtin` | 系統內建角色 |
| `custom` | 使用者自訂角色 |
| `openclaw` | 預留 OpenClaw 來源角色 |

### 訊息類型

| 類型 | 說明 |
|------|------|
| `system` | 系統初始化訊息 |
| `user` | 使用者正式輸入 |
| `agent` | agent 回覆 |
| `summary` | 主持人或系統摘要 |

### 會議狀態

| 狀態 | 說明 |
|------|------|
| `active` | 會議進行中 |
| `closed` | 會議已結束 |

---

## 九、會議流程規格

### 標準流程

1. 使用者建立會議
2. 使用者輸入主題、目標、背景
3. 使用者勾選參與角色
4. 系統建立會議與初始訊息
5. 使用者送出本輪正式討論內容
6. 多個 agent 依序發言
7. 系統產生本輪摘要並更新暫存記憶
8. 使用者可繼續下一輪
9. 使用者關閉會議
10. 使用者匯出文字或 Python 檔案
11. 匯出結果進入長期記憶存檔

### MVP 不做的流程

- intake / confirming / reframing 多階段工作流
- blocker 流程
- 任務分派面板
- 審核簽核流程

---

## 十、UI 版面規格

### 主介面原則

主介面應聚焦於「正在發生的會議」，而不是表單系統。

### 版面分區

| 區塊 | 功能 |
|------|------|
| 上方工具列 | 產品標題、建立會議、設定 |
| 中央主視覺區 | 會議討論內容、逐輪發言、摘要 |
| 右側側欄 | agent 狀態、暫存記憶、長期記憶 |
| 下方輸入區 | 正式會議輸入、使用者插話或補充 |

### UI 重點

1. **主視覺是討論內容**
   中央區域必須是視覺重心。

2. **右側是發話人狀態**
   應能明確看出哪些 agent 在會議中、誰是目前活躍角色。

3. **下方輸入應分清正式輸入與補充輸入**
   不同輸入類型要有清楚區別。

4. **可閱讀性優先**
   不可以再回到像傳統表單頁那樣密密麻麻難閱讀。

5. **預設只顯示短輸出**
   一般角色應以終端機式短句回覆，不預設鋪滿長段全文。

### 未來視覺方向

- 中央討論區有打字感或流動感
- 右側 agent 有綠燈或活躍狀態提示
- 整體更像「會議室」而不是「資料輸入頁」

---

## 十一、設定功能規格

### API 設定

| 欄位 | 說明 |
|------|------|
| `api_mode` | `mock` 或 `live` |
| `openai_api_key` | OpenAI API Key |
| `openai_base_url` | OpenAI Base URL |
| `openai_model` | OpenAI 預設模型 |
| `anthropic_api_key` | Anthropic API Key |
| `anthropic_base_url` | Anthropic Base URL |
| `anthropic_model` | Claude 預設模型 |
| `gemini_api_key` | Gemini API Key |
| `gemini_base_url` | Gemini Base URL |
| `gemini_model` | Gemini 預設模型 |
| `temperature` | 生成溫度 |
| `short_reply_max_tokens` | 一般角色短輸出上限 |
| `full_summary_max_tokens` | 完整整理上限 |

### OpenClaw 設定

| 欄位 | 說明 |
|------|------|
| `openclaw_enabled` | 是否啟用 OpenClaw 整合 |
| `openclaw_gateway_url` | OpenClaw Gateway URL |
| `openclaw_notes` | 備註與整合說明 |

### 設定原則

1. 設定要集中，不要散在多個頁面。
2. 使用者應能在一個設定抽屜內完成大部分模型配置。
3. 沒填 API Key 時，`mock` 模式也要能穩定跑流程。

---

## 十二、角色系統規格

### 內建角色

| 角色 | 主要責任 |
|------|----------|
| 主持人 | 維持節奏、收斂討論、整理結論 |
| 規劃者 | 提出方案與步驟 |
| 質疑者 | 找出不合理處與漏洞 |
| 風險官 | 提醒風險與代價 |
| 執行者 | 將討論轉為可執行項目 |
| 記錄員 | 整理重點、摘要與脈絡 |

### 擴充角色

| 角色 | 主要責任 |
|------|----------|
| 研究員 | 補充資訊與調查方向 |
| 產品顧問 | 從使用者與產品價值角度評估 |
| 技術顧問 | 從架構與實作角度評估 |
| 商業顧問 | 從商業模式與市場角度評估 |
| 法務顧問 | 從合規與風險責任角度提醒 |
| 體驗設計顧問 | 從使用體驗與互動角度評估 |

### 每個角色至少要有

- 顯示名稱
- 顏色
- 角色說明
- 系統提示詞
- 來源類型
- 是否啟用
- provider
- model override
- response mode
- max output tokens

### 回應模式

| 模式 | 說明 |
|------|------|
| `concise` | 一般角色使用，只輸出重點、邏輯、結論 |
| `full_summary` | 主持人或整理角色使用，可輸出完整會議整理 |

### 角色來源規則

| 來源 | 說明 |
|------|------|
| `builtin` | 由系統內建維護 |
| `custom` | 使用者自行建立 |
| `openclaw` | 對接外部角色來源 |

---

## 十三、暫存記憶與長期記憶

### 暫存記憶

暫存記憶只服務當前會議，不保證跨會議自動復用。

暫存記憶至少包含：

- 會議標題
- 會議目標
- 背景文字
- 最新正式輸入
- 最新使用者插話
- 最新摘要
- 目前活躍發話人
- 本輪關鍵筆記

### 長期記憶

長期記憶不在會議中即時建構，而是在會後透過匯出進入。

長期記憶流程：

1. 結束會議
2. 匯出內容
3. 寫入檔案
4. 建立 `MemoryArchive`
5. 後續才有機會接更完整的記憶系統

### 這樣做的原因

- 降低 MVP 複雜度
- 避免會議中同時處理太多狀態
- 保持流程穩定

---

## 十四、匯出規格

### 支援格式

| 格式 | 用途 |
|------|------|
| `text` | 人類可閱讀版本 |
| `python` | 可被程式後續讀取與再處理 |

### 文字匯出必須包含

- 會議標題
- 會議目標
- 會議狀態
- 會議輪數
- 全部訊息紀錄

### Python 匯出必須包含

- 結構化資料
- 會議 metadata
- 暫存記憶
- 全部 messages

### 匯出後行為

1. 寫入 `exports/`
2. 建立 `MemoryArchive`
3. 可在右側長期記憶區顯示

---

## 十五、API 合約

### 核心 API

| 方法 | 路徑 | 用途 |
|------|------|------|
| `GET` | `/api/health` | 健康檢查 |
| `GET` | `/api/bootstrap` | 初始化前端資料 |
| `GET` | `/api/settings` | 讀取設定 |
| `PUT` | `/api/settings` | 更新設定 |
| `GET` | `/api/roles` | 讀取角色 |
| `POST` | `/api/roles` | 建立角色 |
| `PUT` | `/api/roles/{role_id}` | 更新角色 |
| `GET` | `/api/meetings` | 讀取最近會議 |
| `POST` | `/api/meetings` | 建立會議 |
| `GET` | `/api/meetings/{meeting_id}` | 讀取會議 |
| `POST` | `/api/meetings/{meeting_id}/rounds` | 執行一輪會議 |
| `POST` | `/api/meetings/{meeting_id}/full-summary` | 產生完整整理 |
| `POST` | `/api/meetings/{meeting_id}/close` | 關閉會議 |
| `POST` | `/api/meetings/{meeting_id}/export` | 匯出會議 |
| `GET` | `/api/memories` | 讀取長期記憶存檔 |

### API 設計原則

1. 命名清楚，不做過度抽象。
2. 每個 API 對應一個明確使用者操作。
3. 先讓前端可穩定呼叫，再談進一步拆分。

---

## 十六、MVP 驗收清單

### 功能驗收

1. [ ] 可開啟首頁並正常渲染主介面
2. [ ] 可建立一場新會議
3. [ ] 可選擇多個角色參與會議
4. [ ] 可送出一輪正式會議內容
5. [ ] 多個 agent 可產生回應
6. [ ] 系統可產生本輪摘要
7. [ ] 暫存記憶會更新
8. [ ] 會議可關閉
9. [ ] 可匯出 `text`
10. [ ] 可匯出 `python`
11. [ ] 匯出後可建立長期記憶存檔
12. [ ] `mock` 模式下可完整跑通流程
13. [ ] 可配置 OpenAI / Anthropic / Gemini
14. [ ] 一般角色預設為短輸出模式
15. [ ] 可手動觸發完整整理

### 工程驗收

1. [ ] 測試可通過
2. [ ] SQLite 模式可直接啟動
3. [ ] PostgreSQL 模式可切換
4. [ ] API 回應結構一致
5. [ ] 主要流程沒有依賴手動修補資料

---

## 十七、Sprint 規劃

| Sprint | 目標 | 交付內容 |
|--------|------|----------|
| S1 | 重寫產品規格 | 明確定位、邊界、模組與資料結構 |
| S2 | 建立核心資料模型 | 會議、角色、訊息、記憶歸檔 |
| S3 | 建立核心 API | 設定、角色、會議、匯出 |
| S4 | 建立單頁會議室 UI | 主會議區、側欄、輸入區 |
| S5 | 完成暫存記憶與匯出 | 摘要、文字匯出、Python 匯出 |
| S6 | 前端可讀性優化 | 更像會議室的視覺與互動 |
| S7 | OpenClaw 整合預留 | 角色來源與 Gateway 欄位接軌 |

---

## 十八、未來階段

### Phase 2

- 更完整的角色編輯體驗
- 角色提示詞模板庫
- 更好的發話人視覺效果
- 插話與正式輸入的節奏控制

### Phase 3

- OpenClaw 角色匯入
- 更完整的長期記憶策略
- 可插拔模型供應商
- 匯出後自動整理成記憶索引

---

## 十九、行銷與一句話描述

> **一個畫面，讓多個 AI agent 穩定開會。**

### 與其他產品的差異

| 類型 | 常見問題 | Agent Meeting Room 的選擇 |
|------|----------|----------------------------|
| 純聊天工具 | 角色不穩定、缺少會議結構 | 強調角色會議與摘要 |
| 重型 PM 平台 | 操作太重、流程太多 | 只保留會議主流程 |
| AI 編排框架 | 偏開發者、不偏使用介面 | 優先讓使用者看到會議進行 |
| OpenClaw 本體 | 功能廣、整合深 | 這裡只做輕量會議室 |

---

## 二十、總結

這份 `agent.md` 的任務，不只是描述 Agent Meeting Room。
它同時定義了本專案的工作邏輯：

- 規格先行
- 邊界清楚
- MVP 收斂
- 技術選型有理由
- 模組與資料結構可直接開工
- 文件本身就是團隊對齊工具

這個專案後續若再擴充，也必須遵守這份規格的核心原則，而不是回到功能堆疊式開發。
