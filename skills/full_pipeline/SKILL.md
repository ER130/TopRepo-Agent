---
name: full_pipeline
description: |
  Run two or more of this project's stages in one request -- up to the
  whole chain -- with every decision gathered into one plan the user
  confirms once, after which the stages run back to back without
  stopping for per-stage plans. Use when users ask to run the whole or
  full pipeline, "end to end", "start to finish", or name several stages
  in one request.
  Keywords: full pipeline, whole pipeline, end to end, start to finish,
  all stages, chain, orchestrate
requires: [pipeline_common]
---

# Full Pipeline

## The Core Philosophy

> **One plan, one confirmation, then run -- stop only for a failed check
> or a decision the data can't make.**

Each stage skill stops to plan, asks Mode A/B, and confirms its
parameters. That's right when a stage is used on its own. Across a full
run it means the user has to come back at every stage boundary, and a
finished stage sits idle until they do. This skill moves every decision
to the start: gather them all, confirm once, then run the stages in
order.

It does **not** replace the stage skills. Their commands, output checks,
known traps and anti-patterns all still apply -- load each one and
follow it. Only their own "plan first / ask the mode / confirm the
parameters" steps are replaced by this skill's single plan.

## Stages

Every stage works in `runs/<run_name>/` (`skills/_shared/run_layout.md`).

| # | Stage skill | Takes | Leaves | Skip when |
|---|---|---|---|---|
| 1 | `msconvert` | vendor raw files | centroided mzML in `01_toppic_suite/` | the input is already mzML -- still run msconvert's step-4 check on it |
| 2 | `toppic_suite` | mzML + FASTA | `_ms2.msalign`, `_ms2.feature`, `*_ms2_toppic_prsm_single.tsv` in `01_toppic_suite/` | |
| 3 | `toprepo_pipeline` | stage 2's files | `<name>_anno_ms2.msalign` in `02_toprepo_pipeline/` | |
| 4 | `ms_process` | the annotated msalign | train/val(/test) split in `03_ms_process/` | prediction only |
| 5 | `pdpred_pipeline` | the split (training) or the annotated msalign (prediction only) | checkpoint and/or predictions in `04_pdpred_pipeline/` | |

Start and end where the user asks. A run that starts from existing
output starts at that stage -- check the files are there and pass the
previous stage's output check first.

## 1. Before the plan: load, check, look up

1. **Load** each stage skill in the run, plus `param_precedents`
   (`load_skill`). The plan needs their decision rules.
2. **Check the machine**: `skills/_shared/hardware_check.md` step 1.
3. **Check every tool and package the run needs now**, so a missing one
   comes up before the user confirms, not hours into the run:
   - msconvert (stage 1): find `msconvert.exe` -- `msconvert` step 2.
   - TopFD/TopPIC (stage 2): `toppic_suite` Prerequisites step 1.
   - TopRepo (stage 3): `python3 -c "import pandas, numpy, pyteomics, lxml, torch"`.
   - PDpred (stage 5): `python3 -c "import torch, torchinfo, h5py, numpy, pandas"`.

   This section only looks -- it installs nothing. Whatever is missing
   goes in the plan as the run's first step: `toppic_suite`'s install
   flow (with the user's two root steps), Python packages into the
   project's `.venv` (`pipeline_common`, "Python packages" -- including
   which `torch` build). msconvert missing -> the user installs
   ProteoWizard before the run can start.
4. **Look up the inputs once**:
   `python3 skills/param_precedents/scripts/lookup_file.py <every input file>`.
   A hit gives `<dataset_id>` (stage 3), `-f` (stage 2), and the
   dissociation method and FAIMS (stages 4-5) together. Use it for every
   stage -- don't look it up again per stage.

## 2. The plan -- every decision, one confirmation

Don't ask Mode A/B. The plan is always: the machine and data lines from
`hardware_check.md`, the stages to run with their inputs and outputs,
then **one table with every decision, its value, and a one-line reason**
(where the value came from). The user confirms or changes rows once.

