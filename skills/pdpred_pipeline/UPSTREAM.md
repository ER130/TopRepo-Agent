# Upstream: toppic-suite/td-pred

`scripts/` is a copy of TD-Pred, https://github.com/toppic-suite/td-pred,
with the local changes listed below. Unlike `toppic_suite/vendor/` and
`toprepo_pipeline/vendor/`, it is changed in place here -- so every
change is recorded in this file, to make re-syncing with upstream (or
sending the fixes back) possible.

- **Upstream commit**: `2612000afe714e698f0741e978da96d4b45721a0`
  (`main`, 2026-09-14 -- the copy was uploaded here on 2026-09-15)
- **Layout**: upstream's `src/model/*.py` and `src/msalign/*.py` are
  flattened into `scripts/`, which is why the scripts import each other
  by bare module name (`import model_data as md`).
- **Also from upstream**: `skills/ms_process/scripts/convert_msalign_to_tsv.py`
  is upstream's `src/msalign/convert_msalign_to_tsv.py` (changes below).

| Upstream file | Here |
|---|---|
| `src/model/hdf5_generator.py` | `scripts/hdf5_generator.py` -- unchanged |
| `src/model/model_data.py` | `scripts/model_data.py` -- unchanged |
| `src/model/td_pred_model.py` | `scripts/td_pred_model.py` -- unchanged |
| `src/msalign/msalign_anno_to_hdf5.py` | `scripts/msalign_anno_to_hdf5.py` -- unchanged |
| `src/model/td_pred.py` | `scripts/td_pred.py` -- changed |
| `src/model/train_td_pred.py` | `scripts/train_td_pred.py` -- changed |
| `src/msalign/msalign_anno_generator.py` | `scripts/msalign_anno_generator.py` -- changed |
| `src/msalign/convert_msalign_to_tsv.py` | `../ms_process/scripts/convert_msalign_to_tsv.py` -- changed |

## Local changes

### Already in the copy when it was uploaded (2026-09-15)

1. `td_pred.py`: moves the model to the device before loading the
   checkpoint.
2. `msalign_anno_generator.py`: `import model_data as md` instead of
   `import model.model_data as md` (flat layout); `frag_charge_list` read
   as `int32` instead of `float32` in `spectrum_anno`.
3. `train_td_pred.py`: `train_model()`'s `num_epochs` default is 1
   instead of 40. No effect -- `main()` always passes `--epochs`.

### convert_msalign_to_tsv.py (2026-10-30, commit `de9d810`)

4. Leaves out scans `td_pred.py` can't predict and prints the counts by
   reason: no `DATABASE_SEQUENCE`, sequence longer than `--max-length`,
   a residue with no mass in `model_data`, missing precursor charge /
   activation / instrument. Adds `--max-length` (default 200).

### Bug fixes (2026-11-07)

5. `train_td_pred.py`
   - `--target` defaults to `charge` (was `pep_bond`) and only accepts
     `pep_bond`, `b_y`, `charge`. `charge` is the only target
     `td_pred.py` can predict with; a `pep_bond` checkpoint trained by
     default only failed later, with a shape mismatch in `td_pred.py`.
   - Every checkpoint (`<out>_<epoch>`, `<out>_final`) also saves
     `target` and `max_length`. `--load_model` stops with a clear error
     if they differ from this run's.
   - `--train` and `--validate` are required (their defaults were `.mgf`
     file names, but they must be HDF5 files).
   - `similarity_<epoch>.tsv` is written next to `--out`, not into the
     current directory.
   - The startup shape check prints the right expected size,
     `output_len * output_dim` (it printed `output_len` alone).
6. `td_pred.py`
   - Reads `target` and `max_length` from the checkpoint. A non-`charge`
     checkpoint stops with a clear error. Checkpoints that don't record
     them (e.g. the published `td_pred_backbone_model_1.2.1.pth`) are
     treated as `charge` / 200; `--max_length` overrides 200 for those.
   - The model's output size comes from `max_length` and
     `model_data.get_max_fragment_charge()` instead of hardcoded
     199 / 60 / 200.
   - Sequences longer than `max_length` are skipped and counted instead
     of crashing with `IndexError`.
7. `msalign_anno_generator.py`
   - Spectra whose sequence is longer than `max_seq_length` are left out
     (and counted) when the file is read. Before, the first one aborted
     the whole HDF5 conversion with `IndexError`.
   - `__getitem__` works: it called `md.embed_spectrum`, `md.embed_meta`
     and `self.spectrum_anno_to_b_ion`, none of which exist. It now
     returns the same layout as `hdf5_generator.Hdf5BatchGenerator`,
     for a `target_type` given to the constructor (default `charge`).
8. `convert_msalign_to_tsv.py`: the `--max-length` help no longer says
   `td_pred.py` hardcodes 200 -- it now means the checkpoint's
   `max_length`.
