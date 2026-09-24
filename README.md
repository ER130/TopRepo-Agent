# TopRepo-Agent

Two things in one repo:

1. **`code.py`** -- a self-contained coding agent (skill loading, context
   compaction, long-term memory, a task/dependency system, background
   work, cron scheduling, and persistent agent teams with task-bound Git
   worktrees), built by following the
   [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)
   course through its s07-s13 stages. See [`code.py`](#codepy) below.
2. **`skills/`** -- a set of [Agent Skills](https://code.claude.com/docs/en/skills)
   (`SKILL.md` + optional helper scripts) that `code.py` -- or Claude Code
   itself, since the format is the same -- can load on demand. Four of them
   chain together into a full top-down proteomics pipeline: raw MS
   instrument data in, a trained/queried spectral-prediction model out.
   Two more (`code-review`, `pdf`) are generic, unrelated examples.

## `code.py`

The agent itself, following [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)'s
stages s07 through s13 (skipping s14's MCP plugin). Run it directly with
`pip install anthropic python-dotenv pyyaml`, a `.env` with
`ANTHROPIC_API_KEY` and `MODEL_ID` set, then `python3 code.py`.

| Capability | What it adds | Key tools |
|---|---|---|
| Skills (s07) | loads `skills/*/SKILL.md` on demand instead of dumping all of them into the system prompt | `load_skill` |
| Context compaction (s08) | keeps a long conversation under budget: persist large tool output → archive old history → shorten → summarize as a last resort | `compact` |
| Memory (s09) | recalls relevant facts/preferences from `.memory/` at the start of each turn, extracts new ones once a turn ends | -- (automatic) |
| Tasks (s10) | dependency-aware task graph in `.tasks/`, file-locked so concurrent claimants never race | `create_task`, `update_task`, `list_tasks`, `get_task`, `claim_task`, `complete_task` |
| Background work (s11) | a long `bash` call runs in a thread instead of blocking the turn; its result arrives as a notification on a later turn | `bash(run_in_background=true)` |
| Cron (s12) | schedules a prompt on a 5-field cron expression, delivered once the agent is idle; durable jobs survive a restart | `schedule_cron`, `list_crons`, `cancel_cron` |
| Agent teams (s13) | spawns a persistent teammate on its own thread with an independent message history and working directory, coordinated with Lead through a plan-approval/shutdown protocol | `spawn_teammate`, `list_teammates`, `send_message`, `request_shutdown`, `request_plan`, `review_plan` |
| Worktrees (s13) | binds a Task to a real `git worktree` so that Task's file/bash tools -- a teammate's, or Lead's own once it claims that Task -- run isolated from the main working directory | `create_worktree` |

An interactive turn, a scheduled cron turn, and an autonomous turn (woken
by a teammate's message or a finished background task, with nobody
typing) all share one `agent_lock`, so two never run at once.
`remove_worktree` exists but is deliberately not a model tool -- removing
a worktree is destructive Git surgery, meant for a human operator to run
directly, not something the model can call on itself. MCP
(learn-claude-code's s14) isn't included.

Runtime state `code.py` creates while running -- none of it is code, all
of it is gitignored:

| Path | What's in it |
|---|---|
| `.tasks/` | one JSON file per task |
| `.memory/` | durable facts/preferences the agent chose to remember, plus `MEMORY.md`'s catalog |
| `.transcripts/` | full conversation snapshots saved before compaction trims anything |
| `.task_outputs/` | large tool output saved to disk instead of kept in context |
| `.scheduled_tasks.json` | durable (`durable=true`) cron jobs, so they survive a restart |
| `.mailboxes/` | one JSONL file per agent (`lead`, or a teammate's name); a message is deleted once read |
| `.worktrees/` | task-bound Git worktree checkouts, each on its own `wt/<name>` branch |

## The pipeline

```
raw vendor file (.raw/.d)
    │  msconvert  (ProteoWizard -- separate project, not vendored)
    ▼
mzML / mzXML
    │  topfd
    ▼
<name>_ms1/ms2.msalign + <name>_ms1/ms2.feature      ── toppic_suite ──
    │  toppic  (+ a FASTA protein database)
    ▼
<name>_ms2_toppic_prsm_single.tsv (+ proteoform tsv)
    │  extract + merge (msalign/mzml/feature/toppic info)  ── toprepo_pipeline ──
    ▼                                                          Phase 1
<name>_combined_info.tsv
    │  preprocess + merge PrSMs + annotate by ion frequency  ── toprepo_pipeline ──
    ▼                                                          Phase 2
<name>_anno_ms2.msalign   (DATABASE_SEQUENCE on every spectrum)
    │  split by proteoform group (train/val/test)             ── ms_process ──
    ▼
train.msalign / val.msalign / (test.msalign) / scan TSV
    │  HDF5 encode → train or fine-tune → predict             ── pdpred_pipeline ──
    ▼
checkpoint.pth_final  +  predicted spectra (msalign)
```

Each stage is a separate skill so it can be invoked (and loaded into
context) independently -- "just run TopFD on this file" doesn't need to
pull in the model-training playbook, and vice versa.

## Skills

| Skill | Wraps | Reads | Writes |
|---|---|---|---|
| [`toppic_suite`](skills/toppic_suite/SKILL.md) | msconvert (external), [TopFD/TopPIC](https://github.com/toppic-suite/toppic-suite) (source vendored in `skills/toppic_suite/vendor/`, built locally) | raw file or mzML/mzXML, a FASTA database | mzML, `.msalign`, `.feature`, PrSM identification TSVs -- all written beside the input |
| [`toprepo_pipeline`](skills/toprepo_pipeline/SKILL.md) | [TopRepo](https://github.com/toppic-suite/toprepo) (source vendored in `skills/toprepo_pipeline/vendor/`) | `toppic_suite`'s output | a merged info TSV, then the `DATABASE_SEQUENCE`-annotated `.msalign` that everything downstream needs |
| [`ms_process`](skills/ms_process/SKILL.md) | two small original scripts (`skills/ms_process/scripts/`) | `toprepo_pipeline`'s annotated `.msalign` | group-aware train/val(/test) `.msalign` splits, a scan-metadata TSV |
| [`pdpred_pipeline`](skills/pdpred_pipeline/SKILL.md) | the user's own TD-Pred model code (`skills/pdpred_pipeline/scripts/`) | `ms_process`'s splits/TSV | HDF5 tensors, a trained checkpoint, predicted spectra |
| [`code-review`](skills/code-review/SKILL.md) | -- | any diff/codebase | a review write-up (no files) |
| [`pdf`](skills/pdf/SKILL.md) | pdftotext / PyMuPDF / ReportLab | a PDF | extracted text, merged/split/created PDFs |

Each `SKILL.md` is the source of truth for exact commands, flags, and the
non-obvious failure modes found while building and verifying it against
real tools/data -- this README is only an orientation map.

## Data folder conventions

Nothing here is fixed. Every skill resolves a working directory (`<ms_dir>`,
`<toprepo_out_dir>`, `<val_dir>`, `<train_dir>`, `<predict_dir>`, ...) by
checking what already exists or what the user tells it, rather than
assuming a name -- local setups vary. Each skill also names its own
**default** for when there's nothing to go on yet, all as siblings of
`skills/` and `code.py` at the project root:

| Placeholder | Default | Used by |
|---|---|---|
| `<ms_dir>` | `MS_File/<name>/` | `toppic_suite` (writes), `toprepo_pipeline` Phase 1 (reads) |
| `<toprepo_out_dir>` | `TopRepo_Result/TopRepo_<name>/` | `toprepo_pipeline` |
| `<val_dir>` | `Val_File/` | `ms_process`, `pdpred_pipeline` step 3a |
| `<train_dir>` | `Train_result/Train_<name>/` | `pdpred_pipeline` step 2 |
| `<predict_dir>` | `Predict_result/Predict_<name>/` | `pdpred_pipeline` step 3b |

None of these folders exist in the repo itself (they're runtime data, not
code) and none of it is committed -- see `.gitignore`.

## `<dataset_id>` / `<name>`

`<dataset_id>` (e.g. a ProteomeXchange/MassIVE accession like `PXD029703`,
or any string you pick) is threaded through `toprepo_pipeline` as an actual
join key -- use the exact same value in every command for a given dataset,
not just as a label. `<name>` is a looser, human-friendly tag (often the
species or project name) used to name output folders and files
consistently across skills.

## Vendored code

Unlike a typical "clone this from GitHub at runtime" skill, the actual
upstream source this project depends on lives in the repo, the same way
`pdpred_pipeline/scripts/` already vendors the user's own TD-Pred code --
so running the pipeline doesn't depend on GitHub being reachable at the
moment you need it:

| Directory | From | Commit | Size |
|---|---|---|---|
| `skills/toppic_suite/vendor/` | [toppic-suite](https://github.com/toppic-suite/toppic-suite) (Tulane / toppic-suite) | see `vendor/VENDORED_COMMIT.txt` | ~163 MB (dominated by one 87 MB ONNX scoring model TopFD needs at runtime; upstream's own `resources/topmsv/node_modules/` was dropped, unused by the CLI path this project uses) |
| `skills/toprepo_pipeline/vendor/` | [TopRepo](https://github.com/toppic-suite/toprepo) (same team) | see `vendor/VENDORED_COMMIT.txt` | ~19 MB |

It's still their code, not ours -- each `SKILL.md`'s Core Philosophy says
so explicitly: fix problems from this project's own layer (`scripts/`,
never by hand-editing anything under a `vendor/` directory), and re-vendor
(copy over, update `VENDORED_COMMIT.txt`) rather than patch in place when
upstream changes something. `skills/toppic_suite/vendor/build/` and
`vendor/bin/` are build output from compiling the vendored C++ source
locally, not part of what's vendored -- gitignored, regenerated per
machine.

**Genuinely external** (not vendored, no local copy exists):
[ProteoWizard](https://proteowizard.sourceforge.io) (msconvert) -- a
separate project; see `toppic_suite/SKILL.md`'s Core Philosophy for why
its guidance there is less trustworthy than everything else in this repo.

The only other non-vendored, non-generic code is a handful of small
original fix/bookkeeping scripts under `toprepo_pipeline/scripts/`
(`skills/ms_process/scripts/` is fully original too) -- called out as such
in their own `SKILL.md`, alongside the vendored code they sit next to.
