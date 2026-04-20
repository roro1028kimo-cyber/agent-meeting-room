const state = {
  settings: null,
  roles: [],
  meeting: null,
  memories: [],
};

const els = {
  conversationList: document.getElementById("conversation-list"),
  meetingTitle: document.getElementById("meeting-title"),
  meetingObjective: document.getElementById("meeting-objective"),
  meetingStatus: document.getElementById("meeting-status"),
  meetingRound: document.getElementById("meeting-round"),
  stageTitle: document.getElementById("stage-title"),
  stageSummary: document.getElementById("stage-summary"),
  typingPreview: document.getElementById("typing-preview"),
  agentList: document.getElementById("agent-list"),
  archiveList: document.getElementById("archive-list"),
  memoryPreview: document.getElementById("memory-preview"),
  roundInput: document.getElementById("round-input"),
  noteInput: document.getElementById("note-input"),
  runRoundButton: document.getElementById("run-round-button"),
  fullSummaryButton: document.getElementById("full-summary-button"),
  closeMeetingButton: document.getElementById("close-meeting-button"),
  exportTextButton: document.getElementById("export-text-button"),
  exportPythonButton: document.getElementById("export-python-button"),
  settingsDrawer: document.getElementById("settings-drawer"),
  meetingModal: document.getElementById("meeting-modal"),
  settingsForm: document.getElementById("settings-form"),
  roleEditorList: document.getElementById("role-editor-list"),
  meetingRolePicker: document.getElementById("meeting-role-picker"),
  meetingForm: document.getElementById("meeting-form"),
  roleTemplate: document.getElementById("role-editor-template"),
};

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function clipText(value = "", limit = 48) {
  const compact = String(value).replace(/\s+/g, " ").trim();
  if (compact.length <= limit) return compact;
  return `${compact.slice(0, Math.max(0, limit - 1))}…`;
}

function firstLine(value = "") {
  return String(value).split(/\r?\n/).map((line) => line.trim()).find(Boolean) || "";
}

function toInlineLog(value = "", limit = 84) {
  const compact = String(value)
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.replaceAll("｜", "="))
    .join(" / ");
  return clipText(compact, limit);
}

function getVisibleMessages(messages = []) {
  if (!messages.length) return [];
  const latestRound = Math.max(...messages.map((item) => item.round_number || 0));
  const latestRoundMessages = messages.filter((item) => item.round_number === latestRound);
  const fallback = latestRound > 0 ? latestRoundMessages : messages.slice(-8);
  return fallback.filter((item) => item.message_type !== "system").slice(-10);
}

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    throw new Error(typeof payload === "string" ? payload : JSON.stringify(payload));
  }
  return payload;
}

async function bootstrap() {
  const payload = await request("/api/bootstrap");
  state.settings = payload.settings;
  state.roles = payload.roles;
  state.memories = payload.memories;
  renderSettings();
  renderRoleEditors();
  renderRolePicker();
  renderArchives();
  renderMeeting(null);
  if (payload.meetings.length) {
    const latest = await request(`/api/meetings/${payload.meetings[0].id}`);
    renderMeeting(latest);
  }
}

function renderSettings() {
  document.getElementById("settings-api-mode").value = state.settings.api_mode;
  document.getElementById("settings-temperature").value = state.settings.temperature ?? 0.35;
  document.getElementById("settings-short-tokens").value = state.settings.short_reply_max_tokens ?? 48;
  document.getElementById("settings-full-tokens").value = state.settings.full_summary_max_tokens ?? 360;

  document.getElementById("openai-api-key").value = state.settings.openai_api_key || "";
  document.getElementById("openai-base-url").value = state.settings.openai_base_url || "";
  document.getElementById("openai-model").value = state.settings.openai_model || "";
  document.getElementById("anthropic-api-key").value = state.settings.anthropic_api_key || "";
  document.getElementById("anthropic-base-url").value = state.settings.anthropic_base_url || "";
  document.getElementById("anthropic-model").value = state.settings.anthropic_model || "";
  document.getElementById("gemini-api-key").value = state.settings.gemini_api_key || "";
  document.getElementById("gemini-base-url").value = state.settings.gemini_base_url || "";
  document.getElementById("gemini-model").value = state.settings.gemini_model || "";
  document.getElementById("settings-openclaw-url").value = state.settings.openclaw_gateway_url || "";
  document.getElementById("settings-openclaw-notes").value = state.settings.openclaw_notes || "";
}

