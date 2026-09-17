---
name: pdpred_pipeline
description: |
  Run the TD-Pred (PDpred) top-down MS/MS spectral prediction pipeline on a
  TopRepo-annotated MS file (BEGIN IONS/END IONS msalign format) -- convert
  to HDF5, train or fine-tune the model, and run inference. Use when users:
  (1) ask to train, retrain, fine-tune, or run PDpred/TD-Pred
  (2) want predicted top-down spectra for given proteoform sequences
  (3) ask to prepare/convert MS data for top-down spectral prediction
  Keywords: PDpred, TD-Pred, top-down, spectral prediction, proteoform, train, checkpoint, hdf5
---

# PDpred (TD-Pred) Pipeline

## The Core Philosophy

> **Wrap, don't reimplement.**

Every step below calls the user's own already-tested TD-Pred code as a
subprocess via `bash`. This skill includes the right order to run things in, which flags
matter, and where the sharp edges are. All scripts live
in `script/`.

The input MS file should has already been processed(by TopRepo) and
is annotated per spectrum: `BEGIN IONS ... END IONS` blocks. If it hasn't
been -- no `DATABASE_SEQUENCE` on the spectra yet -- that's the
`toprepo_pipeline` skill, run before this one (then `ms_process` to split it).

## When to Use This

- The user wants to train, retrain, fine-tune, or run PDpred/TD-Pred
- The user wants predicted top-down spectra for given proteoform sequences
- The user wants to prepare/convert MS data specifically for this pipeline
  (as opposed to a generic split/convert -- that's the `ms_process` skill)

## Before You Start

**Plan first, then confirm.** Before running anything below, lay out the
plan -- which step(s), against which files, which `--target` and
`--max_length`, whether this is a from-scratch train or a fine-tune -- and
wait for the user to confirm it before executing. A wrong `--target` in
particular only shows up as a shape mismatch much later (see Anti-Patterns);
catching it in the plan is a lot cheaper than after a training run.

**Report before installing something new or touching a script.** The
`torch`/`torchinfo`/`h5py`/`numpy` this pipeline needs are assumed already
installed, since this is the user's own TD-Pred code. If a run turns up a
missing or wrong-version package, or if fixing something means editing a
file under `script/`, stop and tell the user exactly what went wrong and
what you're about to do about it. Wait for their response before
continuing.

## Pipeline

Give training and prediction runs their own folders, referred to below as
`<train_dir>` and `<predict_dir>` -- point each step's `--out`/`--output`
and log redirect at them, so a run's model, log, and any per-run side
files stay together.

**Resolving `<train_dir>`/`<predict_dir>`**: don't assume a name -- if the
user already has a place they keep runs (or one already exists for this
dataset/species), use that. `Train_result/Train_<name>/` and
`Predict_result/Predict_<name>/` at the project root (e.g. training on
human data -> `Train_result/Train_human/`) are this project's own default
when starting fresh, but a suggestion, not a requirement -- ask if
genuinely unclear. Whatever you land on, `mkdir -p` it once before running
the corresponding step, and reuse the same path for that run rather than
re-deriving it.

### 1. Convert each split to HDF5

```
python skills/pdpred_pipeline/script/msalign_anno_to_hdf5.py \
    --msalign <split_out_dir>/<name>_train.msalign \
    --out <split_out_dir>/train.h5 \
    --max_length 200

python skills/pdpred_pipeline/script/msalign_anno_to_hdf5.py \
    --msalign <split_out_dir>/<name>_val.msalign \
    --out <split_out_dir>/val.h5 \
    --max_length 200
```

`--max_length` must match what you'll pass to `train_td_pred.py` in the
next step -- it fixes the model's input/output shapes, and the HDF5
file's stored arrays won't match a differently-shaped model. Same
caveat in reverse: `td_pred.py` (step 3b) has no `--max_length` flag at
all -- it hardcodes 200 -- so a checkpoint trained with any other
`--max_length` can't be used for prediction without also editing
`td_pred.py`. Also note `encode_spectrum`/`spectrum_anno` in
`model_data.py` don't skip or truncate a proteoform longer than
`--max_length`, they raise an `IndexError` and abort the whole
conversion partway through -- check the input's longest
`DATABASE_SEQUENCE` against `--max_length` first if you're working with
a new species/dataset.

### 2. Train / fine-tune

```
mkdir -p <train_dir>

python skills/pdpred_pipeline/script/train_td_pred.py \
    --train <split_out_dir>/train.h5 \
    --validate <split_out_dir>/val.h5 \
    --out <train_dir>/checkpoint.pth \
    --max_length 200 \
    2>&1 | tee <train_dir>/train.log
```

- `--target` is `pep_bond` (default), `b_y`, or `charge`. **If this
  checkpoint is meant for step 3b's `td_pred.py`, you must pass
  `--target charge` explicitly** -- the default (`pep_bond`) trains a
  checkpoint `td_pred.py` can't use (it hardcodes `output_dim=60`,
  i.e. a `charge`-target shape), and there's no error at training
  time to warn you, only a shape mismatch later when you try to
  predict with it. This has already happened once on this project:
  a `pep_bond`-target checkpoint got trained (5 epochs) and never
  used, because `--target` wasn't set.
- To fine-tune from an existing checkpoint instead of training from
  scratch, add `--load_model <path/to/checkpoint>`. Its `--target`
  (and therefore output shape) must match what you're training now --
  `load_state_dict` will raise on a mismatch rather than silently
  loading wrong weights.
