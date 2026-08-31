from pathlib import Path
import shutil

ROOT = Path.home() / "cohost"
ROOT.mkdir(parents=True, exist_ok=True)

OUT = ROOT / "looki-cohost-studio.html"
DOWNLOADS = Path("/storage/emulated/0/Download/looki-cohost-studio.html")

html = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Looki — AI Co-Host Studio</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#04050a;--bg-card:rgba(14,18,36,.92);--line:rgba(255,255,255,.075);
  --line2:rgba(255,255,255,.14);--text:#f0f4ff;--dim:#a0acc8;--faint:#63708d;
  --accent:#6ee7ff;--accent2:#a78bfa;--good:#34d399;--warn:#fbbf24;--danger:#f87171;
  --r:18px;--rs:12px;--shadow:0 12px 38px rgba(0,0,0,.42);
  --font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,sans-serif;
  --mono:"SF Mono","Cascadia Code",monospace;
}
html,body{height:100%;background:var(--bg);color:var(--text);font-family:var(--font);overflow:hidden}
body{
  background:
    radial-gradient(ellipse 80% 45% at 20% 25%,rgba(110,231,255,.09),transparent 60%),
    radial-gradient(ellipse 60% 45% at 80% 15%,rgba(167,139,250,.08),transparent 55%),
    radial-gradient(ellipse 50% 50% at 50% 100%,rgba(52,211,153,.045),transparent 60%),
    #04050a;
}
body::after{
  content:"";position:fixed;inset:0;pointer-events:none;opacity:.36;
  background-image:linear-gradient(rgba(255,255,255,.018) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(255,255,255,.018) 1px,transparent 1px);
  background-size:56px 56px;
}
.topbar{
  position:fixed;top:0;left:0;right:0;height:58px;z-index:10;
  background:rgba(4,5,10,.78);backdrop-filter:blur(22px);border-bottom:1px solid var(--line);
  display:flex;align-items:center;justify-content:space-between;padding:0 22px;
}
.brand{display:flex;align-items:center;gap:10px;cursor:pointer}
.logo{
  width:34px;height:34px;border-radius:11px;display:grid;place-items:center;color:#001017;font-weight:900;
  background:linear-gradient(135deg,var(--accent),var(--accent2));box-shadow:0 0 24px rgba(110,231,255,.22)
}
.brand h1{font-size:14px;line-height:1.05}.brand span{font-size:10px;color:var(--faint);letter-spacing:.11em;text-transform:uppercase}
.pager{display:flex;gap:7px;align-items:center;background:rgba(255,255,255,.035);border:1px solid var(--line);padding:5px 9px;border-radius:999px}
.dot{width:7px;height:7px;border-radius:999px;background:var(--faint);cursor:pointer;transition:.25s}
.dot.active{width:23px;background:var(--accent);box-shadow:0 0 16px rgba(110,231,255,.35)}
.navbtn{
  width:34px;height:34px;border-radius:11px;border:1px solid var(--line);background:rgba(255,255,255,.04);
  color:var(--dim);cursor:pointer;font-weight:800
}
.navbtn:hover{border-color:var(--line2);color:var(--text)}
.navbtn:disabled{opacity:.25;cursor:not-allowed}
.progress{position:fixed;top:0;left:0;right:0;height:2px;background:rgba(255,255,255,.06);z-index:20}
#progressFill{height:100%;width:16.66%;background:linear-gradient(90deg,var(--accent),var(--accent2),var(--good));transition:.35s}
.viewport{position:fixed;inset:0;overflow:hidden}
.track{height:100%;display:flex;transition:transform .65s cubic-bezier(.32,.72,0,1);will-change:transform}
.page{width:100vw;height:100%;flex-shrink:0;overflow-y:auto;padding:82px 28px 30px}
.wrap{max-width:1200px;margin:0 auto}
.center{max-width:760px;margin:0 auto;text-align:center;min-height:calc(100vh - 120px);display:flex;flex-direction:column;justify-content:center}
.eyebrow{display:inline-flex;align-items:center;gap:8px;color:var(--accent);font-size:11px;font-weight:800;letter-spacing:.11em;text-transform:uppercase;margin-bottom:16px}
.eyebrow::before{content:"";width:7px;height:7px;border-radius:999px;background:var(--accent);box-shadow:0 0 14px rgba(110,231,255,.6)}
.title-xl{font-size:clamp(40px,6vw,78px);line-height:.94;font-weight:900;letter-spacing:-.05em}
.title-lg{font-size:clamp(30px,4vw,50px);line-height:1;font-weight:900;letter-spacing:-.035em}
.grad{background:linear-gradient(135deg,var(--accent),var(--accent2),var(--good));-webkit-background-clip:text;background-clip:text;color:transparent}
.dim{color:var(--dim)}.faint{color:var(--faint)}
.card{
  background:var(--bg-card);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow);
  transition:.25s
}
.card:hover{border-color:var(--line2)}
.cardx{cursor:pointer}.cardx:hover{transform:translateY(-2px);border-color:rgba(110,231,255,.22)}
.grid2{display:grid;grid-template-columns:1.1fr .9fr;gap:20px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.badge{
  display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border-radius:999px;background:rgba(255,255,255,.045);
  border:1px solid var(--line);font-size:10px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--dim)
}
.accent{background:rgba(110,231,255,.08);border-color:rgba(110,231,255,.18);color:var(--accent)}
.good{background:rgba(52,211,153,.08);border-color:rgba(52,211,153,.18);color:var(--good)}
.warn{background:rgba(251,191,36,.08);border-color:rgba(251,191,36,.18);color:var(--warn)}
.input{
  width:100%;border:1px solid var(--line);background:rgba(255,255,255,.045);color:var(--text);
  border-radius:var(--rs);padding:15px 18px;font-size:15px;outline:0
}
.input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(110,231,255,.08)}
.btn{
  border:0;border-radius:var(--rs);padding:12px 20px;font-weight:800;cursor:pointer;transition:.22s;
  display:inline-flex;align-items:center;justify-content:center;gap:8px
}
.btn-sm{padding:8px 14px;font-size:12px}.primary{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#001017}
.secondary{background:rgba(255,255,255,.07);border:1px solid var(--line);color:var(--text)}
.ghost{background:transparent;color:var(--dim)}
.btn:hover{transform:translateY(-1px)}.btn:disabled{opacity:.4;cursor:not-allowed;transform:none}
.pill{
  padding:7px 13px;border:1px solid var(--line);background:rgba(255,255,255,.04);border-radius:999px;color:var(--dim);
  font-size:12px;font-weight:800;cursor:pointer
}
.pill:hover,.pill.active{border-color:var(--accent);color:var(--accent);background:rgba(110,231,255,.08)}
#camera{
  position:relative;aspect-ratio:16/9;border-radius:var(--r);overflow:hidden;border:1px solid var(--line);
  background:linear-gradient(135deg,#080c18,#121830,#080c18)
}
#camera::before{
  content:"";position:absolute;inset:0;
  background:radial-gradient(circle at 32% 40%,rgba(110,231,255,.08),transparent 42%),
             radial-gradient(circle at 70% 60%,rgba(167,139,250,.06),transparent 38%);
  animation:cam 4s infinite
}
.face{
  position:absolute;width:105px;height:142px;border:2px solid var(--accent);border-radius:13px;top:25%;left:35%;
  box-shadow:0 0 24px rgba(110,231,255,.4),inset 0 0 24px rgba(110,231,255,.05);opacity:0;transition:.4s
}
.face::before{content:"TRACKING";position:absolute;top:-22px;left:50%;transform:translateX(-50%);font-size:9px;color:var(--accent);background:rgba(0,0,0,.55);padding:2px 8px;border-radius:4px;letter-spacing:.1em}
.overlay{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:space-between;padding:14px;pointer-events:none;z-index:2}
.tag{font-size:11px;color:var(--dim);background:rgba(0,0,0,.48);padding:5px 10px;border-radius:8px;border:1px solid rgba(255,255,255,.05);backdrop-filter:blur(8px)}
.msg{padding:10px 14px;border-radius:14px;max-width:88%;font-size:13px;line-height:1.55;border:1px solid var(--line);word-wrap:break-word;animation:up .3s}
.user{justify-self:end;background:rgba(110,231,255,.065);border-color:rgba(110,231,255,.16)}
.ai{justify-self:start;background:rgba(167,139,250,.065);border-color:rgba(167,139,250,.16)}
.sys{justify-self:center;background:rgba(52,211,153,.06);border-color:rgba(52,211,153,.16);color:var(--good);font-size:11px;text-transform:uppercase;letter-spacing:.06em;text-align:center}
@keyframes up{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes cam{0%,100%{opacity:.42}50%{opacity:.86}}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(248,113,113,.35)}50%{box-shadow:0 0 14px 4px rgba(248,113,113,.35)}}
@keyframes tensor{0%,100%{opacity:.2;transform:scale(.84)}50%{opacity:.75;transform:scale(1)}}
@keyframes spin{to{transform:rotate(360deg)}}
@media(max-width:850px){
  .page{padding:75px 14px 20px}.grid2,.grid3{grid-template-columns:1fr}.brand span{display:none}.topbar{padding:0 12px}
  .title-xl{font-size:42px}
}
</style>
</head>
<body>
<div class="progress"><div id="progressFill"></div></div>

