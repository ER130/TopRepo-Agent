#!/usr/bin/env python3
"""Cross-platform launcher for the TopRepo-Agent web UI.

Runs on macOS, Linux, and inside WSL on Windows (not native Windows
Python -- code.py imports fcntl, which is POSIX-only). On Windows,
`Start TopRepo Agent.vbs` / `start_webui.bat` in this same folder shell
into WSL and invoke this file there; this file itself has no
Windows-specific branch, it just runs as plain Linux once inside WSL.

Usage:
  python3 launch/launch.py              start the server (if not already
                                         running) and open the browser
  python3 launch/launch.py --setup-only create the venv and install
                                         dependencies, then exit
  python3 launch/launch.py --stop       stop a running server
"""
import argparse
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = PROJECT_ROOT / ".venv"
LOG_FILE = PROJECT_ROOT / "webui.log"
HOST = "127.0.0.1"
PORT = 8000


def venv_python() -> Path:
    return VENV_DIR / "bin" / "python3"


def is_wsl() -> bool:
    if "WSL_DISTRO_NAME" in os.environ:
        return True
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        return False


def port_in_use() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((HOST, PORT)) == 0


def ensure_venv() -> None:
    if venv_python().exists():
        return
    print("First run detected -- setting up a Python virtual environment and")
    print("installing dependencies inside the project folder. This happens")
    print("once and may take a minute...")
    subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    subprocess.run(
        [str(venv_python()), "-m", "pip", "install", "-r", str(PROJECT_ROOT / "requirements.txt")],
        check=True,
    )


def start_server() -> None:
    print("Starting TopRepo Agent web server -- first launch can take a few")
    print("seconds while the model client and skills load...")
    # Discarding stdout/stderr here would hide a crash completely -- if
    # the server dies on startup (bad .env, missing dependency, whatever),
    # wait_for_port() below just times out with no clue why. A log file
    # costs nothing and makes that debuggable.
    log = open(LOG_FILE, "w", encoding="utf-8")
    subprocess.Popen(
        [str(venv_python()), "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", str(PORT)],
        cwd=PROJECT_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def wait_for_port(tries: int = 30) -> bool:
    for _ in range(tries):
        if port_in_use():
            return True
        time.sleep(1)
    return False


def open_browser() -> None:
    url = f"http://localhost:{PORT}/"
    wsl = is_wsl()
    print(f"open_browser: is_wsl={wsl}")
    if wsl:
        # Inside WSL there's no browser to open -- reach across to the
        # Windows host instead. explorer.exe is tried first: verified on a
        # real Windows+WSL machine to actually open the browser, unlike
        # `cmd.exe /c start "" <url>`, which launches without error (so the
        # FileNotFoundError fallback below never triggers) but silently
        # fails to open anything -- confirmed the hard way.
        for args in (["explorer.exe", url], ["wslview", url], ["cmd.exe", "/c", "start", "", url]):
            try:
                # NOT start_new_session (see git history -- that broke it).
                # Confirmed on a real machine: Popen() returns a real PID
                # but opens nothing when this whole script is itself a
                # one-shot `wsl.exe bash -lc "..."` invocation -- the
                # moment this script exits, bash's command list is done,
                # so `wsl.exe` tears the whole invocation down, and the
                # WSL-interop relay for explorer.exe apparently gets cut
                # off before it finishes handing off to the Windows side.
                # Running the identical Popen() call interactively (or
                # having bash exec explorer.exe itself, as its own last
                # command) both worked -- only this "fire, then the whole
                # process tree immediately exits" shape failed. Waiting
                # briefly gives the relay time to finish; explorer.exe
                # normally exits on its own well within this once it's
                # handed off to the real browser.
                proc = subprocess.Popen(args)
                print(f"open_browser: launched {args!r} (pid {proc.pid}), waiting briefly")
                try:
                    proc.wait(timeout=5)
                    print("open_browser: launcher process exited on its own")
                except subprocess.TimeoutExpired:
                    print("open_browser: launcher still running after 5s, proceeding anyway")
                return
            except FileNotFoundError:
                print(f"open_browser: {args[0]} not found, trying next")
                continue
        print("open_browser: all WSL browser-open methods failed to launch")
        return
    opened = webbrowser.open(url)
    print(f"open_browser: webbrowser.open returned {opened}")


def stop_server() -> None:
    try:
        subprocess.run(["pkill", "-f", "uvicorn server:app"], check=False)
        print("Stop signal sent (if a server was running).")
    except FileNotFoundError:
        print("Could not find 'pkill' to stop the server -- stop it manually.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup-only", action="store_true", help="create the venv and install dependencies, then exit")
    parser.add_argument("--stop", action="store_true", help="stop a running server")
    args = parser.parse_args()

    if args.stop:
        stop_server()
        return

    ensure_venv()
    if args.setup_only:
        return

    if not port_in_use():
        start_server()
        if not wait_for_port():
            print("Server did not come up within 30 seconds -- opening the")
            print("browser anyway; reload the page once it finishes starting.")
            print(f"If it never comes up, check {LOG_FILE} for the real error.")
    open_browser()


if __name__ == "__main__":
    main()
