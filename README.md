# TopRepo-Agent

Two things in one repo:

1. **`code.py`** -- a small, self-contained coding agent (skill loading,
   context compaction, long-term memory, a task/dependency system, and a
   few safety hooks), built by following a "learn Claude Code" style
   course through its s07-s10 stages.
2. **`skills/`** -- a set of [Agent Skills](https://code.claude.com/docs/en/skills)
   (`SKILL.md` + optional helper scripts) that `code.py` -- or Claude Code
   itself, since the format is the same -- can load on demand. Four of them
   chain together into a full top-down proteomics pipeline: raw MS
   instrument data in, a trained/queried spectral-prediction model out.
   Two more (`code-review`, `pdf`) are generic, unrelated examples.

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
| [`toppic_suite`](skills/toppic_suite/SKILL.md) | msconvert (external), [TopFD/TopPIC](https://github.com/toppic-suite/toppic-suite) (built from source) | raw file or mzML/mzXML, a FASTA database | mzML, `.msalign`, `.feature`, PrSM identification TSVs -- all written beside the input |
| [`toprepo_pipeline`](skills/toprepo_pipeline/SKILL.md) | [TopRepo](https://github.com/toppic-suite/toprepo) (cloned, not vendored) | `toppic_suite`'s output | a merged info TSV, then the `DATABASE_SEQUENCE`-annotated `.msalign` that everything downstream needs |
| [`ms_process`](skills/ms_process/SKILL.md) | two small original scripts (`skills/ms_process/scripts/`) | `toprepo_pipeline`'s annotated `.msalign` | group-aware train/val(/test) `.msalign` splits, a scan-metadata TSV |
| [`pdpred_pipeline`](skills/pdpred_pipeline/SKILL.md) | the user's own TD-Pred model code (`skills/pdpred_pipeline/script/`) | `ms_process`'s splits/TSV | HDF5 tensors, a trained checkpoint, predicted spectra |
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

## Upstream tools (not vendored)

- [TopFD/TopPIC/toppic-suite](https://github.com/toppic-suite/toppic-suite) --
  Tulane University / toppic-suite, built from source, see `toppic_suite/SKILL.md`
- [TopRepo](https://github.com/toppic-suite/toprepo) -- same team, cloned in
  place, see `toprepo_pipeline/SKILL.md`
- [ProteoWizard](https://proteowizard.sourceforge.io) (msconvert) -- separate
  project entirely

These are cloned/built wherever you're running the pipeline, not copied
into this repo -- keeps this project from duplicating (and drifting from)
code it doesn't own. The only exceptions are `pdpred_pipeline/script/`
(the user's own TD-Pred model code) and a handful of small original
fix/bookkeeping scripts under `toprepo_pipeline/scripts/`, both called out
as such in their own `SKILL.md`.
