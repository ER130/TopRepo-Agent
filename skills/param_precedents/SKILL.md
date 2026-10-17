---
name: param_precedents
description: |
  Look up how TopRepo's 38 source projects (112 subdatasets -- the real
  precedent data behind toprepo_file_info_v1.2.1.tsv) were actually
  collected and processed: species, instrument, dissociation method,
  separation method, FAIMS, and -- the headline finding -- the fixed
  cysteine modification each one actually used. Ground a parameter
  recommendation in a real, cited example instead of reasoning from
  scratch or defaulting. Use when users:
  (1) are running toppic_suite and need to decide `-f` (fixed
      modification -- no safe default exists)
  (2) are running pdpred_pipeline and need to know if a dataset's
      dissociation method (HCD/CID vs ETD/EThcD) is compatible with
      TD-Pred's own training data
  (3) are running ms_process or toprepo_pipeline and need to know
      whether a dataset used FAIMS, or whether a `<dataset_id>` matches
      one of TopRepo's own source datasets
  (4) ask directly what parameters a similar/real dataset used, or name
      a species, organism, or instrument model
  Keywords: precedent, example dataset, fixed modification, cysteine
  protection, carbamidomethyl, C57, dissociation method, FAIMS, TopRepo
  corpus, similar dataset, parameter example
---

# Parameter Precedents

## The Core Philosophy

> **Real precedent beats guessing -- but only when the match is real.**

TopRepo didn't invent one global recipe for every dataset it's built
from. Of its 38 source projects (112 subdatasets), the parameters that
generalize -- TopFD's deconvolution settings, TopPIC's mass tolerance
and FDR cutoffs -- are the same corpus-wide. But the ones that genuinely
vary by sample -- fixed cysteine modification, dissociation method,
separation method, FAIMS -- are recorded per dataset, cross-checked
against the published paper for each one. That's a better starting point
than a tool's hardcoded default, and better than reasoning from general
knowledge about the tool alone, because it's a real experimental fact,
not an assumption.

But a precedent is only useful when the match is real. Pull up the
closest matching species/instrument/sample type, say what you found and
where it came from (project number, accession, publication), and say
plainly when nothing here matches closely enough to be worth citing --
don't stretch a thin match into a confident recommendation.

## When to Use This

- Running `toppic_suite` and deciding `-f` -- this is the main reason
  this skill exists (see "Cysteine protection" below)
- Running `pdpred_pipeline` and the training data might include ETD or
  EThcD spectra -- TD-Pred's own training data was HCD/CID only
- Running `ms_process` on a FAIMS dataset, or `toprepo_pipeline` on a
  `<dataset_id>` that might already be one of TopRepo's own 87 source
  accessions
- Anyone asks "what did a similar/real dataset use" or names a species,
  organism, or instrument

## How to Look Up a Precedent

The data lives in `resources/toprepo_datasets_phase1.tsv` -- one row per
subdataset (112 rows, 38 projects). Filter or grep it by `species`,
`sample`, or `instrument` for the closest match to what's being
processed. Columns that actually matter for a parameter decision:

- **`toppic_fixed_mod`** -- already resolved to the exact value to use:
  `none (no -f)`, `C57 (carbamidomethyl Cys)`, or `MIXED - set per raw
  file` (only true for project 20 / PXD049969 -- see below). This is the
  one column `toppic_suite`'s `-f` decision should actually cite.
- **`dissociation_meta`** -- HCD/CID/ETD/EThcD. Trust this over
  `dissociation_S5` where they differ (see "Known data-quality caveats").
- **`faims_meta`** -- Yes/No/mixed.
- **`separation_meta`**, **`instrument`**, **`sample`**, **`species`** --
  for judging how close a match actually is before citing it.
- **`publication`** -- full citation; cite it when you use a row.
- **`flag`** -- non-empty only on rows with a known caveat (read it
  before trusting that row -- see below).

Quote the specific project and accession when a row informs a
recommendation -- e.g. "TopRepo's project 9 (McCool et al., Sci Adv
2022, PXD029703) used carbamidomethyl Cys for a comparable human CZE
dataset" -- not a vague "TopRepo data suggests...". If nothing in the
table is a close match, say so rather than citing a loosely-related row
as though it settles the question.

## What's Corpus-Wide, Not Per-Dataset

Don't treat this skill as a source of exhaustive per-dataset TopFD/TopPIC
numeric tuning -- almost all of it is one blanket recipe TopRepo applied
across the whole corpus:

- **TopFD 1.7.10**: max charge 30, max mass 70,000 Da, peak error
  tolerance 0.02 m/z, MS1 S/N 3, MS/MS S/N 1, precursor window 3 m/z.
- **TopPIC 1.7.11**: 10 ppm precursor/fragment tolerance, one unexpected
  mass shift (-500 to +500 Da), PrSM and proteoform FDR both 0.01,
  cluster tolerance 1.2 Da.

(Full tables with every field: `resources/toprepo_datasets_phase1.md`
section 2.) The only things that genuinely vary per dataset in this
corpus -- and that this skill actually helps with -- are fixed
modification, dissociation method, separation method, and FAIMS. Don't
imply a dataset-specific TopFD/TopPIC tuning precedent exists beyond
those; it doesn't.