function renderRoleEditors() {
  els.roleEditorList.innerHTML = "";
  state.roles.forEach((role) => {
    const fragment = els.roleTemplate.content.cloneNode(true);
    fragment.querySelector("[data-role-name]").textContent = role.display_name;
    fragment.querySelector("[data-role-type]").textContent = `${role.source} / ${role.provider}`;
    fragment.querySelector("[data-role-enabled]").checked = role.enabled;
    fragment.querySelector('[data-role-field="display_name"]').value = role.display_name;
    fragment.querySelector('[data-role-field="description"]').value = role.description;
    fragment.querySelector('[data-role-field="system_prompt"]').value = role.system_prompt;
    fragment.querySelector('[data-role-field="provider"]').value = role.provider;
    fragment.querySelector('[data-role-field="model_override"]').value = role.model_override || "";
    fragment.querySelector('[data-role-field="response_mode"]').value = role.response_mode;
    fragment.querySelector('[data-role-field="max_output_tokens"]').value = role.max_output_tokens ?? 48;
    fragment.querySelector('[data-role-field="color"]').value = role.color;
    fragment.querySelector('[data-role-field="openclaw_agent_id"]').value = role.openclaw_agent_id || "";

    fragment.querySelector("[data-role-save]").addEventListener("click", async (event) => {
      event.preventDefault();
      const card = event.target.closest(".role-editor-card");
      const payload = {
        display_name: card.querySelector('[data-role-field="display_name"]').value,
        description: card.querySelector('[data-role-field="description"]').value,
        system_prompt: card.querySelector('[data-role-field="system_prompt"]').value,
        provider: card.querySelector('[data-role-field="provider"]').value,
        model_override: card.querySelector('[data-role-field="model_override"]').value || null,
        response_mode: card.querySelector('[data-role-field="response_mode"]').value,
        max_output_tokens: Number(card.querySelector('[data-role-field="max_output_tokens"]').value || 48),
        color: card.querySelector('[data-role-field="color"]').value,
        openclaw_agent_id: card.querySelector('[data-role-field="openclaw_agent_id"]').value || null,
        enabled: card.querySelector("[data-role-enabled]").checked,
      };
      const updated = await request(`/api/roles/${role.id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      state.roles = state.roles.map((item) => (item.id === updated.id ? updated : item));
      renderRoleEditors();
      renderRolePicker();
      if (state.meeting) {
        renderMeeting(await request(`/api/meetings/${state.meeting.id}`));
      }
    });

    els.roleEditorList.appendChild(fragment);
  });
}

function renderRolePicker() {
  els.meetingRolePicker.innerHTML = state.roles
    .filter((role) => role.enabled)
    .map(
      (role, index) => `
        <label class="role-pick-card">
          <input type="checkbox" name="selected_role_ids" value="${role.id}" ${index < 4 ? "checked" : ""} />
          <div>
            <strong>${escapeHtml(role.display_name)}</strong>
            <div class="muted">${escapeHtml(role.description)}</div>
            <div class="muted">${escapeHtml(role.provider)} / ${escapeHtml(role.response_mode)}</div>
          </div>
        </label>
      `
    )
    .join("");
}

function renderMeeting(meeting) {
  state.meeting = meeting;
  if (!meeting) {
    els.meetingTitle.textContent = "尚未建立會議";
    els.meetingObjective.textContent = "先建立會議，再送出第一輪正式輸入。";
    els.meetingStatus.textContent = "待命";
    els.meetingRound.textContent = "Round 0";
    els.stageTitle.textContent = "等待會議開始";
    els.stageSummary.textContent = "訊息會以終端機式對話流呈現。";
    renderTypingPreview([]);
    els.conversationList.className = "conversation-list empty";
    els.conversationList.textContent = "建立會議後，這裡會顯示角色的終端機式討論紀錄。";
    els.agentList.className = "agent-list empty";
    els.agentList.textContent = "尚未建立會議。";
    els.memoryPreview.className = "memory-preview empty";
    els.memoryPreview.textContent = "尚無暫存記憶。";
    toggleMeetingControls(false);
    return;
  }

  els.meetingTitle.textContent = meeting.title;
  els.meetingObjective.textContent = meeting.objective || "未設定會議目標。";
  els.meetingStatus.textContent = meeting.status;
  els.meetingRound.textContent = `Round ${meeting.round_count}`;
  els.stageTitle.textContent = meeting.title;
  els.stageSummary.textContent = firstLine(meeting.temporary_memory?.latest_summary) || "每位角色都應只講重點、邏輯與結論。";
  toggleMeetingControls(meeting.status !== "closed");
  els.exportTextButton.disabled = false;
  els.exportPythonButton.disabled = false;
  renderMessages(meeting.messages || []);
  renderParticipants(meeting.participants || [], meeting.active_speaker);
  renderTemporaryMemory(meeting.temporary_memory || {});
  renderArchives(meeting.archives || state.memories);
  renderTypingPreview(meeting.messages || []);
}

function toggleMeetingControls(enabled) {
  els.runRoundButton.disabled = !enabled;
  els.fullSummaryButton.disabled = !enabled;
  els.closeMeetingButton.disabled = !enabled;
  els.exportTextButton.disabled = !enabled;
  els.exportPythonButton.disabled = !enabled;
}

function renderMessages(messages) {
  const visibleMessages = getVisibleMessages(messages);

  if (!visibleMessages.length) {
    els.conversationList.className = "conversation-list empty";
    els.conversationList.textContent = "這場會議還沒有任何內容。";
    return;
  }

  const latestAgent = [...visibleMessages].reverse().find(
    (item) => item.message_type === "agent" || (item.meta_payload || {}).kind === "full_summary"
  );
  els.conversationList.className = "conversation-list";
  els.conversationList.innerHTML = visibleMessages
    .map((message) => {
      const active = latestAgent && latestAgent.id === message.id;
      const toneClass =
        message.message_type === "summary"
          ? "summary-message"
          : message.message_type === "user"
            ? "user-message"
            : "";
      const provider = message.meta_payload?.provider || message.meta_payload?.source || message.message_type;
      const preview = toInlineLog(message.content, message.message_type === "summary" ? 110 : 72);
      const shouldExpand = message.content.includes("\n") || message.content.length > preview.length + 3;
      return `
        <article class="message-card ${active ? "active" : ""} ${toneClass}">
          <div class="message-meta">
            <div class="speaker">
              <span class="light ${active ? "on" : ""}"></span>
              <strong>[R${message.round_number}] ${escapeHtml(message.role_name)}</strong>
            </div>
            <span>${escapeHtml(provider)} / ${escapeHtml(message.message_type)}</span>
          </div>
          <div class="message-inline">${escapeHtml(preview)}</div>
          ${
            shouldExpand
              ? `<details class="message-expand"><summary>展開全文</summary><pre class="message-detail">${escapeHtml(message.content)}</pre></details>`
              : ""
          }
        </article>
      `;
    })
    .join("");
}

function renderTypingPreview(messages) {
  const recent = [...messages]
    .filter((item) => item.message_type === "agent" || item.message_type === "summary")
    .slice(-3);
  if (!recent.length) {
    els.typingPreview.innerHTML = `<span class="typing-line">&gt; 等待第一輪輸入...</span>`;
    return;
  }
  els.typingPreview.innerHTML = recent
    .map((item) => `<span class="typing-line">&gt; [${escapeHtml(item.role_name)}] ${escapeHtml(toInlineLog(item.content, 96))}</span>`)
    .join("");
}

function renderParticipants(participants, activeSpeaker) {
  if (!participants.length) {
    els.agentList.className = "agent-list empty";
    els.agentList.textContent = "尚未建立會議。";
    return;
  }
  els.agentList.className = "agent-list";
  els.agentList.innerHTML = participants
    .map((participant) => {
      const isActive = activeSpeaker === participant.role.display_name;
      return `
        <article class="agent-card ${isActive ? "active-speaker" : ""}">
          <div class="agent-row">
            <div class="agent-chip">
              <span class="light on" style="background:${escapeHtml(participant.role.color)}; box-shadow: 0 0 10px ${escapeHtml(participant.role.color)}"></span>
              <strong>${escapeHtml(participant.role.display_name)}</strong>
            </div>
            <span>${isActive ? "發言中" : "待命"}</span>
          </div>
          <div class="agent-role">${escapeHtml(participant.role.description)}</div>
          <div class="agent-source">${escapeHtml(participant.role.provider)} / ${escapeHtml(participant.role.response_mode)}</div>
        </article>
      `;
    })
    .join("");
}

function renderTemporaryMemory(memory) {
  if (!memory.latest_formal_input && !memory.latest_note_input && !memory.latest_summary) {
    els.memoryPreview.className = "memory-preview empty";
    els.memoryPreview.textContent = "尚無暫存記憶。";
    return;
  }
  const lines = [
    memory.latest_formal_input ? `正式輸入｜${clipText(memory.latest_formal_input, 32)}` : null,
    memory.latest_note_input ? `插話｜${clipText(memory.latest_note_input, 28)}` : null,
    memory.latest_summary ? `摘要｜${clipText(firstLine(memory.latest_summary), 36)}` : null,
  ].filter(Boolean);

  els.memoryPreview.className = "memory-preview";
  els.memoryPreview.innerHTML = lines
    .map((line) => `<article class="memory-card"><div class="message-body">${escapeHtml(line)}</div></article>`)
    .join("");
}

function renderArchives(source = state.memories) {
  const archives = Array.isArray(source) ? source : [];
  state.memories = archives;
  if (!archives.length) {
    els.archiveList.className = "archive-list empty";
    els.archiveList.textContent = "尚未存入長期記憶。";
    return;
  }
  els.archiveList.className = "archive-list";
  els.archiveList.innerHTML = archives
    .map(
      (item) => `
        <article class="archive-card">
          <strong>${escapeHtml(item.export_format.toUpperCase())}</strong>
          <div class="muted">${escapeHtml(item.summary || "無摘要")}</div>
          <div class="muted">${escapeHtml(item.file_path || "")}</div>
        </article>
      `
    )
    .join("");
}

async function saveSettings(event) {
  event.preventDefault();
  const payload = {
    api_mode: document.getElementById("settings-api-mode").value,
    temperature: Number(document.getElementById("settings-temperature").value || 0.35),
    short_reply_max_tokens: Number(document.getElementById("settings-short-tokens").value || 48),
    full_summary_max_tokens: Number(document.getElementById("settings-full-tokens").value || 360),
    openai_api_key: document.getElementById("openai-api-key").value,
    openai_base_url: document.getElementById("openai-base-url").value,
    openai_model: document.getElementById("openai-model").value,
    anthropic_api_key: document.getElementById("anthropic-api-key").value,
    anthropic_base_url: document.getElementById("anthropic-base-url").value,
    anthropic_model: document.getElementById("anthropic-model").value,
    gemini_api_key: document.getElementById("gemini-api-key").value,
    gemini_base_url: document.getElementById("gemini-base-url").value,
    gemini_model: document.getElementById("gemini-model").value,
    openclaw_enabled: Boolean(document.getElementById("settings-openclaw-url").value),
    openclaw_gateway_url: document.getElementById("settings-openclaw-url").value,
    openclaw_notes: document.getElementById("settings-openclaw-notes").value,
  };
  state.settings = await request("/api/settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  alert("設定已儲存。");
}

async function createCustomRole() {
  const payload = {
    display_name: "新角色",
    description: "請描述這個角色的定位",
    system_prompt: "你是會議中的一個角色。只用繁體中文輸出重點、邏輯、結論，不要客套。",
    color: "#7da8ff",
    source: "custom",
    provider: "mock",
    enabled: true,
    response_mode: "concise",
    max_output_tokens: 48,
  };
  const created = await request("/api/roles", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.roles.push(created);
  renderRoleEditors();
  renderRolePicker();
}

async function createMeeting(event) {
  event.preventDefault();
  const formData = new FormData(els.meetingForm);
  const selectedRoleIds = formData.getAll("selected_role_ids").map((value) => Number(value));
  const payload = {
    title: formData.get("title"),
    objective: formData.get("objective") || "",
    context_text: formData.get("context_text") || "",
    selected_role_ids: selectedRoleIds,
  };
  const meeting = await request("/api/meetings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  renderMeeting(meeting);
  closeDrawer(els.meetingModal);
  els.meetingForm.reset();
  renderRolePicker();
}

async function runRound() {
  if (!state.meeting) return;
  const payload = {
    formal_input: els.roundInput.value.trim(),
    note_input: els.noteInput.value.trim(),
  };
  const meeting = await request(`/api/meetings/${state.meeting.id}/rounds`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  els.roundInput.value = "";
  els.noteInput.value = "";
  renderMeeting(meeting);
}

async function runFullSummary() {
  if (!state.meeting) return;
  const meeting = await request(`/api/meetings/${state.meeting.id}/full-summary`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  renderMeeting(meeting);
}

async function closeMeeting() {
  if (!state.meeting) return;
  renderMeeting(
    await request(`/api/meetings/${state.meeting.id}/close`, {
      method: "POST",
      body: JSON.stringify({}),
    })
  );
}

async function exportMeeting(exportFormat) {
  if (!state.meeting) return;
  const result = await request(`/api/meetings/${state.meeting.id}/export`, {
    method: "POST",
    body: JSON.stringify({ export_format: exportFormat, archive: true }),
  });
  const popup = window.open("", "_blank");
  popup.document.write(`<pre>${escapeHtml(result.content)}</pre>`);
  state.memories = await request("/api/memories");
  renderArchives();
  renderMeeting(await request(`/api/meetings/${state.meeting.id}`));
}

function openDrawer(element) {
  element.classList.remove("hidden");
}

function closeDrawer(element) {
  element.classList.add("hidden");
}

document.getElementById("settings-toggle").addEventListener("click", () => openDrawer(els.settingsDrawer));
document.getElementById("settings-close").addEventListener("click", () => closeDrawer(els.settingsDrawer));
document.getElementById("new-meeting-toggle").addEventListener("click", () => openDrawer(els.meetingModal));
document.getElementById("meeting-close").addEventListener("click", () => closeDrawer(els.meetingModal));
document.getElementById("add-role-button").addEventListener("click", createCustomRole);
els.settingsForm.addEventListener("submit", saveSettings);
els.meetingForm.addEventListener("submit", createMeeting);
els.runRoundButton.addEventListener("click", runRound);
els.fullSummaryButton.addEventListener("click", runFullSummary);
els.closeMeetingButton.addEventListener("click", closeMeeting);
els.exportTextButton.addEventListener("click", () => exportMeeting("text"));
els.exportPythonButton.addEventListener("click", () => exportMeeting("python"));

bootstrap().catch((error) => {
  console.error(error);
  alert(`初始化失敗：${error.message}`);
});
