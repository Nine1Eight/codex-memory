
import hashlib
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

DEFAULT_ROLE = "vault"
DEFAULT_PEERS = "https://nine1eight-gladiator-ai-colosseum-arena.hf.space,https://nine1eight-gladiator-ai-colosseum-leaderboard.hf.space"

APP_ROLE = os.getenv("SPACE_ROLE", DEFAULT_ROLE)
PUBLIC_SPACE_NAME = os.getenv("PUBLIC_SPACE_NAME", "gladiator-ai-colosseum-vault")
FEDERATION_PEERS = [
    x.strip().rstrip("/")
    for x in os.getenv("FEDERATION_PEERS", DEFAULT_PEERS).split(",")
    if x.strip()
]
FEDERATION_TOKEN = os.getenv("FEDERATION_TOKEN", "")
STORAGE_DIR = Path(os.getenv("APP_STORAGE_DIR", "/data"))
try:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    STORAGE_DIR = Path(".data")
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = STORAGE_DIR / f"gladiator_{APP_ROLE}.sqlite3"

app = FastAPI(title=f"Gladiator AI Colosseum — {APP_ROLE}", version="1.0.1")

ARENAS = {
    "exactly": {
        "name": "EXACTLY PROTOCOL",
        "company": "Exactly Protocol",
        "type": "Fixed-Rate Lending",
        "chain": "Optimism",
        "platform": "Sherlock",
        "bounty": "$500,000",
        "difficulty": "ENTRY",
        "description": "Authorized sandbox replica only. ERC-4626 vaults, interest models, liquidation engine.",
    },
    "yearn": {
        "name": "YEARN FINANCE v3",
        "company": "Yearn Finance",
        "type": "Yield Aggregation",
        "chain": "Multi-chain",
        "platform": "Sherlock",
        "bounty": "$200,000",
        "difficulty": "ENTRY",
        "description": "Authorized sandbox replica only. Vault logic, strategy contracts, deposit/withdraw flow.",
    },
    "sentiment": {
        "name": "SENTIMENT V2",
        "company": "Sentiment",
        "type": "Leveraged Lending",
        "chain": "Multi-chain",
        "platform": "Sherlock",
        "bounty": "$150,000",
        "difficulty": "NOVICE",
        "description": "Authorized sandbox replica only. SuperPool architecture, risk engine, cross-collateral.",
    },
}

