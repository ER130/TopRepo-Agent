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
  proteoform
requires: [pipeline_common]
---

# TopRepo Pipeline

Planning, Mode A/B, long-running commands and reporting follow
`pipeline_common` (loaded with this skill). This skill adds the TopRepo
specifics.

## The Core Philosophy

> **Every step here is a join, and TopRepo's own README undersells two of the inputs.**

The pipeline merges four independently generated per-spectrum sources
(mzML instrument metadata, msalign deconvolution, TopFD features, TopPIC
identifications) on `(DATASET_ID, MSALIGN file name, MS2 scan)`, then
writes the identification back into the msalign as annotation lines.
Every merge is a pandas `left`/`inner` join: a mismatched file name or
`dataset_id` raises no error -- it just drops rows, sometimes to zero,
with only a `Warning: No matching entry found` or a row count to show
it. Two of the inputs aren't in the README's command lines at all (step
1.5). **Treat every printed row/match count as something to check.**

TopRepo's code is vendored into `skills/toprepo_pipeline/vendor/`, frozen
at `vendor/VENDORED_COMMIT.txt` -- never edit it. Work around problems in
this skill's own `scripts/`, the way `strip_toppic_preamble.py` does.

## When to Use This

- The user wants to run TopRepo itself, from mzML/msalign/feature/TopPIC
  output through to an annotated msalign (or mgf)
- TopFD + TopPIC have already processed a dataset, but nothing has merged
  or annotated it -- this runs **before** `ms_process`
- The user asks for TopRepo's info TSVs, annotated msalign or annotated
  mgf, or the ion-frequency/coverage annotation step

**Not this skill**: raw -> mzML (`msconvert`), TopFD and TopPIC
(`toppic_suite`). This skill starts once mzML + msalign + `.feature` +
TopPIC PrSM TSV exist; without them, run `toppic_suite` first.

## Before the plan, check

Read-only (`pipeline_common`, "Check first"):
- Python packages: `python3 -c "import pandas, numpy, pyteomics, lxml, torch"`.
  Missing ones become the plan's first step (Prerequisites).
- Per input file, `toppic_suite`'s output exists and isn't empty:
  `<input>.mzML`, `<input>_ms2.msalign`, `<input>_ms2.feature`,
  `<input>_ms2_toppic_prsm_single.tsv`. Missing -> tell the user which,
  and that `toppic_suite` comes first.
- TopPIC found something: `grep -m1 'Number of identified PrSMs' <input>_ms2_toppic_prsm_single.tsv`.
  0 -> nothing to annotate; tell the user instead of a plan.
- `<dataset_id>` and step 1.5's 4th argument: the lookups under
  Parameters below.

## Parameters to recommend (Mode B)

`<dataset_id>` has no default and is asked about even in Mode A.

- `<dataset_id>`: first run
  `python3 skills/param_precedents/scripts/lookup_file.py <mzML>`. A file
  from TopRepo's corpus resolves to its accession (e.g. `Tel2_1.mzML` ->
  `PXD027741`): that's the `<dataset_id>`; show the user its documented
  species/instrument/processing. Otherwise an accession the user gives,
  or a stable name you'll reuse everywhere -- never derived from a file
  name. Files resolving to one accession are one dataset: one
  `<dataset_id>`, one `runs/<dataset_id>/`.
- Step 1.5's 4th argument: look for the dataset's msalign file names in
  the shipped `toprepo_file_info_v1.2.1.tsv`. Not there -> build one with
  `make_file_info_tsv.py`; the shipped file would silently 0-row the join.
- Step 2.3's script: `msalign_anno_based_frequency.py` (with the shipped
  `--table`), unless the user wants plain nearest-mass matching with no
  frequency filtering.

## Prerequisites

TopRepo's code is already in `skills/toprepo_pipeline/vendor/` -- no
clone needed. To update it: re-clone https://github.com/toppic-suite/toprepo,
copy `src/`, `script/` and `resources/` over `vendor/`, update
`VENDORED_COMMIT.txt`, and re-check the gotchas below.

Python packages (TopRepo ships no requirements file): `pandas`, `numpy`,
`pyteomics` + `lxml` (for the two scripts that read `.mzML`) from the
project's `requirements-pipeline.txt`, and `torch` -- installed as
`pipeline_common`, "Python packages" says. Check with
`python3 -c "import pandas, numpy, pyteomics, lxml, torch"`. `torch` is
needed by steps 2.2/2.3 although nothing here is a model:
`vendor/src/process/msalign/msalign_reader.py` subclasses
`torch.utils.data.Dataset`, so the import is required; the CPU build is
enough for this skill.

## Pipeline