<header class="topbar">
  <div class="brand" onclick="goToPage(0)">
    <div class="logo">◉</div>
    <div><h1>Looki</h1><span>AI Co-Host</span></div>
  </div>
  <div class="pager">
    <div class="dot active" onclick="goToPage(0)"></div>
    <div class="dot" onclick="goToPage(1)"></div>
    <div class="dot" onclick="goToPage(2)"></div>
    <div class="dot" onclick="goToPage(3)"></div>
    <div class="dot" onclick="goToPage(4)"></div>
    <div class="dot" onclick="goToPage(5)"></div>
  </div>
  <div style="display:flex;gap:8px">
    <button class="navbtn" id="prevBtn" onclick="prevPage()">←</button>
    <button class="navbtn" id="nextBtn" onclick="nextPage()">→</button>
  </div>
</header>

<div class="viewport">
<div class="track" id="pageTrack">

<section class="page" id="page1">
  <div class="center">
    <div class="eyebrow" style="margin-left:auto;margin-right:auto">Gemma 4 Good — Cactus Track</div>
    <h1 class="title-xl">What will you<br><span class="grad">create</span>?</h1>
    <p class="dim" style="max-width:560px;margin:18px auto 34px;font-size:18px;line-height:1.6">
      Describe your video. Looki builds your shot list, writes your script, and coaches you live — all on-device.
    </p>
    <div style="position:relative;max-width:600px;margin:0 auto 24px;width:100%">
      <input class="input" id="ideaInput" placeholder="e.g., 5-minute review of noise-cancelling headphones" style="padding-right:132px" onkeydown="if(event.key==='Enter')generatePlan()">
      <button class="btn btn-sm primary" id="generateBtn" onclick="generatePlan()" style="position:absolute;right:6px;top:50%;transform:translateY(-50%)">Generate →</button>
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-bottom:42px">
      <button class="pill" onclick="pickIdea(this,'Mechanical keyboard review')">Keyboard review</button>
      <button class="pill" onclick="pickIdea(this,'Tokyo street food tour')">Tokyo food vlog</button>
      <button class="pill" onclick="pickIdea(this,'DSLR photography basics tutorial')">Photo tutorial</button>
      <button class="pill" onclick="pickIdea(this,'15-minute pasta recipe')">Quick recipe</button>
      <button class="pill" onclick="pickIdea(this,'Smart home starter kit unboxing')">Smart home</button>
    </div>
    <div class="grid3">
      <div class="card" style="padding:22px;text-align:center"><div style="font-size:30px">🎙️</div><b>Voice Wake</b><div class="faint" style="font-size:12px">"Looki, co-host this"</div></div>
      <div class="card" style="padding:22px;text-align:center"><div style="font-size:30px">🧠</div><b>Edge AI</b><div class="faint" style="font-size:12px">Local multimodal reasoning</div></div>
      <div class="card" style="padding:22px;text-align:center"><div style="font-size:30px">📦</div><b>Auto Export</b><div class="faint" style="font-size:12px">Chapters, captions, tags</div></div>
    </div>
  </div>
