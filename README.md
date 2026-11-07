# TopRepo-Agent

TopRepo-Agent is a Claude-powered coding agent paired with a set of
Agent Skills that together run a full top-down mass spectrometry
proteomics pipeline -- from raw instrument data through deconvolution,
proteoform identification, dataset annotation, and spectral-prediction
model training -- so you don't need to know each underlying tool's
commands, or have a deep biology background, to run it. Use it from a
terminal or through a browser-based chat interface.

## Setup

```
git clone https://github.com/ER130/TopRepo-Agent.git
cd TopRepo-Agent
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-pipeline.txt
cp .env.example .env
```

Everything installs into the project's own `.venv`: recent Ubuntu (23.04+)
refuses `pip install` into the system Python. If `python3 -m venv` fails
on Ubuntu, install the venv module first: `sudo apt install python3-venv`.
The web UI launchers below create the same `.venv` on their own.
`requirements-pipeline.txt` holds the packages the pipeline scripts use;
`torch` isn't in it -- the agent installs the build that fits your
machine (GPU or CPU) the first time a step needs it.

Open `.env` and replace the placeholder `ANTHROPIC_API_KEY` with your own
key from [console.anthropic.com](https://console.anthropic.com/), and set
`MODEL_ID`. Both are required -- the agent won't start without them.

The agent runs on Linux or macOS only; on Windows it runs inside WSL
(Ubuntu). TopFD/TopPIC are installed natively the first time you ask for
them: the agent builds them from the source in `skills/toppic_suite/`,
and asks you to run the two install steps in your own terminal (the
dependencies with `sudo apt install` or `brew install`, then
`sudo make install`). Supported: Ubuntu (including Ubuntu under WSL) and macOS.

## Running it

**Command line**:
```
.venv/bin/python3 code.py
```

**Web UI** (a browser chat interface instead of the terminal) -- easiest
way to start it, per platform:
- **Windows** (with WSL): double-click `launch/Start TopRepo Agent.vbs`
- **macOS**: double-click `launch/Start TopRepo Agent.command`
- **Linux**: run `python3 launch/launch.py`

Each sets up its own `.venv` on first run and opens your browser straight
to the chat UI. See `launch/README.md` for details.

Or start it manually instead:
```
.venv/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```
then open `http://localhost:8000/`.

Note: when the agent wants to run a command that needs your OK (for
example deleting files outside a run's own folders), the terminal asks
`Allow? [y/N]` and the web UI shows an Approve/Deny card in the chat. A
card left unanswered for 10 minutes counts as Deny.

---

Each skill under `skills/` has its own `SKILL.md` describing exactly
what it does, what it needs, and how to use it -- that's the source of
truth for the pipeline's details, not this file.
