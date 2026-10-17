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
- on the very first run on a machine, sets up a dedicated Python
  virtualenv inside the project (`.venv`) and installs
  `requirements.txt` into it -- a console window opens just for this one
  step so you can see it happen (and see the error if something's
  missing, like `python3` itself); every run after that skips straight
  past this;
- starts the web server inside WSL, if it isn't already running --
  double-clicking again while it's already running just opens another
  browser tab, it won't start a second server;
- opens your default browser straight to it.

No terminal window stays visible except during that one-time setup.
`launch/start_webui.bat` is the script that actually does the work; the
root-level `.vbs` just runs it hidden -- open that `.bat` directly
instead (see "If it doesn't work" below) if you want to see what it's
doing on every run, not just the first.

## Stopping the server

Double-click `stop_webui.bat` in this folder, or just leave it running
in the background -- it only listens on `localhost`.

## If it doesn't work

- The one-time setup assumes `python3 -m venv` works inside your WSL
  distro (true on a normal Ubuntu-on-WSL install) and that `pip install
  -r requirements.txt` can reach PyPI. If setup fails, its console
  window (see above) shows the real error -- fix that, then double-click
  the icon again; it retries setup since `.venv` wasn't created.
- If you already have a working venv elsewhere and would rather point at
  that than let this create a new one, edit `start_webui.bat`: replace
  the `source .venv/bin/activate` lines with `source
  '<your WSL path>/bin/activate'`.
- Assumes `wsl.exe` is on your Windows PATH (true by default once WSL
  itself is installed).
- **Not run on a real Windows machine this session** -- written and
  reasoned through against documented `cmd.exe`/WSL/VBScript behavior,
  not verified end to end the way the rest of this repo's Linux-side
  instructions are. If double-clicking `Start TopRepo Agent.vbs` does
  nothing visible, double-click `launch/start_webui.bat` directly
  instead so its console window stays open and shows what actually
  happened.
