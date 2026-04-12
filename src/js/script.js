/* ═══════════════════════════════════════════════════════════
   BenX AI — Web UI Script v2.0
   Real-time backend connection via WebSocket + SSE
   ═══════════════════════════════════════════════════════════ */

"use strict";

// ── Config ──────────────────────────────────────────────────
const API_BASE    = window.location.origin;
const WS_URL      = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws`;
const METRICS_INT = 3000;   // ms between metric polls
const ACTIVITY_INT = 8000;  // ms between random activity items

// ── DOM refs ─────────────────────────────────────────────────
const ui = {
  clock:          document.getElementById("clock"),
  dateLabel:      document.getElementById("dateLabel"),
  statusDot:      document.getElementById("statusDot"),
  statusLabel:    document.getElementById("statusLabel"),
  statusPill:     document.getElementById("connectionStatus"),
  thinkingLabel:  document.getElementById("thinkingLabel"),
  thinkingInd:    document.getElementById("thinkingIndicator"),
  activityList:   document.getElementById("activityList"),
  activityChip:   document.getElementById("activityChip"),
  metricsChip:    document.getElementById("metricsChip"),
  chatWindow:     document.getElementById("chatWindow"),
  chatInput:      document.getElementById("chatInput"),
  sendBtn:        document.getElementById("sendBtn"),
  voiceBtn:       document.getElementById("voiceBtn"),
  clearBtn:       document.getElementById("clearBtn"),
  clearHistBtn:   document.getElementById("clearHistoryBtn"),
  taskList:       document.getElementById("taskList"),
  queuedCount:    document.getElementById("queuedCount"),
  modelSelect:    document.getElementById("modelSelect"),
  agentToggle:    document.getElementById("agentToggle"),
  uploadBtn:      document.getElementById("uploadBtn"),
  fileInput:      document.getElementById("fileInput"),
  attachPreview:  document.getElementById("attachmentPreview"),
  previewImg:     document.getElementById("previewImg"),
  removeAttach:   document.getElementById("removeAttach"),
  heroTimestamp:  document.getElementById("heroTimestamp"),
  toastContainer: document.getElementById("toastContainer"),
  chips:          document.querySelectorAll("[data-command]"),
};

// ── State ────────────────────────────────────────────────────
let ws = null;
let wsReady = false;
let isStreaming = false;
let mediaRecorder = null;
let audioChunks = [];
let attachedImage = null;   // { dataUrl, file }
let currentStreamEl = null; // DOM element receiving streamed text
let currentStreamText = ""; // accumulated streamed text

// ── Markdown renderer (lightweight, no deps) ─────────────────
function renderMarkdown(text) {
  return text
    // Code blocks
    .replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
      const id = "code-" + Math.random().toString(36).slice(2);
      return `<pre id="${id}"><button class="copy-code" onclick="copyCode('${id}')">Copy</button><code class="lang-${lang}">${escHtml(code.trim())}</code></pre>`;
    })
    // Inline code
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    // Bold
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    // Italic
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    // Headers
    .replace(/^### (.+)$/gm, "<h4>$1</h4>")
    .replace(/^## (.+)$/gm, "<h3>$1</h3>")
    .replace(/^# (.+)$/gm, "<h2>$1</h2>")
    // Unordered list
    .replace(/^\s*[-*] (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>[\s\S]*?<\/li>)/g, "<ul>$1</ul>")
    // Ordered list
    .replace(/^\d+\. (.+)$/gm, "<li>$1</li>")
    // Horizontal rule
    .replace(/^---+$/gm, "<hr>")
    // Paragraphs (double newlines)
    .replace(/\n{2,}/g, "</p><p>")
    // Single newlines
    .replace(/\n/g, "<br>")
    // Wrap in paragraph if no block elements
    .replace(/^(?!<[a-z])(.+)/, "<p>$1</p>");
}

function escHtml(str) {
  return str.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

window.copyCode = function(id) {
  const pre = document.getElementById(id);
  const code = pre ? pre.querySelector("code")?.innerText || "" : "";
  navigator.clipboard.writeText(code).then(() => showToast("Copied!", "success"));
};

// ── Clock ────────────────────────────────────────────────────
function nowParts() {
  const now = new Date();
  const pad = n => String(n).padStart(2, "0");
  return {
    stamp: `[${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}]`,
    time:  `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`,
    date:  now.toLocaleDateString(undefined, { month:"short", day:"2-digit", year:"numeric" })
  };
}

function updateClock() {
  const { stamp, time, date } = nowParts();
  ui.clock.textContent = time;
  ui.dateLabel.textContent = date;
  ui.heroTimestamp.textContent = stamp;
}

// ── System Metrics (real data) ────────────────────────────────
function setMeter(id, pct, maxPct = 100) {
  const el = document.getElementById(id);
  if (el) el.style.width = `${Math.min(100, (pct / maxPct) * 100)}%`;
}

function colorValue(id, value, warnAt, highAt) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove("metric-ok", "metric-warn", "metric-high");
  if (value >= highAt)  el.classList.add("metric-high");
  else if (value >= warnAt) el.classList.add("metric-warn");
  else el.classList.add("metric-ok");
}

async function fetchMetrics() {
  try {
    const res = await fetch(`${API_BASE}/api/metrics`, { signal: AbortSignal.timeout(4000) });
    if (!res.ok) throw new Error("non-ok");
    const m = await res.json();

    // CPU
    document.getElementById("cpuValue").textContent = `${m.cpu}%`;
    setMeter("cpuMeter", m.cpu);
    colorValue("cpuValue", m.cpu, 70, 90);

    // RAM
    const ramLabel = m.ram_used_gb ? `${m.ram}% (${m.ram_used_gb}GB)` : `${m.ram}%`;
    document.getElementById("ramValue").textContent = ramLabel;
    setMeter("ramMeter", m.ram);
    colorValue("ramValue", m.ram, 75, 90);

    // Disk
    document.getElementById("diskValue").textContent = m.disk ? `${m.disk}%` : "—";
    setMeter("diskMeter", m.disk || 0);
    colorValue("diskValue", m.disk || 0, 75, 90);

    // Network
    const net = m.network_kbps;
    const netLabel = net > 1000 ? `${(net/1024).toFixed(1)} MB/s` : `${Math.round(net)} KB/s`;
    document.getElementById("networkValue").textContent = netLabel;
    setMeter("networkMeter", net, 2000);

    // Temp
    document.getElementById("tempValue").textContent = m.temp ? `${m.temp}°C` : "—";
    setMeter("tempMeter", m.temp || 0, 100);
    colorValue("tempValue", m.temp || 0, 70, 85);

    // Battery
    const battCard = document.getElementById("batteryCard");
    if (m.battery !== null && m.battery !== undefined) {
      const battLabel = m.charging ? `${m.battery}% ⚡` : `${m.battery}%`;
      document.getElementById("batteryValue").textContent = battLabel;
      setMeter("batteryMeter", m.battery);
      colorValue("batteryValue", m.battery, 0, 0); // handled separately
      const bvEl = document.getElementById("batteryValue");
      bvEl.classList.remove("metric-ok","metric-warn","metric-high");
      if (m.battery < 15) bvEl.classList.add("metric-high");
      else if (m.battery < 30) bvEl.classList.add("metric-warn");
      else bvEl.classList.add("metric-ok");
      if (battCard) battCard.style.display = "";
    } else {
      if (battCard) battCard.style.display = "none";
    }

    ui.metricsChip.textContent = "Live";
  } catch {
    // Metrics fetch failed — keep previous values
  }
}

// ── WebSocket ────────────────────────────────────────────────
function connectWS() {
  setStatus("connecting");
  try {
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      wsReady = true;
      setStatus("connected");
      addActivity("WebSocket connected to BenX backend.");
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        handleServerMessage(msg);
      } catch { /* ignore malformed */ }
    };

    ws.onclose = () => {
      wsReady = false;
      setStatus("disconnected");
      addActivity("Connection dropped. Reconnecting…");
      setTimeout(connectWS, 3500);
    };

    ws.onerror = () => {
      setStatus("error");
    };
  } catch {
    setStatus("error");
    setTimeout(connectWS, 5000);
  }
}

function setStatus(state) {
  const labels = { connecting:"Connecting…", connected:"Operational", disconnected:"Reconnecting…", error:"Error" };
  ui.statusPill.className = "status-pill " + (state === "connected" ? "connected" : state === "error" ? "error" : "");
  ui.statusLabel.textContent = labels[state] || state;
}

function handleServerMessage(msg) {
  switch (msg.type) {
    case "status":
      setThinking(msg.text);
      break;

    case "chunk":
      if (currentStreamEl) {
        currentStreamText += msg.text;
        currentStreamEl.querySelector(".message-body").innerHTML =
          renderMarkdown(currentStreamText) +
          '<span class="streaming-cursor"></span>';
        scrollChat();
      }
      break;

    case "command_result":
      finaliseStream(msg.text, true);
      addActivity(`Command executed: ${msg.action}`);
      break;

    case "done":
      finaliseStream(currentStreamText);
      setThinking("Operational");
      isStreaming = false;
      enableInput();
      break;

    case "error":
      finaliseStream(msg.text, false, true);
      setThinking("Operational");
      isStreaming = false;
      enableInput();
      showToast(msg.text, "error");
      break;

    case "metrics":
      // Metrics pushed over WS — optional fallback
      break;
  }
}

// ── Chat logic ────────────────────────────────────────────────
function scrollChat() {
  ui.chatWindow.scrollTo({ top: ui.chatWindow.scrollHeight, behavior: "smooth" });
}

function addChatMessage(role, html, isError = false) {
  const { stamp } = nowParts();
  const el = document.createElement("article");
  el.className = `chat-message ${role}${isError ? " error" : ""}`;
  const name = role === "assistant" ? "BenX" : "You";
  el.innerHTML = `
    <div class="message-meta">
      <strong>${name}</strong>
      <span class="timestamp">${stamp}</span>
    </div>
    <div class="message-body">${html}</div>`;
  ui.chatWindow.appendChild(el);
  scrollChat();
  return el;
}

function addTypingIndicator() {
  const el = document.createElement("div");
  el.className = "typing-indicator";
  el.id = "typingIndicator";
  el.innerHTML = `<span class="dot"></span><span class="dot"></span><span class="dot"></span>`;
  ui.chatWindow.appendChild(el);
  scrollChat();
  return el;
}

function removeTypingIndicator() {
  const el = document.getElementById("typingIndicator");
  if (el) el.remove();
}

function startAssistantStream() {
  removeTypingIndicator();
  const { stamp } = nowParts();
  const el = document.createElement("article");
  el.className = "chat-message assistant";
  el.innerHTML = `
    <div class="message-meta">
      <strong>BenX</strong>
      <span class="timestamp">${stamp}</span>
    </div>
    <div class="message-body"><span class="streaming-cursor"></span></div>`;
  ui.chatWindow.appendChild(el);
  scrollChat();
  currentStreamEl = el;
  currentStreamText = "";
  return el;
}

function finaliseStream(text, isCommand = false, isError = false) {
  if (currentStreamEl) {
    const body = currentStreamEl.querySelector(".message-body");
    if (isCommand) {
      body.innerHTML = `<pre>${escHtml(text)}</pre>`;
    } else if (isError) {
      body.innerHTML = `<p style="color:var(--accent-red)">${escHtml(text)}</p>`;
      currentStreamEl.classList.add("error");
    } else {
      body.innerHTML = renderMarkdown(text);
    }
    scrollChat();
  }
  currentStreamEl = null;
  currentStreamText = "";
}

function disableInput() {
  ui.sendBtn.disabled = true;
  ui.chatInput.disabled = true;
}

function enableInput() {
  ui.sendBtn.disabled = false;
  ui.chatInput.disabled = false;
  ui.chatInput.focus();
}

function setThinking(label) {
  ui.thinkingLabel.textContent = label;
  if (label === "Operational") {
    ui.thinkingInd.classList.add("idle");
  } else {
    ui.thinkingInd.classList.remove("idle");
  }
}

async function submitMessage(text) {
  text = (text || ui.chatInput.value).trim();
  if (!text || isStreaming) return;

  // Add user message
  addChatMessage("user", renderMarkdown(text));
  addActivity(`User: ${text.slice(0, 60)}`);
  postSharedMessage("You", text);
  ui.chatInput.value = "";

  const imagefile = attachedImage ? attachedImage.file : null;
  clearAttachment();

  isStreaming = true;
  disableInput();
  addTypingIndicator();
  setThinking("🧠 Processing…");

  const model = ui.modelSelect.value || null;
  const agentMode = ui.agentToggle.getAttribute("aria-checked") === "true";

  // If there's an image attachment, use the POST endpoint
  if (imagefile) {
    await submitWithImage(text, imagefile);
    return;
  }

  // Use WebSocket if available, else fall back to SSE
  if (wsReady && ws) {
    removeTypingIndicator();
    startAssistantStream();
    ws.send(JSON.stringify({ type:"chat", message: text, model, agent_mode: agentMode }));
  } else {
    await submitViaSSE(text, model, agentMode);
  }
}

async function submitViaSSE(text, model, agentMode) {
  const params = new URLSearchParams({ message: text, agent_mode: agentMode });
  if (model) params.append("model", model);

  try {
    const source = new EventSource(`${API_BASE}/api/chat/stream?${params}`);
    removeTypingIndicator();
    startAssistantStream();

    source.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        handleServerMessage(msg);
        if (msg.type === "done" || msg.type === "error" || msg.type === "command_result") {
          source.close();
        }
      } catch { /* ignore */ }
    };

    source.onerror = () => {
      source.close();
      finaliseStream("❌ Connection error. Make sure the BenX server is running.", false, true);
      isStreaming = false;
      enableInput();
      setThinking("Operational");
    };
  } catch (e) {
    finaliseStream(`❌ ${e.message}`, false, true);
    isStreaming = false;
    enableInput();
    setThinking("Operational");
  }
}

async function submitWithImage(text, file) {
  removeTypingIndicator();
  const msgEl = startAssistantStream();

  try {
    const form = new FormData();
    form.append("image", file);
    const res = await fetch(`${API_BASE}/api/screenshot/analyze`, { method:"POST", body: form });
    const data = await res.json();
    finaliseStream(data.result || "❌ Analysis failed.");
    addActivity("Screenshot analyzed by vision AI.");
  } catch (e) {
    finaliseStream(`❌ Upload error: ${e.message}`, false, true);
  }

  isStreaming = false;
  enableInput();
  setThinking("Operational");
}

// ── Voice ────────────────────────────────────────────────────
async function toggleVoice() {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
    ui.voiceBtn.classList.remove("recording");
    ui.voiceBtn.setAttribute("aria-pressed", "false");
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      const blob = new Blob(audioChunks, { type: "audio/wav" });
      const form = new FormData();
      form.append("audio", blob, "voice.wav");

      setThinking("🎙️ Transcribing…");
      try {
        const res = await fetch(`${API_BASE}/api/voice`, { method:"POST", body: form });
        const data = await res.json();
        if (data.success && data.text) {
          ui.chatInput.value = data.text;
          ui.chatInput.focus();
          addActivity(`Voice captured: "${data.text.slice(0, 50)}"`);
        } else {
          showToast("Voice not understood. Try again.", "error");
        }
      } catch {
        showToast("Voice transcription failed.", "error");
      }
      setThinking("Operational");
    };

    mediaRecorder.start();
    ui.voiceBtn.classList.add("recording");
    ui.voiceBtn.setAttribute("aria-pressed", "true");
    addActivity("Voice recording started…");
    showToast("🎙️ Recording — click Voice to stop", "info");

  } catch {
    showToast("Microphone access denied.", "error");
  }
}

// ── File/Image attachment ─────────────────────────────────────
function clearAttachment() {
  attachedImage = null;
  ui.attachPreview.style.display = "none";
  ui.previewImg.src = "";
  ui.fileInput.value = "";
}

ui.fileInput.addEventListener("change", () => {
  const file = ui.fileInput.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    attachedImage = { dataUrl: e.target.result, file };
    ui.previewImg.src = e.target.result;
    ui.attachPreview.style.display = "block";
    showToast("Image attached — send to analyze with AI vision.", "info");
  };
  reader.readAsDataURL(file);
});

// ── Activity feed ─────────────────────────────────────────────
const activityLines = [
  "Indexed command surfaces and runtime capabilities.",
  "System telemetry streams stabilized.",
  "Voice shortcut standing by for input capture.",
  "Project analysis pipeline cached for fast follow-up.",
  "Automation planner generated a dry-run sequence.",
  "UI layer refreshed with updated visual hierarchy.",
  "RAG memory synchronized with conversation context.",
  "Browser workspace state snapshot recorded.",
  "Dependency health check completed.",
  "Screen analysis pipeline primed.",
];

const routineSets = [
  ["Sync AI conversation history", "Monitor system resource peaks", "Stage voice wake-word listener"],
  ["Index project codebase for analysis", "Watch clipboard for automation triggers", "Cache recent screen text"],
  ["Refresh browser tab workspace map", "Check scheduled task queue", "Update developer memory context"],
];

function addActivity(text) {
  const { stamp } = nowParts();
  const item = document.createElement("article");
  item.className = "activity-item";
  item.innerHTML = `
    <span class="activity-time">${stamp}</span>
    <div><strong>BenX</strong><p>${text}</p></div>`;
  ui.activityList.prepend(item);
  while (ui.activityList.children.length > 5) {
    ui.activityList.removeChild(ui.activityList.lastElementChild);
  }
}

function updateRoutines() {
  const set = routineSets[Math.floor(Math.random() * routineSets.length)];
  ui.taskList.innerHTML = "";
  set.forEach(task => {
    const li = document.createElement("li");
    li.textContent = task;
    ui.taskList.appendChild(li);
  });
  ui.queuedCount.textContent = `0${set.length}`.slice(-2);
}

// ── Toast notifications ───────────────────────────────────────
function showToast(message, type = "info", duration = 3500) {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  const icons = { success:"✔", error:"✕", info:"ℹ" };
  toast.innerHTML = `<span>${icons[type] || "ℹ"}</span> ${message}`;
  ui.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    toast.style.transition = "opacity 0.3s, transform 0.3s";
    setTimeout(() => toast.remove(), 350);
  }, duration);
}

// ── Event listeners ───────────────────────────────────────────
ui.sendBtn.addEventListener("click", () => submitMessage());

ui.chatInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    submitMessage();
  }
});

ui.clearBtn.addEventListener("click", () => {
  ui.chatWindow.innerHTML = "";
  addChatMessage("assistant", "<p>Conversation buffer cleared. Ready for the next task.</p>");
  addActivity("Conversation window cleared.");
});

ui.clearHistBtn.addEventListener("click", async () => {
  if (!confirm("Clear full conversation history from memory?")) return;
  try {
    await fetch(`${API_BASE}/api/history/clear`, { method: "POST" });
    showToast("History cleared.", "success");
  } catch {
    showToast("Could not clear server history.", "error");
  }
  ui.chatWindow.innerHTML = "";
  addChatMessage("assistant", "<p>History cleared. Starting fresh.</p>");
});

ui.voiceBtn.addEventListener("click", toggleVoice);

ui.agentToggle.addEventListener("click", () => {
  const on = ui.agentToggle.getAttribute("aria-checked") === "true";
  ui.agentToggle.setAttribute("aria-checked", String(!on));
  showToast(`Agent mode ${!on ? "enabled" : "disabled"}.`, "info");
});

ui.uploadBtn.addEventListener("click", () => ui.fileInput.click());
ui.removeAttach.addEventListener("click", clearAttachment);

ui.chips.forEach(btn => {
  btn.addEventListener("click", () => {
    const cmd = btn.dataset.command;
    ui.chatInput.value = cmd;
    ui.chatInput.focus();
  });
});

// ── Shared chat sync (GTK4 ↔ Web) ───────────────────────────
let _lastSyncId = 0;

async function pollSharedMessages() {
  try {
    const res = await fetch(`${API_BASE}/api/messages?since=${_lastSyncId}`, { signal: AbortSignal.timeout(3000) });
    const data = await res.json();
    for (const msg of (data.messages || [])) {
      _lastSyncId = Math.max(_lastSyncId, msg.id);
      if (msg.source === "gtk4") {
        const role = msg.sender === "BenX" ? "assistant" : "user";
        const label = role === "assistant" ? "BenX" : msg.sender;
        const { stamp } = nowParts();
        const el = document.createElement("article");
        el.className = `chat-message ${role} synced-gtk4`;
        el.innerHTML = `
          <div class="message-meta">
            <strong>${label} <span style="font-size:0.75em;opacity:0.55">[GTK4]</span></strong>
            <span class="timestamp">${msg.timestamp || stamp}</span>
          </div>
          <div class="message-body">${renderMarkdown(msg.text)}</div>`;
        ui.chatWindow.appendChild(el);
        scrollChat();
        addActivity(`GTK4 → ${label}: ${msg.text.slice(0, 50)}`);
      }
    }
  } catch { /* server not running or no new messages */ }
}

async function postSharedMessage(sender, text) {
  try {
    await fetch(`${API_BASE}/api/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sender, text }),
      signal: AbortSignal.timeout(3000),
    });
  } catch { /* ignore */ }
}

// ── Load conversation history ─────────────────────────────────
async function loadHistory() {
  try {
    const res = await fetch(`${API_BASE}/api/history?limit=20`);
    const data = await res.json();
    if (!data.messages || data.messages.length === 0) return;

    // Show last few messages
    const recent = data.messages.slice(-6);
    recent.forEach(msg => {
      const role = msg.role === "user" ? "user" : "assistant";
      addChatMessage(role, renderMarkdown(msg.content || ""));
    });
    addActivity(`Loaded ${data.messages.length} messages from history.`);
  } catch {
    // Server not connected yet — that's fine
  }
}

// ── Init ─────────────────────────────────────────────────────
updateClock();
updateRoutines();
addActivity("Dashboard initialised — connecting to BenX backend…");

// Start WS
connectWS();

// Start metrics polling
fetchMetrics();

// Intervals
setInterval(updateClock, 1000);
setInterval(fetchMetrics, METRICS_INT);
setInterval(() => addActivity(activityLines[Math.floor(Math.random() * activityLines.length)]), ACTIVITY_INT);
setInterval(updateRoutines, 15000);
setInterval(pollSharedMessages, 2000);

// Load history after a short delay (let WS connect first)
setTimeout(loadHistory, 1200);
