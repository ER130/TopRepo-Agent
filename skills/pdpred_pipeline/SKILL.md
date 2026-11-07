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
requires: [pipeline_common]
---

# PDpred (TD-Pred) Pipeline

## The Core Philosophy

> **Wrap, don't reimplement.**

Every step below calls the user's own already-tested TD-Pred code as a
subprocess via `bash`. This skill includes the right order to run things in, which flags
matter, and where the sharp edges are. All scripts live
in `scripts/` -- a copy of https://github.com/toppic-suite/td-pred with
local fixes, all listed in `skills/pdpred_pipeline/UPSTREAM.md`.

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

Planning, Mode A/B, long-running commands and reporting follow
`pipeline_common` (loaded with this skill). This skill adds the TD-Pred
specifics.

**The device matters most here**: training uses a GPU if PyTorch sees
one and falls back to CPU otherwise, which is far slower. The plan says
which device training will use, and on CPU proposes timing one epoch
before committing to many.

### Parameters to recommend (Mode B)

Even in Mode A, check the input's longest `DATABASE_SEQUENCE` against
`--max_length` and pick `--target` by what the checkpoint is for.

- `--max_length`: the default is 200. Check the input's longest
  `DATABASE_SEQUENCE` first: spectra with a longer one are left out of
  the HDF5 file (step 1 prints how many). If that's more than a few,
  recommend raising `--max_length` to cover them and say by how much --
  `td_pred.py` reads it from the checkpoint, so prediction follows.
- `--target`: the default, `charge`, is the only target `td_pred.py`
  (step 3b) can predict with. Recommend `pep_bond` or `b_y` only when the
  user wants a checkpoint for something other than `td_pred.py`, and say
  that it then can't be used for step 3b.
- If the training data comes from (or resembles) the TopRepo corpus,
  check the `param_precedents` skill for the source dataset's
  dissociation method before training. TD-Pred's own training data was
  HCD/CID only -- a dataset with ETD/EThcD spectra (some do, even within
  an otherwise HCD/CID project) is fragmentation the model was never
  validated against; exclude those files or flag them to the user rather
  than training on them unexamined.
- `--load_model`: no default -- recommend fine-tuning from an existing
  checkpoint (and say which one) when one already exists for this
  dataset/species and fits the intended `--target`; recommend training
  from scratch only when none does.

**Check the Python packages before the first step**:
`python3 -c "import torch, torchinfo, h5py, numpy, pandas"`. Missing ones
go into the project's `.venv` as `pipeline_common`, "Python packages"
says -- for training, `torch` must match the GPU from the hardware check.
A script change the user approves also gets an entry in `UPSTREAM.md`.

## Pipeline

Every step runs in the background (`pipeline_common`): training always
takes longer than a normal bash call's 120 s, and HDF5 conversion or
prediction on a real dataset usually does.

Give training and prediction runs their own folders, referred to below as
`<train_dir>` and `<predict_dir>` -- point each step's `--out`/`--output`
and log redirect at them, so a run's model, log, and any per-run side
files stay together.

**Resolving `<train_dir>`/`<predict_dir>`**: don't assume a name -- if the
user already has a place they keep runs (or one already exists for this
dataset/species), use that. Otherwise these are
`runs/<run_name>/04_pdpred_pipeline/train/<name>/` and
`.../predict/<name>/` -- see `skills/_shared/run_layout.md` for what
`<run_name>` is and the full `runs/` layout. `<name>` is a free label for
this particular train/predict attempt (reuse `<run_name>` itself unless
you're keeping multiple attempts side by side, e.g. different
hyperparameters). Treat the default as a suggestion, not a requirement --
ask if genuinely unclear. Whatever you land on, `mkdir -p` it once before
running the corresponding step, and reuse the same path for that run
rather than re-deriving it.

After training or predicting finishes, append a line to
`runs/<run_name>/run_log.txt` (format in `skills/_shared/run_layout.md`)
noting which step ran and the key parameters (`--target`, `--max_length`,
checkpoint used, etc).

### 1. Convert each split to HDF5

