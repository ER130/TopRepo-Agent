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
---

# MS Process

Two small, single-purpose tools for getting a TopRepo-annotated
`.msalign` file into the shape another step needs. Neither owns any
model logic -- that lives in `pdpred_pipeline`.

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

## Tool 1: split_ms_file.py

`scripts/split_ms_file.py`, run via `bash`. It auto-detects the block
delimiter (`BEGIN SPECTRUM/END SPECTRUM`, `BEGIN IONS/END IONS`, or
`BEGIN PRSM/END PRSM`).

```
python skills/ms_process/scripts/split_ms_file.py \
    --input <full_annotated_file> \
    --group-field DATABASE_SEQUENCE \
    --seed 42 \
    --output-dir <split_out_dir> \
    --val-file-dir Val_File
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

`--group-field DATABASE_SEQUENCE` -- the script's own default is
`PROTEOFORM_ID`, but TopRepo files actually use `DATABASE_SEQUENCE`
(holds the full proteoform sequence). Check the field name against the
actual file headers before running on a new species/dataset -- it may
differ. For protein-level splitting instead, use the protein accession
field.

**Known quirk**: spectra that weren't identified have an empty
`DATABASE_SEQUENCE` and all get grouped into one giant bucket. The
splitter assigns groups by target spectrum count (greedy, largest
group first), so this bucket lands wherever is furthest below its
target at that point -- normally train, since it usually has the
largest target -- and the realized spectrum-count ratio stays close
to the requested ratio despite the one oversized group. Only worry if
this single bucket alone is bigger than a whole split's target (that
split will still overshoot); check the printed spectrum counts, which
is what the splitter actually optimizes for. (These unidentified
spectra get dropped later by `msalign_anno_to_hdf5.py` anyway.)

## Tool 2: convert_msalign_to_tsv.py

`scripts/convert_msalign_to_tsv.py`, run via `bash`. Straight
extraction, no grouping decision involved.

```
python skills/ms_process/scripts/convert_msalign_to_tsv.py <input>.msalign <scans>.tsv
```

Pulls one row per spectrum with `DATASET_ID`, `MZML_FILE_NAME`,
`MSALIGN_FILE_NAME`, `MS2_SCAN`, `DATABASE_SEQUENCE`,
`PRECURSOR_CHARGE`, `INSTRUMENT`, `ACTIVATION`, `COLLISION_ENERGY`.
This is exactly the column set `td_pred.py --input` expects -- most
often you'll run this on a val-split `.msalign` file to build the
prediction input for that held-out set.

This project keeps validation-derived files under `Val_File/` at the
project root (sibling to `MS_File/`, `skills/`, `code.py`) -- write the
output TSV there (e.g. `Val_File/<name>_scans.tsv`) unless the user
says otherwise.

## Anti-Patterns

| Pattern | Problem | Fix |
|---|---|---|
| Splitting spectra directly (no `--group-field`) | Same proteoform leaks across train/val, inflates validation accuracy | Always group first (see Core Philosophy above) |
| Ignoring the `[warn]` line about ungrouped spectra | Those spectra were silently dropped from the split | Check `--group-field` against the file's actual headers before re-running |
| Guessing a ratio other than the default (0.8 train/val, or 0.15 val/test) | May not be what the user wants | Confirm the ratio (and input path, if ambiguous) with the user first |
| Assuming it's always a 2-way train/val split | Whether you get 2-way or 3-way depends on whether `<input>_test<ext>` already exists in `--val-file-dir` -- easy to miss on a first run | Read the "Found existing test set" / "No existing test set" line the script prints; don't assume from the command alone |
| Copying either script elsewhere before running it | Meant to be invoked from its own path so the loader can find it consistently | Always call `skills/ms_process/scripts/<name>.py` in place |
| Writing the scans TSV to a random/temp path | Makes it hard to find later, breaks the project's own convention | Write to `Val_File/` (see Tool 2 above) unless told otherwise |

## Resources

**Implementation**:
- `scripts/split_ms_file.py` -- group-aware train/val splitter; run it,
  don't reimplement its logic inline
- `scripts/convert_msalign_to_tsv.py` -- msalign to scan-metadata TSV;
  same rule, run it as-is