Work from one flat directory per dataset, `<toprepo_out_dir>` -- by
default `runs/<dataset_id>/02_toprepo_pipeline/` (`run_layout.md`; reuse
one that already exists for this dataset). **`cd` into it and run every
command from there** -- step 1.5 depends on it. The inputs from
`toppic_suite` are in `../01_toppic_suite/`.

**`<project>` in the commands is the project root as an absolute path**
(`pwd` from the project root, e.g. `/mnt/d/Projects/TopRepo-Agent`).
From inside `<toprepo_out_dir>`, a relative `skills/...` path doesn't
exist -- the first command would fail with `No such file or directory`.
Same for `PYTHONPATH`, `--table` and `--theo_file`.

**Use the exact same `<dataset_id>` string in every command** -- it's a
join key, not a label, and it names the `runs/` folder.

When Phase 2 produces the annotated msalign, append a line to
`../run_log.txt`.

### Phase 1 -- merge spectral info into one TSV per dataset

**1.1 Extract mzML info**
```
python3 <project>/skills/toprepo_pipeline/vendor/src/process/mzml/extract_mzml_info.py <dataset_id> <input>.mzML <dataset_id>_<mzml_stem>_mzml_info.tsv
```
Name the output **exactly** `<dataset_id>_<mzml_stem>_mzml_info.tsv`
(e.g. `PXD029703_spectra_mzml_info.tsv` for `spectra.mzML`) -- step 1.5
looks for that name. Every other output name is yours to choose.

**1.2 Extract msalign info**
```
python3 <project>/skills/toprepo_pipeline/vendor/src/process/msalign/extract_msalign_info.py <dataset_id> <input>_ms2.msalign <name>_msalign_info.tsv
```

**1.3 Extract feature info**
```
python3 <project>/skills/toprepo_pipeline/vendor/src/process/feature/extract_feature_info.py <dataset_id> <input>_ms2.feature <name>_feature_info.tsv
```

**1.4 Preprocess the TopPIC PrSM TSV** -- the `*_toppic_prsm_single.tsv`
(best PrSM per spectrum), preamble stripped first:
```
python3 <project>/skills/toprepo_pipeline/scripts/strip_toppic_preamble.py <input>_toppic_prsm_single.tsv <name>_prsm_single_clean.tsv
python3 <project>/skills/toprepo_pipeline/vendor/src/process/prsm/prsm_preprocess.py <name>_prsm_single_clean.tsv <dataset_id> --output <name>_toppic_info.tsv
```
Not TopRepo's own `vendor/src/util/tsv/remove_params.py`: it strips the
`** Parameters **` block but not the three `Number of identified ...`
lines TopPIC 1.9.0 prints before the header, and `prsm_preprocess.py`
then crashes with `ValueError: dict contains fields not in fieldnames:
None`. `strip_toppic_preamble.py` removes both.

**1.5 Merge into one combined-info TSV**
```
python3 <project>/skills/toprepo_pipeline/vendor/src/process/tsv/merge_mzml_msalign_toppic_info.py <name>_msalign_info.tsv <name>_feature_info.tsv <name>_toppic_info.tsv <name>_file_info.tsv <name>_combined_info.tsv
```
Two undocumented requirements (both verified):
- **The 4th argument is an inner join.** The README points it at the
  shipped `vendor/resources/toprepo_file_info_v1.2.1.tsv`, which only
  lists the ~4,615 msalign files of TopRepo's own corpus -- for any other
  dataset the step runs cleanly and writes a **0-row** file. Build one
  (placeholder `PROJECT id`/`SUBDATASET id` are fine; nothing downstream
  reads them):
  ```
  python3 <project>/skills/toprepo_pipeline/scripts/make_file_info_tsv.py \
      --dataset-id <dataset_id> --msalign <name>_ms2.msalign --mzml <input>.mzML \
      --output <name>_file_info.tsv
  ```
  Repeat `--msalign`/`--mzml` (same order) for more runs in the dataset,
  or `--append` to add datasets to one shared file.
- **Step 1.1's output is a hidden input.** The script takes the first
  row's `FILE_NAME` from `<name>_msalign_info.tsv`, turns `.mzML` into
  `_mzml_info.tsv`, prepends `<dataset_id>_`, and opens that name in the
  current directory -- `FileNotFoundError` if step 1.1's file isn't there
  under exactly that name.

Report the row count of `<name>_combined_info.tsv`; 0 rows -> stop.

### Phase 2 -- produce the annotated msalign (what ms_process/pdpred_pipeline expect)

**2.1 Preprocess the msalign** (adds `DATASET_ID`, normalizes field names):
```
python3 <project>/skills/toprepo_pipeline/vendor/src/process/msalign_anno/msalign_preprocess.py <input>_ms2.msalign <dataset_id> <name>_ms2_preprocess.msalign
```