## Cysteine Protection: Don't Default to C57

**Only 9 of 38 projects (about 19% of the corpus's 3,165 raw files) used
carbamidomethylation.** The other 28 used no fixed modification at all.
The same lab appears on both sides of this split (project 9's and
project 2's CZE datasets use C57; several of the same group's other
datasets don't), so "which lab ran it" isn't a usable shortcut either.

**Never default `toppic -f` to C57 because it's the more commonly-known
choice -- in this corpus it's the minority value, not the safe default.**
Ask whether the sample was alkylated before reaching for a precedent;
only fall back to the closest matching row if the user genuinely doesn't
know, and say explicitly that it's a precedent-based guess, not a fact
about their sample.

One dataset (project 20, PXD049969) needs the modification set per raw
file, not per project: only its 3 `*_1DLC_alkylated_*` files are C57,
the other 124 are none -- the study was literally comparing sample-prep
methods, alkylation included, as an experimental variable.

## Known Data-Quality Caveats

- **Project 25 (MSV000079978)**: TopRepo's own supplementary table says
  this subdataset is all-CID. It's wrong -- the real per-file metadata
  table shows 24 CID + 16 ETD, matching the ETD-named files exactly.
  This is the only place in the whole corpus where the two sources
  disagree. If pulling training data from this project for
  `pdpred_pipeline`, exclude the 16 ETD files -- TD-Pred was trained
  only on HCD/CID.
- **Project 17 (PXD029792)**: 3 of 107 files have ambiguous names (both
  "CID25" and "HCD30" appear in the filename). Both sources say CID for
  all of them, but since both come from the same TopRepo curation, that
  agreement isn't independent confirmation. Low priority -- only the
  real scan headers would settle it.
- **Project 3's species label** ("E. coli K-12 25922") is
  self-contradictory in every source that repeats it -- ATCC 25922 is
  not a K-12 strain. Doesn't affect any parameter; don't repeat the
  label as though it were unambiguous.
- **General lesson, not specific to any one row**: when two sources
  "agree" but share the same upstream curation, that's not independent
  confirmation. Check whether sources are actually independent before
  treating agreement as settled -- this is exactly how the project 25
  discrepancy was caught (the file names, a genuinely independent
  source, disagreed with the curated table).

## Anti-Patterns

| Pattern | Problem | Fix |
|---|---|---|
| Defaulting `-f` to C57 because it's the well-known/common choice | Only ~19% of this corpus's files used it -- it's the minority, not a safe default | Ask whether the sample was alkylated; use a precedent only as a fallback, and say so explicitly |
| Treating this skill as a source of per-dataset TopFD/TopPIC numeric tuning | Almost the entire corpus shares one parameter set -- only `-f`/dissociation/separation/FAIMS genuinely vary | Read "What's Corpus-Wide, Not Per-Dataset" before citing a row as if every field were dataset-specific |
| Citing `dissociation_S5` without checking `dissociation_meta` | The two disagree for project 25, and S5 is the one that's wrong there | Trust `dissociation_meta` where they differ |
| Presenting a loosely-matching species/instrument as a confident precedent | A thin match stated with false confidence is worse than admitting there's no precedent | State how close the match actually is; say plainly when nothing matches well |
| Citing "TopRepo data" or "the corpus" without naming the specific project/accession | Not checkable, not useful to the user | Always name the project number, accession, and publication when a row informs a recommendation |
| Treating two sources that share the same upstream curation as independent confirmation | That's exactly how project 25's wrong supplementary-table value went unnoticed until file names (a genuinely separate source) were checked | Ask whether two "agreeing" sources actually derive from different origins before trusting the agreement |

## Resources

- `resources/toprepo_datasets_phase1.tsv` -- the lookup table, 112 rows
  (one per subdataset), columns described above.
- `resources/toprepo_datasets_phase1.md` -- the full research write-up:
  source provenance, integrity checks against this project's own
  `toprepo_file_info_v1.2.1.tsv`, the complete 38-project table, and
  every cross-check against the original papers (including which values
  are directly from TopRepo's own curation vs. inferred from reading an
  original paper, and the confidence/source tag on each).
- `resources/build_phase1_table.py` -- regenerates the TSV from
  TopRepo's own supplementary Excel file (tables S1/S3/S5/S6) plus the
  toprepo.org per-file metadata table(s). Re-run it if TopRepo publishes
  an updated supplement or adds new datasets.

**Source**: Li K, Liu K, Fulcher JM, Kaulich PT, Tang H, Liu X.
Comprehensive top-down mass spectral repository enables pan-dataset
analysis and top-down spectral prediction. bioRxiv 2026,
doi:10.64898/2026.02.20.707032 (v2). Cross-checked against this
project's own
`skills/toprepo_pipeline/vendor/resources/toprepo_file_info_v1.2.1.tsv`
(every row in the lookup table above joins to it with zero mismatches).

**Related skills**: `toppic_suite` (uses this for `-f`), `pdpred_pipeline`
(uses this for dissociation-method compatibility), `ms_process` and
`toprepo_pipeline` (FAIMS and exact-dataset-match awareness).
