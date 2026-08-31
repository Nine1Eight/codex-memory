const WS_ENDPOINT = "ws://localhost:8080/ws";
const HEALTH = "http://localhost:8080/health";
const MODEL = "local-gguf";

const statusEl = document.getElementById("status");
const runBtn = document.getElementById("runBtn");
const voiceBtn = document.getElementById("voiceBtn");
const streamEl = document.getElementById("stream");

runBtn.onclick = () => execute();
voiceBtn.onclick = () => startVoice();

let registry = JSON.parse(localStorage.getItem("registry") || "[]");
let policies = JSON.parse(localStorage.getItem("policies") || "{}");
let memory = JSON.parse(localStorage.getItem("memory") || "[]");

async function healthCheck() {
  try {
    const res = await fetch(HEALTH);
    statusEl.innerText = res.ok ? "AI Online" : "Offline";
  } catch { statusEl.innerText = "Offline"; }
}

function execute() {
  const input = document.getElementById("prompt").value.trim();
  if (!input) return;
  streamEl.innerText = "";
  streamInference(buildMessages(input));
}

function buildMessages(userInput) {
  return [
    { role:"system", content: SYSTEM_PROMPT },
    { role:"system", content: "Registry: " + JSON.stringify(registry) },
    { role:"system", content: "Policies: " + JSON.stringify(policies) },
    { role:"system", content: "Memory: " + JSON.stringify(memory.slice(-10)) },
    { role:"user", content:userInput }
  ];
}

function streamInference(messages) {
  const ws = new WebSocket(WS_ENDPOINT);
  ws.onopen = () => {
    ws.send(JSON.stringify({
      model: MODEL,
      messages,
      stream:true,
      temperature:0.2
    }));
  };

  ws.onmessage = (evt) => {
    const data = JSON.parse(evt.data);
    if (data.token) {
      streamEl.innerText += data.token;
    }
    if (data.done) {
      try {
        const layout = extractJSON(streamEl.innerText);
        applyLayout(layout);
        trainMemory(messages, layout);
      } catch {}
      ws.close();
    }
  };
}

function extractJSON(text) {
  const s = text.indexOf("{");
  const e = text.lastIndexOf("}");
  return JSON.parse(text.slice(s, e+1));
}

function applyLayout(layout) {
  if (!layout.dock || !layout.grid) return;
  render("dock", layout.dock);
  render("grid", layout.grid);
  localStorage.setItem("layout", JSON.stringify(layout));
}

function render(target, apps) {
  const container = document.getElementById(target);
  container.innerHTML = "";
  apps.forEach(pkg => {
    if (!enforcePolicy(pkg)) return;
    const div = document.createElement("div");
    div.className = "app";
    div.innerText = pkg;
    div.onclick = () => launch(pkg);
    container.appendChild(div);
  });
}

function enforcePolicy(pkg) {
  if (policies.block && policies.block.includes(pkg)) return false;
  return true;
}

function launch(pkg) {
  if (window.Android && Android.launchApp) {
    Android.launchApp(pkg);
  } else {
    location.href = "intent://" + pkg;
  }
}

function trainMemory(messages, layout) {
  memory.push({ input: messages[messages.length-1].content, layout });
  localStorage.setItem("memory", JSON.stringify(memory));
}

function startVoice() {
  const rec = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
  rec.lang = "en-US";
  rec.onresult = (e) => {
    document.getElementById("prompt").value = e.results[0][0].transcript;
    execute();
  };
  rec.start();
}

function autoIndexApps(list) {
  registry = list;
  localStorage.setItem("registry", JSON.stringify(registry));
}

const SYSTEM_PROMPT = `
You are a secure enterprise launcher.
Return ONLY JSON:
{
 "dock":["pkg1","pkg2","pkg3","pkg4"],
 "grid":["pkgA","pkgB","pkgC","pkgD","pkgE","pkgF"]
}
`;

(function boot(){
  const saved = localStorage.getItem("layout");
  if (saved) applyLayout(JSON.parse(saved));
  healthCheck();
})();
