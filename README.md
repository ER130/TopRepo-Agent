# TopRepo-Agent

TopRepo-Agent is a Claude-powered coding agent (`code.py`) paired with a
set of Agent Skills that together run a full top-down mass spectrometry
proteomics pipeline -- from raw instrument data through deconvolution,
proteoform identification, dataset annotation, and spectral-prediction
model training -- so you don't need to know each underlying tool's
commands, or have a deep biology background, to run it. Use it from a
terminal or through a browser-based chat interface.

## Setup

```
git clone https://github.com/ER130/TopRepo-Agent.git
cd TopRepo-Agent
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and replace the placeholder `ANTHROPIC_API_KEY` with your own
key from [console.anthropic.com](https://console.anthropic.com/), and set
`MODEL_ID`. Both are required -- the agent won't start without them.

## Running it

**Command line**:
```
python3 code.py
```

**Web UI** (a browser chat interface instead of the terminal):
```
uvicorn server:app --host 0.0.0.0 --port 8000
```
then open `http://localhost:8000/`. On Windows with WSL, double-click
`Start TopRepo Agent.vbs` at the project root instead -- it sets
everything up and opens the browser for you, no terminal needed. See
`launch/README.md` for details.

Note: in the web UI, a command the agent judges risky is refused
automatically rather than prompting you to approve it, unlike the
terminal's `Allow? [y/N]`.

---

Each skill under `skills/` has its own `SKILL.md` describing exactly
what it does, what it needs, and how to use it -- that's the source of
truth for the pipeline's details, not this file.
