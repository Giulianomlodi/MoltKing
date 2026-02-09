"""
MoltKing Command Center — FastAPI Backend
REST API + WebSocket for process management and game state streaming.
"""

import os
import sys
import json
import time
import signal
import asyncio
import subprocess
from pathlib import Path
from typing import Optional

import httpx
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

load_dotenv()

# Discordia API config
DISCORDIA_API = "https://discordia.ai/api"
DISCORDIA_KEY = "ma_9f7f102690aaf89999b84cb0f431ef6b"

BASE_DIR = Path(__file__).parent
STRATEGY_PARAMS = BASE_DIR / "strategy_params.json"
STRATEGY_LOG = BASE_DIR / "strategy_log.jsonl"
LLM_CONFIG_PATH = BASE_DIR / "llm_config.json"
HUMAN_SUGGESTION_PATH = BASE_DIR / "human_suggestion.json"
DASHBOARD_DIST = BASE_DIR / "dashboard" / "dist"

DEFAULT_LLM_CONFIG = {
    "provider": "nvidia",
    "model": "moonshotai/kimi-k2.5",
    "api_key": "",
    "models": {
        "nvidia": ["moonshotai/kimi-k2.5"],
        "anthropic": [
            "claude-haiku-4-5-20251001",
            "claude-3-7-sonnet-20250219",
            "claude-sonnet-4-5-20250929",
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
            "claude-3-5-haiku-20241022",
        ],
        "openai": ["gpt-4o", "gpt-4o-mini", "o3-mini"],
    },
}