</section>

<section class="page" id="page2">
  <div class="wrap">
    <div class="eyebrow">Production Plan — <span id="planTopic" class="dim">Waiting</span></div>
    <h2 class="title-lg" style="margin-bottom:24px">Your <span class="grad">shot list</span> & script</h2>
    <div class="grid2">
      <div class="card" style="padding:24px">
        <div style="display:flex;justify-content:space-between;margin-bottom:16px">
          <span class="badge accent">🎬 Shot List</span><span class="faint" id="shotMeta" style="font-size:12px">0 shots</span>
        </div>
        <div id="shotList" style="display:grid;gap:9px"></div>
        <div style="margin-top:16px;display:grid;grid-template-columns:1fr 1fr;gap:10px">
          <div class="card" style="padding:14px"><div id="estRuntime" style="font-size:22px;font-weight:900;color:var(--accent)">--</div><div class="faint" style="font-size:11px">Est. runtime</div></div>
          <div class="card" style="padding:14px"><div id="brollTotal" style="font-size:22px;font-weight:900;color:var(--good)">--</div><div class="faint" style="font-size:11px">B-roll shots</div></div>
        </div>
        <div style="margin-top:14px;display:flex;gap:10px">
          <button class="btn btn-sm primary" onclick="goToPage(2)">▶ Enter Studio</button>
          <button class="btn btn-sm secondary" onclick="regeneratePlan()">↻ Regenerate</button>
        </div>
      </div>
      <div class="card" style="padding:24px;display:flex;flex-direction:column">
        <span class="badge">📝 Script Outline</span>
        <div id="scriptBox" style="margin-top:14px;flex:1;padding:16px;border-radius:var(--rs);background:rgba(255,255,255,.025);border:1px solid var(--line);font-size:13px;line-height:1.75;color:var(--dim);overflow:auto;max-height:58vh"></div>
        <div class="faint" style="margin-top:12px;font-size:12px">💡 Click any shot to mark it complete.</div>
      </div>
    </div>
  </div>
</section>

