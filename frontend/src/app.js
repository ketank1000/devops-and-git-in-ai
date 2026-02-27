/* ── State ───────────────────────────────────────────────────────────────────── */
const API_BASE   = 'http://localhost:8000';
let conversationId  = null;
let isLoading       = false;
let conversations   = JSON.parse(localStorage.getItem('ai_conversations') || '[]');

/* ── Init ────────────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  renderHistory();
  checkStatus();
  setInterval(checkStatus, 30_000);
});

/* ── Health check ────────────────────────────────────────────────────────────── */
async function checkStatus() {
  const dot  = document.getElementById('statusDot');
  const text = document.getElementById('statusText');
  try {
    const res  = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(5000) });
    const data = await res.json();
    if (data.status === 'healthy' && data.ollama === 'healthy') {
      dot.className = 'status-indicator online';
      text.textContent = `Online · ${data.model}`;
      document.getElementById('modelName').textContent = data.model;
    } else {
      dot.className = 'status-indicator offline';
      text.textContent = `Degraded (ollama: ${data.ollama})`;
    }
  } catch {
    dot.className = 'status-indicator offline';
    text.textContent = 'Offline';
  }
}

/* ── Conversation management ─────────────────────────────────────────────────── */
function newConversation() {
  conversationId = null;
  clearMessages();
  document.getElementById('chatTitle').textContent = 'New Conversation';
  renderHistory();
}

function clearMessages() {
  const msgs = document.getElementById('messages');
  msgs.innerHTML = `
    <div class="welcome">
      <div class="welcome-icon">🤖</div>
      <h2>Hello! I'm TinyLlama</h2>
      <p>An open-source AI assistant running entirely in your own infrastructure.<br/>
         Ask me anything — I'm here to help!</p>
    </div>`;
}

function saveConversation(title) {
  if (!conversationId) return;
  const existing = conversations.find(c => c.id === conversationId);
  if (!existing) {
    conversations.unshift({ id: conversationId, title: title.slice(0, 50), ts: Date.now() });
    if (conversations.length > 30) conversations.pop();
    localStorage.setItem('ai_conversations', JSON.stringify(conversations));
    renderHistory();
  }
}

function renderHistory() {
  const ul = document.getElementById('historyList');
  ul.innerHTML = conversations.map(c => `
    <li class="${c.id === conversationId ? 'active' : ''}"
        onclick="loadConversation('${c.id}', '${escHtml(c.title)}')"
        title="${escHtml(c.title)}">
      💬 ${escHtml(c.title)}
    </li>`).join('');
}

async function loadConversation(id, title) {
  conversationId = id;
  document.getElementById('chatTitle').textContent = title;
  clearMessages();
  renderHistory();

  try {
    const res  = await fetch(`${API_BASE}/conversations/${id}/messages`);
    if (!res.ok) return;
    const msgs = await res.json();
    // Hide welcome screen
    document.getElementById('messages').innerHTML = '';
    msgs.forEach(m => appendMessage(m.role, m.content, false));
    scrollToBottom();
  } catch { /* DB may be unavailable – silently skip */ }
}

/* ── Messaging ───────────────────────────────────────────────────────────────── */
async function sendMessage() {
  if (isLoading) return;

  const input = document.getElementById('userInput');
  const text  = input.value.trim();
  if (!text) return;

  // Remove welcome screen on first message
  const welcome = document.querySelector('.welcome');
  if (welcome) welcome.remove();

  isLoading = true;
  toggleSend(false);
  input.value  = '';
  input.style.height = 'auto';

  appendMessage('user', text);
  const typingId = showTyping();

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ message: text, conversation_id: conversationId }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data     = await res.json();
    conversationId = data.conversation_id;
    removeTyping(typingId);
    appendMessage('assistant', data.response);
    saveConversation(text);
  } catch (err) {
    removeTyping(typingId);
    appendMessage('assistant', `⚠️ Error: ${err.message}. Please check that the AI service is running.`);
  } finally {
    isLoading = false;
    toggleSend(true);
    input.focus();
  }
}

/* ── DOM helpers ─────────────────────────────────────────────────────────────── */
function appendMessage(role, content, scroll = true) {
  const container = document.getElementById('messages');

  const row    = document.createElement('div');
  row.className = `msg-row ${role === 'user' ? 'user' : 'assistant'}`;

  const avatar  = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? '🧑' : '🤖';

  const bubble  = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = content;   // use textContent to prevent XSS

  row.appendChild(avatar);
  row.appendChild(bubble);
  container.appendChild(row);

  if (scroll) scrollToBottom();
}

function showTyping() {
  const container = document.getElementById('messages');
  const id  = `typing-${Date.now()}`;
  const row = document.createElement('div');
  row.id    = id;
  row.className = 'msg-row assistant';
  row.innerHTML = `
    <div class="avatar">🤖</div>
    <div class="typing-bubble">
      <span class="dot"></span>
      <span class="dot"></span>
      <span class="dot"></span>
    </div>`;
  container.appendChild(row);
  scrollToBottom();
  return id;
}

function removeTyping(id) {
  document.getElementById(id)?.remove();
}

function toggleSend(enabled) {
  document.getElementById('sendBtn').disabled = !enabled;
}

function scrollToBottom() {
  const el = document.getElementById('messages');
  el.scrollTop = el.scrollHeight;
}

/* ── Input helpers ───────────────────────────────────────────────────────────── */
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

/* ── Util ────────────────────────────────────────────────────────────────────── */
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