def load_suggestion() -> Optional[dict]:
    """Load current human suggestion, or None if no active suggestion."""
    if HUMAN_SUGGESTION_PATH.exists():
        try:
            return json.loads(HUMAN_SUGGESTION_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return None


def save_suggestion(text: str):
    """Save a human suggestion to disk."""
    HUMAN_SUGGESTION_PATH.write_text(json.dumps({
        "suggestion": text,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }, indent=2))


def clear_suggestion():
    """Remove the human suggestion file."""
    try:
        HUMAN_SUGGESTION_PATH.unlink()
    except FileNotFoundError:
        pass


def load_llm_config() -> dict:
    """Load LLM config from file, creating with defaults if missing.
    Always falls back to ANTHROPIC_API_KEY env var when saved key is empty."""
    if LLM_CONFIG_PATH.exists():
        try:
            cfg = json.loads(LLM_CONFIG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            cfg = dict(DEFAULT_LLM_CONFIG)
    else:
        cfg = dict(DEFAULT_LLM_CONFIG)
    # Always update models list from defaults
    cfg["models"] = DEFAULT_LLM_CONFIG["models"]
    # Fall back to env var when no key saved
    if not cfg.get("api_key"):
        if cfg.get("provider") == "nvidia":
            cfg["api_key"] = os.environ.get("KIMI_API_KEY", "") or os.environ.get("LLM_API_KEY", "")
        elif cfg.get("provider") == "anthropic":
            cfg["api_key"] = os.environ.get("ANTHROPIC_API_KEY", "") or os.environ.get("LLM_API_KEY", "")
        else:
            cfg["api_key"] = os.environ.get("LLM_API_KEY", "")
    return cfg


def save_llm_config(cfg: dict):
    LLM_CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def redact_key(key: str) -> str:
    if not key or len(key) < 8:
        return ""
    return f"...{key[-4:]}"

app = FastAPI(title="MoltKing Command Center")

# --- Process management ---

PID_FILE = BASE_DIR / ".pids.json"

class ProcessManager:
    def __init__(self):
        self.bot_proc: Optional[subprocess.Popen] = None
        self.ai_proc: Optional[subprocess.Popen] = None
        self.bot_start_time: Optional[float] = None
        self.ai_start_time: Optional[float] = None
        self.bot_pid_v: Optional[int] = None
        self.ai_pid_v: Optional[int] = None
        self._load_pids()

    def _load_pids(self):
        """Restore process status from file if server restarted."""
        if PID_FILE.exists():
            try:
                data = json.loads(PID_FILE.read_text())
                # Note: We can only check if they are alive, we can't easily 
                # get a Popen object back for an existing process to wait() on it,
                # but we can check if the PID is still active and belongs to our script.
                self.bot_start_time = data.get("bot_start_time")
                self.ai_start_time = data.get("ai_start_time")
                
                bot_pid = data.get("bot_pid")
                if bot_pid and self._check_pid_alive(bot_pid):
                    # We create a dummy popen-like object or just store the pid
                    self.bot_pid_v = bot_pid
                
                ai_pid = data.get("ai_pid")
                if ai_pid and self._check_pid_alive(ai_pid):
                    self.ai_pid_v = ai_pid
            except Exception:
                pass

    def _save_pids(self):
        data = {
            "bot_pid": self.bot_proc.pid if self.bot_running else getattr(self, "bot_pid_v", None),
            "bot_start_time": self.bot_start_time,
            "ai_pid": self.ai_proc.pid if self.ai_running else getattr(self, "ai_pid_v", None),
            "ai_start_time": self.ai_start_time,
        }
        PID_FILE.write_text(json.dumps(data))

    def _check_pid_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _is_alive(self, proc: Optional[subprocess.Popen], fallback_pid: str = None) -> bool:
        if proc is not None:
            return proc.poll() is None
        pid = getattr(self, fallback_pid) if fallback_pid else None
        return self._check_pid_alive(pid) if pid else False

    @property
    def bot_running(self) -> bool:
        return self._is_alive(self.bot_proc, "bot_pid_v")

    @property
    def ai_running(self) -> bool:
        return self._is_alive(self.ai_proc, "ai_pid_v")

    def status(self) -> dict:
        return {
            "botRunning": self.bot_running,
            "botPid": self.bot_proc.pid if (self.bot_proc and self.bot_proc.poll() is None) else getattr(self, "bot_pid_v", None),
            "botUptime": round(time.time() - self.bot_start_time) if self.bot_running and self.bot_start_time else None,
            "aiRunning": self.ai_running,
            "aiPid": self.ai_proc.pid if (self.ai_proc and self.ai_proc.poll() is None) else getattr(self, "ai_pid_v", None),
            "aiUptime": round(time.time() - self.ai_start_time) if self.ai_running and self.ai_start_time else None,
        }

    def start_bot(self, turns: int = 9999) -> dict:
        if self.bot_running:
            return {"success": False, "error": "Bot already running"}
        self.bot_proc = subprocess.Popen(
            [sys.executable, str(BASE_DIR / "discordia_bot.py"), "--turns", str(turns)],
            cwd=str(BASE_DIR),
        )
        self.bot_start_time = time.time()
        self.bot_pid_v = self.bot_proc.pid
        self._save_pids()
        return {"success": True, "pid": self.bot_proc.pid}

    def stop_bot(self) -> dict:
        if not self.bot_running:
            return {"success": False, "error": "Bot not running"}
        
        pid = self.bot_proc.pid if (self.bot_proc and self.bot_proc.poll() is None) else getattr(self, "bot_pid_v", None)
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                # If we have the handle, wait for it
                if self.bot_proc and self.bot_proc.poll() is None:
                    try:
                        self.bot_proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.bot_proc.kill()
            except ProcessLookupError:
                pass
        
        self.bot_proc = None
        self.bot_pid_v = None
        self.bot_start_time = None
        self._save_pids()
        return {"success": True}

    def start_ai(self) -> dict:
        if self.ai_running:
            return {"success": False, "error": "AI service already running"}
        cfg = load_llm_config()
        api_key = cfg.get("api_key", "")
        if not api_key:
            return {"success": False, "error": "No API key configured — open LLM Settings"}
        env = os.environ.copy()
        env["LLM_PROVIDER"] = cfg.get("provider", "nvidia")
        env["LLM_MODEL"] = cfg.get("model", "moonshotai/kimi-k2.5")
        env["LLM_API_KEY"] = api_key
        print(f"[ProcessManager] Starting AI service with provider={cfg.get('provider')} model={cfg.get('model')}")
        try:
            self.ai_proc = subprocess.Popen(
                [sys.executable, str(BASE_DIR / "ai_strategy_service.py")],
                cwd=str(BASE_DIR),
                env=env,
            )
            self.ai_start_time = time.time()
            self.ai_pid_v = self.ai_proc.pid
            self._save_pids()
            print(f"[ProcessManager] AI service started with PID {self.ai_proc.pid}")
            return {"success": True, "pid": self.ai_proc.pid}
        except Exception as e:
            print(f"[ProcessManager] Failed to start AI service: {e}")
            return {"success": False, "error": str(e)}

    def stop_ai(self) -> dict:
        if not self.ai_running:
            return {"success": False, "error": "AI service not running"}
        
        pid = self.ai_proc.pid if (self.ai_proc and self.ai_proc.poll() is None) else getattr(self, "ai_pid_v", None)
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                if self.ai_proc and self.ai_proc.poll() is None:
                    try:
                        self.ai_proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.ai_proc.kill()
            except ProcessLookupError:
                pass

        self.ai_proc = None
        self.ai_pid_v = None
        self.ai_start_time = None
        self._save_pids()
        return {"success": True}


pm = ProcessManager()

# --- Discordia API helpers ---

async def discordia_get(path: str, params: dict = None, client: httpx.AsyncClient = None) -> dict:
    try:
        if client:
            r = await client.get(
                f"{DISCORDIA_API}{path}",
                headers={"X-API-Key": DISCORDIA_KEY},
                params=params,
                timeout=5,
            )
        else:
            async with httpx.AsyncClient() as c:
                r = await c.get(
                    f"{DISCORDIA_API}{path}",
                    headers={"X-API-Key": DISCORDIA_KEY},
                    params=params,
                    timeout=5,
                )
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- REST endpoints ---

@app.get("/api/status")
def get_status():
    return pm.status()

@app.post("/api/bot/start")
def bot_start(turns: int = Query(9999)):
    return pm.start_bot(turns)

@app.post("/api/bot/stop")
def bot_stop():
    return pm.stop_bot()

@app.post("/api/ai/start")
def ai_start():
    return pm.start_ai()

@app.post("/api/ai/stop")
def ai_stop():
    return pm.stop_ai()

@app.get("/api/game/state")
async def game_state():
    return await discordia_get("/game/state")

@app.get("/api/strategy/params")
def strategy_params():
    try:
        return json.loads(STRATEGY_PARAMS.read_text())
    except Exception:
        return {}

@app.get("/api/strategy/log")
def strategy_log(limit: int = Query(50)):
    try:
        lines = STRATEGY_LOG.read_text().strip().split("\n")
        entries = []
        for line in lines[-limit:]:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries
    except FileNotFoundError:
        return []

@app.get("/api/chat")
async def chat(limit: int = Query(20)):
    return await discordia_get("/chat/messages", {"limit": limit})


# --- LLM config endpoints ---

class LlmConfigUpdate(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None


@app.get("/api/llm/config")
def get_llm_config():
    cfg = load_llm_config()
    return {
        "provider": cfg.get("provider", "anthropic"),
        "model": cfg.get("model", "claude-haiku-4-5-20251001"),
        "keyHint": redact_key(cfg.get("api_key", "")),
        "hasKey": bool(cfg.get("api_key")),
        "models": cfg.get("models", DEFAULT_LLM_CONFIG["models"]),
    }


@app.post("/api/llm/config")
def update_llm_config(body: LlmConfigUpdate):
    cfg = load_llm_config()
    if body.provider is not None:
        cfg["provider"] = body.provider
    if body.model is not None:
        cfg["model"] = body.model
    if body.api_key is not None:
        cfg["api_key"] = body.api_key
    save_llm_config(cfg)
    return {
        "success": True,
        "provider": cfg["provider"],
        "model": cfg["model"],
        "hasKey": bool(cfg.get("api_key")),
    }

# --- WebSocket ---

class LogWatcher:
    """Watches strategy_log.jsonl for new entries."""
    def __init__(self):
        self._last_size = 0
        self._init()

    def _init(self):
        try:
            self._last_size = STRATEGY_LOG.stat().st_size
        except FileNotFoundError:
            self._last_size = 0

    def check_new_entries(self) -> list[dict]:
        try:
            current_size = STRATEGY_LOG.stat().st_size
        except FileNotFoundError:
            return []
        if current_size <= self._last_size:
            if current_size < self._last_size:
                self._last_size = current_size
            return []
        with open(STRATEGY_LOG, "r") as f:
            f.seek(self._last_size)
            new_data = f.read()
        self._last_size = current_size
        entries = []
        for line in new_data.strip().split("\n"):
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries


active_websockets: list[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    active_websockets.append(ws)
    watcher = LogWatcher()
    update_event = asyncio.Event()
    update_event.set()  # Initial update
    
    async with httpx.AsyncClient() as client:
        async def receiver():
            try:
                while True:
                    msg = await ws.receive_json()
                    cmd = msg.get("type")
                    if not cmd:
                        continue
                        
                    print(f"[WS] Received command: {cmd}")
                    if cmd == "bot_start":
                        pm.start_bot(msg.get("turns", 9999))
                    elif cmd == "bot_stop":
                        pm.stop_bot()
                    elif cmd == "ai_start":
                        pm.start_ai()
                    elif cmd == "ai_stop":
                        pm.stop_ai()
                    elif cmd == "human_suggestion":
                        text = msg.get("suggestion", "").strip()
                        if text:
                            save_suggestion(text)
                    elif cmd == "clear_suggestion":
                        clear_suggestion()
                    elif cmd == "ping":
                        await ws.send_json({"type": "pong"})
                        continue
                        
                    # After any state-changing command, trigger an immediate update
                    update_event.set()
            except WebSocketDisconnect:
                pass
            except Exception as e:
                print(f"[WS] Receiver error: {e}")

        async def sender():
            try:
                while True:
                    # Wait for next update or regular heartbeat interval (1s)
                    try:
                        await asyncio.wait_for(update_event.wait(), timeout=1.0)
                        update_event.clear()
                    except asyncio.TimeoutError:
                        pass
                    
                    # Build state message
                    llm_cfg = load_llm_config()
                    state_data = {
                        **pm.status(),
                        "llmConfig": {
                            "provider": llm_cfg.get("provider", "anthropic"),
                            "model": llm_cfg.get("model", ""),
                            "hasKey": bool(llm_cfg.get("api_key")),
                        },
                    }
                    
                    # Fetch data in parallel
                    gs_task = discordia_get("/game/state", client=client)
                    chat_task = discordia_get("/chat/messages", {"limit": 30}, client=client)
                    
                    try:
                        gs, chat_resp = await asyncio.gather(gs_task, chat_task, return_exceptions=True)
                        
                        if isinstance(gs, dict) and gs.get("success") and gs.get("data"):
                            d = gs["data"]
                            state_data["tick"] = d.get("tick")
                            state_data["agent"] = d.get("agent")
                            units = d.get("myUnits", [])
                            state_data["units"] = {
                                "workers": len([u for u in units if u.get("type") == "worker"]),
                                "soldiers": len([u for u in units if u.get("type") == "soldier"]),
                                "healers": len([u for u in units if u.get("type") == "healer"]),
                                "total": len(units),
                            }
                            structs = d.get("myStructures", [])
                            spawns = [s for s in structs if s.get("type") == "spawn"]
                            state_data["structures"] = {
                                "spawns": len(spawns),
                                "towers": len([s for s in structs if s.get("type") == "tower"]),
                                "storages": len([s for s in structs if s.get("type") == "storage"]),
                                "spawnEnergy": sum(s.get("energy", 0) for s in spawns),
                            }
                            # Threats from visible chunks
                            enemy_units = []
                            for chunk in d.get("visibleChunks", []):
                                for u in chunk.get("units", []):
                                    if u.get("ownerId") and u["ownerId"] != d.get("agent", {}).get("id"):
                                        enemy_units.append(u)
                            state_data["threats"] = {
                                "enemyUnits": len(enemy_units),
                            }
                            # Map data for LiveMap
                            state_data["mapChunks"] = d.get("visibleChunks", [])
                        
                        if isinstance(chat_resp, dict) and chat_resp.get("success"):
                            state_data["chatMessages"] = chat_resp.get("data", [])
                        else:
                            state_data["chatMessages"] = []
                            
                    except Exception:
                        state_data["chatMessages"] = []

                    # Read current params (fast disk read)
                    try:
                        state_data["params"] = json.loads(STRATEGY_PARAMS.read_text())
                    except Exception:
                        state_data["params"] = {}

                    # Include human suggestion
                    state_data["humanSuggestion"] = load_suggestion()

                    await ws.send_json({"type": "state", "data": state_data})

                    # Check for new log entries
                    new_entries = watcher.check_new_entries()
                    for entry in new_entries:
                        await ws.send_json({"type": "log_entry", "data": entry})

            except WebSocketDisconnect:
                pass
            except Exception as e:
                print(f"[WS] Sender error: {e}")
            finally:
                if ws in active_websockets:
                    active_websockets.remove(ws)

        # Run both tasks concurrently
        await asyncio.gather(receiver(), sender())

# --- Debug Endpoints ---

@app.get("/api/debug/fs")
def debug_fs(path: str = "."):
    """Lists files for debugging deployment paths."""
    p = Path(path)
    if not p.exists():
        return {"error": f"Path {path} does not exist"}
    try:
        return {
            "path": str(p.absolute()),
            "contents": os.listdir(p) if p.is_dir() else "is_file",
            "cwd": os.getcwd()
        }
    except Exception as e:
        return {"error": str(e)}

# --- Static file serving (production) ---

def find_dashboard():
    paths = [
        BASE_DIR / "dashboard" / "dist",
        Path("/app/dashboard/dist"),
        Path.cwd() / "dashboard" / "dist"
    ]
    for p in paths:
        if p.exists():
            return p
    return None

@app.get("/")
async def serve_dashboard_root():
    dist = find_dashboard()
    if dist:
        index = dist / "index.html"
        if index.exists():
            return FileResponse(index)
        return {"error": "Dashboard dist exists but index.html is missing", "path": str(dist)}
    
    return {
        "error": "Dashboard dist folder not found",
        "tried_paths": [str(BASE_DIR / "dashboard" / "dist"), "/app/dashboard/dist", str(Path.cwd() / "dashboard" / "dist")],
        "cwd": os.getcwd(),
        "ls_cwd": os.listdir() if Path.cwd().exists() else [],
        "ls_dashboard": os.listdir("dashboard") if Path("dashboard").exists() else "dashboard folder missing"
    }

@app.get("/{full_path:path}")
async def serve_dashboard_assets(full_path: str):
    if full_path.startswith("api/"):
        return {"detail": "Not Found"}
    
    dist = find_dashboard()
    if not dist:
        return {"error": "Dashboard dist not found"}
        
    file_path = dist / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    
    # Static files (images, etc) fallback
    if "." in full_path:
        return {"detail": "Not Found"}
        
    # SPA fallback
    index = dist / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"error": "index.html missing"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