<section class="page" id="page3">
  <div class="wrap">
    <div class="eyebrow">Live Studio — <span id="studioTopic" class="dim">Session</span></div>
    <h2 class="title-lg" style="margin-bottom:20px"><span class="grad">Co-Host</span> Control Center</h2>
    <div class="grid2">
      <div>
        <div id="camera">
          <div class="overlay">
            <div style="display:flex;justify-content:space-between"><span class="tag">🔴 LIVE</span><span class="tag">1080p · 30fps</span></div>
            <div style="display:flex;justify-content:space-between"><span class="tag">Looki Wearable v1.2</span><span class="tag">87% · 2h 14m</span></div>
          </div>
          <div class="face" id="faceBox"></div>
          <div style="position:absolute;inset:0;display:grid;place-items:center;font-size:52px;opacity:.08">📷</div>
        </div>
        <div class="grid3" style="margin-top:12px">
          <div class="card" style="padding:14px;text-align:center"><div id="sceneConf" style="font-size:23px;font-weight:900;color:var(--accent)">--</div><div class="faint" style="font-size:11px">Scene Confidence</div></div>
          <div class="card" style="padding:14px;text-align:center"><div id="brollLive" style="font-size:23px;font-weight:900;color:var(--good)">0/0</div><div class="faint" style="font-size:11px">B-Roll Captured</div></div>
          <div class="card" style="padding:14px;text-align:center"><div id="chapLive" style="font-size:23px;font-weight:900;color:var(--warn)">0/0</div><div class="faint" style="font-size:11px">Chapters Set</div></div>
        </div>
      </div>
      <div>
        <div id="timerDisplay" class="card" style="font-family:var(--mono);font-size:33px;font-weight:900;color:var(--accent);text-align:center;padding:18px;margin-bottom:14px">00:00:00</div>
        <div style="display:grid;gap:9px;margin-bottom:14px">
          <div class="card" id="statusGemma" style="padding:14px;display:flex;gap:12px;align-items:center"><div>🧠</div><div style="flex:1"><b>Gemma 4 Vision</b><div class="faint" id="gemmaStatusText" style="font-size:12px">Ready to analyze</div></div><span id="gemmaBadge" class="badge good">Standby</span></div>
          <div class="card" id="statusBroll" style="padding:14px;display:flex;gap:12px;align-items:center"><div>🎬</div><div style="flex:1"><b>B-Roll Coach</b><div class="faint" id="brollStatusText" style="font-size:12px">Waiting for session</div></div><span id="brollBadge" class="badge">Idle</span></div>
          <div class="card" id="statusChapter" style="padding:14px;display:flex;gap:12px;align-items:center"><div>📊</div><div style="flex:1"><b>Chapter AI</b><div class="faint" id="chapterStatusText" style="font-size:12px">Monitoring off</div></div><span id="chapterBadge" class="badge">Idle</span></div>
          <div class="card" id="statusExport" style="padding:14px;display:flex;gap:12px;align-items:center"><div>📦</div><div style="flex:1"><b>Export Engine</b><div class="faint" id="exportStatusText" style="font-size:12px">Will activate on wrap</div></div><span id="exportBadge" class="badge">Off</span></div>
        </div>
        <div style="display:flex;gap:8px">
          <button class="btn btn-sm primary" id="startBtn" onclick="startSession()" style="flex:1">▶ Start Session</button>
          <button class="btn btn-sm secondary" id="wrapBtn" onclick="wrapSession()" disabled style="flex:1">⏹ Wrap</button>
          <button class="btn btn-sm ghost" onclick="goToPage(3)">💬</button>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="page" id="page4">
  <div class="wrap" style="height:100%;display:flex;flex-direction:column">
    <div class="eyebrow">Live Guidance</div>
    <h2 class="title-lg" style="margin-bottom:16px">Talk to your <span class="grad">co-host</span></h2>
    <div class="grid2" style="flex:1;min-height:0">
      <div class="card" style="padding:20px;display:flex;flex-direction:column;min-height:0">
        <div style="display:flex;justify-content:space-between;margin-bottom:12px"><span class="badge accent">💬 Co-Host Chat</span><span class="faint" id="chatStatus" style="font-size:11px">Offline</span></div>
        <div id="chatMessages" style="flex:1;overflow:auto;display:grid;gap:10px;min-height:260px;padding-right:6px">
          <div class="msg sys">🎬 Session ready. Type to talk to Looki.</div>
        </div>
        <div style="display:flex;gap:8px;margin-top:12px;padding-top:12px;border-top:1px solid var(--line)">
          <input class="input" id="chatInput" placeholder="Ask Looki anything..." style="flex:1;padding:10px 14px" onkeydown="if(event.key==='Enter')sendChat()">
          <button class="btn btn-sm primary" onclick="sendChat()">Send</button>
        </div>
      </div>
      <div class="card" style="padding:20px;display:flex;flex-direction:column;min-height:0">
        <div style="display:flex;justify-content:space-between;margin-bottom:12px"><span class="badge warn">🎯 Live Cues</span><span class="faint" id="cueCount" style="font-size:11px">0 active</span></div>
        <div id="cueStack" style="flex:1;overflow:auto;display:grid;gap:9px">
          <div class="card" style="padding:14px"><span class="badge accent">💡 Tip</span><div style="margin-top:7px;font-weight:800">Start your session</div><div class="faint" style="font-size:12px;line-height:1.55">Hit Start Session to activate live coaching.</div></div>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="page" id="page5">
  <div class="wrap">
    <div class="eyebrow">Gemma 4 Edge Reasoning — All Local</div>
    <h2 class="title-lg" style="margin-bottom:20px">The <span class="grad">brain</span> behind Looki</h2>
    <div class="grid2">
      <div id="layerStack" style="display:grid;gap:9px"></div>
      <div>
        <div class="card" style="padding:20px;margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;margin-bottom:12px"><span class="badge accent">⚡ Tensor Activity</span><span class="faint" style="font-size:11px">26B Q4_K_M</span></div>
          <div style="aspect-ratio:1;border:1px solid var(--line);border-radius:var(--r);position:relative;overflow:hidden;background:radial-gradient(circle at 30% 30%,rgba(110,231,255,.09),transparent 50%),linear-gradient(135deg,rgba(14,18,36,.7),rgba(6,8,16,.95))">
            <div id="tensorGrid" style="position:absolute;inset:16px;display:grid;grid-template-columns:repeat(8,1fr);grid-template-rows:repeat(8,1fr);gap:3px"></div>
            <div class="tag" style="position:absolute;bottom:12px;left:50%;transform:translateX(-50%)">8 tok/s · Snapdragon 8 Gen 3</div>
          </div>
        </div>
        <div class="card" style="padding:18px;margin-bottom:10px"><b>🔒 Privacy Architecture</b><p class="faint" style="font-size:12px;line-height:1.7;margin-top:8px">All inference via llama.cpp with 4-bit quantization. No footage leaves the device. Wake phrase runs on dedicated NPU at &lt;50mW.</p></div>
        <div class="grid3">
          <div class="card" style="padding:14px"><b style="font-size:20px;color:var(--accent)">8 tok/s</b><div class="faint" style="font-size:11px">Inference</div></div>
          <div class="card" style="padding:14px"><b style="font-size:20px;color:var(--good)">&lt;8GB</b><div class="faint" style="font-size:11px">RAM</div></div>
          <div class="card" style="padding:14px"><b style="font-size:20px;color:var(--warn)">100%</b><div class="faint" style="font-size:11px">Offline</div></div>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="page" id="page6">
  <div class="wrap">
    <div class="eyebrow">Export Package — Ready to Publish</div>
    <h2 class="title-lg" style="margin-bottom:20px">Your <span class="grad">ready-to-post</span> bundle</h2>
    <div class="grid2">
      <div class="card" style="padding:24px">
        <div style="display:flex;justify-content:space-between;margin-bottom:16px"><span class="badge accent">📑 Chapter Markers</span><span class="faint" id="chapterCountDisplay" style="font-size:12px">0 markers</span></div>
        <div id="chapterList" style="display:grid;gap:10px"></div>
      </div>
      <div>
        <div class="card" style="padding:24px;margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;margin-bottom:16px"><span class="badge accent">📦 Export Files</span><span class="faint" style="font-size:12px">Generated locally</span></div>
          <div id="fileList" style="display:grid;gap:10px"></div>
          <div style="margin-top:14px"><b>🏷️ SEO Tags</b><div id="tagCloud" style="margin-top:10px;display:flex;flex-wrap:wrap;gap:7px"></div></div>
        </div>
        <div class="card" style="padding:24px;text-align:center">
          <div class="faint" style="font-size:13px">Session Summary</div>
          <div style="font-size:24px;font-weight:900;margin:8px 0 16px"><span id="finalDuration">0:00</span> · <span id="finalBroll" style="color:var(--good)">0</span> cues · <span id="finalChapters" style="color:var(--warn)">0</span> chapters</div>
          <div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap">
            <button class="btn btn-sm primary" onclick="downloadPackage()">⬇ Download Package</button>
            <button class="btn btn-sm secondary" onclick="goToPage(0)">🎬 New Session</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

