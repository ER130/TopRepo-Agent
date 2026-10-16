#!/usr/bin/env python3
"""
server.py - web front end for code.py

A thin FastAPI wrapper around the existing agent in code.py. It never
re-implements agent logic: it imports code.py as a library, drives the
same session_history/agent_lock/run_agent_turn_locked the CLI uses, and
hooks into the new "TurnComplete" event (added in code.py alongside this
file) to capture only the model's final reply text per turn -- the same
text print_latest_assistant_text already shows in the terminal, never a
"[HOOK] ..."/"> bash" tool-call trace line, since those are only ever
print()'d straight to this process's own stdout and never touch
session_history.

Run with: uvicorn server:app --host 0.0.0.0 --port 8000
(from the project root, same place you'd run `python code.py`, so WORKDIR
resolves the same way for both).
"""

import importlib.util
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent
STATIC_DIR = PROJECT_ROOT / "static"

# Load code.py by file path rather than `import code` -- "code" is also a
# stdlib module name, and which one wins depends on sys.path ordering at
# import time. Loading by explicit path removes that ambiguity entirely.
_spec = importlib.util.spec_from_file_location("agent_core", PROJECT_ROOT / "code.py")
agent_core = importlib.util.module_from_spec(_spec)
sys.modules["agent_core"] = agent_core
_spec.loader.exec_module(agent_core)


# -- Display log: a simplified, web-facing view of the conversation --
#
# session_history (inside agent_core) stays the raw Claude-format message
# list the model actually sees -- tool_use/tool_result blocks and all.
# DISPLAY_LOG is a separate, append-only list of {id, role, text, ts}
# entries: one per real user message, one per turn's final assistant
# text, one per upload notice. Monotonic ids let the frontend long-poll
# for "anything after id N" without re-sending things it already rendered.

DISPLAY_LOG: list[dict] = []
_log_lock = threading.Lock()
_log_cond = threading.Condition(_log_lock)
_next_id = 1


def _append_display(role: str, text: str) -> dict:
    global _next_id
    with _log_cond:
        entry = {
            "id": _next_id,
            "role": role,
            "text": text,
            "ts": datetime.now().isoformat(timespec="seconds"),
        }
        _next_id += 1
        DISPLAY_LOG.append(entry)
        _log_cond.notify_all()
        return entry


def _on_turn_complete(messages: list):
    """Fires for every turn -- a chat request, a cron job, an autonomous
    turn woken by a finished background task -- so all three show up in
    the web chat the same way, not just the one this request triggered."""
    text = agent_core.latest_assistant_text(messages)
    if text:
        _append_display("assistant", text)


agent_core.register_hook("TurnComplete", _on_turn_complete)


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent_core.start_runtime_threads()
    try:
        yield
    finally:
        agent_core.stop_runtime_threads()


app = FastAPI(lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
def chat(req: ChatRequest):
    text = (req.message or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty message")

    with _log_cond:
        start_id = DISPLAY_LOG[-1]["id"] if DISPLAY_LOG else 0
    _append_display("user", text)

    # Runs on a FastAPI thread-pool thread, never the process's literal
    # main thread -- so a destructive-command or fabricated-data-write
    # permission check (see code.py's request_permission) fails closed
    # with a plain denial message instead of blocking on input() with no
    # terminal to read from. Same fail-closed behavior cron/teammate
    # turns already rely on; the web UI has no approve/deny flow yet, so
    # anything that would need one is simply refused rather than hanging.
    try:
        with agent_core.agent_lock:
            agent_core.run_agent_turn_locked(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

    with _log_cond:
        items = [e for e in DISPLAY_LOG if e["id"] > start_id]
    return {"items": items}


@app.post("/api/upload")
def upload(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="no filename")

    uploads_dir = agent_core.WORKDIR / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    # Path(...).name strips any directory components the client sent,
    # so this can't escape uploads_dir regardless of what filename a
    # browser or a crafted request supplies.
    safe_name = Path(file.filename).name
    dest = uploads_dir / f"{uuid.uuid4().hex[:8]}_{safe_name}"
    with dest.open("wb") as out:
        while chunk := file.file.read(1024 * 1024):
            out.write(chunk)

    rel = dest.relative_to(agent_core.WORKDIR)
    # Drop a note straight into session_history (not just DISPLAY_LOG) so
    # the agent already knows this file exists on its very next turn,
    # the same way a background-task result or cron firing gets injected
    # -- the user shouldn't have to repeat the path back to it.
    agent_core.session_history.append(
        {"role": "user", "content": f"[Uploaded file] {dest}"}
    )
    entry = _append_display("system", f"\U0001F4CE Uploaded: {safe_name} → {rel}")
    return {"items": [entry], "path": str(dest)}


@app.get("/api/history")
def history(since: int = 0, wait: float = 0.0):
    deadline = time.time() + max(0.0, min(wait, 60.0))
    with _log_cond:
        while True:
            items = [e for e in DISPLAY_LOG if e["id"] > since]
            if items or time.time() >= deadline:
                return {"items": items}
            _log_cond.wait(timeout=max(0.0, deadline - time.time()))


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))
