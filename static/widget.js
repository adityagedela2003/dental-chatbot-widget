(function () {

  var API_URL = "https://web-production-d199d.up.railway.app/chat";

  // ── STATE ────────────────────────────────────────────────────────────────
  var messages        = [];
  var phoneConfirmed  = false;
  var isOpen          = false;
  var isTyping        = false;

  // ── STYLES ───────────────────────────────────────────────────────────────
  var style = document.createElement("style");
  style.textContent = [
    "#aria-btn {",
    "  position:fixed; bottom:28px; right:28px; width:60px; height:60px;",
    "  border-radius:50%; background:linear-gradient(135deg,#2563eb,#1d4ed8);",
    "  color:white; border:none; cursor:pointer; font-size:26px;",
    "  box-shadow:0 4px 20px rgba(37,99,235,0.45); z-index:99998;",
    "  display:flex; align-items:center; justify-content:center;",
    "  transition:transform 0.2s;",
    "}",
    "#aria-btn:hover { transform:scale(1.08); }",
    "#aria-box {",
    "  position:fixed; bottom:100px; right:28px; width:370px; height:540px;",
    "  background:#fff; border-radius:18px;",
    "  box-shadow:0 8px 40px rgba(0,0,0,0.18);",
    "  display:flex; flex-direction:column; z-index:99999; overflow:hidden;",
    "  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;",
    "  transition:opacity 0.25s,transform 0.25s;",
    "  opacity:0; transform:translateY(16px) scale(0.97); pointer-events:none;",
    "}",
    "#aria-box.open { opacity:1; transform:translateY(0) scale(1); pointer-events:all; }",
    "#aria-head {",
    "  background:linear-gradient(135deg,#2563eb,#1d4ed8); color:white;",
    "  padding:16px 18px; display:flex; align-items:center; gap:12px;",
    "}",
    "#aria-avatar {",
    "  width:40px; height:40px; border-radius:50%;",
    "  background:rgba(255,255,255,0.25); display:flex;",
    "  align-items:center; justify-content:center; font-size:20px; flex-shrink:0;",
    "}",
    "#aria-head-info { flex:1; }",
    "#aria-head-name { font-weight:700; font-size:15px; }",
    "#aria-head-status { font-size:12px; opacity:0.85; margin-top:1px; }",
    "#aria-close {",
    "  background:none; border:none; color:white; font-size:22px;",
    "  cursor:pointer; opacity:0.8; line-height:1; padding:0;",
    "}",
    "#aria-close:hover { opacity:1; }",
    "#aria-msgs {",
    "  flex:1; overflow-y:auto; padding:16px;",
    "  display:flex; flex-direction:column; gap:10px;",
    "  background:#f8faff; scroll-behavior:smooth;",
    "}",
    "#aria-msgs::-webkit-scrollbar { width:4px; }",
    "#aria-msgs::-webkit-scrollbar-thumb { background:#cbd5e1; border-radius:4px; }",
    ".ab {",
    "  max-width:82%; padding:10px 14px; border-radius:16px;",
    "  font-size:14px; line-height:1.5; word-wrap:break-word;",
    "}",
    ".ab.bot {",
    "  background:#fff; color:#1e293b; border-bottom-left-radius:4px;",
    "  box-shadow:0 1px 4px rgba(0,0,0,0.08); align-self:flex-start;",
    "}",
    ".ab.bot p { margin:0 0 6px 0; }",
    ".ab.bot p:last-child { margin-bottom:0; }",
    ".ab.bot ul { margin:6px 0; padding-left:18px; }",
    ".ab.bot li { margin-bottom:4px; line-height:1.5; }",
    ".ab.bot strong { color:#1d4ed8; font-weight:600; }",
    ".ab.user {",
    "  background:linear-gradient(135deg,#2563eb,#1d4ed8); color:white;",
    "  border-bottom-right-radius:4px; align-self:flex-end;",
    "}",
    ".ab.typing { display:flex; gap:4px; align-items:center; }",
    ".ab.typing span {",
    "  width:7px; height:7px; background:#94a3b8; border-radius:50%;",
    "  animation:ab-bounce 1.2s infinite;",
    "}",
    ".ab.typing span:nth-child(2) { animation-delay:0.2s; }",
    ".ab.typing span:nth-child(3) { animation-delay:0.4s; }",
    "@keyframes ab-bounce {",
    "  0%,60%,100% { transform:translateY(0); }",
    "  30% { transform:translateY(-6px); }",
    "}",
    "#aria-input-row {",
    "  display:flex; align-items:center; padding:12px 14px;",
    "  border-top:1px solid #e2e8f0; background:#fff; gap:8px;",
    "}",
    "#aria-input {",
    "  flex:1; border:1.5px solid #e2e8f0; border-radius:24px;",
    "  padding:9px 16px; font-size:14px; outline:none;",
    "  transition:border-color 0.2s; font-family:inherit;",
    "}",
    "#aria-input:focus { border-color:#2563eb; }",
    "#aria-send {",
    "  width:38px; height:38px; border-radius:50%;",
    "  background:linear-gradient(135deg,#2563eb,#1d4ed8);",
    "  color:white; border:none; cursor:pointer;",
    "  display:flex; align-items:center; justify-content:center;",
    "  flex-shrink:0; transition:transform 0.15s;",
    "}",
    "#aria-send:hover { transform:scale(1.08); }",
    "#aria-send:disabled { opacity:0.5; cursor:not-allowed; transform:none; }",
    "#aria-foot {",
    "  text-align:center; font-size:11px; color:#94a3b8;",
    "  padding:6px; background:#fff;",
    "}",
    ".aria-lead-badge {",
    "  background:#f0fdf4; border:1px solid #86efac; border-radius:12px;",
    "  padding:10px 14px; font-size:12px; color:#166534; margin-top:4px;",
    "}"
  ].join("\n");
  document.head.appendChild(style);

  // ── HTML ─────────────────────────────────────────────────────────────────
  var wrap = document.createElement("div");
  wrap.innerHTML = [
    '<button id="aria-btn" title="Chat with Aria">&#129463;</button>',
    '<div id="aria-box">',
    '  <div id="aria-head">',
    '    <div id="aria-avatar">&#128105;&#8205;&#9877;&#65039;</div>',
    '    <div id="aria-head-info">',
    '      <div id="aria-head-name">Aria &mdash; Dental Assistant</div>',
    '      <div id="aria-head-status">&#9679; Online now</div>',
    '    </div>',
    '    <button id="aria-close">&times;</button>',
    '  </div>',
    '  <div id="aria-msgs"></div>',
    '  <div id="aria-input-row">',
    '    <input id="aria-input" type="text" placeholder="Type a message..." autocomplete="off" />',
    '    <button id="aria-send">',
    '      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">',
    '        <line x1="22" y1="2" x2="11" y2="13"></line>',
    '        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>',
    '      </svg>',
    '    </button>',
    '  </div>',
    '  <div id="aria-foot">Powered by Bright Smile Dental</div>',
    '</div>'
  ].join("\n");
  document.body.appendChild(wrap);

  // ── DOM REFS ─────────────────────────────────────────────────────────────
  var btn    = document.getElementById("aria-btn");
  var box    = document.getElementById("aria-box");
  var msgs   = document.getElementById("aria-msgs");
  var input  = document.getElementById("aria-input");
  var send   = document.getElementById("aria-send");
  var close  = document.getElementById("aria-close");

  // ── TOGGLE ───────────────────────────────────────────────────────────────
  function toggle() {
    isOpen = !isOpen;
    box.classList.toggle("open", isOpen);
    btn.innerHTML = isOpen ? "&times;" : "&#129463;";
    btn.style.fontSize = isOpen ? "28px" : "26px";
    if (isOpen && messages.length === 0) initChat();
    if (isOpen) setTimeout(function() { input.focus(); }, 300);
  }
  btn.addEventListener("click", toggle);
  close.addEventListener("click", toggle);

  // ── RENDER MARKDOWN-LITE ─────────────────────────────────────────────────
  function render(text) {
    // Step 1: Extract Google Maps URLs BEFORE escaping
    // Replace them with a placeholder so they survive HTML escaping
    var mapUrls = [];
    var processed = text.replace(/https?:\/\/(?:maps\.google\.com|goo\.gl\/maps|google\.com\/maps)[^\s]*/g, function(url) {
      var idx = mapUrls.length;
      mapUrls.push(url);
      return "___MAPURL" + idx + "___";
    });

    // Step 2: Escape HTML
    var html = processed
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Step 3: Bold **text**
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

    // Step 4: Restore map URLs as styled clickable buttons
    html = html.replace(/___MAPURL(\d+)___/g, function(match, idx) {
      var url = mapUrls[parseInt(idx)];
      return '<a href="' + url + '" target="_blank" rel="noopener" style="' +
        'display:inline-flex;align-items:center;gap:6px;margin:6px 0;' +
        'background:#1d4ed8;color:white;text-decoration:none;' +
        'padding:8px 14px;border-radius:20px;font-size:13px;font-weight:600;">' +
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="white">' +
        '<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/>' +
        '<circle cx="12" cy="9" r="2.5" fill="#1d4ed8"/>' +
        '</svg>' +
        'Open in Google Maps</a>';
    });

    // Step 5: Process lines for bullets and paragraphs
    var lines = html.split("\n");
    var out = "";
    var inList = false;

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i].trim();
      if (line.indexOf("- ") === 0 || line.indexOf("* ") === 0) {
        if (!inList) { out += "<ul>"; inList = true; }
        out += "<li>" + line.substring(2) + "</li>";
      } else {
        if (inList) { out += "</ul>"; inList = false; }
        if (line === "") {
          out += "<br>";
        } else {
          out += "<p>" + line + "</p>";
        }
      }
    }
    if (inList) out += "</ul>";
    return out;
  }

  // ── ADD BUBBLE ───────────────────────────────────────────────────────────
  function addBubble(role, text) {
    var div = document.createElement("div");
    div.className = "ab " + (role === "user" ? "user" : "bot");
    if (role === "user") {
      div.textContent = text;
    } else {
      div.innerHTML = render(text);
    }
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }

  // ── TYPING DOTS ──────────────────────────────────────────────────────────
  function showTyping() {
    var div = document.createElement("div");
    div.className = "ab bot typing";
    div.id = "aria-typing";
    div.innerHTML = "<span></span><span></span><span></span>";
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }
  function hideTyping() {
    var el = document.getElementById("aria-typing");
    if (el) el.remove();
  }

  // ── CALL API ─────────────────────────────────────────────────────────────
  function callAPI(callback) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", API_URL, true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onload = function() {
      if (xhr.status === 200) {
        callback(null, JSON.parse(xhr.responseText));
      } else {
        callback(new Error("Server error " + xhr.status), null);
      }
    };
    xhr.onerror = function() { callback(new Error("Network error"), null); };
    xhr.send(JSON.stringify({
      messages:        messages,
      phone_confirmed: phoneConfirmed
    }));
  }

  // ── SEND MESSAGE ─────────────────────────────────────────────────────────
  function sendMsg() {
    var text = input.value.trim();
    if (!text || isTyping) return;

    addBubble("user", text);
    messages.push({ role: "user", content: text });
    input.value = "";
    send.disabled = true;
    isTyping = true;
    showTyping();

    callAPI(function(err, data) {
      hideTyping();
      if (err) {
        addBubble("bot", "Sorry, I'm having trouble connecting. Please try again.");
      } else {
        phoneConfirmed  = data.phone_confirmed;
        addBubble("bot", data.reply);
        messages.push({ role: "assistant", content: data.reply });

        if (data.lead && data.lead.name) {
          var badge = document.createElement("div");
          badge.className = "aria-lead-badge";
          badge.innerHTML = "&#10003; <strong>Details saved!</strong> Our receptionist will call <strong>" + (data.lead.phone || "") + "</strong> shortly.";
          msgs.appendChild(badge);
          msgs.scrollTop = msgs.scrollHeight;
        }
      }
      isTyping = false;
      send.disabled = false;
      input.focus();
    });
  }

  // ── INIT GREETING ────────────────────────────────────────────────────────
  function initChat() {
    showTyping();
    messages = [{ role: "user", content: "Hello" }];
    callAPI(function(err, data) {
      hideTyping();
      messages = [];
      if (err) {
        addBubble("bot", "Hi! Welcome to Bright Smile Dental. How can I help you today?");
      } else {
        phoneConfirmed  = data.phone_confirmed;
        addBubble("bot", data.reply);
        messages.push({ role: "assistant", content: data.reply });
      }
    });
  }

  // ── EVENTS ───────────────────────────────────────────────────────────────
  input.addEventListener("keydown", function(e) {
    if (e.key === "Enter") { e.preventDefault(); sendMsg(); }
  });
  send.addEventListener("click", sendMsg);

})();