</div>
</div>

<div id="toastContainer" style="position:fixed;bottom:22px;right:22px;z-index:50;display:grid;gap:8px;pointer-events:none"></div>

<script>
const State={page:0,totalPages:6,session:{active:false,startTime:null,timer:null},stats:{broll:0,chapters:0,duration:0},plan:null,idea:""};

const pageTrack=document.getElementById("pageTrack");
const progressFill=document.getElementById("progressFill");
const prevBtn=document.getElementById("prevBtn");
const nextBtn=document.getElementById("nextBtn");

function escapeHTML(v){return String(v).replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));}

function updateNav(){
  pageTrack.style.transform=`translateX(-${State.page*100}vw)`;
  progressFill.style.width=`${((State.page+1)/State.totalPages)*100}%`;
  prevBtn.disabled=State.page===0;nextBtn.disabled=State.page===State.totalPages-1;
  document.querySelectorAll(".dot").forEach((d,i)=>d.classList.toggle("active",i===State.page));
}
function goToPage(n){if(n>=0&&n<State.totalPages){State.page=n;updateNav();}}
function nextPage(){goToPage(State.page+1)} function prevPage(){goToPage(State.page-1)}
document.addEventListener("keydown",e=>{
  const tag=(e.target&&e.target.tagName)?e.target.tagName.toUpperCase():"";
  if(tag==="INPUT"||tag==="TEXTAREA"||tag==="SELECT"||e.target.isContentEditable)return;
  if(e.key==="ArrowRight"||e.key===" "){e.preventDefault();nextPage()}
  if(e.key==="ArrowLeft"){e.preventDefault();prevPage()}
});
let sx=0,sy=0;
document.addEventListener("touchstart",e=>{sx=e.changedTouches[0].screenX;sy=e.changedTouches[0].screenY},{passive:true});
document.addEventListener("touchend",e=>{const dx=sx-e.changedTouches[0].screenX,dy=sy-e.changedTouches[0].screenY;if(Math.abs(dx)>65&&Math.abs(dx)>Math.abs(dy))dx>0?nextPage():prevPage()},{passive:true});

function toast(message,type="info"){
  const c=document.getElementById("toastContainer"),el=document.createElement("div");
  const color={info:"var(--accent)",success:"var(--good)",warn:"var(--warn)",error:"var(--danger)"}[type]||"var(--accent)";
  el.style.cssText=`padding:12px 18px;border-radius:12px;background:var(--bg-card);border:1px solid ${color};color:${color};font-size:13px;font-weight:800;box-shadow:var(--shadow);pointer-events:auto;transition:.3s`;
  el.textContent=message;c.appendChild(el);setTimeout(()=>{el.style.opacity="0";el.style.transform="translateY(10px)";setTimeout(()=>el.remove(),300)},2800);
}