```
python3 skills/pdpred_pipeline/scripts/msalign_anno_to_hdf5.py \
    --msalign <split_out_dir>/<name>_train.msalign \
    --out <split_out_dir>/train.h5 \
    --max_length 200

python3 skills/pdpred_pipeline/scripts/msalign_anno_to_hdf5.py \
    --msalign <split_out_dir>/<name>_val.msalign \
    --out <split_out_dir>/val.h5 \
    --max_length 200
```

`--max_length` must match what you'll pass to `train_td_pred.py` in the
next step -- it fixes the model's input/output shapes, and the HDF5
file's stored arrays won't match a differently-shaped model. Spectra
whose `DATABASE_SEQUENCE` is longer than `--max_length` are left out;
the conversion prints `Skipped N of M spectra ... (longest: L)` --
report that line.

### 2. Train / fine-tune

```
mkdir -p <train_dir>

python3 skills/pdpred_pipeline/scripts/train_td_pred.py \
    --train <split_out_dir>/train.h5 \
    --validate <split_out_dir>/val.h5 \
    --out <train_dir>/checkpoint.pth \
    --max_length 200 \
    2>&1 | tee <train_dir>/train.log
```

- `--target` is `charge` (default), `pep_bond`, or `b_y`. Only a
  `charge` checkpoint works with step 3b's `td_pred.py`; each
  checkpoint records its `target` and `max_length`, and `td_pred.py`
  stops with a clear error on any other target.
- To fine-tune from an existing checkpoint instead of training from
  scratch, add `--load_model <path/to/checkpoint>`. Its `--target` and
  `--max_length` must match this run's -- the script stops with an
  error naming the mismatch.
- Validation runs automatically every epoch -- no separate evaluate
  script exists. Each epoch prints train/val loss and cosine
  similarity (captured in `train.log` above via `tee`), and saves
  `<out>_<epoch>`, i.e. `<train_dir>/checkpoint.pth_<epoch>`, plus
  `similarity_<epoch>.tsv` (per-spectrum validation similarity) in the
  same folder. Final checkpoint after all epochs: `checkpoint.pth_final`.
- Multi-GPU: `torchrun --nproc_per_node=N skills/pdpred_pipeline/scripts/train_td_pred.py ...`
  instead of `python3 ...`, same `--out`/`tee` pattern as above.

### 3. Predict

```
# a) get scan metadata into TSV -- use the ms_process skill's converter.
#    If ms_process's splitter produced a 3-way split, <val_dir>/<name>_test.msalign
#    exists -- use that for a genuinely held-out evaluation (val gets looked at
#    every epoch during training, so it's not fully unseen). Otherwise use the
#    val split -- check <val_dir> before assuming which one you have.
python3 skills/ms_process/scripts/convert_msalign_to_tsv.py \
    <split_out_dir>/<name>_val.msalign \
    <val_dir>/<name>_scans.tsv

# b) predict spectra for every row in that TSV using a trained checkpoint
mkdir -p <predict_dir>

python3 skills/pdpred_pipeline/scripts/td_pred.py \
    --input <val_dir>/<name>_scans.tsv \
    --model <train_dir>/checkpoint.pth_final \
    --output <predict_dir>/<name>_predictions.msalign \
    2>&1 | tee <predict_dir>/predict.log
```

The converter in a) leaves out spectra `td_pred.py` can't predict (no
sequence, longer than `--max-length`, unknown residue, missing metadata)
and prints the counts -- pass them on to the user. For a checkpoint
trained with a `--max_length` other than 200, pass the same value to the
converter's `--max-length`; `td_pred.py` itself reads it from the
checkpoint.

`<val_dir>` here is the same directory `ms_process` resolved for the scan
TSV -- reuse it rather than picking a new one. The predicted spectra and
this run's log go to `<predict_dir>`, resolved the same way as `<train_dir>`
above.

### Predict only -- with an existing model, no training