def now() -> int:
    return int(time.time())

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS players (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                last_seen INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS matches (
                id TEXT PRIMARY KEY,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                arena_key TEXT NOT NULL,
                arena_name TEXT NOT NULL,
                role_origin TEXT NOT NULL,
                status TEXT NOT NULL,
                winner TEXT,
                player_score INTEGER DEFAULT 0,
                opponent_score INTEGER DEFAULT 0,
                trace_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                match_id TEXT NOT NULL,
                player_id TEXT,
                kind TEXT NOT NULL,
                payload TEXT NOT NULL,
                event_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_matches_player ON matches(player_id);
            CREATE INDEX IF NOT EXISTS idx_events_match ON events(match_id);
            """
        )

init_db()

def stable_hash(obj: Any) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()

def db_insert_event(match_id: str, player_id: Optional[str], kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    item = {
        "match_id": match_id,
        "player_id": player_id,
        "kind": kind,
        "payload": payload,
        "created_at": now(),
        "origin": PUBLIC_SPACE_NAME,
        "role": APP_ROLE,
    }
    event_id = str(uuid.uuid4())
    event_hash = stable_hash(item)
    with connect() as con:
        con.execute(
            "INSERT INTO events(id, match_id, player_id, kind, payload, event_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (event_id, match_id, player_id, kind, json.dumps(payload), event_hash, item["created_at"]),
        )
    item["id"] = event_id
    item["event_hash"] = event_hash
    return item

async def federate_event(event: Dict[str, Any]):
    if not FEDERATION_TOKEN or not FEDERATION_PEERS:
        return
    headers = {"x-federation-token": FEDERATION_TOKEN}
    async with httpx.AsyncClient(timeout=8) as client:
        for peer in FEDERATION_PEERS:
            try:
                await client.post(f"{peer}/api/federation/event", json=event, headers=headers)
            except Exception:
                pass

class StartMatch(BaseModel):
    player_name: str = Field(default="NEUROVOID-7", max_length=64)
    arena_key: str = Field(default="exactly")

class MatchEvent(BaseModel):
    match_id: str
    player_id: Optional[str] = None
    kind: str
    payload: Dict[str, Any] = Field(default_factory=dict)

class FinishMatch(BaseModel):
    match_id: str
    winner: str = Field(pattern="^(player|opponent)$")
    player_score: int = 0
    opponent_score: int = 0

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "role": APP_ROLE,
        "space": PUBLIC_SPACE_NAME,
        "peers": FEDERATION_PEERS,
        "db": str(DB_PATH),
        "time": now(),
    }

@app.post("/api/match/start")
async def start_match(req: StartMatch):
    arena = ARENAS.get(req.arena_key, ARENAS["exactly"])
    player_id = stable_hash({"name": req.player_name.strip() or "NEUROVOID-7"})[:16]
    match_id = str(uuid.uuid4())
    created = now()
    trace_seed = {
        "match_id": match_id,
        "player_id": player_id,
        "arena": req.arena_key,
        "created_at": created,
        "role_origin": APP_ROLE,
    }
    trace_hash = stable_hash(trace_seed)

    with connect() as con:
        con.execute(
            "INSERT OR REPLACE INTO players(id, name, created_at, last_seen) VALUES (?, ?, COALESCE((SELECT created_at FROM players WHERE id=?), ?), ?)",
            (player_id, req.player_name, player_id, created, created),
        )
        con.execute(
            """INSERT INTO matches(
                id, player_id, player_name, arena_key, arena_name, role_origin,
                status, winner, player_score, opponent_score, trace_hash, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                match_id,
                player_id,
                req.player_name,
                req.arena_key,
                arena["name"],
                APP_ROLE,
                "active",
                None,
                0,
                0,
                trace_hash,
                created,
                created,
            ),
        )

    event = db_insert_event(match_id, player_id, "match_started", {"arena": arena, "trace_hash": trace_hash})
    await federate_event(event)
    return {"match_id": match_id, "player_id": player_id, "arena": arena, "trace_hash": trace_hash}

@app.post("/api/match/event")
async def add_event(req: MatchEvent):
    event = db_insert_event(req.match_id, req.player_id, req.kind, req.payload)
    await federate_event(event)
    return event

@app.post("/api/match/finish")
async def finish_match(req: FinishMatch):
    updated = now()
    with connect() as con:
        row = con.execute("SELECT * FROM matches WHERE id=?", (req.match_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="match not found")
        con.execute(
            "UPDATE matches SET status='finished', winner=?, player_score=?, opponent_score=?, updated_at=? WHERE id=?",
            (req.winner, req.player_score, req.opponent_score, updated, req.match_id),
        )
        player_id = row["player_id"]

    event = db_insert_event(
        req.match_id,
        player_id,
        "match_finished",
        {"winner": req.winner, "player_score": req.player_score, "opponent_score": req.opponent_score},
    )
    await federate_event(event)
    return {"ok": True, "event": event}

@app.post("/api/federation/event")
def inbound_federation_event(event: Dict[str, Any], x_federation_token: Optional[str] = Header(default=None)):
    if FEDERATION_TOKEN and x_federation_token != FEDERATION_TOKEN:
        raise HTTPException(status_code=403, detail="bad federation token")

    match_id = str(event.get("match_id", "external"))
    player_id = event.get("player_id")
    kind = "federated_" + str(event.get("kind", "event"))
    payload = {"source_event": event}

    saved = db_insert_event(match_id, player_id, kind, payload)
    return {"ok": True, "saved": saved["id"]}

@app.get("/api/leaderboard")
def leaderboard():
    with connect() as con:
        rows = con.execute(
            """
            SELECT player_id, player_name,
                   COUNT(*) AS matches,
                   SUM(CASE WHEN winner='player' THEN 1 ELSE 0 END) AS wins,
                   MAX(player_score) AS best_score,
                   MAX(updated_at) AS last_seen
            FROM matches
            GROUP BY player_id, player_name
            ORDER BY wins DESC, best_score DESC, last_seen DESC
            LIMIT 50
            """
        ).fetchall()
    return [dict(r) for r in rows]

@app.get("/api/vault")
def vault():
    with connect() as con:
        rows = con.execute(
            """
            SELECT id, player_name, arena_name, winner, player_score, opponent_score, trace_hash, updated_at
            FROM matches
            WHERE status='finished'
            ORDER BY updated_at DESC
            LIMIT 100
            """
        ).fetchall()
    return [dict(r) for r in rows]

@app.get("/api/report/{match_id}")
def report(match_id: str):
    with connect() as con:
        match = con.execute("SELECT * FROM matches WHERE id=?", (match_id,)).fetchone()
        events = con.execute("SELECT * FROM events WHERE match_id=? ORDER BY created_at ASC", (match_id,)).fetchall()
    if not match:
        raise HTTPException(status_code=404, detail="match not found")
    return {
        "match": dict(match),
        "events": [dict(e) for e in events],
        "report_hash": stable_hash({"match": dict(match), "events": [dict(e) for e in events]}),
        "scope_notice": "Authorized sandbox traces only. Do not use this report as instruction to target live systems without written authorization.",
    }

@app.get("/", response_class=HTMLResponse)
def index():
    role = APP_ROLE
    arena_url = os.getenv("ARENA_SPACE_URL", "")
    vault_url = os.getenv("VAULT_SPACE_URL", "")
    leaderboard_url = os.getenv("LEADERBOARD_SPACE_URL", "")

    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gladiator AI Colosseum — {role}</title>
<style>
:root {{
  --bg:#09090f; --card:#12121b; --line:#2a2a3a; --text:#e8e8ef;
  --dim:#8b8b99; --green:#00ff9d; --red:#ff0044; --gold:#ffaa00; --blue:#4488ff;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:radial-gradient(circle at top,#151522,#09090f 55%); color:var(--text); font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
header {{ border-bottom:1px solid var(--line); padding:16px; display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; background:#0b0b12ee; position:sticky; top:0; }}
.logo {{ color:var(--green); font-weight:900; letter-spacing:1px; }}
.badge {{ border:1px solid var(--gold); color:var(--gold); padding:4px 8px; border-radius:999px; }}
main {{ max-width:1180px; margin:0 auto; padding:18px; display:grid; grid-template-columns:1.1fr .9fr; gap:16px; }}
.card {{ background:linear-gradient(180deg,#141420,#0f0f17); border:1px solid var(--line); border-radius:16px; padding:16px; box-shadow:0 12px 40px #0008; }}
h1,h2,h3 {{ margin:0 0 12px; }}
button,select,input {{ background:#0a0a10; color:var(--text); border:1px solid var(--line); padding:11px; border-radius:10px; font-family:inherit; }}
button {{ cursor:pointer; text-transform:uppercase; letter-spacing:.08em; }}
button.primary {{ border-color:var(--green); color:var(--green); }}
button.danger {{ border-color:var(--red); color:var(--red); }}
.grid {{ display:grid; grid-template-columns:repeat(6,1fr); gap:7px; margin:14px 0; }}
.cell {{ aspect-ratio:1; border:1px solid #33334a; background:#191927; display:flex; align-items:center; justify-content:center; border-radius:8px; cursor:pointer; }}
.cell.sel {{ border-color:var(--green); color:var(--green); box-shadow:0 0 16px #00ff9d55; }}
.row {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin:10px 0; }}
.bar {{ height:22px; border:1px solid var(--line); background:#07070c; border-radius:99px; overflow:hidden; }}
.fill {{ height:100%; width:0%; transition:.25s; background:linear-gradient(90deg,var(--green),#00aa66); }}
.fill.red {{ background:linear-gradient(90deg,var(--red),#ff5588); }}
pre {{ white-space:pre-wrap; max-height:380px; overflow:auto; background:#08080d; border:1px solid var(--line); border-radius:12px; padding:12px; }}
a {{ color:var(--blue); }}
@media(max-width:900px) {{ main {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<header>
  <div><div class="logo">⚔️ Gladiator AI Colosseum</div><div style="color:var(--dim)">Space role: {role} • {PUBLIC_SPACE_NAME}</div></div>
  <div class="row">
    <span class="badge">multi-space federation</span>
    <span class="badge">sandbox authorized</span>
  </div>
</header>
<main>
<section class="card">
  <h2>Arena Console</h2>
  <div class="row">
    <input id="playerName" value="NEUROVOID-7" placeholder="player / agent name">
    <select id="arena">
      <option value="exactly">Exactly Protocol — $500,000</option>
      <option value="yearn">Yearn Finance v3 — $200,000</option>
      <option value="sentiment">Sentiment V2 — $150,000</option>
    </select>
    <button class="primary" onclick="startMatch()">Start Match</button>
  </div>

  <div class="row">
    <div style="flex:1">
      <div>Player Progress: <span id="pScore">0</span>%</div>
      <div class="bar"><div class="fill" id="pFill"></div></div>
    </div>
    <div style="flex:1">
      <div>Opponent Progress: <span id="oScore">0</span>%</div>
      <div class="bar"><div class="fill red" id="oFill"></div></div>
    </div>
  </div>

  <h3>Target Sequence</h3>
  <div id="target" class="row"></div>

  <h3>Hex Grid</h3>
  <div id="grid" class="grid"></div>

  <div class="row">
    <button onclick="clearBuffer()">Clear Buffer</button>
    <button class="primary" onclick="execute()">Execute Sequence</button>
    <button class="danger" onclick="finish('opponent')">Forfeit</button>
  </div>

  <h3>Trace</h3>
  <pre id="trace">waiting...</pre>
</section>

<section class="card">
  <h2>Federation Nodes</h2>
  <pre id="health">loading...</pre>
  <div class="row">
    <button onclick="loadLeaderboard()">Load Leaderboard</button>
    <button onclick="loadVault()">Load Vault</button>
  </div>
  <pre id="side">ready</pre>

  <h3>Expected URLs</h3>
  <pre>Arena: {arena_url}
Vault: {vault_url}
Leaderboard: {leaderboard_url}</pre>
</section>
</main>

<script>
let matchId=null, playerId=null, p=0, o=0, buffer=[], selected=[];
const hex="0123456789ABCDEF";
let target=[]; let grid=[];

function byId(x){{return document.getElementById(x)}}
function log(x){{ byId("trace").textContent = JSON.stringify(x,null,2) + "\\n\\n" + byId("trace").textContent; }}
function byte(){{return hex[Math.floor(Math.random()*16)] + hex[Math.floor(Math.random()*16)]}}

function initGrid(){{
  target = Array.from({{length:5}}, byte);
  grid = Array.from({{length:36}}, byte);
  byId("target").innerHTML = target.map(x=>`<button>${{x}}</button>`).join("");
  byId("grid").innerHTML = grid.map((x,i)=>`<div class="cell" onclick="pick(${{i}})" id="c${{i}}">${{x}}</div>`).join("");
}}
function pick(i){{
  if(!matchId || selected.includes(i) || buffer.length>=5) return;
  selected.push(i); buffer.push(grid[i]); byId("c"+i).classList.add("sel");
  eventLog("cell_selected", {{index:i, value:grid[i], buffer}});
}}
function clearBuffer(){{
  buffer=[]; selected.forEach(i=>byId("c"+i).classList.remove("sel")); selected=[];
}}
async function eventLog(kind,payload){{
  if(!matchId) return;
  const r = await fetch("/api/match/event", {{
    method:"POST", headers:{{"content-type":"application/json"}},
    body:JSON.stringify({{match_id:matchId, player_id:playerId, kind, payload}})
  }});
  log(await r.json());
}}
async function startMatch(){{
  initGrid(); p=0; o=0; updateBars(); clearBuffer();
  const r = await fetch("/api/match/start", {{
    method:"POST", headers:{{"content-type":"application/json"}},
    body:JSON.stringify({{player_name:byId("playerName").value, arena_key:byId("arena").value}})
  }});
  const data = await r.json(); matchId=data.match_id; playerId=data.player_id; log(data);
}}
function updateBars(){{
  byId("pScore").textContent=p; byId("oScore").textContent=o;
  byId("pFill").style.width=p+"%"; byId("oFill").style.width=o+"%";
}}
async function execute(){{
  if(!matchId || buffer.length===0) return;
  let exact=0, partial=0;
  for(let i=0;i<Math.min(buffer.length,target.length);i++){{
    if(buffer[i]===target[i]) exact++;
    else if(buffer[i][0]===target[i][0] || buffer[i][1]===target[i][1]) partial++;
  }}
  let gain = 8 + Math.floor(72/6) + Math.floor((exact + partial*.5)*6);
  p = Math.min(100, p + gain);
  o = Math.min(100, o + 6 + Math.floor(Math.random()*14));
  updateBars();
  await eventLog("sequence_executed", {{buffer, target, exact, partial, gain, player_progress:p, opponent_progress:o}});
  clearBuffer();
  if(p>=100) await finish("player");
  else if(o>=100) await finish("opponent");
}}
async function finish(winner){{
  if(!matchId) return;
  const r = await fetch("/api/match/finish", {{
    method:"POST", headers:{{"content-type":"application/json"}},
    body:JSON.stringify({{match_id:matchId, winner, player_score:p, opponent_score:o}})
  }});
  log(await r.json());
  matchId=null;
}}
async function loadHealth(){{
  const r=await fetch("/api/health"); byId("health").textContent=JSON.stringify(await r.json(),null,2);
}}
async function loadLeaderboard(){{
  const r=await fetch("/api/leaderboard"); byId("side").textContent=JSON.stringify(await r.json(),null,2);
}}
async function loadVault(){{
  const r=await fetch("/api/vault"); byId("side").textContent=JSON.stringify(await r.json(),null,2);
}}
initGrid(); loadHealth();
</script>
</body>
</html>
"""

@app.get("/robots.txt")
def robots():
    return JSONResponse({"policy": "no automated live-target activity; sandbox competition only"})