const Templates={
 keyboard:{topic:"Mechanical Keyboard Review",runtime:"6:00",broll:6,
  shots:["Unboxing & First Look","Build Quality Close-Up","Typing Sound Test","RGB Lighting Demo","Gaming Performance","Final Verdict"].map((t,i)=>({n:i+1,title:t,desc:["Open packaging and first reaction","Macro keycaps, switches, frame","ASMR typing with switch comparison","Cycle lighting modes in dim room","Show latency and rollover","Pros, cons, price, call-to-action"][i],dur:["0:45","1:00","1:30","0:45","1:00","1:00"][i]})),
  script:"<b>OPEN</b><br>[CU: Box front] Hook the viewer with the core promise.<br><br><b>BUILD</b><br>[Macro] Show texture, switch feel, and frame quality.<br><br><b>SOUND</b><br>[ASMR mic] Capture typing test without music.<br><br><b>VERDICT</b><br>[Hero shot] Price, best audience, final recommendation.",
  tags:["#mechanicalkeyboard","#keychron","#typingsounds","#gaming","#techreview","#unboxing"]},
 tokyo:{topic:"Tokyo Street Food Tour",runtime:"5:30",broll:6,
  shots:["Shibuya Crossing Intro","Takoyaki Stand","Ramen Shop","Taiyaki Making","Night Market Walk","Outro at Senso-ji"].map((t,i)=>({n:i+1,title:t,desc:["Wide crossing shot","Batter, flip, sauce drizzle","Steam, noodles, first bite","Mold pour and reveal","Neon tracking shot","Temple backdrop outro"][i],dur:["0:30","1:00","1:30","0:45","1:00","0:45"][i]})),
  script:"<b>OPEN</b><br>[Wide: Shibuya] Establish the city energy.<br><br><b>FOOD</b><br>[Close-ups] Show process before taste reaction.<br><br><b>NIGHT</b><br>[Tracking] Use neon ambience as transition.",
  tags:["#tokyo","#streetfood","#japantravel","#foodvlog","#takoyaki","#ramen"]},
 dslr:{topic:"DSLR Photography Basics",runtime:"7:30",broll:6,
  shots:["Camera Body Overview","Aperture Demo","Shutter Speed Test","ISO Comparison","Manual Mode Walkthrough","Final Photo Showcase"].map((t,i)=>({n:i+1,title:t,desc:["Buttons and ports","Depth-of-field comparison","Freeze vs blur","Noise levels","Triangle live demo","Gallery montage"][i],dur:["1:00","1:30","1:30","1:00","1:30","1:00"][i]})),
  script:"<b>INTRO</b><br>Explain manual mode in one sentence.<br><br><b>TRIANGLE</b><br>Aperture = depth, shutter = motion, ISO = sensitivity.<br><br><b>SHOWCASE</b><br>End with proof shots.",
  tags:["#photography","#dslr","#tutorial","#manualmode","#beginner","#photo"]},
 pasta:{topic:"15-Minute Pasta Recipe",runtime:"3:45",broll:6,
  shots:["Ingredients Flat Lay","Garlic & Oil Sizzle","Pasta Boil","Toss & Emulsify","Plating","First Bite"].map((t,i)=>({n:i+1,title:t,desc:["Overhead mise en place","Close-up sizzle","Pasta drop","Sauce toss","Twirl and garnish","Reaction"][i],dur:["0:30","0:30","0:30","1:00","0:45","0:30"][i]})),
  script:"<b>PREP</b><br>Show every ingredient first.<br><br><b>COOK</b><br>Use close sound-rich food shots.<br><br><b>PLATE</b><br>Twirl high, garnish, first bite.",
  tags:["#cooking","#pasta","#quickrecipe","#food","#15minutemeals"]},
 smarthome:{topic:"Smart Home Starter Kit Unboxing",runtime:"6:00",broll:6,
  shots:["Box Reveal","Hub Setup","Sensor Placement","Automation Demo","Voice Control","Price Breakdown"].map((t,i)=>({n:i+1,title:t,desc:["Seal peel and contents","App pairing","Mount sensors","Lights on/off","Goodnight routine","Kit vs individual cost"][i],dur:["0:45","1:00","1:30","1:00","0:45","1:00"][i]})),
  script:"<b>UNBOX</b><br>Show the kit and value promise.<br><br><b>SETUP</b><br>Pair and mount devices.<br><br><b>DEMO</b><br>Show automation and voice control.",
  tags:["#smarthome","#unboxing","#homeautomation","#iot","#techreview"]}
};

function pickIdea(el,text){document.getElementById("ideaInput").value=text;document.querySelectorAll(".pill").forEach(p=>p.classList.remove("active"));el.classList.add("active")}
function detectTemplate(idea){
  const x=idea.toLowerCase();
  if(x.includes("tokyo")||x.includes("japan")||x.includes("food tour"))return"tokyo";
  if(x.includes("dslr")||x.includes("camera")||x.includes("photo"))return"dslr";
  if(x.includes("pasta")||x.includes("recipe")||x.includes("cook"))return"pasta";
  if(x.includes("smart")||x.includes("home")||x.includes("iot"))return"smarthome";
  return"keyboard";
}
function generatePlan(){
  const input=document.getElementById("ideaInput"),btn=document.getElementById("generateBtn"),idea=input.value.trim();
  if(!idea){input.focus();toast("Enter a video idea first","warn");return}
  State.idea=idea;btn.disabled=true;const old=btn.innerHTML;btn.innerHTML='<span style="display:inline-block;animation:spin 1s linear infinite">⟳</span> Analyzing';
  setTimeout(()=>{const key=detectTemplate(idea);State.plan=JSON.parse(JSON.stringify(Templates[key]));State.plan.topic=idea;renderPlan();btn.disabled=false;btn.innerHTML=old;toast("Production plan generated","success");goToPage(1)},550);
}
function regeneratePlan(){toast("Regenerating plan","info");generatePlan()}

function renderPlan(){
  const p=State.plan;if(!p)return;
  document.getElementById("planTopic").textContent=p.topic;document.getElementById("studioTopic").textContent=p.topic;
  document.getElementById("estRuntime").textContent=p.runtime;document.getElementById("brollTotal").textContent=p.broll;
  document.getElementById("shotMeta").textContent=`${p.shots.length} shots · Est. ${p.runtime}`;
  document.getElementById("shotList").innerHTML=p.shots.map(s=>`
    <div class="card cardx" style="padding:14px;display:grid;grid-template-columns:38px 1fr 58px;gap:12px;align-items:center" onclick="this.style.opacity=this.style.opacity==='0.45'?'1':'0.45'">
      <div style="width:32px;height:32px;border-radius:10px;display:grid;place-items:center;background:linear-gradient(135deg,var(--accent),var(--accent2));color:#001017;font-weight:900">${s.n}</div>
      <div><b style="font-size:14px">${escapeHTML(s.title)}</b><div class="faint" style="font-size:12px">${escapeHTML(s.desc)}</div></div>
      <div style="text-align:right;color:var(--accent);font-weight:900;font-size:13px">${s.dur}</div>
    </div>`).join("");
  document.getElementById("scriptBox").innerHTML=p.script;
  document.getElementById("chapterList").innerHTML=p.shots.map((s,i)=>`<div class="card" style="padding:14px"><div style="color:var(--accent);font-weight:900;font-size:12px">0${i}:00 — 0${i+1}:00</div><b>${escapeHTML(s.title)}</b><div class="faint" style="font-size:12px">${escapeHTML(s.desc)}</div></div>`).join("");
  document.getElementById("tagCloud").innerHTML=p.tags.map(t=>`<span class="badge accent">${escapeHTML(t)}</span>`).join("");
  document.getElementById("sceneConf").textContent="--";document.getElementById("brollLive").textContent=`0/${p.broll}`;document.getElementById("chapLive").textContent=`0/${p.shots.length}`;
  document.getElementById("fileList").innerHTML=[
    "📝 auto_captions.srt — <span id='captionLines'>0</span> lines",
    "📄 transcript.txt — <span id='wordCount'>0</span> words",
    "🎬 session.edl — DaVinci Resolve",
    "🎞️ session.xml — Final Cut Pro",
    "🖼️ thumb_01.jpg — Score: <span id='thumb1'>0</span>",
    "🖼️ thumb_02.jpg — Score: <span id='thumb2'>0</span>",
    "🖼️ thumb_03.jpg — Score: <span id='thumb3'>0</span>"
  ].map(x=>`<div class="card" style="padding:11px;font-size:13px;color:var(--dim)">${x}</div>`).join("");
}

