---
name: pipeline_common
description: |
  Rules every stage of this project's pipeline shares -- planning and
  confirming with the user, Mode A/B plans, when to stop and report, and
  how to run and report long jobs. Loaded automatically with each stage
  skill; no need to load it on its own.
internal: true
---

# Pipeline Common Rules

Each stage skill (`msconvert`, `toppic_suite`, `toprepo_pipeline`,
`ms_process`, `pdpred_pipeline`, `full_pipeline`) relies on these and
adds only its own parameters and steps.

## Before running anything

**Check the machine** before the plan: `skills/_shared/hardware_check.md`
step 1, and put its results in the plan next to the values chosen from
them (threads, device, where the data is). Folders and `run_log.txt`:
`skills/_shared/run_layout.md`.

**Inside a `full_pipeline` run** -- this stage is part of a plan the user
already confirmed through `full_pipeline`: skip the plan, the Mode A/B
question and the parameter confirmation below; use that plan's values and
go straight to running. Every check and rule in the stage skill still
applies.

**Otherwise, plan first, then confirm.** Lay out which steps run, in what
order, on which files, and wait for the user's confirmation before
running anything. A wrong input file or parameter is far cheaper to catch
in the plan than after a long run.

**Ask Mode A (quick) or B (detailed) before writing the plan** -- unless
the user already picked one earlier in this session; then reuse it. A new
session has no earlier answer, so ask.
- **Mode A**: a concise plan -- steps and files only. You still work out
  every value as Mode B would, before running; Mode A only changes what
  the plan shows. A value with no default that needs the user (e.g.
  TopPIC's `-f`, `<dataset_id>`) is still asked for.
- **Mode B**: for each parameter the stage skill lists, say what it
  controls, recommend a value for this run with a short reason, and say
  explicitly whether it differs from the tool's default ("the default is
  right here, because ..." counts too). A restated default isn't a
  recommendation.

Then ask whether the user wants to keep the values or change any, and
confirm back any changed value before using it.

**Stop and report before going beyond the stage skill's documented
setup**: a package or library it doesn't list, a compiler or build error,
or a fix that means editing a script. Say exactly what went wrong and what
you'd do, and wait for the user. Never edit anything under a `vendor/`
folder -- it's someone else's code, frozen at `VENDORED_COMMIT.txt`; work
around problems in the skill's own `scripts/`. Never invent data to fill
a gap (a FASTA, a TSV row, a parameter value): say what's missing.

## Python packages

The agent's commands run in the project's `.venv` (`code.py` puts it
first on PATH), so `python3`, `python` and `pip` there mean the venv.
Install Python packages only there -- never into the system Python, and
never with `--break-system-packages` or `sudo pip`.
- The pipeline scripts' packages: `pip install -r requirements-pipeline.txt`
  (from the project root). The launcher installs them on first setup; if
  one is missing, run this without asking -- it's the expected setup.
- `torch` (TopRepo steps 2.2/2.3, PDpred) depends on the machine, so it
  isn't in that file. From the hardware check: an NVIDIA GPU ->
  `pip install torch` (the Linux default build includes CUDA); no GPU or
  macOS -> on Linux `pip install torch --index-url https://download.pytorch.org/whl/cpu`,
  on macOS `pip install torch`. Say which one in the plan.
- `python3 -c "import sys; print(sys.prefix)"` shows which environment a
  command really uses. If it isn't the project's `.venv` (e.g. the agent
  was started outside the launcher, with no venv), say so instead of
  installing anything.

## Long-running commands

- Anything that can take over 120 s (TopFD, TopPIC, msconvert on a real
  file, builds, HDF5 conversion, training, prediction) runs with the bash
  tool's **`run_in_background: true`**, as the plain command -- no `&`,
  no `nohup`. A normal call is killed at 120 s, and `&`/`nohup` children
  are killed with the call's process group when it returns; either way the
  job dies partway and leaves partial output.
- A result saying `Error: Timeout` means the command was killed: delete
  its partial output and re-run it in the background. Don't read meaning
  into what it left.
- **Finished means the background task's notification arrived** with
  status `completed` -- not that an output file appeared. Until then, check
  progress with `tail` on its log.
- One heavy job at a time, each with the full thread count; `code.py`
  queues heavy jobs anyway, but plan them in order.

## Reporting back

- Each step's state in one word -- **running**, **finished**, or
  **failed** -- with the evidence: log tail, files and sizes, the counts
  the step printed. A test on one file isn't the batch ("test run on 1 of
  8 files done; batch not started"); never mark running work complete.
- Exact output paths after each step, and the tool version where the
  stage skill asks for it.
- Append the step's line to `run_log.txt` when it finishes
  (`run_layout.md`).
