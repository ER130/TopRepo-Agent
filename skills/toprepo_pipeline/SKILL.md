---
name: toprepo_pipeline
description: |
  Run TopRepo's own upstream pipeline (https://github.com/toppic-suite/toprepo)
  to turn matched mzML + msalign + feature + TopPIC identification files into
  merged spectral-info TSVs and a TopRepo-annotated .msalign file -- the
  DATABASE_SEQUENCE-bearing file that the ms_process and pdpred_pipeline
  skills expect as their starting point. This is the upstream half of the
  chain; ms_process/pdpred_pipeline are the downstream half.
  Use when users:
  (1) ask to run, set up, or use "TopRepo" itself -- not just consume a file
      that's already been through it
  (2) have raw TopFD/TopPIC output (msalign, .feature, PrSM tsv, mzML) that
      hasn't been merged or annotated into a DATABASE_SEQUENCE-bearing
      msalign yet
  (3) ask to generate an annotated msalign or annotated mgf file from scratch
  (4) mention dataset IDs / PXD or MSV accessions, PrSM, proteoform ID,
      ion frequency table, or "spectral repository" while preparing data
      for TD-Pred
  Keywords: TopRepo, TopFD, TopPIC, PrSM, mzML, msalign, feature file,
  dataset ID, annotated msalign, annotated mgf, spectral repository,
  proteoform, msconvert
---

# TopRepo Pipeline

## The Core Philosophy

> **Every step here is a join, and TopRepo's own README undersells two of the inputs.**

The whole pipeline is: take four independently-generated per-spectrum
sources (mzML instrument metadata, msalign deconvolution output, TopFD
feature detection, TopPIC identification) and merge them on
`(DATASET_ID, MSALIGN file name, MS2 scan)`, then write the identification
back into the msalign file as annotation lines. Every merge in this chain is
a pandas `left`/`inner` join, and a mismatched filename or an inconsistent
`dataset_id` doesn't raise an error -- it just drops rows, sometimes to
zero, with only a `Warning: No matching entry found` or a plain row count to
notice it by. Two of those input requirements aren't even in the README's
own command lines (verified below) -- get them wrong and step 1.5 either
crashes on a file it never told you it needed, or silently writes a 0-row
file. Treat every printed row/match count in this pipeline as something to
check, not a formality.

TopRepo is also **someone else's tool, not ours** -- it's a separately
maintained repo (Tulane University / toppic-suite). Its code is vendored
into `skills/toprepo_pipeline/vendor/` (see Prerequisites) so this skill
runs without depending on GitHub being reachable at the moment you need
it -- but it's still their code, frozen at the commit in
`vendor/VENDORED_COMMIT.txt`, not ours to modify. Fix problems in this
skill's own layer (`scripts/`), not by hand-editing anything under
`vendor/`; if upstream fixes something here first, re-vendor rather than
patch in place.

## When to Use This

- The user wants to run TopRepo itself, from mzML/msalign/feature/TopPIC
  output through to an annotated msalign (or mgf)
- The user has a dataset that TopFD + TopPIC have already processed, but
  nothing has merged/annotated it yet -- do this **before** `ms_process`
- The user asks specifically for TopRepo's info-TSV, annotated-msalign, or
  annotated-mgf outputs, or mentions the ion-frequency/coverage-rate
  annotation step

**Not this skill**: `msconvert` (raw -> mzML), TopFD (mzML -> msalign +
`.feature`), and TopPIC (msalign -> PrSM identification TSV) are separate
compiled tools from the same toppic-suite family, covered by the
`toppic_suite` skill. TopRepo -- and this skill -- start **after** those
three have already produced their output; it does not run them. If the
user doesn't have mzML + msalign + `.feature` + TopPIC PrSM TSV yet, use
`toppic_suite` first rather than guessing at how to invoke TopFD/TopPIC here.

## Prerequisites

