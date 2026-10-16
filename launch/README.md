# Desktop launcher (Windows + WSL)

One-time setup, then a normal double-clickable icon on the Desktop --
no console window, no typing the server command, no typing
`localhost:8000` into a browser by hand.

This can't be a real `.exe`: `code.py` imports `fcntl` (POSIX-only, used
for the task-store file locking), so the agent only runs under WSL/Linux/
macOS, not native Windows Python. These scripts drive the existing WSL
setup instead of replacing it.

## Setup (once)

1. Right-click `make_shortcut.ps1` -> **Run with PowerShell**.
   If Windows blocks it ("running scripts is disabled on this system"),
   open PowerShell in this folder instead and run:
   ```
   powershell -ExecutionPolicy Bypass -File make_shortcut.ps1
   ```
2. This creates a **"TopRepo Agent"** icon on your Desktop.

## Every time after that

Double-click the Desktop icon. It:
- starts the web server inside WSL, if it isn't already running (first
  launch takes a few seconds while the model client and skills load) --
  double-clicking again while it's already running just opens another
  browser tab, it won't start a second server;
- opens your default browser straight to it.

No terminal window stays visible.

## Stopping the server

Double-click `stop_webui.bat` in this folder, or just leave it running
in the background -- it only listens on `localhost`.

## If it doesn't work

- `start_webui.bat` assumes the project's virtualenv is named `.venv`
  right next to `code.py`/`server.py`, matching this project's setup so
  far -- if yours is named differently, edit the `.venv` in that file to
  match.
- Assumes `wsl.exe` is on your Windows PATH (true by default once WSL
  itself is installed).
- **Not run on a real Windows machine this session** -- written and
  reasoned through against documented `cmd.exe`/WSL/VBScript behavior,
  not verified end to end the way the rest of this repo's Linux-side
  instructions are. If double-clicking the Desktop icon does nothing
  visible, double-click `start_webui.bat` directly instead (not the
  `.vbs`) so its console window stays open and shows what actually
  happened.
