# Desktop launcher (Windows, macOS, Linux)

No setup step, no typing the server command, no typing `localhost:8000`
into a browser by hand.

All the real logic -- creating the venv, installing dependencies,
starting the server, waiting for it to come up, opening the browser --
lives in one cross-platform file, `launch.py`. It only runs under
POSIX Python (macOS, Linux, or WSL on Windows): `code.py` imports
`fcntl` (POSIX-only, used for the task-store file locking), so the
agent can't run under native Windows Python. The per-OS files below
are just thin entry points that get you to `python3 launch/launch.py`.

## Windows (WSL)

Double-click **`Start TopRepo Agent.vbs`** in this folder. It:
- on the very first run on a machine, opens a visible console window
  and runs `launch.py --setup-only` inside WSL to create a dedicated
  virtualenv (`.venv`) in the project and install `requirements.txt`
  into it -- so you can see it happen, and see the error if something's
  missing, like `python3` itself; every run after that skips straight
  past this;
- otherwise runs `launch.py` inside WSL hidden, which starts the web
  server if it isn't already running (double-clicking again while it's
  already running just opens another browser tab, it won't start a
  second server) and opens your default browser straight to it.

`start_webui.bat` in this folder is the script that actually invokes
WSL; the `.vbs` just runs it hidden and waits for it to finish -- if it
exits with an error, the `.vbs` pops up a message box saying so rather
than failing silently. For the actual error text, don't double-click
`start_webui.bat` directly (with no console held open on error, it'll
flash closed too fast to read) -- open Command Prompt, `cd` into this
`launch` folder, and run `start_webui.bat` there instead, so the output
stays on screen in that already-open window (see "If it doesn't work"
below).

Assumes `wsl.exe` is on your Windows PATH (true by default once WSL
itself is installed) and that `python3 -m venv` works inside your WSL
distro (true on a normal Ubuntu-on-WSL install).

## macOS

Double-click **`Start TopRepo Agent.command`** in this folder. The
first time, macOS may warn that it's from an unidentified developer --
right-click it and choose "Open" to confirm once. It runs
`python3 launch/launch.py` directly (no WSL layer needed on macOS),
which does the same venv setup / server start / browser open described
above, in a Terminal window.

## Linux

There's no single double-click convention that works reliably across
Linux desktop environments, so there's no entry-point file here. From
a terminal in the project root, run:
```
python3 launch/launch.py
```

## Stopping the server

There's no dedicated stop script -- run the same launcher with
`--stop`:
```
python3 launch/launch.py --stop
```
(on Windows, run that inside WSL, e.g. `wsl.exe bash -lc "cd '<project
dir>' && python3 launch/launch.py --stop"`, or just open a WSL terminal
and run it there). Or just leave the server running in the background
-- it only listens on `localhost`.

## If it doesn't work

- The one-time setup assumes `pip install -r requirements.txt` can
  reach PyPI. If setup fails, its console window shows the real error
  -- fix that, then run the launcher again; it retries setup since
  `.venv` wasn't created.
- If you already have a working venv elsewhere and would rather point
  at that than let this create a new one, edit `launch.py`'s
  `venv_python()` to return that venv's `python3` instead.
- If double-clicking `Start TopRepo Agent.vbs` does nothing and no
  message box appears either, confirm `wsl.exe` is actually on your
  Windows PATH first -- open Command Prompt, `cd` into this `launch`
  folder, and run `start_webui.bat` there to see the real error (not by
  double-clicking the `.bat` directly, which closes too fast to read
  once it's done).
