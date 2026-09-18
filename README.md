# TopRepo-Agent

Two components here

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

The agent itself:
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
| [`pdpred_pipeline`](skills/pdpred_pipeline/SKILL.md) | the user's own TD-Pred model code (`skills/pdpred_pipeline/script/`) | `ms_process`'s splits/TSV | HDF5 tensors, a trained checkpoint, predicted spectra |
| [`code-review`](skills/code-review/SKILL.md) | -- | any diff/codebase | a review write-up (no files) |
| [`pdf`](skills/pdf/SKILL.md) | pdftotext / PyMuPDF / ReportLab | a PDF | extracted text, merged/split/created PDFs |

Each `SKILL.md` is the source of truth for exact commands, flags, and the
non-obvious failure modes found while building and verifying it against
real tools/data -- this README is only an orientation map.