When the user wants predictions but no training (e.g. "use the backbone
model to predict these"), skip steps 1-2:

1. **The model**: a checkpoint trained with `--target charge` (what
   `td_pred.py` expects). The published one is TD-Pred's backbone model,
   `td_pred_backbone_model_1.2.1.pth`, which TD-Pred's own README uses
   with `td_pred.py`. It's on the TD-Pred authors' Box share,
   https://tulane.box.com/s/6pam0vzs618044vbt2y8bjuavxzl7fsn -- ask the
   user to download it and give you the path; don't look for another
   copy or substitute another `.pth` from that share without asking
   (the purpose of the "simplified" model there isn't documented).
   It doesn't record its target or `max_length`; `td_pred.py` treats
   such checkpoints as `charge` / 200.
2. **The input**: the TopRepo-annotated `.msalign` (from
   `toprepo_pipeline`). No split is needed when nothing is trained --
   predict on the whole file unless the user wants a subset.
3. Run step 3 a) on that file, then 3 b) with `--model <path to the
   .pth>`, into a `<predict_dir>` named for the model (e.g.
   `.../predict/backbone_1.2.1/`).

## Anti-Patterns

| Pattern | Problem | Fix |
|---|---|---|
| Passing `.msalign` paths to `--train`/`--validate` | The script loads HDF5 via `hdf5_generator.Hdf5BatchGenerator` -- msalign paths fail | Always convert to `.h5` first (step 1), pass those paths |
| Training with `--target pep_bond`/`b_y` when the checkpoint is meant for prediction | `td_pred.py` only predicts with a `charge` checkpoint (it stops with an error on others) | Keep the default `charge` unless the checkpoint is for something else; if someone wants step 3b with a non-`charge` checkpoint, say so rather than writing a workaround |
| Assuming "just evaluate this checkpoint on this val set" has a dedicated script | It doesn't -- validation is built into `train_td_pred.py`'s training loop, there's no standalone eval mode | Say so rather than guessing; offer to write a thin eval-only script (reusing the validation-phase logic already in `train_td_pred.py`) if the user wants one |
| Assuming "run the pipeline" means all 3 steps | The user may only want one step (e.g. just predict with an existing checkpoint) | Confirm which step(s) before running anything |
| Copying scripts elsewhere, or `cd`-ing into a different directory first | All scripts use flat sibling imports (e.g. `import model_data as md`) that rely on Python adding the invoked script's own directory to `sys.path` | Always invoke by full path under `skills/pdpred_pipeline/scripts/` |
| Launching a full training run without warning the user | Can take hours, and a normal bash call is killed at 120s | Confirm epoch count/expected runtime first, then run it with `run_in_background: true` (not `&`) |
| Running step 1 on a new species/dataset without checking sequence lengths | Spectra longer than `--max_length` are left out of training; if many are, the model never sees that part of the data | Check the input's longest `DATABASE_SEQUENCE` against `--max_length` before running, and report step 1's `Skipped N of M` line |
| Editing a file under `scripts/` without recording it | `scripts/` is a copy of upstream TD-Pred; an unrecorded change is lost or conflicts on the next re-sync | Ask first (Before You Start), then add the change to `UPSTREAM.md` |
| Writing a checkpoint/log/prediction straight to the project root or scattering runs across ad-hoc paths | Runs from different datasets/species pile up ungrouped -- hard to find or compare later | Resolve `<train_dir>`/`<predict_dir>` once per run (see Pipeline above), `mkdir -p` it first, and point `--out`/`--output` and the log `tee` at it |

## Resources

**Implementation** (all under `scripts/`):
- `msalign_anno_to_hdf5.py` + `msalign_anno_generator.py` -- msalign to
  HDF5 (step 1). `MsalignAnnoBatchGenerator` can also feed a
  `DataLoader` directly (same layout as the HDF5 dataset), but the
  training script reads HDF5.
- `train_td_pred.py` + `td_pred_model.py` + `hdf5_generator.py` --
  training/fine-tuning (step 2)
- `td_pred.py` -- inference against a `charge`-target checkpoint (step 3b)
- `model_data.py` -- shared encoding helpers used by all of the above
- `UPSTREAM.md` -- where `scripts/` comes from and every local change

**Related skill**:
- `ms_process` -- splitting and the TSV converter (step 3a) live there,
  not here

## Reporting back

- Report exact output file paths after each step, not just "done".