function setStatus(id,state,color,text){
  const badge=document.getElementById(id+"Badge"),status=document.getElementById(id+"StatusText"),card=document.getElementById("status"+id.charAt(0).toUpperCase()+id.slice(1));
  badge.textContent=state;badge.className="badge "+(color==="good"?"good":color==="warn"?"warn":"");
  status.textContent=text;
  if(color==="good"){card.style.borderColor="rgba(52,211,153,.23)";card.style.background="rgba(52,211,153,.035)"}
  else if(color==="warn"){card.style.borderColor="rgba(251,191,36,.23)";card.style.background="rgba(251,191,36,.035)"}
}
function startSession(){
  if(State.session.active)return;if(!State.plan){document.getElementById("ideaInput").value="Mechanical keyboard review";generatePlan();toast("Plan created first — enter studio again","warn");return}
  State.session.active=true;State.session.startTime=Date.now();State.stats={broll:0,chapters:0,duration:0};
  document.getElementById("startBtn").disabled=true;document.getElementById("startBtn").innerHTML="<span style='width:8px;height:8px;border-radius:999px;background:var(--danger);animation:pulse 1.4s infinite'></span> LIVE";
  document.getElementById("wrapBtn").disabled=false;document.getElementById("chatStatus").textContent="Online";document.getElementById("faceBox").style.opacity="1";
  setStatus("gemma","On","good","Analyzing scene composition");setStatus("broll","On","good","Scanning B-roll opportunities");setStatus("chapter","On","good","Monitoring topic shifts");setStatus("export","Wait","warn","Will activate on wrap");
  addChat("sys","🎬 Session LIVE. Looki is analyzing your feed.");toast("Session started","success");
  State.session.timer=setInterval(()=>{const e=Math.floor((Date.now()-State.session.startTime)/1000);State.stats.duration=e;
    const h=String(Math.floor(e/3600)).padStart(2,"0"),m=String(Math.floor((e%3600)/60)).padStart(2,"0"),s=String(e%60).padStart(2,"0");
    document.getElementById("timerDisplay").textContent=`${h}:${m}:${s}`;document.getElementById("sceneConf").textContent=(88+Math.floor(Math.random()*10))+"%";simulateCue(e);
  },1000);
}
function simulateCue(e){
  const cues=[
    [5,"tip","Lighting Check","Key light is slightly warm. Balance or use it stylistically."],
    [12,"broll","B-Roll Cue","Capture a close-up detail shot now."],
    [20,"chapter","Chapter Set","Topic shift detected. Marked introduction."],
    [30,"tip","Framing","Eyes should land near upper third."],
    [40,"broll","B-Roll Cue","Cut to texture or product movement shot."],
    [55,"chapter","Chapter Set","New segment detected."],
    [70,"broll","B-Roll Cue","Reaction shot recommended."],
    [90,"tip","Pacing","Add a visual break before continuing."]
  ];
  const c=cues.find(x=>x[0]===e);if(!c)return;addCue(c[1],c[2],c[3]);if(c[1]==="broll")State.stats.broll++;if(c[1]==="chapter")State.stats.chapters++;updateStats();
}
function updateStats(){const p=State.plan;document.getElementById("brollLive").textContent=`${State.stats.broll}/${p?p.broll:6}`;document.getElementById("chapLive").textContent=`${State.stats.chapters}/${p?p.shots.length:6}`}
function wrapSession(){
  if(!State.session.active)return;State.session.active=false;clearInterval(State.session.timer);
  document.getElementById("startBtn").disabled=false;document.getElementById("startBtn").textContent="▶ Start Session";document.getElementById("wrapBtn").disabled=true;document.getElementById("chatStatus").textContent="Offline";document.getElementById("faceBox").style.opacity="0";
  setStatus("gemma","Done","good","Analysis complete");setStatus("broll","Done","good",`${State.stats.broll} cues captured`);setStatus("chapter","Done","good",`${State.stats.chapters} chapters set`);setStatus("export","On","good","Export package ready");
  const e=State.stats.duration,d=`${Math.floor(e/60)}:${String(e%60).padStart(2,"0")}`;
  document.getElementById("finalDuration").textContent=d;document.getElementById("finalBroll").textContent=State.stats.broll;document.getElementById("finalChapters").textContent=State.stats.chapters;
  document.getElementById("captionLines").textContent=Math.floor(e/1.5);document.getElementById("wordCount").textContent=Math.floor(e*2.3);
  ["thumb1","thumb2","thumb3"].forEach((id,i)=>document.getElementById(id).textContent=80+i+Math.floor(Math.random()*15));
  document.getElementById("chapterCountDisplay").textContent=`${State.stats.chapters} markers`;
  addChat("sys",`✅ Session wrapped. ${d} filmed. Export ready.`);addCue("tip","Export Ready","Captions, chapters, edit list, and tags generated.");toast("Session complete","success");setTimeout(()=>goToPage(5),700);
}

