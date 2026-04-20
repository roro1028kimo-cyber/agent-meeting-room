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
  agentList: document.getElementById("agent-list"),
  archiveList: document.getElementById("archive-list"),
  memoryPreview: document.getElementById("memory-preview"),
  roundInput: document.getElementById("round-input"),
  noteInput: document.getElementById("note-input"),
  runRoundButton: document.getElementById("run-round-button"),
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

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail = typeof payload === "string" ? payload : JSON.stringify(payload);
    throw new Error(detail);
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
  const settings = state.settings;
  document.getElementById("settings-api-mode").value = settings.api_mode;
  document.getElementById("settings-api-key").value = settings.api_key || "";
  document.getElementById("settings-base-url").value = settings.base_url || "";
  document.getElementById("settings-model-name").value = settings.model_name || "";
  document.getElementById("settings-temperature").value = settings.temperature ?? 0.7;
  document.getElementById("settings-max-tokens").value = settings.max_tokens ?? 700;
  document.getElementById("settings-openclaw-url").value = settings.openclaw_gateway_url || "";
  document.getElementById("settings-openclaw-notes").value = settings.openclaw_notes || "";
}

function renderRoleEditors() {
  els.roleEditorList.innerHTML = "";
  state.roles.forEach((role) => {
    const fragment = els.roleTemplate.content.cloneNode(true);
    fragment.querySelector("[data-role-name]").textContent = role.display_name;
    fragment.querySelector("[data-role-type]").textContent = role.source;
    fragment.querySelector("[data-role-enabled]").checked = role.enabled;
    fragment.querySelector('[data-role-field="display_name"]').value = role.display_name;
    fragment.querySelector('[data-role-field="description"]').value = role.description;
    fragment.querySelector('[data-role-field="system_prompt"]').value = role.system_prompt;
    fragment.querySelector('[data-role-field="color"]').value = role.color;

    fragment.querySelector("[data-role-save]").addEventListener("click", async (event) => {
      event.preventDefault();
      const card = event.target.closest(".role-editor-card");
      const payload = {
        display_name: card.querySelector('[data-role-field="display_name"]').value,
        description: card.querySelector('[data-role-field="description"]').value,
        system_prompt: card.querySelector('[data-role-field="system_prompt"]').value,
        color: card.querySelector('[data-role-field="color"]').value,
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
        const refreshed = await request(`/api/meetings/${state.meeting.id}`);
        renderMeeting(refreshed);
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
    els.meetingObjective.textContent = "請先建立一場新會議。";
    els.meetingStatus.textContent = "待命";
    els.meetingRound.textContent = "Round 0";
    els.conversationList.className = "conversation-list empty";
    els.conversationList.textContent = "建立會議後，這裡會顯示使用者與各個 agent 的逐輪討論。";
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
  toggleMeetingControls(true);
  renderMessages(meeting.messages || []);
  renderParticipants(meeting.participants || []);
  renderTemporaryMemory(meeting.temporary_memory || {});
  renderArchives(meeting.archives || state.memories);
}

function toggleMeetingControls(enabled) {
  els.runRoundButton.disabled = !enabled;
  els.closeMeetingButton.disabled = !enabled;
  els.exportTextButton.disabled = !enabled;
  els.exportPythonButton.disabled = !enabled;
}

function renderMessages(messages) {
  if (!messages.length) {
    els.conversationList.className = "conversation-list empty";
    els.conversationList.textContent = "這場會議還沒有任何內容。";
    return;
  }
  const latestAgent = [...messages].reverse().find((item) => item.message_type === "agent");
  els.conversationList.className = "conversation-list";
  els.conversationList.innerHTML = messages
    .map((message) => {
      const active = latestAgent && latestAgent.id === message.id;
      return `
        <article class="message-card ${active ? "active" : ""}">
          <div class="message-meta">
            <div class="speaker">
              <span class="light ${active ? "on" : ""}"></span>
              <strong>${escapeHtml(message.role_name)}</strong>
            </div>
            <span class="message-type">${escapeHtml(message.message_type)} / Round ${message.round_number}</span>
          </div>
          <div class="message-body">${escapeHtml(message.content)}</div>
        </article>
      `;
    })
    .join("");
}

function renderParticipants(participants) {
  if (!participants.length) {
    els.agentList.className = "agent-list empty";
    els.agentList.textContent = "尚未建立會議。";
    return;
  }

  const latestAgentName = [...(state.meeting?.messages || [])]
    .reverse()
    .find((item) => item.message_type === "agent")?.role_name;

  els.agentList.className = "agent-list";
  els.agentList.innerHTML = participants
    .map((participant) => {
      const isActive = latestAgentName === participant.role.display_name;
      return `
        <article class="agent-card">
          <div class="agent-row">
            <div class="agent-chip">
              <span class="light on" style="background:${escapeHtml(participant.role.color)}"></span>
              <strong>${escapeHtml(participant.role.display_name)}</strong>
            </div>
            <span>${isActive ? "發言中" : "待命"}</span>
          </div>
          <div class="agent-role">${escapeHtml(participant.role.description)}</div>
          <div class="agent-source">${escapeHtml(participant.role.source)}</div>
        </article>
      `;
    })
    .join("");
}

function renderTemporaryMemory(memory) {
  const notes = memory.notes || [];
  const latestSummary = memory.latest_summary || "";
  if (!notes.length && !latestSummary) {
    els.memoryPreview.className = "memory-preview empty";
    els.memoryPreview.textContent = "尚無暫存記憶。";
    return;
  }
  els.memoryPreview.className = "memory-preview";
  els.memoryPreview.innerHTML = `
    <article class="memory-card">
      <strong>最新摘要</strong>
      <div class="message-body">${escapeHtml(latestSummary || "尚未產生")}</div>
    </article>
    ${notes
      .slice(-5)
      .reverse()
      .map(
        (note) => `
          <article class="memory-card">
            <div class="message-body">${escapeHtml(note)}</div>
          </article>
        `
      )
      .join("")}
  `;
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
    api_key: document.getElementById("settings-api-key").value,
    base_url: document.getElementById("settings-base-url").value,
    model_name: document.getElementById("settings-model-name").value,
    temperature: Number(document.getElementById("settings-temperature").value || 0.7),
    max_tokens: Number(document.getElementById("settings-max-tokens").value || 700),
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
    system_prompt: "你是一個會議室中的輕量角色。請使用繁體中文發言，先說重點，再補充理由。",
    color: "#a78bfa",
    source: "custom",
    enabled: true,
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
    user_input: [els.roundInput.value.trim(), els.noteInput.value.trim()].filter(Boolean).join("\n"),
  };
  const meeting = await request(`/api/meetings/${state.meeting.id}/rounds`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  els.roundInput.value = "";
  els.noteInput.value = "";
  renderMeeting(meeting);
}

async function closeMeeting() {
  if (!state.meeting) return;
  const meeting = await request(`/api/meetings/${state.meeting.id}/close`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  renderMeeting(meeting);
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
  const refreshed = await request(`/api/meetings/${state.meeting.id}`);
  renderMeeting(refreshed);
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
els.settingsForm.addEventListener("submit", saveSettings);
document.getElementById("add-role-button").addEventListener("click", createCustomRole);
els.meetingForm.addEventListener("submit", createMeeting);
els.runRoundButton.addEventListener("click", runRound);
els.closeMeetingButton.addEventListener("click", closeMeeting);
els.exportTextButton.addEventListener("click", () => exportMeeting("text"));
els.exportPythonButton.addEventListener("click", () => exportMeeting("python"));

bootstrap().catch((error) => {
  console.error(error);
  alert(`初始化失敗：${error.message}`);
});
