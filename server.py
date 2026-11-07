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
import os
import signal
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


def _append_display(role: str, text: str, **extra) -> dict:
    global _next_id
    with _log_cond:
        entry = {
            "id": _next_id,
            "role": role,
            "text": text,
            "ts": datetime.now().isoformat(timespec="seconds"),
            **extra,
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


# -- Approvals: the web version of the terminal's "Allow? [y/N]" --
#
# code.py calls PERMISSION_PROMPTER from whichever thread is running the
# turn (a chat request, or an autonomous turn woken by a finished
# background job). It posts an "approval" entry to DISPLAY_LOG, which the
# page renders as a card with Approve/Deny buttons, and blocks until
# /api/approve answers it. An unanswered card is denied after
# APPROVAL_TIMEOUT_SECONDS, so a turn waiting on a closed tab can't hold
# agent_lock -- and keep the idle watchdog from ever stopping -- forever.

APPROVAL_TIMEOUT_SECONDS = 10 * 60

_pending_approvals: dict[str, dict] = {}
_approvals_lock = threading.Lock()


def _approval_detail(block) -> str:
    if block.name == "bash":
        return block.input.get("command", "")
    return f"{block.name}: {block.input.get('path', '')}"


def _web_prompter(block, reason: str) -> bool:
    approval_id = uuid.uuid4().hex[:12]
    pending = {"event": threading.Event(), "approved": False}
    with _approvals_lock:
        _pending_approvals[approval_id] = pending
    _append_display("approval", reason, approval_id=approval_id,
                    detail=_approval_detail(block))
    answered = pending["event"].wait(APPROVAL_TIMEOUT_SECONDS)
    with _approvals_lock:
        _pending_approvals.pop(approval_id, None)
    approved = answered and pending["approved"]
    if answered:
        note = "Approved." if approved else "Denied."
    else:
        note = (f"No answer in {APPROVAL_TIMEOUT_SECONDS // 60} minutes "
                "-- denied.")
    _append_display("system", note, resolves=approval_id, approved=approved)
    return approved


agent_core.PERMISSION_PROMPTER = _web_prompter


# -- Idle auto-stop + manual stop --
#
# A non-technical user closing the browser tab has no reason to think the
# server (and whatever it's running) is still alive in the background --
# there's no reliable way for a web page to catch "the user closed this
# tab" and ask them first (beforeunload can only show the browser's own
# fixed "leave this page?" prompt, not a custom choice, and fires on a
# plain refresh too). So instead: track the last time any request came
# in -- including the frontend's own long-poll, so "no requests at all"
# really does mean "no tab has this page open anymore" -- and shut down
# after IDLE_TIMEOUT_SECONDS with nothing. A visible Stop Server button
# in the UI covers the "I'm done right now" case directly.

IDLE_TIMEOUT_SECONDS = 15 * 60

_last_activity = time.time()
_activity_lock = threading.Lock()


def _touch_activity() -> None:
    global _last_activity
    with _activity_lock:
        _last_activity = time.time()


def _trigger_shutdown(delay: float = 0.5) -> None:
    def _shutdown():
        time.sleep(delay)
        os.kill(os.getpid(), signal.SIGTERM)

    threading.Thread(target=_shutdown, daemon=True).start()


def _idle_watchdog() -> None:
    while True:
        time.sleep(60)
        # A closed tab with TopFD/TopPIC/training still running in the
        # background isn't "idle": shutting down here would kill the job.
        if agent_core.work_in_progress():
            _touch_activity()
            continue
        with _activity_lock:
            idle_for = time.time() - _last_activity
        if idle_for >= IDLE_TIMEOUT_SECONDS:
            print(f"No requests for {int(idle_for)}s -- shutting down.")
            _trigger_shutdown(delay=0)
            return


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent_core.start_runtime_threads()
    threading.Thread(target=_idle_watchdog, daemon=True).start()
    try:
        yield
    finally:
        agent_core.stop_runtime_threads()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def _track_activity(request, call_next):
    _touch_activity()
    return await call_next(request)


@app.post("/api/stop")
def stop():
    _trigger_shutdown()
    return {"status": "stopping"}


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

    # A permission check during this turn blocks here until the user
    # answers its approval card (see _web_prompter); the page keeps
    # long-polling /api/history meanwhile, which is how the card arrives.
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
    # Queue a note for the agent (not just DISPLAY_LOG) so it knows this
    # file exists without the user repeating the path. Queued rather than
    # appended to session_history: a turn may be mid tool call right now,
    # and a message between its tool_use and tool_result breaks the
    # history for every later API call (see code.py's upload notices).
    agent_core.queue_upload_notice(f"[Uploaded file] {dest}")
    entry = _append_display("system", f"\U0001F4CE Uploaded: {safe_name} → {rel}")
    return {"items": [entry], "path": str(dest)}


class ApprovalAnswer(BaseModel):
    approval_id: str
    approve: bool


@app.post("/api/approve")
def approve(req: ApprovalAnswer):
    with _approvals_lock:
        pending = _pending_approvals.get(req.approval_id)
        if pending is None or pending["event"].is_set():
            raise HTTPException(status_code=404,
                                detail="no such pending approval")
        pending["approved"] = req.approve
        pending["event"].set()
    return {"status": "ok"}


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