function addChat(who,text){
  const c=document.getElementById("chatMessages"),d=document.createElement("div");
  d.className="msg "+(who==="user"?"user":who==="ai"?"ai":"sys");
  if(who==="user")d.innerHTML=`<div class="faint" style="font-size:10px;margin-bottom:3px">You</div>${escapeHTML(text)}`;
  else if(who==="ai")d.innerHTML=`<div class="faint" style="font-size:10px;margin-bottom:3px">Looki</div>${text}`;
  else d.textContent=text;
  c.appendChild(d);c.scrollTop=c.scrollHeight;
}
function sendChat(){
  const input=document.getElementById("chatInput"),text=input.value.trim();if(!text)return;addChat("user",text);input.value="";
  setTimeout(()=>{const l=text.toLowerCase();let r;
    if(l.includes("b-roll")||l.includes("broll"))r="🎬 <b>B-Roll:</b> Capture macro texture, then a wide context shot.";
    else if(l.includes("light")||l.includes("exposure"))r="💡 <b>Lighting:</b> Raise key light slightly and watch mixed color temperature.";
    else if(l.includes("script")||l.includes("say"))r="📝 <b>Script:</b> Try: “Here are three things viewers should know before buying.”";
    else if(l.includes("wrap")||l.includes("done"))r=`✅ <b>Ready:</b> ${State.stats.broll} B-roll cues and ${State.stats.chapters} chapters captured.`;
    else r="🧠 <b>Gemma analysis:</b> Scene, pacing, and audio are being monitored locally. Keep going.";
    addChat("ai",r);
  },350);
}
function addCue(type,title,text){
  const s=document.getElementById("cueStack"),d=document.createElement("div");
  const cls=type==="broll"?"warn":type==="chapter"?"good":"accent";
  const label=type==="broll"?"🎬 B-Roll":type==="chapter"?"📑 Chapter":"💡 Tip";
  d.className="card";d.style.cssText="padding:14px;animation:up .3s";
  d.innerHTML=`<span class="badge ${cls}">${label}</span><div style="margin-top:7px;font-weight:900">${escapeHTML(title)}</div><div class="faint" style="font-size:12px;line-height:1.55">${escapeHTML(text)}</div>`;
  s.insertBefore(d,s.firstChild);if(s.children.length>8)s.lastChild.remove();document.getElementById("cueCount").textContent=`${s.children.length} active`;
}
function downloadPackage(){
  const pkg={session:State.idea||"Untitled",duration:document.getElementById("timerDisplay").textContent,broll:State.stats.broll,chapters:State.stats.chapters,tags:State.plan?State.plan.tags:[],generatedAt:new Date().toISOString(),engine:"Gemma 4 local simulation",privacy:"100% local demo"};
  const blob=new Blob([JSON.stringify(pkg,null,2)],{type:"application/json"}),url=URL.createObjectURL(blob),a=document.createElement("a");
  a.href=url;a.download=`looki_export_${Date.now()}.json`;a.click();URL.revokeObjectURL(url);toast("Package downloaded","success");
}

function init(){
  updateNav();
  const layers=["Multimodal Input Encoder","Intent Classifier","Scene Quality Analyzer","B-Roll Engine","Chapter Detector","Export Generator"];
  document.getElementById("layerStack").innerHTML=layers.map((x,i)=>`<div class="card cardx" style="padding:16px;display:grid;grid-template-columns:42px 1fr auto;gap:12px;align-items:center"><div style="width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,var(--accent),var(--accent2));display:grid;place-items:center;color:#001017;font-weight:900">${String(i+1).padStart(2,"0")}</div><div><b>${x}</b><div class="faint" style="font-size:12px">Runs locally with deterministic export state.</div></div><span class="badge good">● Local</span></div>`).join("");
  const tg=document.getElementById("tensorGrid");for(let i=0;i<64;i++){const c=document.createElement("div");c.style.cssText=`border-radius:4px;background:${i%5===0?"rgba(52,211,153,.08)":i%3===0?"rgba(167,139,250,.09)":"rgba(110,231,255,.07)"};animation:tensor ${2+Math.random()}s ease-in-out infinite;animation-delay:${Math.random()*2}s`;tg.appendChild(c);}
  State.plan=JSON.parse(JSON.stringify(Templates.keyboard));State.idea="Mechanical keyboard review";renderPlan();
}
init();
</script>
</body>
</html>
"""

OUT.write_text(html, encoding="utf-8")

full = OUT.read_text(encoding="utf-8")
checks = {
    "DOCTYPE": full.lstrip().startswith("<!DOCTYPE"),
    "Closing HTML": full.rstrip().endswith("</html>"),
    "6 Pages": all(('id="page' + str(i) + '"') in full for i in range(1, 7)),
    "JS Core": "const State" in full,
    "Chat": "function sendChat()" in full,
    "Timer": "session.timer" in full,
    "Export DL": "downloadPackage" in full,
    "Toast": "function toast(" in full,
    "HTML Escape Guard": "function escapeHTML" in full,
    "No /mnt/agents": "/mnt/agents" not in full,
}

print(f"✅ BUILT: {OUT}")
print(f"✅ SIZE: {len(full):,} characters")
print()
print("Validation:")
for name, ok in checks.items():
    print(f"  {'✅' if ok else '❌'} {name}")

if not all(checks.values()):
    raise SystemExit("❌ Build validation failed.")

try:
    if DOWNLOADS.parent.exists():
        shutil.copy2(OUT, DOWNLOADS)
        print()
        print(f"✅ COPIED TO DOWNLOADS: {DOWNLOADS}")
except Exception as e:
    print()
    print(f"⚠️ Could not copy to Downloads: {e}")
    print("Run: termux-setup-storage")
    print(f"Then: cp {OUT} {DOWNLOADS}")

print()
print("✅ READY")
print(f"Open local: {OUT}")
print(f"Open Android Downloads: {DOWNLOADS}")
