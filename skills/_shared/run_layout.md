# Shared run-folder layout

Reference, not a skill -- `code.py`'s `SkillLoader` only scans
`skills/*/SKILL.md`, so this file (not named `SKILL.md`) is never loaded
automatically or listed in the skill catalog. The four pipeline skills
(`toppic_suite`, `toprepo_pipeline`, `ms_process`, `pdpred_pipeline`) each
link here for the parts of their output-folder convention that are the
same across all of them; read it when one of them tells you to.

## The layout

One dataset's entire journey through the pipeline lives under one folder:

```
runs/<run_name>/
  run_log.txt                     -- append-only, one line per finished stage
  01_toppic_suite/                -- raw file, mzML, msalign, .feature, PrSM TSV
  02_toprepo_pipeline/             -- Phase 1 TSVs + the annotated msalign/mgf
  03_ms_process/                  -- train/val(/test) split + scan metadata TSV
  04_pdpred_pipeline/
    train/<name>/                 -- checkpoint + training log
    predict/<name>/               -- predictions + predict log
```

`<run_name>` is the same identifier `toprepo_pipeline` calls
`<dataset_id>` -- its own accession (e.g. `PXD029703`) when it has one,
otherwise any stable name you'll reuse everywhere. **Before creating a
new `runs/<run_name>/`, check whether one already exists for this
dataset** -- later stages read an earlier stage's output, so reusing the
same folder is what lets them find it.

## run_log.txt

Append one line per finished stage, don't rewrite the file. Format:

```
<UTC timestamp>  <skill name>  <one-line summary>
```

Example:
```
2026-10-22T03:14:00Z  toppic_suite  PXD027741: 4 raw -> mzML/msalign/feature/PrSM, TopFD/TopPIC default params
```

A plain shell append is enough -- no JSON, no locking:
```
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)  <skill name>  <summary>" >> runs/<run_name>/run_log.txt
```

## What's NOT here

Each skill still documents, in its own SKILL.md, the parts that are
actually specific to it: which numbered subfolder it owns, any
constraint on how that folder must be used (e.g. `toprepo_pipeline`
needs a flat working directory it `cd`s into), and what `<name>` means
for `pdpred_pipeline`'s two sub-roots. This file only covers what's
identical across all four.