**0. TopRepo's code is already here.** Vendored at
`skills/toprepo_pipeline/vendor/` (from
`https://github.com/toppic-suite/toprepo`, commit recorded in
`vendor/VENDORED_COMMIT.txt`) -- no clone needed, everything below
references that path directly. To pick up upstream changes later,
re-clone and copy `src/`, `script/`, and `resources/` over the existing
`vendor/` contents, update `VENDORED_COMMIT.txt`, and re-check the
gotchas below still hold (they were verified against the vendored
commit, not necessarily whatever upstream has since become).

**Python deps** (none of this ships a requirements file -- verified by
running each step in a clean environment):
```
pip install pandas numpy pyteomics
```
`pandas`/`numpy` cover everything; `pyteomics` is only needed for the two
scripts that read `.mzML` directly (`extract_mzml_info.py`,
`convert_mzml_to_mgf.py`).

**One more hidden dependency, only for step 2.2/2.3**:
`skills/toprepo_pipeline/vendor/src/process/msalign/msalign_reader.py` subclasses
`torch.utils.data.Dataset` for no functional reason (it's only ever used
through its own generator method, never batched or indexed) -- but the
import still runs, so `merge_msalign_prsm.py`, `msalign_anno.py`, and
`msalign_anno_based_frequency.py` all hard-require `torch` to be installed
even though nothing here is a model. A CPU-only build is enough:
```
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

## Pipeline

Work from one flat directory per dataset, referred to below as
`<toprepo_out_dir>`. `cd` into it and run every command below from there --
step 1.5 depends on this (see below).

**Resolving `<toprepo_out_dir>`**: don't assume a name -- check whether
the user already has a location in mind or one already exists for this
dataset before creating a new one. `TopRepo_Result/TopRepo_<name>/` at the
project root is this project's own default when starting fresh (matching
the `Train_result/Train_<name>/` pattern `pdpred_pipeline` uses), but it's
a suggestion, not a requirement -- a local setup may keep things elsewhere.
Resolve it once and reuse it for the whole run.

`<dataset_id>` is any string you choose (TopRepo's own convention is a
ProteomeXchange/MassIVE accession like `PXD029703`) -- **use the exact same
string in every command below**; it's threaded through as a join key, not
just a label.

### Phase 1 -- merge spectral info into one TSV per dataset

**1.1 Extract mzML info** -- needs the real input mzML file.
```
python3 skills/toprepo_pipeline/vendor/src/process/mzml/extract_mzml_info.py <dataset_id> <input>.mzML <dataset_id>_<mzml_stem>_mzml_info.tsv
```
Name the output **exactly** `<dataset_id>_<mzml_stem>_mzml_info.tsv` (e.g.
`PXD029703_spectra_mzml_info.tsv` for an input `spectra.mzML`) -- see the
step 1.5 note below for why this isn't optional, unlike every other output
name in this pipeline which you're free to choose.

**1.2 Extract msalign info**
```
python3 skills/toprepo_pipeline/vendor/src/process/msalign/extract_msalign_info.py <dataset_id> <input>_ms2.msalign <name>_msalign_info.tsv
```

**1.3 Extract feature info**
```
python3 skills/toprepo_pipeline/vendor/src/process/feature/extract_feature_info.py <dataset_id> <input>_ms2.feature <name>_feature_info.tsv
```

**1.4 Preprocess the TopPIC PrSM TSV** -- use the `*_toppic_prsm_single.tsv`
(single best PrSM per spectrum), not the multi-PrSM one. TopPIC's raw output
isn't directly usable -- strip its preamble first:
```
python3 skills/toprepo_pipeline/scripts/strip_toppic_preamble.py <input>_toppic_prsm_single.tsv <name>_prsm_single_clean.tsv
python3 skills/toprepo_pipeline/vendor/src/process/prsm/prsm_preprocess.py <name>_prsm_single_clean.tsv <dataset_id> --output <name>_toppic_info.tsv
```
Don't use TopRepo's own `skills/toprepo_pipeline/vendor/src/util/tsv/remove_params.py` for
this -- verified against real TopPIC 1.9.0 output: it only strips the
`********** Parameters **********`-delimited block, but TopPIC also prints
3 summary lines (`Number of identified PrSMs: 0`, `... proteoforms: 0`,
`... proteins: 0`) right before the real header, which `remove_params.py`
leaves in place. Feeding *that* into `prsm_preprocess.py` crashes it with
`ValueError: dict contains fields not in fieldnames: None` (it parses the
first summary line as a one-column header). `strip_toppic_preamble.py`
does both jobs in one pass -- skip it entirely.

**1.5 Merge into one combined-info TSV** -- this is where the two
undocumented requirements live; both verified by running this script in a
clean directory:

```
python3 skills/toprepo_pipeline/vendor/src/process/tsv/merge_mzml_msalign_toppic_info.py <name>_msalign_info.tsv <name>_feature_info.tsv <name>_toppic_info.tsv <name>_file_info.tsv <name>_combined_info.tsv
```

- The **4th argument is not a free choice** -- the README's own example
  points it at `skills/toprepo_pipeline/vendor/resources/toprepo_file_info_v1.2.1.tsv`, but
  that file only lists the ~4,615 msalign files already in TopRepo's
  *own published corpus* (checked: it has no row for a new dataset, or
  even for the generic filenames used in TopRepo's own walkthrough). This
  argument is used in an **inner** join -- point it at that shipped file
  for a dataset that isn't already in TopRepo and step 1.5 runs cleanly and
  silently writes a **0-row** `<name>_combined_info.tsv`. Build your own
  instead with the helper in this skill (nothing downstream reads
  `PROJECT id`/`SUBDATASET id`, so placeholder values are fine):
  ```
  python3 skills/toprepo_pipeline/scripts/make_file_info_tsv.py \
      --dataset-id <dataset_id> --msalign <name>_ms2.msalign --mzml <input>.mzML \
      --output <name>_file_info.tsv
  ```
  Repeat `--msalign`/`--mzml` (same order) for more than one run in the
  dataset, or pass `--append` to add more datasets to one shared file later.
- The **mzML-info file from step 1.1 is a second, silent input** -- the
  script never takes it as a CLI argument. It reads the first row's
  `FILE_NAME` out of `<name>_msalign_info.tsv`, replaces `.mzML` with
  `_mzml_info.tsv`, prepends `<dataset_id>_`, and reads *that* filename as
  a bare relative path -- i.e. it must already be sitting in the current
  working directory under that exact derived name, or this step crashes
  with `FileNotFoundError` before it ever gets to the file_info join above.
  This is why step 1.1's output name is not optional and why every command
  in this phase must run from the same directory.

### Phase 2 -- produce the annotated msalign (what ms_process/pdpred_pipeline expect)

**2.1 Preprocess the msalign** (adds `DATASET_ID`, normalizes field names --
pure text, no extra deps):
```
python3 skills/toprepo_pipeline/vendor/src/process/msalign_anno/msalign_preprocess.py <input>_ms2.msalign <dataset_id> <name>_ms2_preprocess.msalign
```

**2.2 Merge in the PrSM identification** -- needs `PYTHONPATH` set to
`skills/toprepo_pipeline/vendor/src`, or it fails with `ModuleNotFoundError: No module named
'process'` (verified: this is true exactly as the README's own command is
written, regardless of your working directory):
```
PYTHONPATH=skills/toprepo_pipeline/vendor/src python3 skills/toprepo_pipeline/vendor/src/process/msalign_anno/merge_msalign_prsm.py \
    --tsv <name>_combined_info.tsv --msalign <name>_ms2_preprocess.msalign --out <name>_ms2_prsm.msalign
