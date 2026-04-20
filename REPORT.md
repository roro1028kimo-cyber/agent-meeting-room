# REPORT｜Agent Meeting Room 重構狀態報告

> 這份報告說明目前程式已經完成到哪裡、哪些地方已對齊新版 `agent.md`，以及下一步還有哪些收斂空間。

---

## 一、重構目標

| 項目 | 說明 |
|------|------|
| **重構方向** | 從舊版流程型介面，改為輕量化多 agent 會議室 |
| **核心原則** | 單機優先、穩定優先、一畫面完成、暫存記憶先行 |
| **規格依據** | [agent.md](C:\codex\agent-meeting-room\agent.md:1) |
| **與 OpenClaw 關係** | 整合對象，不重做 Gateway / Skills |

---

## 二、這次已完成的對齊項目

### 1. 會議輸入模式已對齊

原本前端只是把兩個輸入欄位拼成一個字串送出，現在已改為真正分流：

- `formal_input`
- `note_input`

對應意義如下：

| 欄位 | 說明 |
|------|------|
| `formal_input` | 正式會議輸入 |
| `note_input` | 使用者插話 / 補充 |

這讓前端與後端都真正符合新版規格，而不是只有 UI 上看起來分開。

### 2. 暫存記憶內容已對齊

暫存記憶目前已明確保存：

- `latest_formal_input`
- `latest_note_input`
- `latest_summary`
- `active_speaker`
- `notes`

這比原本單一 `latest_user_input` 更符合會議室產品邏輯。

### 3. 多供應商設定已落地

目前設定頁已可分開保存以下供應商設定：

- `OpenAI`
- `Anthropic / Claude`
- `Gemini`

同時角色層也已可設定：

- `provider`
- `model_override`
- `response_mode`
- `max_output_tokens`

這代表同一場會議中的不同角色，已能綁不同供應商與模型。

### 4. 短輸出 / 完整整理機制已對齊

目前已明確區分兩種輸出模式：

- `concise`
- `full_summary`

一般角色以短輸出為主，只保留：

- `重點`
- `邏輯`
- `結論`

主持人、執行官、記錄員則可在需要時輸出完整整理。

### 5. 主畫面已改為終端機式會議流

主畫面目前已收斂到以下結構：

- 上方：會議標題與狀態
- 中央：終端機式討論流與 live transcript
- 右側：與會 agent、暫存記憶、長期記憶
- 下方：正式會議輸入與使用者插話

另外已把訊息預設改為較短的單列預覽，避免第一輪就把整頁塞滿。

### 6. Markdown 文件已同步

目前已同步更新：

- [agent.md](C:\codex\agent-meeting-room\agent.md:1)
- [README.md](C:\codex\agent-meeting-room\README.md:1)
- [REPORT.md](C:\codex\agent-meeting-room\REPORT.md:1)
- [AGENT_MD_STANDARD.md](C:\codex\agent-meeting-room\.codex\standards\AGENT_MD_STANDARD.md:1)

---

## 三、目前程式結構狀態

### 後端

已收斂成以下主軸：

- 設定管理
- 角色管理
- 會議建立
- 回合執行
- 會議結束
- 匯出與記憶存檔

### 前端

已收斂成以下主軸：

- 單頁會議室
- 主討論區
- 右側角色與記憶側欄
- 下方雙輸入區
- 設定抽屜
- 建立會議視窗

---

## 四、仍可繼續優化的地方

### 視覺層

- live transcript 還可再更像真正終端機
- 訊息可再加入「只看本輪 / 展開全文」的切換感
- 右側席位狀態還能更有會議臨場感

### 互動層

- 可加入最近會議切換
- 可加入一鍵複製匯出內容
- 可加入完整整理的 provider 指定選項

### 整合層

- 尚未真正串接 OpenClaw Gateway
- 尚未真正載入 OpenClaw 角色清單
- 尚未建立角色模板匯入機制

---

## 五、目前驗證方式

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

應驗證以下內容：

1. 首頁可正常載入
2. bootstrap 可正常回傳設定與角色
3. 會議可建立並執行一輪
4. 暫存記憶會保存正式輸入、插話與摘要
5. 匯出可建立長期記憶存檔

---

## 六、目前判斷

目前這版已經從「可跑的原型」進一步收斂成「單機優先、終端機式、多供應商、多角色可分配模型」的第一版會議室。

如果用目前標準來看：

- 產品邏輯：已大致對齊
- API 結構：已大致對齊
- 文件規格：已同步
- UI 可讀性：已明顯改善
- OpenClaw 整合：仍停在預留層

---

## 七、建議下一步

下一輪最值得繼續做的三件事：

1. 繼續壓低第一輪資訊密度，讓多角色仍可快速掃描
2. 補上最近會議切換與完整整理切換體驗
3. 設計 OpenClaw 角色接入的第一版橋接流程
