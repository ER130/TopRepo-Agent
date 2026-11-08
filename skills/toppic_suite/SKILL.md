---
name: toppic_suite
description: |
  Run the raw-data-to-identification chain that sits upstream of
  toprepo_pipeline -- installed natively on Ubuntu (including Ubuntu
  under WSL on Windows) or macOS, per toppic-suite's own build
  instructions, with the user running the root steps: TopFD
  (centroided mzML -> deconvoluted msalign + LC-MS
  feature files, from https://github.com/toppic-suite/toppic-suite), and
  TopPIC (msalign + feature + FASTA -> PrSM identification TSV, same repo).
  Use when users:
  (1) ask to build, install, compile, or run TopFD, TopPIC, or "toppic-suite"
  (2) have a centroided mzML/mzXML file (from a raw file: run the
      msconvert skill first) and want it deconvoluted and/or searched
      against a protein database
  (3) ask what topfd/toppic flags do, or hit a build error for this repo
  (4) mention PrSM, proteoform identification, spectral deconvolution,
      isotopic envelope while preparing data for TopRepo/TD-Pred
  Keywords: TopFD, TopPIC, toppic-suite, deconvolution,
  isotopic envelope, feature detection, PrSM, FASTA search, EnvCNN, MIScore
requires: [pipeline_common]
---

# TopPIC Suite (TopFD -> TopPIC)

Planning, Mode A/B, long-running commands and reporting follow
`pipeline_common` (loaded with this skill). This skill adds the TopFD /
TopPIC specifics.

## The Core Philosophy

> **This repo's own manuals lag behind what you actually build -- trust `--help`, not `doc/*.md`.**

`topfd --help`/`toppic --help` disagree with
`skills/toppic_suite/vendor/doc/topfd_manual.md` and `toppic_manual.md`
on real things: changed defaults (`topfd`'s ECScore cutoff: 0.5 in the
manual, 0.1 in the binary), flags whose meaning flipped (`-f` was opt-in
`--additional-feature-search`, is now opt-out
`--disable-additional-feature-search`), flags the manual doesn't mention
(`-R`/`--proteoform-type` on `toppic`, `-v`/`--env-cnn-cutoff` and
`-l`/`--split-intensity-ratio` on `topfd`) -- and builds that all report
1.9.0 differ from each other (step 2). Build every command from the
installed binary's `--help`, never from the manual or memory.

toppic-suite's source is vendored into `skills/toppic_suite/vendor/`,
frozen at `vendor/VENDORED_COMMIT.txt` -- never edit it.

**Raw vendor files (.raw/.d) aren't this skill's job**: the `msconvert`
skill converts them to centroided mzML first.

## When to Use This

- The user has mzML/mzXML that hasn't been through TopFD/TopPIC yet --
  this is the step **before** `toprepo_pipeline`
- The user wants to build/install TopFD or TopPIC, or asks what a flag does
- The user has TopFD `.msalign`/`.feature` output and a FASTA, and wants
  proteoform identification (PrSM) results
- **Not this skill**: once you have `*_toppic_prsm_single.tsv` and the
  matching mzML/msalign/feature files, move on to `toprepo_pipeline`

## Before the plan, check

Read-only (`pipeline_common`, "Check first"):
- TopFD/TopPIC installed: Prerequisites step 1. Not installed -> the
  install flow becomes the plan's first part; say up front that it needs
  the user for two root steps.
- The input: a centroided mzML with MS2 spectra (`msconvert`'s step-4
  check). Vendor raw files -> `msconvert` first, with its own checks.
- The FASTA: exists, isn't empty, starts with `>` (`head -c 200`). None
  given -> ask for it instead of a plan; never write or download one.
- `-f`: run `lookup_file.py` on the input now (Parameters below).

## Parameters to recommend (Mode B)

- `-u` (threads, both tools): the default, 1, is essentially never right.
  `cores - 1`, lower if memory is short (`hardware_check.md`); the plan
  says e.g. "16 cores -> `-u 15`".
- TopFD `-a`/`-o`/`-g`: `-o` only once you've checked the input lacks MS1
  spectra; `-g` only if the user doesn't need HTML **and** this machine's
  `topfd --help` says `-g` skips HTML (step 2's flag notes); `-a` stays
  at its default (activation read per spectrum from the input).
- TopPIC `-f` has no default and no safe guess -- it follows the sample
  prep (iodoacetamide -> C57; iodoacetic acid -> C58; none). Decide it in
  `param_precedents`' order: the input's own corpus entry
  (`python3 skills/param_precedents/scripts/lookup_file.py <input file>`;
  a hit decides it) -> the user's answer -> if the user doesn't know, the
  data itself ("Deciding `-f` from the data", step 3). Never from how
  common a value is, or from a similar dataset. Until decided, the plan
  says "`-f`: to be decided by trial runs".
- TopPIC `-d`: on for any real run -- without it, filtering uses raw
  E-values instead of an FDR estimate. Off only for a quick smoke test.
- `-x`/`-b`/`-B`: `-x` only once you've confirmed there's no matching
  `.feature` file; `-b`/`-B` from `toppic --help`, not memory.

## Prerequisites

TopFD/TopPIC are installed natively, following toppic-suite's own build
instructions (`vendor/UPSTREAM_README.md`). This flow is the expected
setup: follow it without asking. There is no Docker path.

**Memory**: the tools' docs ask for at least 16 GB for real datasets --
a real constraint. With less, say so before a big job (effect on `-u`:
`hardware_check.md`).

### Step 1 -- is it already installed?

Once per session, before anything else in this skill:
```
topfd --help 2>&1 | head -1             # e.g. "TopFD 1.9.0.0"
toppic --help 2>&1 | grep -m1 Version   # e.g. "Version: 1.9.0.0"
```
- **Both run and report 1.9.x** -> use them and skip the rest of
  Prerequisites.
- **Both run, but report another version** -> tell the user in one line
  and carry on. Don't ask them to choose and don't reinstall:
  > ⚠️ Found TopFD/TopPIC <version>. This skill was verified against
  > 1.9.0, so output files and flag defaults may differ slightly.

  Say it only the first time this session. If one of this skill's output
  checks fails later, name the version difference as the likely cause.
- **Not found, or `--help` errors** -> step 2.

### Step 2 -- which instructions

The agent only runs on Linux or macOS (`code.py` needs POSIX), so on a
Windows PC it is running inside WSL -- and WSL's Ubuntu is the system to
install into. Check once:
```
uname -s                                       # Linux or Darwin
grep -E '^(ID|VERSION_ID)=' /etc/os-release    # Linux only
```
- **Ubuntu, including Ubuntu under WSL** -> the Ubuntu commands below.
  Upstream documents Ubuntu 24.04; other releases usually work but aren't
  verified -- put the release in the plan.
- **macOS** -> the macOS commands below. Copied from upstream and **not
  verified by this project** -- say so in the plan.
- **Anything else** (another Linux distro, WSL with a non-Ubuntu distro)
  -> tell the user this skill supports Ubuntu and macOS only, and stop.
  Never use upstream's MSYS2 guide (`vendor/doc/windows_build.md`): it
  builds Windows `.exe` files, not the Linux binaries the agent runs.

### Step 3 -- the user installs the dependencies (needs root)

You can't run these yourself: `code.py` blocks any command containing
`sudo`, and the bash tool has no terminal to type a password into. Give
the user the commands for their OS, ask them to run them in their own
terminal (on Windows: an Ubuntu/WSL terminal), and wait for them to say
it's done.

Ubuntu:
```
sudo apt update
sudo apt install build-essential cmake clang libboost-all-dev libxerces-c-dev \
    libsqlite3-dev zlib1g-dev rapidjson-dev qtbase5-dev
```

macOS (Homebrew refuses `sudo`, so none here; if `brew` itself is
missing, send the user to https://brew.sh first):
```
brew install boost xerces-c sqlite3 zlib onnxruntime rapidjson cmake qt@5
```

`qtbase5-dev`/`qt@5` are for the GUI tools. They stay in the list because
`make install` builds and installs every target, GUIs included -- without
Qt, step 5 fails.

### Step 4 -- you build (no root)

If `skills/toppic_suite/vendor/bin/topfd` already exists from an earlier
build that finished, skip to step 5. Otherwise, in the background:
```
cd skills/toppic_suite/vendor
mkdir -p build && cd build
cmake ..
make -j<cores>
```
Build the full target set as upstream does, not `make topfd toppic`:
step 5's `make install` builds anything still missing first, which would
then compile the rest as root in the user's terminal.

- **Succeeds** -> step 5.
- **Fails** -> stop. Show the user the first error in the output (not
  just the last lines), the OS release from step 2, and `cmake --version`
  and `clang --version`. Don't edit `vendor/`, don't try another way of
  installing, and don't install other packages without asking.

### Step 5 -- the user installs (needs root)

Ask the user to run, in their own terminal:
```
cd <absolute path of skills/toppic_suite/vendor/build>
sudo make install
```
Give them the real absolute path (`pwd` from `vendor/build`) -- on
Windows that's a `/mnt/<drive>/...` path, run from the Ubuntu/WSL
terminal. This installs into `/usr/local/bin` (plus `/usr/local/lib/toppic`
and `/usr/share/toppic` on Linux, or `resources/` beside the binaries on
macOS). Wait for them to say it's done. Don't run the binaries from
`vendor/bin/` instead: without the install they can't find their
`resources/` folder (`The resource directory ... does not exist!`).

### Step 6 -- verify

1. `topfd --help 2>&1 | head -1` and `toppic --help 2>&1 | grep -m1 Version`
   should both report 1.9.0.
   - Linux, `error while loading shared libraries: libonnxruntime.so...`
     -> the installed binary can't find the ONNX Runtime library that
     `make install` put in `/usr/local/lib/toppic`. Ask the user to run
     `echo /usr/local/lib/toppic | sudo tee /etc/ld.so.conf.d/toppic.conf && sudo ldconfig`,
     then check again. Only on this error -- an install that finds the
     library on its own needs nothing.
   - `Could not load a transcoding service` -> a locale problem upstream
     documents. Ask the user to add `export LC_ALL=en_US.UTF-8` and
     `export LANG=en_US.UTF-8` to `~/.bashrc`, open a new terminal, and
     restart the agent.
2. Smoke test on the bundled fixture, in a scratch folder (not `runs/`,
   not `<ms_dir>`):
   ```
   mkdir -p /tmp/toppic_smoke
   cp skills/toppic_suite/vendor/tests/data/mzxml_test.mzXML /tmp/toppic_smoke/
   cd /tmp/toppic_smoke && topfd -u 2 mzxml_test.mzXML > topfd.log 2>&1; tail -2 topfd.log; ls -la
   ```
   It passes when the log ends with `TopFD finished.` and
   `mzxml_test_ms2.msalign` and `mzxml_test_ms2.feature` exist and aren't
   empty (4 MS1 + 12 MS/MS scans, a few seconds). Leave
   `/tmp/toppic_smoke` where it is (`/tmp` is cleared on reboot, and
   deleting outside `runs/` would ask the user for approval for nothing).
   If it fails, stop and show the user the log.

## Pipeline

Keep a dataset's mzML, FASTA, and TopFD/TopPIC output together in one
directory, `<ms_dir>` -- by default `runs/<run_name>/01_toppic_suite/`
(`run_layout.md`; append a `run_log.txt` line when you create it). Use an
existing folder for this dataset if there is one; resolve it once and
reuse it for every step. **`uploads/` is never `<ms_dir>`** -- it's where
the web UI drops every upload for all datasets; copy inputs from there.

### 1. Input mzML

Raw vendor files: the `msconvert` skill first. An mzML the user gave you:
run `msconvert`'s output check (its step 4) before TopFD -- it must be
centroided and have MS2 spectra.

### 2. TopFD -- deconvolute mzML/mzXML to msalign + feature files

In the background (`pipeline_common`), from `<ms_dir>`:
```
cd <ms_dir> && topfd -u <threads> <input>.mzML > topfd_<input>.log 2>&1
```
A TopFD run that was killed leaves partial output -- typically just the
MS1 part, since TopFD finishes MS1 before MS2. An "MS1-only" result has
always meant a killed run, never the data.

A finished TopFD run writes these into `<ms_dir>`:

- **Always**: `<input>_ms2.msalign`, `<input>_ms2.feature`,
  `<input>_feature.xml`, plus `<input>_ms1.msalign` and
  `<input>_ms1.feature` unless the run used `-o`.
- **Depends on the build -- never use these to judge a run**: an
  `<input>_html/` folder and/or an `<input>.sqlite` database. Builds that
  all report themselves as 1.9.0 differ here: the vendored source writes
  `_html/` (skippable with `-g`); another 1.9.0 build writes
  `<input>.sqlite` ("SQLite database output: Yes" in its log) and no
  `_html/`. A `.sqlite` next to complete output is normal.

The `<input>_ms2.msalign` fields (`FILE_NAME`, `SCANS`, `ACTIVATION`,
`PRECURSOR_CHARGE`, ...) are exactly what `toprepo_pipeline`'s Phase 1
expects.

**Flags come from `topfd --help`.** `param_precedents` lists TopRepo's
corpus values (max charge 30, max mass 70,000 Da, ...) as numbers, not
flag names: map each to a flag `--help` lists, or leave it at the default
and say so. Never write a flag `--help` doesn't list (`-max_charge`,
`-window` aren't real).

**After it completes, check before going on.** Good when all hold:
```
tail -1 topfd_<input>.log                      # TopFD finished.
grep -c '^BEGIN IONS' <input>_ms2.msalign      # > 0
grep -m3 '^LEVEL=' <input>_ms2.msalign         # LEVEL=2
ls -la <ms_dir>                                # the "Always" files above, none empty
```
If any check fails, or the files differ from the "Always" list (a bare
`<input>.msalign`, split `<input>_ms1.msalign_0` .. `_7`, no `_ms2`
file), **stop and show the user** `ls -la <ms_dir>`, the log's last
lines, and the first line of `topfd --help`. Don't explain the difference
away, and never conclude "the data has no MS/MS" -- count MS2 in the
input instead: `grep -c 'name="ms level" value="2"' <input>.mzML`. Usual
cause: a killed run (no `TopFD finished.`); next: a version other than
1.9.0.

Useful flags (from the real `--help`): `-a` activation (default `FILE`,
read per spectrum -- don't override unless the input lacks it); `-u`
threads (default 1 -- always set it). **`-g` differs between builds**:
in the vendored source it skips HTML, but another 1.9.0 build uses `-g`
for `--frag-num-filtering`, which changes the deconvolution itself --
read this machine's `--help` before passing it, and never pass it just to
skip HTML. `-m` max mass: 50,000 Da by default in 1.9; TopRepo used
70,000 Da (TopFD 1.7.10). Keep the default -- PDpred only takes
sequences up to 200 residues (~22 kDa) by default -- unless the user wants
TopRepo's exact setting or expects proteoforms above 50 kDa. `-o` if the
input has no MS1 spectra (fixture: `tests/data/mzxml_test_no_ms1.mzXML`).

### 3. TopPIC -- search msalign against a FASTA for proteoform identification

In the background, from `<ms_dir>` (FASTA there too), only after TopFD
passed step 2's check:
```
cd <ms_dir> && toppic -u <threads> -f C57 <database>.fasta <input>_ms2.msalign \
    > toppic_<input>.log 2>&1
```

**Argument order: FASTA first, msalign second** -- `toppic [options]
database-file-name spectrum-file-name`. It has been reversed before when
the command was retyped from memory; copy it from here or `--help`.

**The spectrum file is always `<input>_ms2.msalign`, never `_ms1`.**
TopPIC matches fragment ions, which only MS/MS (`LEVEL=2`) spectra have.
On an MS1 file it runs for hours without an error and produces
meaningless results (an agent once started a 32-48 h batch on eight
`_ms1.msalign_N` files). No `_ms2.msalign` -> back to TopFD's check, and
tell the user.

**Several input files: one at a time** (TopFD too), each with the full
`-u`. Two runs at once oversubscribe the CPU, and two TopPIC runs against
one FASTA also compete for its `<database>.fasta_idx/` index.

TopPIC finds the matching `<input>_ms2.feature` in the same directory by
name (`-x` if you deliberately have none) and writes
`<input>_ms2_toppic_prsm.tsv`, `<input>_ms2_toppic_prsm_single.tsv`,
`<input>_ms2_toppic_proteoform.tsv`, `<input>_ms2_toppic_proteoform_single.tsv`,
matching XML files and (build-dependent) an `<input>_html/` folder.
Downstream uses `*_prsm_single.tsv`.

`-f C57`/`-f C58` sets the fixed cysteine modification (carbamidomethylation/
carboxymethylation). `-d` runs a decoy search to estimate FDR; without it,
filtering uses raw E-values (`-t`/`-v`/`-T`/`-V`).

**The first run against a FASTA builds `<database>.fasta_idx/`** and later
runs reuse it -- **even after the FASTA changes** (verified: it isn't
rebuilt). Whenever the FASTA content changes, delete
`<database>.fasta_idx/` or use a new file name.

**Deciding `-f` from the data** (only when the user doesn't know the
sample prep). Run TopFD as usual first; the trials reuse its output.

1. **One trial file decides for the whole dataset** (one sample prep).
   Candidates: `none` and C57; add C58 only if iodoacetic acid is
   plausible. Up to ~3,000 MS2 spectra: the whole `_ms2.msalign`.
   Larger: every k-th spectrum, k = total / 1,000 rounded up:
   ```
   grep -c '^BEGIN IONS' <input>_ms2.msalign          # total
   awk -v k=<k> '/^BEGIN IONS/{n++; keep=((n-1)%k==0)} n==0||keep' \
       <input>_ms2.msalign > trial_<value>/<input>_ms2.msalign
   ```
   (Not yet verified with TopPIC on a subset -- if it errors, use the
   whole file and say so.)
2. **One folder per candidate** (`trial_none/`, `trial_C57/`, ...), each
   with the msalign and a copy of `<input>_ms2.feature` under the same
   base name. Run `toppic` with the real run's flags (`-u`, `-d`) plus
   that candidate's `-f` (none: no `-f`), one at a time, in the background.
3. **Compare** each folder's `*_prsm_single.tsv`:
   - PrSMs at the 1% FDR cutoff (rows) -- the main measure.
   - Identified proteoforms containing C -- the most sensitive to `-f`: a
     wrong choice leaves each cysteine 57 Da off, which TopPIC can only
     explain as an unexpected shift (one allowed by default), so Cys-rich
     proteoforms drop out.
   - In the `none` run, unexpected shifts near +57.02 Da on cysteines (or
     -57.02 Da in the C57 run) point to the other value.
4. **Decide.** A candidate wins with at least 10% more PrSMs and agreeing
   cysteine evidence. With fewer than ~50 PrSMs in every run, or a
   smaller or contradictory difference, the data can't tell: show the user
   the numbers and let them choose. Record the result in the plan and
   `run_log.txt`, e.g. "`-f` C57 -- trial on 1,000 spectra of st_1: C57
   401 PrSMs vs none 312; 38 vs 9 Cys-containing proteoforms".
5. **Don't redo the winner.** A whole-file trial used the real run's
   flags, so its output *is* that file's result -- move it into `<ms_dir>`
   and run only the remaining files. (A subset trial is just a test: run
   that file in full afterwards.)

## Reporting back

As in `pipeline_common`, plus: the real `Version:` line from `--help`,
and the right terms -- mzML is undeconvoluted input, msalign is TopFD's
deconvoluted output.

## Checklist before each command

- Flags from this machine's `--help`, not the manual, memory or the corpus
  table -- and check what `-g` means here.
- TopFD/TopPIC in the background, one file at a time, `-u` set.
- `toppic <fasta> <input>_ms2.msalign` -- FASTA first, `_ms2` only.
- TopFD done = `TopFD finished.` + the "Always" files; `_html/`/`.sqlite`
  prove nothing either way.
- FASTA changed -> delete `<database>.fasta_idx/` first.
- `-f` from the input's own corpus entry, the user, or trial runs --
  never from a similar dataset.

## Resources

**Vendored** (`skills/toppic_suite/vendor/`, from
https://github.com/toppic-suite/toppic-suite at `vendor/VENDORED_COMMIT.txt`;
`resources/topmsv/node_modules/` was left out -- web-visualization
tooling the CLI doesn't use):
- `vendor/UPSTREAM_README.md` -- the build instructions Prerequisites follows
- `vendor/doc/topfd_manual.md`, `toppic_manual.md` -- output-file
  descriptions and worked examples, **not** flag defaults
- `vendor/doc/windows_build.md` -- upstream's MSYS2 Windows build. **Not
  used**: on Windows the agent runs inside WSL and installs the Linux build.
- `vendor/tests/data/mzxml_test.mzXML`, `mzxml_test_no_ms1.mzXML` --
  bundled fixtures; the first is Prerequisites step 6's smoke test

**Related skills**: `msconvert` (before: raw -> centroided mzML),
`toprepo_pipeline` (next: merges this skill's output and annotates it),
then `ms_process`, `pdpred_pipeline`.