| Decision | Stage | Rule (from the stage skill) |
|---|---|---|
| `<run_name>` = `<dataset_id>` | all | lookup hit -> its accession; otherwise ask. Never derive it from a filename |
| Output format | 1 | centroided mzML, `peakPicking vendor msLevel=1-` first (`msconvert`'s table) |
| FASTA | 2 | from the user. Never write or download one yourself |
| `-u` | 2 | `cores - 1`, lower if memory is short (`hardware_check.md`) |
| `-f` | 2 | lookup hit -> its value; else the user's answer; else "decided by trial runs after TopFD" (`toppic_suite`, "Deciding `-f` from the data") |
| `-d` | 2 | on |
| `file_info` TSV | 3 | built with `make_file_info_tsv.py` unless the dataset is in the shipped corpus |
| Annotation script | 3 | `msalign_anno_based_frequency.py` |
| Train, or predict only | 5 | the user's choice. Predict only: ask now for the path to the backbone model (`pdpred_pipeline`, "Predict only") |
| Split | 4 | `--group-field DATABASE_SEQUENCE`; 2-way vs 3-way and the ratios per `ms_process` |
| `--target` | 5 | `charge` (the default) -- this run predicts with the checkpoint |
| `--max_length` | 5 | 200; checked against the data after stage 3 (see below) |
| Device, `--epochs` | 5 | GPU if one is found, else CPU. Epochs default 50: on CPU say it'll be slow and let the user pick the number |
| ETD/EThcD files | 5 | from the lookup: list them and say they'll be excluded from training unless the user says otherwise |

Say which decisions can only be settled during the run, and the rule
that will settle them (next section). Then wait for the user's
confirmation. **That one "yes" covers every stage and every row.**

## 3. Run

- Run the stages in order, each with its own skill's commands, checks
  and folder conventions. Don't write per-stage plans, don't ask Mode
  A/B, don't re-confirm values that are in the plan.
- Long steps go in the background (`run_in_background: true`), as each
  stage skill says. When one finishes, run that stage's output check and,
  if it passes, start the next step straight away.
- After each stage: one status line in the chat and the stage's
  `run_log.txt` line, e.g.
  `Stage 2/5 toppic_suite finished: st_1, st_2 -> 412 / 388 PrSMs at 1% FDR (-u 15, -f C57). Next: toprepo_pipeline.`

**Decisions made during the run, by rule, without stopping:**
- `-f` by trial runs: `toppic_suite`'s rule picks the winner. Stop only
  when that rule says the data can't tell.
- 2-way vs 3-way split: `ms_process`'s rule, from what's on disk.
- `--max_length`: after stage 3, count the spectra whose
  `DATABASE_SEQUENCE` is longer than the planned value. They're left out
  of training and prediction (the scripts skip and count them), so this
  only needs a decision when it's a large share -- then stop (below)
  and offer a larger `--max_length`. Otherwise keep the value and put
  the count in the status line.
- A value a stage skill tells you to change mid-run (e.g. halving `-u`
  after an out-of-memory kill): change it, and say so in the status line.

## 4. When to stop

Stop and ask the user only when:
- a stage's output check fails, or a command fails;
- the `-f` trial runs can't tell;
- a large share of the spectra is longer than the planned `--max_length`;
- something comes up the plan didn't cover: a missing input, an install
  beyond what the stage skills document, an approval the user denied.

When you stop, report in `pipeline_common`'s "Reporting back" terms: what
finished, what failed (with the evidence), what hasn't started. After
the fix, resume from the failed stage -- not from the start. Earlier
stages' output and `run_log.txt` show what's done.

## Anti-Patterns

| Pattern | Problem | Fix |
|---|---|---|
| Writing a stage's own plan, asking Mode A/B, or re-confirming its parameters during a confirmed full run | Brings back the stop at every stage boundary this skill exists to remove | Run from the confirmed plan; stop only for section 4's reasons |
| Skipping a stage skill's output check because the plan was confirmed | The confirmation covers the decisions, not the results -- a killed TopFD or a 0-row join still has to be caught | Run every check the stage skill lists |
| Finding a missing tool or package mid-run | The run stalls hours in, waiting on the user | Check everything in section 1, step 3, before the plan |
| Looking up `<dataset_id>` and `-f` separately per stage | Two lookups of the same files; a mismatch between them splits one dataset in two | One `lookup_file.py` run in section 1, used everywhere |
| Changing a planned value silently | The user confirmed specific values | Change only by a stage skill's own rule, and say so in the status line |
| Restarting from stage 1 after a mid-run failure | Throws away finished stages | Resume from the failed stage |

## Resources

- Stage skills: `msconvert`, `toppic_suite`, `toprepo_pipeline`,
  `ms_process`, `pdpred_pipeline`; decisions: `param_precedents`.
- `skills/_shared/run_layout.md` -- folders and `run_log.txt`.
- `skills/_shared/hardware_check.md` -- machine check, threads, devices.