```
Always pass `--out` explicitly -- it's technically optional and silently
falls back to a generic `ms2_spectra_annot.msalign` in the current
directory if you omit it.

**2.3 Annotate** -- adds `DATABASE_SEQUENCE`, `SEQUENCE_COVERAGE`, and
per-peak ion labels; this is the step that produces the file `ms_process`
and `pdpred_pipeline` expect. Same `PYTHONPATH` requirement as 2.2.
```
PYTHONPATH=skills/toprepo_pipeline/vendor/src python3 skills/toprepo_pipeline/vendor/src/process/msalign_anno/msalign_anno_based_frequency.py \
    --msalign <name>_ms2_prsm.msalign --table skills/toprepo_pipeline/vendor/resources/toprepo_ion_freq_v1.2.1.tsv --out <name>_anno_ms2.msalign
```
`<name>_anno_ms2.msalign` is the file to hand to `ms_process`'s
`split_ms_file.py --input`.

`msalign_anno_based_frequency.py` is not the only annotation script --
`msalign_anno.py` also exists, doing plain nearest-theoretical-mass
matching with no frequency table and no `--rate` filter. They are not
interchangeable; the README's own worked example uses the frequency-table
version above, so default to that unless the user specifically wants the
simpler nearest-mass behavior.

### Phase 3 (optional) -- produce an annotated mgf

Only needed if the user specifically wants an annotated `.mgf`; **not** on
the path to `ms_process`/`pdpred_pipeline`, which only need Phase 2's
output.

```
python3 skills/toprepo_pipeline/vendor/src/process/mzml/convert_mzml_to_mgf.py <input>.mzML <name>_ms2.mgf
python3 skills/toprepo_pipeline/vendor/src/process/mgf/mgf_add_dataset_id.py <name>_ms2.mgf <dataset_id> <name>_dataset_id_ms2.mgf
python3 skills/toprepo_pipeline/vendor/src/process/mgf/mgf_anno_file.py \
    --theo_file skills/toprepo_pipeline/vendor/resources/theo_patt.txt \
    --mgf_file <name>_dataset_id_ms2.mgf \
    --msalign_file <name>_anno_ms2.msalign \
    --out <name>_anno_ms2.mgf
