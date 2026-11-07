---
name: ms_process
description: |
  Process TopRepo-annotated top-down MS (.msalign) files before they go into
  PDpred/TD-Pred: split into train/val (or train/val/test if no test set
  exists yet), or extract scan metadata into a TSV for prediction input.
  Use when users:
  (1) ask to "split" an ms/msalign file
  (2) mention a ratio(default 80:20, or 70:15:15 with a test set) train/
      validation split for MS data
  (3) are about to train or fine-tune PDpred/TD-Pred and haven't split their
      data yet
  (4) need a TSV of scan metadata from an msalign file (e.g. to run td_pred.py)
  Keywords: split, train val test, msalign, proteoform, TD-Pred, PDpred, group split, tsv, convert
requires: [pipeline_common]
---

# MS Process

Two small, single-purpose tools for getting a TopRepo-annotated
`.msalign` file into the shape another step needs. Neither owns any
model logic -- that lives in `pdpred_pipeline`. Neither one produces the
annotated `.msalign` in the first place -- if that doesn't exist yet
(you're starting from raw mzML/msalign/feature/TopPIC output), that's the
`toprepo_pipeline` skill, run before this one.

## The Core Philosophy

> **Split by group, not by spectrum.**

The same proteoform shows up in many spectra -- different charge
states, fractions, retention times. Split those spectra randomly and
the same proteoform ends up on both sides of train/val: the model
partly memorizes it during training, and validation accuracy looks
better than it really is. Splitting by **group** (the proteoform
itself, or the protein) instead means no group spans both files, so
validation actually measures generalization to unseen proteoforms.

**That's the whole design decision** for the splitter. The TSV
converter has no comparable decision to get right -- it's a
straight field extraction -- which is why it's a much shorter section
below.

## When to Use This

- The user wants to split an MS/msalign file into train/val
- The user mentions a ratio (80:20 or otherwise) for MS training data
- The user is about to run the `pdpred_pipeline` skill and the input
  file hasn't been split yet -- do this first, before HDF5 conversion
- The user needs scan metadata as a TSV -- most commonly to build the
  `--input` file for `td_pred.py`'s prediction step
- The input file has no `DATABASE_SEQUENCE`/proteoform annotation at
  all yet -- that's `toprepo_pipeline`, not this skill; run it first

## Before You Start

Planning, Mode A/B and reporting follow `pipeline_common` (loaded with
this skill).

**Before the plan, check** (read-only; `pipeline_common`, "Check first"):
- The input exists and is TopRepo-annotated: `grep -c '^BEGIN IONS' <input>`
  is above 0 and `grep -m1 '^DATABASE_SEQUENCE=.' <input>` finds a
  sequence. Not annotated -> `toprepo_pipeline` comes first; tell the user.
- 2-way or 3-way: whether `<val_dir>/<input>_test<ext>` already exists
  (Tool 1). Say in the plan which one you expect and why.

### Parameters to recommend (Mode B)

Even in Mode A, check `--group-field` against the input's real headers.

- `--group-field`: the default, `DATABASE_SEQUENCE`, is the proteoform
  sequence TopRepo writes into each spectrum -- check the input's headers
  have it. Recommend `PROTEIN_ACCESSION` instead only if the user
  actually wants protein-level, not proteoform-level, splitting.
- `--seed`: 42 is an arbitrary convention, not a value worth re-deriving --
  recommend keeping it unless the user wants multiple independent splits
  to compare, in which case recommend a different seed per split and say so.
- `--train-ratio`/`--test-ratio`: the 0.8/0.15 defaults are reasonable
  general-purpose choices, but check the dataset size first -- a small
  dataset (a few hundred groups) can leave val/test too thin at 15% each
  to be meaningful; recommend a larger val/test share for a small dataset
  and say why, rather than defaulting blindly.
- If the input traces back to a known TopRepo source dataset, check the
  `param_precedents` skill for whether it used FAIMS. A FAIMS run can
  produce several msalign files from one underlying raw file (split by
  compensation voltage) -- flag this to the user before splitting, since
  it may affect what they consider a genuinely held-out group.

Recommend a ratio only after stating which case (2-way vs 3-way)
applies. Neither tool needs anything installed. `convert_msalign_to_tsv.py`
comes from upstream TD-Pred: record any change to it in
`skills/pdpred_pipeline/UPSTREAM.md`.

## Tool 1: split_ms_file.py

`scripts/split_ms_file.py`, run via `bash`. It auto-detects the block
delimiter (`BEGIN SPECTRUM/END SPECTRUM`, `BEGIN IONS/END IONS`, or
`BEGIN PRSM/END PRSM`).

```
python3 skills/ms_process/scripts/split_ms_file.py \
    --input <full_annotated_file> \
    --group-field DATABASE_SEQUENCE \
    --seed 42 \
    --output-dir <split_out_dir> \
    --val-file-dir <val_dir>
```

**Checks `--val-file-dir` first to decide 2-way vs. 3-way** (this
happens automatically, no flag needed to choose):
- **`<input>_test<ext>` already exists there** -- plain train/val split
  using `--train-ratio` (default 0.8), same as before. `--test-ratio`
  is ignored.
- **No test set yet** -- train/val/**test** split instead, using
  `--test-ratio` (default 0.15, symmetric val/test -> 70:15:15).
  `--train-ratio` is ignored. Train and val go to `--output-dir` as
  usual; **test goes to `--val-file-dir`** (creating it if needed), so
  the next run against the same input finds it and takes the 2-way
  path.

`--group-field DATABASE_SEQUENCE` (the default) holds the full
proteoform sequence in TopRepo-annotated files. For protein-level
splitting, use `PROTEIN_ACCESSION`. If no spectrum has the field, the
script stops before writing anything and lists the fields it did find.

Spectra with an empty `DATABASE_SEQUENCE` (not identified) are left out
of the split and counted in the `[warn] N / M spectra had no ... field`
line -- they'd be dropped later by `msalign_anno_to_hdf5.py` anyway.
Report that line; if N is most of M, check the file before going on.

## Tool 2: convert_msalign_to_tsv.py

`scripts/convert_msalign_to_tsv.py`, run via `bash`. Straight
extraction, no grouping decision involved.

```
python3 skills/ms_process/scripts/convert_msalign_to_tsv.py <input>.msalign <scans>.tsv
```

Pulls one row per spectrum with `DATASET_ID`, `MZML_FILE_NAME`,
`MSALIGN_FILE_NAME`, `MS2_SCAN`, `DATABASE_SEQUENCE`,
`PRECURSOR_CHARGE`, `INSTRUMENT`, `ACTIVATION`, `COLLISION_ENERGY`.
This is exactly the column set `td_pred.py --input` expects -- most
often you'll run this on a val-split `.msalign` file to build the
prediction input for that held-out set.

It leaves out spectra `td_pred.py` can't predict, and prints how many
were skipped and why: no `DATABASE_SEQUENCE` (unidentified -- verified
to crash `td_pred.py`), a sequence longer than `--max-length` (default
200, which `td_pred.py` hardcodes), a residue letter the model has no
mass for, or a missing precursor charge/activation/instrument. Report
the `Wrote N of M scans` line and the skip counts to the user; if most
spectra were skipped, stop and show them before predicting.

Write the output TSV to the same `<val_dir>` used for `--val-file-dir`
above (e.g. `<val_dir>/<name>_scans.tsv`), so the test split and the
scan TSV built from it stay together.

**Resolving `<val_dir>`/`<split_out_dir>`**: don't assume a name -- if the
user already has a location for this dataset's split/validation files, use
that. Otherwise this is `runs/<run_name>/03_ms_process/` -- see
`skills/_shared/run_layout.md` for what `<run_name>` is and the full
`runs/` layout. Use the same directory for both `<val_dir>` and
`<split_out_dir>` unless there's a reason to keep them apart. Treat the
default as a suggestion, not a requirement; ask if it's genuinely
unclear, and resolve it once per dataset rather than re-deriving it each
run.

After the split (or the TSV conversion) finishes, append a line to
`runs/<run_name>/run_log.txt` (format in `skills/_shared/run_layout.md`)
noting which tool/ratio/input was used.

## Anti-Patterns

| Pattern | Problem | Fix |
|---|---|---|
| Splitting spectra directly (no `--group-field`) | Same proteoform leaks across train/val, inflates validation accuracy | Always group first (see Core Philosophy above) |
| Ignoring the `[warn]` line about ungrouped spectra | Those spectra were silently dropped from the split | Check `--group-field` against the file's actual headers before re-running |
| Guessing a ratio other than the default (0.8 train/val, or 0.15 val/test) | May not be what the user wants | Confirm the ratio (and input path, if ambiguous) with the user first |
| Assuming it's always a 2-way train/val split | Whether you get 2-way or 3-way depends on whether `<input>_test<ext>` already exists in `--val-file-dir` -- easy to miss on a first run | Read the "Found existing test set" / "No existing test set" line the script prints; don't assume from the command alone |
| Copying either script elsewhere before running it | Meant to be invoked from its own path so the loader can find it consistently | Always call `skills/ms_process/scripts/<name>.py` in place |
| Writing the scans TSV to a random/temp path instead of alongside the split it came from | Makes it hard to find later | Write next to `<val_dir>` (see Tool 2 above); resolve that path once, don't scatter outputs |

## Resources

**Implementation**:
- `scripts/split_ms_file.py` -- group-aware train/val splitter; run it,
  don't reimplement its logic inline
- `scripts/convert_msalign_to_tsv.py` -- msalign to scan-metadata TSV;
  same rule, run it as-is
