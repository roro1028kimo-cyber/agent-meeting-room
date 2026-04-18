const state = {
  meetingId: null,
  meeting: null,
};

const createMeetingForm = document.getElementById("create-meeting-form");
const discussionForm = document.getElementById("discussion-form");
const interruptForm = document.getElementById("interrupt-form");
const reframeForm = document.getElementById("reframe-form");
const confirmButton = document.getElementById("confirm-button");
const finalizeButton = document.getElementById("finalize-button");
const exportButtons = Array.from(document.querySelectorAll(".export-button"));
const timeline = document.getElementById("timeline");
const summaryCard = document.getElementById("summary-card");
const interruptList = document.getElementById("interrupt-list");
const meetingStatePill = document.getElementById("meeting-state-pill");
const meetingModePill = document.getElementById("meeting-mode-pill");
const meetingIdText = document.getElementById("meeting-id-text");
const discussionSubmit = document.getElementById("discussion-submit");
const interruptSubmit = document.getElementById("interrupt-submit");
const reframeSubmit = document.getElementById("reframe-submit");

function textToLines(value) {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || "Request failed");
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

function renderMeeting(meeting) {
  state.meeting = meeting;
  state.meetingId = meeting.id;

  meetingStatePill.textContent = meeting.current_state;
  meetingModePill.textContent = meeting.meeting_mode;
  meetingIdText.textContent = `meeting_id: ${meeting.id}`;

  discussionSubmit.disabled = false;
  interruptSubmit.disabled = false;
  reframeSubmit.disabled = false;
  confirmButton.disabled = false;
  finalizeButton.disabled = false;
  exportButtons.forEach((button) => {
    button.disabled = false;
  });

  renderTimeline(meeting.messages || []);
  renderSummary(meeting.chair_summary || {});
  renderInterrupts(meeting.interrupts || []);
}

function renderTimeline(messages) {
  if (!messages.length) {
    timeline.className = "timeline empty";
    timeline.textContent = "目前尚無會議訊息。";
    return;
  }

  timeline.className = "timeline";
  timeline.innerHTML = messages
    .map((message) => {
      return `
        <article class="message-card">
          <div class="message-meta">
            <span class="role-tag">${message.role_name}</span>
            <span class="message-type">${message.message_type}</span>
          </div>
          <div class="message-body">${escapeHtml(message.content)}</div>
        </article>
      `;
    })
    .join("");
}

function renderSummary(summary) {
  if (!summary.conclusion) {
    summaryCard.className = "summary-card empty";
    summaryCard.textContent = "尚未產出摘要。";
    return;
  }

  summaryCard.className = "summary-card";
  summaryCard.innerHTML = `
    <section class="summary-block">
      <h3>目前結論</h3>
      <p>${escapeHtml(summary.conclusion)}</p>
    </section>
    <section class="summary-block">
      <h3>已確認事項</h3>
      ${renderList(summary.confirmed_items)}
    </section>
    <section class="summary-block">
      <h3>主要風險</h3>
      ${renderList(summary.risks)}
    </section>
    <section class="summary-block">
      <h3>待決事項</h3>
      ${renderList(summary.pending_decisions)}
    </section>
    <section class="summary-block">
      <h3>下一步</h3>
      <ul>
        ${(summary.next_actions || [])
          .map(
            (item) =>
              `<li>${escapeHtml(item.task)} / ${escapeHtml(item.owner)} / ${escapeHtml(
                item.due
              )}</li>`
          )
          .join("")}
      </ul>
    </section>
  `;
}

function renderInterrupts(interrupts) {
  if (!interrupts.length) {
    interruptList.className = "interrupt-list empty";
    interruptList.textContent = "目前沒有待處理插話。";
    return;
  }

  interruptList.className = "interrupt-list";
  interruptList.innerHTML = interrupts
    .map(
      (item) => `
        <article class="interrupt-item">
          <span class="interrupt-badge">${item.priority} / ${item.status}</span>
          <div>${escapeHtml(item.message)}</div>
        </article>
      `
    )
    .join("");
}

function renderList(items = []) {
  if (!items.length) {
    return "<p>目前沒有資料。</p>";
  }
  return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function escapeHtml(value = "") {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

createMeetingForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(createMeetingForm);
  const payload = {
    topic: formData.get("topic"),
    meeting_mode: formData.get("meeting_mode"),
    background: formData.get("background") || "",
    timeline: formData.get("timeline") || "",
    task_list: textToLines(formData.get("task_list") || ""),
    blockers: textToLines(formData.get("blockers") || ""),
    risks: textToLines(formData.get("risks") || ""),
    acceptance_criteria: textToLines(formData.get("acceptance_criteria") || ""),
    kpis: [],
  };

  try {
    const meeting = await request("/api/meetings", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderMeeting(meeting);
  } catch (error) {
    alert(`建立會議失敗：${error.message}`);
  }
});

discussionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.meetingId) {
    return;
  }

  const formData = new FormData(discussionForm);
  const payload = {
    message: formData.get("message") || "",
  };

  try {
    const meeting = await request(`/api/meetings/${state.meetingId}/discussion`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    discussionForm.reset();
    renderMeeting(meeting);
  } catch (error) {
    alert(`送出討論失敗：${error.message}`);
  }
});

interruptForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.meetingId) {
    return;
  }

  const formData = new FormData(interruptForm);
  const payload = {
    message: formData.get("message") || "",
    priority: formData.get("priority"),
    mode: "meeting",
  };

  try {
    const meeting = await request(`/api/meetings/${state.meetingId}/interrupts`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    interruptForm.reset();
    renderMeeting(meeting);
  } catch (error) {
    alert(`提交插話失敗：${error.message}`);
  }
});

reframeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.meetingId) {
    return;
  }

  const formData = new FormData(reframeForm);
  const payload = {
    updated_context: formData.get("updated_context") || "",
  };

  try {
    const meeting = await request(`/api/meetings/${state.meetingId}/reframe`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    reframeForm.reset();
    renderMeeting(meeting);
  } catch (error) {
    alert(`重整前提失敗：${error.message}`);
  }
});

confirmButton.addEventListener("click", async () => {
  if (!state.meetingId) {
    return;
  }

  try {
    const meeting = await request(`/api/meetings/${state.meetingId}/confirm`, {
      method: "POST",
      body: JSON.stringify({ note: "使用者已確認目前前提，可進入正式會議。" }),
    });
    renderMeeting(meeting);
  } catch (error) {
    alert(`確認前提失敗：${error.message}`);
  }
});

finalizeButton.addEventListener("click", async () => {
  if (!state.meetingId) {
    return;
  }

  try {
    const meeting = await request(`/api/meetings/${state.meetingId}/finalize`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    renderMeeting(meeting);
  } catch (error) {
    alert(`整理最終摘要失敗：${error.message}`);
  }
});

exportButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    if (!state.meetingId) {
      return;
    }

    const format = button.dataset.export;
    try {
      const result = await request(`/api/meetings/${state.meetingId}/export?format=${format}`);
      if (format === "json") {
        const popup = window.open("", "_blank");
        popup.document.write(`<pre>${escapeHtml(JSON.stringify(result, null, 2))}</pre>`);
      } else {
        const popup = window.open("", "_blank");
        popup.document.write(result);
      }
    } catch (error) {
      alert(`匯出失敗：${error.message}`);
    }
  });
});