- Validation runs automatically every epoch -- no separate evaluate
  script exists. Each epoch prints train/val loss and cosine
  similarity (captured in `train.log` above via `tee`), and saves
  `<out>_<epoch>`, i.e. `<train_dir>/checkpoint.pth_<epoch>`.
  Final checkpoint after all epochs: `checkpoint.pth_final`. One
  exception to the "everything lands in the run folder" rule:
  `similarity_<epoch>.tsv` is hardcoded to write to the process's
  current working directory, not next to `--out` -- collect it
  afterward with `mv similarity_*.tsv <train_dir>/` (from wherever you
  ran the command).
- The "Output shape ... (expected: ...)" sanity-check line printed
  before training starts is misleading for `b_y`/`charge` targets: it
  prints `output_len` alone, not `output_len * output_dim`, so for
  `--target charge` it'll say "expected (4, 199)" next to an actual
  shape of `(4, 11940)`. That's a cosmetic bug in the script, not a
  real mismatch -- ignore it.
- Multi-GPU: `torchrun --nproc_per_node=N skills/pdpred_pipeline/script/train_td_pred.py ...`
  instead of `python ...`, same `--out`/`tee` pattern as above.

### 3. Predict

```
# a) get scan metadata into TSV -- use the ms_process skill's converter.
#    If ms_process's splitter produced a 3-way split, <val_dir>/<name>_test.msalign
#    exists -- use that for a genuinely held-out evaluation (val gets looked at
#    every epoch during training, so it's not fully unseen). Otherwise use the
#    val split -- check <val_dir> before assuming which one you have.
python skills/ms_process/scripts/convert_msalign_to_tsv.py \
    <split_out_dir>/<name>_val.msalign \
    <val_dir>/<name>_scans.tsv

# b) predict spectra for every row in that TSV using a trained checkpoint
mkdir -p <predict_dir>

python skills/pdpred_pipeline/script/td_pred.py \
    --input <val_dir>/<name>_scans.tsv \
    --model <train_dir>/checkpoint.pth_final \
    --output <predict_dir>/<name>_predictions.msalign \
    2>&1 | tee <predict_dir>/predict.log
```

`<val_dir>` here is the same directory `ms_process` resolved for the scan
TSV -- reuse it rather than picking a new one. The predicted spectra and
this run's log go to `<predict_dir>`, resolved the same way as `<train_dir>`
above.

## Anti-Patterns

| Pattern | Problem | Fix |
|---|---|---|
| Passing `.msalign` paths to `--train`/`--validate` | The flags default to `.mgf`-looking names but the script actually loads HDF5 via `hdf5_generator.Hdf5BatchGenerator` -- msalign paths fail | Always convert to `.h5` first (step 2), pass those paths |
| Training without `--target charge` when the checkpoint is meant for prediction | `td_pred.py` hardcodes `output_dim=60`, i.e. assumes a `charge`-target checkpoint; the default `pep_bond` (or `b_y`) checkpoint's shape won't match, and nothing warns you until you try to predict | Confirm the intended `--target` before running step 2; if a checkpoint wasn't trained with `charge` and someone wants to run step 3b with it, say so rather than running -- don't write a workaround script without flagging it first |
| Assuming "just evaluate this checkpoint on this val set" has a dedicated script | It doesn't -- validation is built into `train_td_pred.py`'s training loop, there's no standalone eval mode | Say so rather than guessing; offer to write a thin eval-only script (reusing the validation-phase logic already in `train_td_pred.py`) if the user wants one |
| Assuming "run the pipeline" means all 3 steps | The user may only want one step (e.g. just predict with an existing checkpoint) | Confirm which step(s) before running anything |
| Copying scripts elsewhere, or `cd`-ing into a different directory first | All scripts use flat sibling imports (e.g. `import model_data as md`) that rely on Python adding the invoked script's own directory to `sys.path` | Always invoke by full path under `skills/pdpred_pipeline/script/` |
| Launching a full training run without warning the user | Can take hours; blocks the loop if run in the foreground | Confirm epoch count/expected runtime first, run in the background |
| Running step 1 on a new species/dataset without checking sequence lengths | `encode_spectrum`/`spectrum_anno` raise `IndexError` and abort partway through the file if any `DATABASE_SEQUENCE` is longer than `--max_length` -- you lose the whole run, not just that one spectrum | Check the input's longest `DATABASE_SEQUENCE` against `--max_length` before running, or raise `--max_length` to cover it |
| Writing a checkpoint/log/prediction straight to the project root or scattering runs across ad-hoc paths | Runs from different datasets/species pile up ungrouped -- hard to find or compare later | Resolve `<train_dir>`/`<predict_dir>` once per run (see Pipeline above), `mkdir -p` it first, and point `--out`/`--output` and the log `tee` at it |

## Resources

**Implementation** (all under `script/`):
- `msalign_anno_to_hdf5.py` + `msalign_anno_generator.py` -- msalign to
  HDF5 (step 1). Only `MsalignAnnoBatchGenerator.__init__` and
  `.convert_anno_msalign_to_hdf5()` are used/working -- its
  `__getitem__` (the on-the-fly `torch.utils.data.Dataset` path) calls
  `md.embed_spectrum`/`md.embed_meta`/`self.spectrum_anno_to_b_ion`,
  none of which exist (the real methods are `md.encode_spectrum`,
  `md.encode_meta`, `self.spectrum_anno`). Don't wire this class
  directly into a `DataLoader` -- it'll crash immediately.
- `train_td_pred.py` + `td_pred_model.py` + `hdf5_generator.py` --
  training/fine-tuning (step 2)
- `td_pred.py` -- inference against a `charge`-target checkpoint (step 3b)
- `model_data.py` -- shared encoding helpers used by all of the above

**Related skill**:
- `ms_process` -- splitting and the TSV converter (step 3a) live there,
  not here

## Reporting back

- Report exact output file paths after each step, not just "done".