```
`mgf_anno_file.py` uses `multiprocessing.Pool` with `cpu_count() - 1`
workers by default (`--num_workers` to override) -- be mindful on a shared
machine, same as confirming epoch counts before a `pdpred_pipeline`
training run.

## Batch processing many datasets at once

`skills/toprepo_pipeline/vendor/script/*.sh` has folder-level wrappers (`extract_folder_*.sh`,
`merge_folder_*.sh`, `preprocess_folder_msalign.sh`, `extract_folder_toppic_zip.sh`,
etc.) built for TopRepo's own large-scale corpus builds around a numbered
`00_toprepo_toppic_output/` -> `01_prsm/` -> ... folder convention -- read
the comment block at the top of each `.sh` file before using one, and confirm
the expected input layout with the user first. These aren't verified here
the way the per-file steps above are; for a single dataset, the per-file
commands above are the more predictable path.

## Anti-Patterns

| Pattern | Problem | Fix |
|---|---|---|
| Pointing step 1.5's 4th argument at the shipped `toprepo_file_info_v1.2.1.tsv` for a dataset that isn't already in TopRepo | Inner join finds no match -> `<name>_combined_info.tsv` is silently written with 0 rows, and everything after it is empty too | Build your own with `scripts/make_file_info_tsv.py` (see step 1.5) |
| Feeding TopPIC's raw `*_toppic_prsm_single.tsv` (or TopRepo's own `remove_params.py` output) straight into `prsm_preprocess.py` (step 1.4) | Verified against real TopPIC 1.9.0 output: `remove_params.py` only strips the `**Parameters**` block, not TopPIC's 3-line `Number of identified ...` summary right before the real header -- `prsm_preprocess.py` then crashes with `ValueError: dict contains fields not in fieldnames: None` | Run `scripts/strip_toppic_preamble.py` first (see step 1.4) |
| Naming step 1.1's output anything other than `<dataset_id>_<mzml_stem>_mzml_info.tsv`, or running step 1.5 from a different directory | Step 1.5 derives that filename internally and reads it as a bare relative path -- `FileNotFoundError` if it's not exactly there | Name it exactly as step 1.1 above shows, keep the whole dataset's Phase 1/2 run in one working directory |
| Running `merge_msalign_prsm.py` / `msalign_anno.py` / `msalign_anno_based_frequency.py` without `PYTHONPATH=skills/toprepo_pipeline/vendor/src` | They `from process.msalign import msalign_reader`; without `src` on the path that's `ModuleNotFoundError: No module named 'process'`, exactly as the README's own command line is written | Prefix with `PYTHONPATH=skills/toprepo_pipeline/vendor/src` as shown in steps 2.2/2.3 |
| Assuming steps 2.2/2.3 need no extra install because they're "just text processing" | `msalign_reader.py` subclasses `torch.utils.data.Dataset` for no real reason, so `torch` is a hard import-time dependency of those three scripts | `pip install torch` (CPU build is enough) alongside pandas/numpy/pyteomics |
| Treating a `Warning: No matching entry found ... Skipping annotation.` from step 2.2 as noise | It means that spectrum's `(DATASET_ID, MSALIGN file name, MS2 scan)` didn't match anything in `<name>_combined_info.tsv` and got dropped, not annotated | Check the "Processed N spectra. Filtered M spectra." counts; investigate before continuing if M << N |
| Assuming `msalign_anno.py` and `msalign_anno_based_frequency.py` are interchangeable | Different matching logic (nearest-mass vs. frequency-filtered) and different required inputs (the latter needs `--table`) | Default to `msalign_anno_based_frequency.py` (the README's own choice) unless the user asks for the simpler one |
| Running Phase 3 because it "seems like the next step" | It's a parallel, optional output (annotated mgf); `ms_process`/`pdpred_pipeline` only need Phase 2's annotated msalign | Skip Phase 3 unless the user specifically asks for an annotated mgf |
| Hand-editing a file under `vendor/` to fix a bug instead of working around it from this skill's own layer | `vendor/` is a frozen copy of someone else's code (see Core Philosophy) -- an in-place edit silently diverges from `VENDORED_COMMIT.txt` and gets lost/conflicts on the next re-vendor | Fix it in `scripts/` (a wrapper, a preprocessing step) the way `strip_toppic_preamble.py` already does, not inside `vendor/` |
| Vendoring a fresh `pip install` of `pandas`/`numpy`/`pyteomics`/`torch` into a shared environment without asking | Can silently up/downgrade packages another project on the same machine depends on | Prefer a virtualenv/conda env for TopRepo when one isn't already set up; confirm with the user first if unsure |

## Resources

**Vendored** (`skills/toprepo_pipeline/vendor/`, from
`https://github.com/toppic-suite/toprepo` -- see `VENDORED_COMMIT.txt`
for the exact commit, and Prerequisites for how to update it):
- `vendor/UPSTREAM_README.md` -- the original 3-phase walkthrough this
  skill is built on top of (with the two step-1.5 gaps and the
  import/dependency issues above filled in)
- `vendor/resources/toprepo_ion_freq_v1.2.1.tsv` -- required `--table`
  for step 2.3
- `vendor/resources/theo_patt.txt` -- required `--theo_file` for step 3.3

**Implementation (this skill's own layer, not vendored)**:
- `scripts/make_file_info_tsv.py` -- builds the step-1.5 file_info TSV for
  datasets not already in TopRepo's own corpus
- `scripts/strip_toppic_preamble.py` -- cleans TopPIC's raw TSV output for
  step 1.4 (TopRepo's own `remove_params.py` doesn't finish the job -- see
  step 1.4 and the Anti-Patterns table)
- Both are original bookkeeping/fixes on top of vendored TopRepo code,
  not part of it -- see Core Philosophy for why that distinction matters

**Related skills**:
- `toppic_suite` -- the step *before* this one: msconvert -> TopFD -> TopPIC,
  producing the mzML/msalign/`.feature`/PrSM-TSV files this skill's Phase 1
  merges together
- `ms_process` -- takes over from this skill's Phase 2 output: splitting
  the annotated msalign into train/val(/test), and converting to the scan
  TSV `td_pred.py` needs
- `pdpred_pipeline` -- the model training/inference steps after that

## Reporting back

- Report exact output file paths after each step, not just "done" --
  same convention as `pdpred_pipeline`.
- Report the row/spectrum counts step 1.5 and step 2.2 print (or a 0-row
  warning), not just that the command exited successfully -- those are the
  two steps that fail silently rather than loudly.