**2.2 Merge in the PrSM identification** -- needs `PYTHONPATH`, or it
fails with `ModuleNotFoundError: No module named 'process'` (true of the
README's own command, from any directory):
```
PYTHONPATH=<project>/skills/toprepo_pipeline/vendor/src python3 <project>/skills/toprepo_pipeline/vendor/src/process/msalign_anno/merge_msalign_prsm.py \
    --tsv <name>_combined_info.tsv --msalign <name>_ms2_preprocess.msalign --out <name>_ms2_prsm.msalign
```
Always pass `--out` (without it, output silently goes to
`ms2_spectra_annot.msalign`). Each `Warning: No matching entry found ...
Skipping annotation.` is a spectrum whose join key matched nothing and
was dropped: compare the `Processed N spectra. Filtered M spectra.` line,
and investigate before going on if M is close to N.

**2.3 Annotate** -- adds `DATABASE_SEQUENCE`, `SEQUENCE_COVERAGE` and
per-peak ion labels. Same `PYTHONPATH`:
```
PYTHONPATH=<project>/skills/toprepo_pipeline/vendor/src python3 <project>/skills/toprepo_pipeline/vendor/src/process/msalign_anno/msalign_anno_based_frequency.py \
    --msalign <name>_ms2_prsm.msalign --table <project>/skills/toprepo_pipeline/vendor/resources/toprepo_ion_freq_v1.2.1.tsv --out <name>_anno_ms2.msalign
```
`<name>_anno_ms2.msalign` is `ms_process`'s input. The other annotation
script, `msalign_anno.py`, is not interchangeable: plain
nearest-theoretical-mass matching, no frequency table, no `--rate`
filter -- only if the user asks for it.

### Phase 3 (optional) -- produce an annotated mgf

Only if the user asks for an annotated `.mgf`; `ms_process` and
`pdpred_pipeline` need only Phase 2.
```
python3 <project>/skills/toprepo_pipeline/vendor/src/process/mzml/convert_mzml_to_mgf.py <input>.mzML <name>_ms2.mgf
python3 <project>/skills/toprepo_pipeline/vendor/src/process/mgf/mgf_add_dataset_id.py <name>_ms2.mgf <dataset_id> <name>_dataset_id_ms2.mgf
python3 <project>/skills/toprepo_pipeline/vendor/src/process/mgf/mgf_anno_file.py \
    --theo_file <project>/skills/toprepo_pipeline/vendor/resources/theo_patt.txt \
    --mgf_file <name>_dataset_id_ms2.mgf \
    --msalign_file <name>_anno_ms2.msalign \
    --out <name>_anno_ms2.mgf
```
`mgf_anno_file.py` uses `cpu_count() - 1` worker processes by default
(`--num_workers` to change; `hardware_check.md`).

## Batch processing many datasets at once

`vendor/script/*.sh` has folder-level wrappers (`extract_folder_*.sh`,
`merge_folder_*.sh`, ...) built for TopRepo's own corpus builds, around a
numbered `00_toprepo_toppic_output/` -> `01_prsm/` -> ... layout. Not
verified here: read each script's header and confirm the layout with the
user first. For one dataset, the per-file steps above are more predictable.

## Reporting back

As in `pipeline_common`, plus the counts from steps 1.5 and 2.2 -- the
two steps that fail silently.

## Checklist before each command

- Running from `<toprepo_out_dir>`, with `<project>/skills/...` absolute
  paths and the same `<dataset_id>` everywhere.
- Step 1.1's output named `<dataset_id>_<mzml_stem>_mzml_info.tsv`.
- Step 1.5's 4th argument is a file_info TSV that lists this dataset.
- `PYTHONPATH` set for steps 2.2/2.3; `--out` always given.
- Row/spectrum counts checked after 1.5 and 2.2.

## Resources

**Vendored** (`vendor/`, from https://github.com/toppic-suite/toprepo at
`VENDORED_COMMIT.txt`):
- `vendor/UPSTREAM_README.md` -- the original 3-phase walkthrough
- `vendor/resources/toprepo_ion_freq_v1.2.1.tsv` -- step 2.3's `--table`
- `vendor/resources/theo_patt.txt` -- Phase 3's `--theo_file`

**This skill's own scripts** (not vendored):
- `scripts/make_file_info_tsv.py` -- step 1.5's file_info TSV for a
  dataset outside TopRepo's corpus
- `scripts/strip_toppic_preamble.py` -- step 1.4's TopPIC TSV cleanup

**Related skills**: `msconvert` and `toppic_suite` before this one;
`ms_process` (split, scan TSV) and `pdpred_pipeline` after.
