# Desktop launcher (Windows + WSL)

No setup step, no console window, no typing the server command, no
typing `localhost:8000` into a browser by hand.

This can't be a real `.exe`: `code.py` imports `fcntl` (POSIX-only, used
for the task-store file locking), so the agent only runs under WSL/Linux/
macOS, not native Windows Python. These scripts drive the existing WSL
setup instead of replacing it.

## Use

Double-click **`Start TopRepo Agent.vbs`** at the project root (next to
`code.py`, `server.py`). It:
- starts the web server inside WSL, if it isn't already running (first
  launch takes a few seconds while the model client and skills load) --
  double-clicking again while it's already running just opens another
  browser tab, it won't start a second server;
- opens your default browser straight to it.

No terminal window stays visible. `launch/start_webui.bat` is the script
that actually does the work; the root-level `.vbs` just runs it hidden --
open that `.bat` directly instead (see "If it doesn't work" below) if you
want to see what it's doing.

## Stopping the server

Double-click `stop_webui.bat` in this folder, or just leave it running
in the background -- it only listens on `localhost`.

## If it doesn't work

- `start_webui.bat` has the WSL path to the venv's `activate` script
  hardcoded in a `VENV_ACTIVATE` variable near the top (on this project
  so far, that venv actually lives in a sibling project folder, not
  inside `TopRepo-Agent` itself) -- if yours is somewhere else, edit
  that one line. If you'd rather not depend on another project's venv
  at all, set up a dedicated one here instead: `python3 -m venv .venv`
  from the `TopRepo-Agent` folder, then `source .venv/bin/activate && pip
  install -r requirements.txt`, then point `VENV_ACTIVATE` at
  `"%WSLDIR%/.venv/bin/activate"` in the script.
- Assumes `wsl.exe` is on your Windows PATH (true by default once WSL
  itself is installed).
- **Not run on a real Windows machine this session** -- written and
  reasoned through against documented `cmd.exe`/WSL/VBScript behavior,
  not verified end to end the way the rest of this repo's Linux-side
  instructions are. If double-clicking `Start TopRepo Agent.vbs` does
  nothing visible, double-click `launch/start_webui.bat` directly
  instead so its console window stays open and shows what actually
  happened.
