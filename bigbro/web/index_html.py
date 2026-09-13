"""Single-file dashboard for BigBro. No external assets — works fully offline in-app."""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>BigBro — your developer agent</title>
<style>
:root{
  --bg:#0b0e14; --panel:#11151f; --panel2:#161b28; --line:#232a3b;
  --text:#e6e9f0; --dim:#8b93a7; --accent:#f5b942; --accent2:#4da3ff; --err:#ff6b6b;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
#login{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:radial-gradient(1200px 600px at 50% -100px,#1a2233,#0b0e14)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:34px;width:350px;text-align:center}
.logo{font-size:44px}
h1{margin:8px 0 2px;font-size:22px;letter-spacing:3px}
.sub{color:var(--dim);font-size:13px;margin-bottom:22px}
input[type=password],textarea{width:100%;background:var(--panel2);border:1px solid var(--line);border-radius:10px;color:var(--text);padding:11px 13px;font:inherit;outline:none}
input:focus,textarea:focus{border-color:var(--accent)}
button{cursor:pointer;border:0;border-radius:10px;padding:11px 16px;font:inherit;font-weight:600}
.primary{background:var(--accent);color:#1a1205}
.primary:hover{filter:brightness(1.1)}
.primary:disabled{opacity:.5;cursor:default}
.ghost{background:transparent;color:var(--dim);border:1px solid var(--line)}
.ghost:hover{color:var(--text)}
#app{display:none;flex-direction:column;height:100vh}
header{display:flex;align-items:center;gap:12px;padding:12px 18px;background:var(--panel);border-bottom:1px solid var(--line);flex-wrap:wrap}
header .brand{font-weight:800;letter-spacing:3px}
header .meta{color:var(--dim);font-size:12px;margin-left:auto;margin-right:4px}
#messages{flex:1;overflow-y:auto;padding:24px 16px;display:flex;flex-direction:column;gap:14px}
.msg{display:flex}
.msg.user{justify-content:flex-end}
.bubble{max-width:80%;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px 15px;overflow-wrap:anywhere}
.msg.user .bubble{background:#20283a;border-color:#2c3752}
.bubble pre{background:#0a0d13;border:1px solid var(--line);border-radius:8px;padding:10px;overflow-x:auto;font-size:13px;margin:8px 0}
.bubble code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px}
.bubble :not(pre)>code{background:#0a0d13;padding:1px 5px;border-radius:5px}
.bubble h3,.bubble h4{margin:10px 0 4px}
.events{margin-top:10px;border-top:1px dashed var(--line);padding-top:8px}
.events summary{color:var(--dim);font-size:12px;cursor:pointer}
.ev{font-size:12px;color:var(--dim);margin-top:4px}
.ev b{color:var(--accent2)}
.err{color:var(--err)}
#composer{display:flex;gap:10px;padding:14px 16px;background:var(--panel);border-top:1px solid var(--line)}
#composer textarea{flex:1;resize:none;height:52px}
.spin{display:inline-block;width:14px;height:14px;border:2px solid var(--line);border-top-color:var(--accent);border-radius:50%;animation:sp .8s linear infinite;vertical-align:-2px;margin-right:8px}
@keyframes sp{to{transform:rotate(360deg)}}
#modal{position:fixed;inset:0;background:rgba(0,0,0,.6);display:none;align-items:center;justify-content:center;z-index:9}
#modal .card{width:540px;max-height:70vh;overflow-y:auto;text-align:left}
.caprow{border-bottom:1px solid var(--line);padding:10px 0}
.caprow b{color:var(--accent2)}
.caprow div{color:var(--dim);font-size:12.5px;margin-top:2px}
</style>
</head>
<body>

<div id="login">
  <div class="card">
    <div class="logo">🕶️</div>
    <h1>BIGBRO</h1>
    <div class="sub">Your personal full-stack developer agent.<br/>Enter your access token to unlock.</div>
    <input type="password" id="tok" placeholder="Access token" autocomplete="off"/>
    <div style="margin-top:14px"><button class="primary" style="width:100%" onclick="doLogin()">Unlock</button></div>
    <div id="login-err" class="err" style="margin-top:10px;font-size:13px"></div>
  </div>
</div>

<div id="app">
  <header>
    <span style="font-size:22px">🕶️</span><span class="brand">BIGBRO</span>
    <span class="meta" id="meta"></span>
    <button class="ghost" onclick="newSession()">New session</button>
    <button class="ghost" onclick="showCaps()">Capabilities</button>
  </header>
  <div id="messages"></div>
  <div id="composer">
    <textarea id="input" placeholder="Describe what to build… (Enter to send, Shift+Enter for newline)"></textarea>
    <button class="primary" id="sendbtn" onclick="send()">Send</button>
  </div>
</div>

<div id="modal" onclick="if(event.target===this)this.style.display='none'">
  <div class="card">
    <h3 style="margin-top:0">Capabilities</h3>
    <div id="caplist"></div>
    <div style="margin-top:16px"><button class="ghost" style="width:100%" onclick="document.getElementById('modal').style.display='none'">Close</button></div>
  </div>
</div>

<script>
const $ = s => document.querySelector(s);
let token = localStorage.getItem("bb_token") || "";
let sessionId = localStorage.getItem("bb_session") || "";
let busy = false;

const esc = s => String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
function md(s){
  s = esc(s);
  s = s.replace(/```(\w*)\n([\s\S]*?)```/g, (m,l,c) => "<pre><code>" + c + "</code></pre>");
  s = s.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/^### (.*)$/gm, "<h4>$1</h4>").replace(/^## (.*)$/gm, "<h3>$1</h3>");
  s = s.replace(/\n/g, "<br>");
  return s;
}
function showLogin(){
  $("#login").style.display = "flex";
  $("#app").style.display = "none";
  localStorage.removeItem("bb_token");
  token = "";
}
async function doLogin(){
  const t = $("#tok").value.trim();
  if (!t) return;
  try {
    const r = await fetch("/api/login", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({token: t})});
    if (!r.ok) throw new Error((await r.json()).detail || "bad token");
    token = t; localStorage.setItem("bb_token", t);
    $("#login").style.display = "none";
    $("#app").style.display = "flex";
    greet(); enterApp();
  } catch(e) { $("#login-err").textContent = e.message; }
}
async function enterApp(){
  try {
    const r = await fetch("/api/health", {headers: {Authorization: "Bearer " + token}});
    if (!r.ok) throw new Error("unauthorized");
    const h = await r.json();
    $("#meta").textContent = h.provider + "/" + h.model + " · " + h.capabilities.length + " capabilities";
  } catch(e) {}
}
function greet(){
  addBubble("assistant", "Hey. I'm <b>BigBro</b> — I build your websites, mobile apps, integration layers, and backends. Tell me what we're shipping.");
}
function addBubble(who, html){
  const m = document.createElement("div"); m.className = "msg " + who;
  const b = document.createElement("div"); b.className = "bubble"; b.innerHTML = html;
  m.appendChild(b); $("#messages").appendChild(b && m);
  $("#messages").scrollTop = $("#messages").scrollHeight;
  return b;
}
function renderEvents(events){
  if (!events || !events.length) return "";
  const rows = events.map(e =>
    '<div class="ev">⚙ <b>' + esc(e.name) + '</b> — ' + esc((e.detail || "").split("\n")[0]).slice(0,140) + '</div>'
  ).join("");
  return '<details class="events"><summary>' + events.length + ' action' + (events.length>1?"s":"") + '</summary>' + rows + '</details>';
}
async function send(){
  const inp = $("#input");
  const text = inp.value.trim();
  if (!text || busy) return;
  busy = true; $("#sendbtn").disabled = true; inp.value = "";
  addBubble("user", esc(text));
  const b = addBubble("assistant", "<span class='spin'></span>BigBro is working…");
  try {
    const r = await fetch("/api/chat", {method:"POST", headers:{"Content-Type":"application/json","Authorization":"Bearer "+token}, body: JSON.stringify({message: text, session_id: sessionId})});
    if (r.status === 401) { showLogin(); throw new Error("session expired — log in again"); }
    if (!r.ok) { const d = await r.json().catch(()=>({})); throw new Error(d.detail || "HTTP " + r.status); }
    const data = await r.json();
    sessionId = data.session_id; localStorage.setItem("bb_session", sessionId);
    b.innerHTML = md(data.reply) + renderEvents(data.events);
  } catch(e) {
    b.innerHTML = '<span class="err">⚠ ' + esc(e.message) + '</span>';
  }
  busy = false; $("#sendbtn").disabled = false;
  $("#messages").scrollTop = $("#messages").scrollHeight;
  inp.focus();
}
function newSession(){
  sessionId = ""; localStorage.removeItem("bb_session");
  $("#messages").innerHTML = "";
  greet();
}
async function showCaps(){
  $("#modal").style.display = "flex";
  try {
    const r = await fetch("/api/capabilities", {headers: {Authorization: "Bearer " + token}});
    const caps = await r.json();
    $("#caplist").innerHTML = caps.map(c =>
      '<div class="caprow"><b>' + esc(c.name) + '</b><div>' + esc(c.description) + '</div></div>'
    ).join("");
  } catch(e) { $("#caplist").innerHTML = '<div class="err">' + esc(e.message) + '</div>'; }
}
const inp = $("#input");
inp.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } });
$("#tok").addEventListener("keydown", e => { if (e.key === "Enter") doLogin(); });
(function init(){
  if (token) {
    fetch("/api/health", {headers: {Authorization: "Bearer " + token}})
      .then(r => { if (r.ok) { $("#login").style.display = "none"; $("#app").style.display = "flex"; greet(); enterApp(); } else showLogin(); })
      .catch(showLogin);
  }
})();
</script>
</body>
</html>
"""
