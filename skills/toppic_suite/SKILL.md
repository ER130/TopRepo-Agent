---
name: toppic_suite
description: |
  Run the raw-data-to-identification chain that sits upstream of
  toprepo_pipeline -- by default compiling locally on Ubuntu/macOS, per
  toppic-suite's own build instructions, or through the official
  `toppicsuite/toppic` Docker image on Windows or any other OS: TopFD
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
---

# TopPIC Suite (TopFD -> TopPIC)

## The Core Philosophy

> **This repo's own manuals lag behind what you actually build -- trust `--help`, not `doc/*.md`.**

Verified directly: this skill was written against a real build of HEAD
(reports itself as `Version: 1.9.0`), and `topfd --help`/`toppic --help`
disagree with `skills/toppic_suite/vendor/doc/topfd_manual.md` and
`toppic_manual.md` on real things -- default values that changed
(`topfd`'s ECScore cutoff is documented as 0.5, the built binary's default
is 0.1), flags whose meaning flipped (`-f` was opt-in
`--additional-feature-search`, is now opt-out
`--disable-additional-feature-search`), and flags the manual doesn't
mention at all (`-R`/`--proteoform-type` on `toppic`, `-v`/`--env-cnn-cutoff`
and `-l`/`--split-intensity-ratio` on `topfd`). Don't quote a flag's
default or meaning from the manual without cross-checking `--help` from
the binary you actually have.

toppic-suite's source is vendored into `skills/toppic_suite/vendor/` (see
Prerequisites) so building doesn't depend on GitHub being reachable --
but it's still frozen at the commit in `vendor/VENDORED_COMMIT.txt`, not
ours to modify; fix problems from this skill's own layer, not by
hand-editing anything under `vendor/`.

**Raw vendor files (.raw/.d) aren't this skill's job**: load the
`msconvert` skill first -- it converts them to centroided mzML and checks
the result. Start here once you have that mzML.

## When to Use This

- The user has mzML/mzXML that hasn't been through TopFD/TopPIC yet --
  this is the step **before** `toprepo_pipeline` (raw files: `msconvert`
  skill first)
- The user wants to build/install TopFD or TopPIC, or asks what a flag does
- The user already has TopFD `.msalign`/`.feature` output and a FASTA, and
  wants proteoform identification (PrSM) results
- **Not this skill**: once you have `*_toppic_prsm_single.tsv` and the
  matching mzML/msalign/feature files, move on to `toprepo_pipeline`

## Before You Start

**Check the machine first.** Read `skills/_shared/hardware_check.md` and run its
step-1 commands (cores, memory, GPU, disk, where the data is) before
writing the plan. Thread counts and run order come from its table, and
the plan shows the check's results next to the values chosen.

**Plan first, then confirm.** Before running anything below, lay out the
plan for the task -- which of Prerequisites/Pipeline steps apply, in what
order, against which files -- and wait for the user to confirm it before
executing. This is a real build-and-run workflow with real failure modes
(see Core Philosophy); catching a wrong assumption (wrong input file,
wrong FASTA, wrong thread count) before anything runs is much cheaper
than after.

**Ask which mode before writing the plan: A (quick) or B (detailed).**
Check this session's conversation so far for an earlier answer first --
if the user already picked a mode earlier in this same session, reuse it
without asking again; a new session (e.g. the user closed and reopened
the agent) has no earlier answer to find, so ask fresh. Mode A: a concise
plan -- steps and files only, skip the parameter list below. Mode B: the
detailed plan below, with parameter values and why. Wait for the answer
before writing the plan either way.

**Mode A still means reasoning through each value, just not displaying
it.** Work out the same recommended values as Mode B below before you
actually run anything -- Mode A only changes what the *plan* shows, never
a license to fall back to the tool's raw default unexamined. If a value
genuinely needs the user's input to pick (e.g. `-f`, which has no
default), ask for it even in Mode A -- the plan stays concise, the
missing decision still can't be skipped.

**In Mode B, reason about each parameter and recommend a value -- don't
just surface the tool's default and ask "is this OK."** For each flag
below, work out what it actually controls, decide whether the hard-coded
default fits this specific run, and state your own recommended value with
a short reason -- say explicitly when the recommendation differs from the
default, and just as explicitly say "the default is right here, because
..." when it isn't.

- `-u` (threads, both tools): the default is 1, which is essentially never
  the right value. Use `skills/_shared/hardware_check.md`: `cores - 1`, lower
  if memory is short, and the plan says e.g. "16 cores -> `-u 15`".
- `-a`/`-o`/`-g` on TopFD: recommend `-o` only once you've checked the
  input actually lacks MS1 spectra; recommend `-g` only if the user has
  said the HTML output isn't needed; otherwise recommend leaving `-a` at
  its default (reads activation per-spectrum from the input).
- `-f` on TopPIC has no default and no safe guess -- it follows the
  sample prep (iodoacetamide alkylation -> C57; iodoacetic acid -> C58;
  none). Decide it in `param_precedents`' order ("Deciding `-f`"): the
  input's own corpus entry (`python3
  skills/param_precedents/scripts/lookup_file.py <input file>`) -> the
  user's answer -> **if the user doesn't know, the data itself** (see
  "Deciding `-f` from the data" under step 3). Never pick it from how
  common a value is in the corpus or in a similar dataset. Until it's
  decided, the plan says "`-f`: to be decided by trial runs", not a
  recommendation.
- `-d` on TopPIC: recommend turning it on for any real identification run
  -- without it, filtering falls back to raw E-values instead of an FDR
  estimate, which is rarely what's actually wanted (reasonable to skip
  only for a quick smoke test).
- `-x`/`-b`/`-B`: recommend `-x` only once you've confirmed there's no
  matching `.feature` file for the input; for `-b`/`-B`, check `toppic
  --help` for what's actually installed before recommending a value
  rather than assuming from memory.

State the recommendation, then ask whether the user wants to keep it or
change it before you execute -- confirm back any changed value before
using it.

**Report before installing something new or touching a script.** The
apt packages and build steps already listed under Prerequisites are the
expected setup -- run those without asking. But if the build or a run
hits something Prerequisites doesn't already cover (a missing/wrong-version
system library, a compiler too old, anything needing an `apt install`
beyond the documented list), or if fixing it would mean editing a file
under `vendor/` (never do this silently -- see Core Philosophy), stop and
tell the user exactly what went wrong and what you're about to do about
it. Wait for their response before continuing.

**This explicitly includes Docker itself, on the OSes that need it.** If
the user isn't on Ubuntu or macOS, Docker is the only path this skill
offers (see Prerequisites) -- if Docker isn't installed, that's a real,
unavoidable instance of "something new": point the user to the right
installer for their OS and stop there. Don't attempt to install Docker
Desktop yourself (it needs a GUI/admin install on every OS) and don't
attempt a native Windows build instead just because Docker isn't there
yet (see Prerequisites for why). Wait for the user to confirm Docker is
installed and running before re-checking.

## Prerequisites

**Check for an existing build first.** `which topfd toppic` (already on
`PATH`), or a previous build under `skills/toppic_suite/vendor/build/` --
if either already works (`topfd --help` runs cleanly), use it directly and
skip everything below. Don't rebuild, and don't switch to Docker, just
because this section mentions both paths.

**Which path to take depends on the OS, checked once per machine:**
- **Ubuntu** -> compile from source, see "Building from source" below.
  This is the path this skill has actually verified end to end (Clang 18,
  CMake 3.28, Boost 1.83 from apt all worked).
- **macOS** -> also compile from source, via Homebrew, see "Building from
  source" below. This is copied from toppic-suite's own upstream README,
  not independently verified this session -- say so when you use it.
- **Everything else** (Windows, or any OS that isn't Ubuntu/macOS) -> use
  the official `toppicsuite/toppic` Docker image, see "Docker" below.
  **Don't attempt a native Windows build**, even though the upstream repo
  documents one (`vendor/doc/windows_build.md`, MSYS2-based) -- this
  skill specifically routes Windows to Docker, not to that doc.

**Memory**: TopFD/TopPIC's own docs say "at least 16 GB memory" for real
datasets. This is a real constraint on large LC-MS runs, not boilerplate --
if the machine has less, say so before launching a big job rather than
letting it OOM partway through. How that affects `-u`: `skills/_shared/hardware_check.md`.

### Docker (Windows, or any OS other than Ubuntu/macOS)

Docker sidesteps the whole C++ toolchain and every failure mode documented
under "Building from source" below (missing/wrong-version libraries, the
broken RPATH after `make install`, compiler availability) at the cost of
one upfront Docker install.

**Step 1 -- is Docker installed and running?**
```
docker info
```
- **Command not found**: Docker isn't installed. Stop, tell the user, and
  send them to install it based on their OS -- then wait for their
  confirmation it's installed before continuing (per Before You Start):
  - **Windows**: Docker Desktop (https://www.docker.com/products/docker-desktop/).
    It needs WSL2 as its backend -- check `wsl --status` first; if WSL2
    isn't set up, that has to happen before (or during) the Docker Desktop
    install, or the installer falls back to the slower Hyper-V backend or
    fails outright.
  - **Any other non-Ubuntu/macOS system** (other Linux distros, BSDs,
    etc.): either Docker Desktop for Linux, or the lighter Docker Engine
    via the distro's package manager (e.g. `apt install docker.io` on
    Debian-family distros, or the official convenience script at
    get.docker.com) -- no GUI needed for what this skill does. After
    install, add the user's account to the `docker` group so `docker`
    runs without `sudo` (`sudo usermod -aG docker $USER`, then log out/in
    or `newgrp docker`) -- the single most common "installed but still
    doesn't work" snag on Linux.
- **Found, but `docker info` errors or hangs**: Docker is installed but
  the daemon isn't running. Tell the user to start Docker Desktop (or, on
  a native Linux install, `sudo systemctl start docker`) and confirm
  before retrying -- don't re-send install instructions for something
  that's already installed, that's a different problem with a different fix.
- **Succeeds**: Docker is ready, move to Step 2.

**Step 2 -- is the image already pulled?**
```
docker image inspect toppicsuite/toppic
```
Errors with "No such image" -> pull it (verified ~461.7 MB):
```
docker pull toppicsuite/toppic
```
Succeeds -> already pulled, skip straight to Pipeline below -- don't
re-pull on every run.

**The image itself is stale**: Docker Hub shows it hasn't been updated in
5+ years, so its TopFD/TopPIC version -- and default flag values, see Core
Philosophy -- may not match what this skill verified against a fresh HEAD
build. Fine for validating that the pipeline mechanically works; if the
user cares about matching the latest algorithm versions and is on
Ubuntu/macOS, say so and point them at the native build below instead.

### Building from source (Ubuntu or macOS)

Look for an existing build/install first (see "Check for an existing
build" above) -- rebuilding from scratch each time wastes real time on
this codebase's size. Otherwise build the vendored source directly (no
clone needed).

**Ubuntu** -- verified end to end (Clang 18, CMake 3.28, Boost 1.83 from
apt all worked; the upstream README also documents Redhat 9, see
`vendor/UPSTREAM_README.md`):
```
cd skills/toppic_suite/vendor
apt install build-essential cmake clang libboost-all-dev libxerces-c-dev \
    libsqlite3-dev zlib1g-dev rapidjson-dev qtbase5-dev   # qtbase5-dev only needed for the GUI targets
mkdir -p build && cd build
cmake ..
make -j$(nproc) topfd toppic   # console tools only -- skips the slow Qt GUI build; add topmg/topindex/topdiff/topdia if needed
make install                    # installs to /usr/local/bin, /usr/local/lib/toppic, /usr/share/toppic on Linux
echo /usr/local/lib/toppic > /etc/ld.so.conf.d/toppic.conf && ldconfig   # see "make install ships a broken binary" below -- not optional
```

**macOS** -- copied from the upstream README (`vendor/UPSTREAM_README.md`),
**not verified this session** -- say so if you use it, and confirm each
step actually works rather than assuming it matches the Ubuntu behavior
below:
```
cd skills/toppic_suite/vendor
brew install boost xerces-c sqlite3 zlib onnxruntime rapidjson cmake
brew install qt@5   # only needed for the GUI targets
mkdir -p build && cd build
cmake ..
make -j$(sysctl -n hw.ncpu) topfd toppic
make install
```
The RPATH bug documented below was only confirmed on Linux -- check
`otool -L` (the macOS equivalent of `readelf -d`) on the installed binary
before assuming it either does or doesn't apply on macOS.

All of `ext/{pwiz,boost,onnx,htslib,rapidxml,xml2json,catch}` and the
Linux ONNX Runtime `.so` (`lib/toppic/libonnxruntime.so`) are already
vendored for the Linux build -- no submodule init or separate ONNX Runtime
install needed there (macOS installs its own via `brew install
onnxruntime` above instead). `vendor/build/` and `vendor/bin/` are build
output (gitignored), not part of what's vendored -- don't expect them to
already exist on a fresh checkout.

**`make install` on its own ships a binary that cannot run (confirmed on
Linux).** Verified: `readelf -d /usr/local/bin/topfd` (and `toppic`) shows
**no RPATH/RUNPATH at all** after `make install`, so
`/usr/local/bin/topfd --help` fails with `error while loading shared
libraries: libonnxruntime.so.1.14.1: cannot open shared object file`
(exit 127) -- `libonnxruntime.so` sits in `/usr/local/lib/toppic/`, which
isn't a default linker search path and nothing points there. This is a
real bug in the project's own `CMakeLists.txt`: the
`-Wl,-rpath=$ORIGIN/../lib/toppic` flag is assigned to
`CMAKE_SHARED_LINKER_FLAGS`, which CMake only applies to *shared library*
targets, never to `add_executable` targets like `topfd`/`toppic` --
confirmed by contrast: the **build-tree** copy (`build/../bin/topfd`,
before `make install`) works fine and carries a different, working
absolute `RUNPATH` straight into the build tree's own `lib/toppic/`, which
`make install`'s copy doesn't inherit. The `ldconfig` line above (or
`export LD_LIBRARY_PATH=/usr/local/lib/toppic` per shell if you can't
write to `/etc`) fixes it persistently on Linux; do this immediately
after every `make install`, not just once if it happens to work the first
time you try running from the build tree. On macOS, check `otool -L`
instead, per the macOS build note above -- this hasn't been independently
confirmed to hit the same bug there.

**Skipping `make install`**: `topfd`/`toppic` look for their `resources/`
directory next to the executable first, then fall back to
`/usr/share/toppic` -- confirmed by reading `getResourceDir()` in
`src/common/util/file_util.cpp` and by running `topfd --help` and a real
deconvolution both before and after symlinking `skills/toppic_suite/vendor/resources`
next to the built binary. Without either, every run fails with `The
resource directory ... does not exist!`. `make install` handles this for
you; skip it only if you symlink or copy `resources/` next to wherever you
run `topfd`/`toppic` from.

**Raw vendor files** (Thermo `.raw`, Bruker `.d`, etc.) are converted to
centroided mzML by the `msconvert` skill, not here.

## Pipeline

Keep a dataset's raw file, mzML, and TopFD/TopPIC output together in one
directory, referred to below as `<ms_dir>` -- `toprepo_pipeline`'s Phase 1
reads directly from whatever ends up here, so wherever you pick, use it
consistently for the whole dataset.

**Resolving `<ms_dir>`**: don't assume a name -- check first. If the user
already has a folder for this dataset (they mentioned a path, or one
already exists with matching files in it), use that. Otherwise this is
`runs/<run_name>/01_toppic_suite/` -- see `skills/_shared/run_layout.md`
for what `<run_name>` is, the full `runs/` layout, and the `run_log.txt`
convention (append a line there when you create `<ms_dir>` for the first
time this run). Treat the default as a suggestion, not a requirement: a
local setup may already keep raw MS data somewhere else entirely (a data
drive, a folder per instrument run, whatever the user's lab already
uses). Resolve it once (ask if genuinely ambiguous) and reuse the same
path for every step below, rather than re-deriving or renaming mid-run.

### 1. Input mzML

Raw vendor files: load the `msconvert` skill first -- it converts them to
the centroided mzML TopFD needs. An mzML the user gave you: run the
`msconvert` skill's output check (its step 4) before TopFD -- it must be
centroided and have MS2 spectra.

### 2. TopFD -- deconvolute mzML/mzXML to msalign + feature files

**If you're on the native-build path (Ubuntu/macOS, per Prerequisites),**
run the installed binary directly from `<ms_dir>` (or give it an absolute
path):
```
cd <ms_dir> && topfd -u <threads> <input>.mzML > topfd_<input>.log 2>&1
```

**If you're on the Docker path (Windows, or any other OS),** `-v` needs an
**absolute** host path -- resolve `<ms_dir>` to one first (e.g.
`$(pwd)/<ms_dir>` if you're already in its parent) rather than passing a
relative path, which fails confusingly rather than with a clear error.
From a WSL shell, Docker Desktop's WSL2 integration resolves a WSL path
like `/mnt/d/...` correctly on its own; from native Windows PowerShell,
use the `D:\...` form instead.

```
docker run --rm -v <absolute path to ms_dir>:/data toppicsuite/toppic \
    topfd -u <threads> /data/<input>.mzML > topfd_<input>.log 2>&1
```
Either form: **run it with the bash tool's `run_in_background: true`,
exactly as written above -- no trailing `&`, no `nohup`.** A normal bash
call is killed after 120s, and TopFD on a real mzML file takes minutes.
`&`/`nohup` doesn't get around that either: the call's whole process
group is killed the moment it returns. Both mistakes kill TopFD partway
through and leave partial output behind -- typically just the MS1 part,
since TopFD finishes MS1 before MS2, plus a half-written `.sqlite`
(and `.sqlite-shm`). That's what an "MS1-only" result has been every
time on this project, never the data. With `run_in_background: true`
there's no time limit; the result arrives as a task notification on a
later turn, and you can `tail` the log meanwhile. A bash result saying
`Error: Timeout` means the command was killed: delete its partial
outputs and re-run it in the background -- don't read meaning into what
it left.

The underlying command and flags are the same binary this skill already
verified end to end against a source build (the mzXML test fixture
bundled at `skills/toppic_suite/vendor/tests/data/mzxml_test.mzXML`,
4 MS1 + 12 MS/MS scans, ~4.5s; see the image-staleness note under
Prerequisites for why the Docker image's exact version may differ) --
produces `<input>_ms1.msalign`, `<input>_ms2.msalign`, `<input>_ms1.feature`,
`<input>_ms2.feature`, `<input>_feature.xml`, and an `<input>_html/` folder,
written into `/data` inside the container and so landing directly in
`<ms_dir>` on the host (no separate copy-out step). The `<input>_ms2.msalign`
fields (`FILE_NAME`, `SCANS`, `ACTIVATION`, `PRECURSOR_CHARGE`, ...) match
exactly what `toprepo_pipeline`'s Phase 1 extraction scripts expect.

**Build the command from `topfd --help`, not from memory or the corpus
parameter table.** `param_precedents` lists TopRepo's corpus values (max
charge 30, max mass 70,000 Da, ...) as numbers, not flag names. Map each
one to the flag `--help` actually shows, and leave it at the default
(saying so) if you can't find a matching flag. Never write flags that
`--help` doesn't list: a plan once used `topfd -m ... -max_charge 30
-window 3`, none of which are real.

**"Finished" means the background task's notification arrived with
status `completed`, not that a file appeared.** Until then the run is in
progress; check on it with `tail topfd_<input>.log`. A run reported as
"only MS1 came out" at ~5% progress was just still running.

**After it completes, check the output set before going on.** All six
outputs above should be there, and `<input>_ms2.msalign` must exist and
hold `LEVEL=2` spectra (`grep -m3 '^LEVEL=' <input>_ms2.msalign`). If
it's missing, or the output looks different from the list above (for
example a bare `<input>.msalign`, split files like `<input>_ms1.msalign_0`
.. `_7`, a leftover `.sqlite`/`.sqlite-shm`, other names), **stop and show
the user** `ls -la <ms_dir>`, the last lines of the log, and the first
line of `topfd --help` (the version). Don't explain the difference away
and carry on -- and never conclude "the data has no MS/MS" from it.
Check the input directly instead: `grep -c 'name="ms level" value="2"'
<input>.mzML` counts its MS2 spectra. The usual cause is a run that was
killed partway (see above); a different TopFD version than the 1.9.0
this skill was verified against is the next suspect.

Useful flags (from the real `--help`, not the manual -- see Core
Philosophy): `-a` activation method (default `FILE`, i.e. read per-spectrum
from the input -- don't override this unless the input genuinely lacks
it), `-u` thread count (default 1 -- always set this explicitly on a
multi-core machine), `-g` to skip HTML generation if you don't need
visualization. `-m` max mass: 50,000 Da by default in this TopFD 1.9;
TopRepo itself used 70,000 Da (TopFD 1.7.10). Keep the default --
PDpred only takes sequences up to 200 residues (~22 kDa) anyway -- and
pass `-m 70000` only if the user wants TopRepo's exact setting or
expects proteoforms above 50 kDa. `-o`/`--missing-level-one` if the input has no MS1 spectra
(the tests/data mzxml_test_no_ms1.mzXML fixture is exactly this case).

### 3. TopPIC -- search msalign against a FASTA for proteoform identification

**Native-build path (Ubuntu/macOS):** run from `<ms_dir>`, where the
msalign/feature files from step 2 and the FASTA already live:
```
cd <ms_dir> && toppic -u <threads> -f C57 <database>.fasta <input>_ms2.msalign \
    > toppic_<input>.log 2>&1
```

**Docker path (Windows, or any other OS):** the FASTA has to live under
the same mounted directory as the msalign -- put it in `<ms_dir>` too (or
mount a second `-v` for it) so both paths resolve inside the container:
```
docker run --rm -v <absolute path to ms_dir>:/data toppicsuite/toppic \
    toppic -u <threads> -f C57 /data/<database>.fasta /data/<input>_ms2.msalign \
    > toppic_<input>.log 2>&1
```

Either form: **run it with `run_in_background: true`, no `&`** -- same
reason as TopFD: TopPIC on a real msalign file takes far longer than the
120s a normal bash call gets. Don't start it until TopFD's background
task has completed and passed the output check in step 2.

**Deciding `-f` from the data** (only when the user doesn't know the
sample prep -- see `param_precedents`, "Deciding `-f`"). Run TopFD as
usual first; the trials reuse its output.

1. **Pick the trial input.** Up to ~3,000 MS2 spectra: use one whole
   `_ms2.msalign` file. Larger: take one file (for a multi-file dataset,
   one or two typical files -- not every file) and keep every k-th
   spectrum, with k = total / 1,000 rounded up:
   ```
   grep -c '^BEGIN IONS' <input>_ms2.msalign          # total
   awk -v k=<k> '/^BEGIN IONS/{n++; keep=((n-1)%k==0)} n==0||keep' \
       <input>_ms2.msalign > trial_<value>/<input>_ms2.msalign
   ```
   (Not yet verified with TopPIC on a subset -- if TopPIC errors on it,
   use the whole file and say so.)
2. **One folder per candidate** -- `trial_none/`, `trial_C57/` (add
   `trial_C58/` only if iodoacetic acid is plausible). Each holds the
   msalign and a copy of `<input>_ms2.feature` under the same base name:
   TopPIC looks for `<msalign name without .msalign>.feature` next to the
   msalign. Run `toppic` with the same flags as the real run (`-u`, `-d`)
   plus that candidate's `-f` (none: no `-f`), one candidate at a time,
   in the background.
3. **Compare** in each folder's `*_prsm_single.tsv`:
   - PrSMs at the 1% FDR cutoff (the number of rows) -- the main measure.
   - Identified proteoforms containing C -- the one most sensitive to
     `-f`: a wrong choice leaves each cysteine 57 Da off, which TopPIC can
     only explain as an unexpected shift, and only one is allowed by
     default, so Cys-rich proteoforms drop out.
   - In the `none` run, unexpected shifts near +57.02 Da on cysteines (or
     -57.02 Da in the C57 run) point to the other value.
4. **Decide.** A candidate wins if it has at least 10% more PrSMs and
   the cysteine evidence agrees. With fewer than ~50 PrSMs in every run,
   or a smaller or contradictory difference, the data can't tell:
   show the user the numbers and let them choose. State the result in
   the plan, e.g. "`-f` C57 -- trial on 1,000 spectra of st_1: C57 401
   PrSMs vs none 312; 38 vs 9 Cys-containing proteoforms", and put the
   same line in `run_log.txt`.

**Several input files: one TopPIC run at a time** (same for TopFD), each
with the full `-u`. Two at once oversubscribe the CPU, and two TopPIC runs
against the same FASTA also compete for its `<database>.fasta_idx/`
index -- on this project that left two single-threaded runs crawling for
over an hour. Start the next file when the previous one's background task
has completed.

**The spectrum file is always `<input>_ms2.msalign` -- never
`<input>_ms1.msalign`.** TopPIC identifies proteoforms by matching
fragment ions, and only MS/MS (`LEVEL=2`) spectra have them. MS1
spectra hold precursor masses only. TopPIC will run on an MS1 file
without erroring and spend hours producing meaningless results. That
happened once: with no `_ms2.msalign` produced, an agent decided
"LEVEL=1 is the expected input for TopPIC" and started a 32-48 hour
batch on eight `_ms1.msalign_N` files. If there's no `_ms2.msalign`, go
back to TopFD (see the output check in step 2) and tell the user.
Don't substitute.

**Argument order: the FASTA always comes first, the msalign file second --
`toppic [options] database-file-name spectrum-file-name`, confirmed from
`toppic --help`'s own usage line. Reversing these has already happened once
on this project; re-check the order above (or `toppic --help`) each time
you write this command rather than reconstructing it from memory.**

Verified (against a source build; see the staleness note) end to end: TopPIC
auto-detects and uses the matching `<input>_ms2.feature` from the same
directory (no need to name it -- it's derived from the msalign filename;
pass `-x` if you deliberately have no feature file). Produces exactly the
files `toprepo_pipeline`'s Phase 1 step 1.4 expects:
`<input>_ms2_toppic_prsm.tsv`, `<input>_ms2_toppic_prsm_single.tsv`,
`<input>_ms2_toppic_proteoform.tsv`, `<input>_ms2_toppic_proteoform_single.tsv`,
matching XML files, and an `<input>_html/` folder, all written back into
`<ms_dir>` on the host -- use the `*_prsm_single.tsv` one downstream, as
`toprepo_pipeline` already documents.

`-f C57`/`-f C58` sets the fixed cysteine modification (carbamidomethylation/
carboxymethylation) -- confirm which applies to the sample prep rather than
guessing. `-d` runs a decoy search to estimate FDR; without it, filtering
uses raw E-values (see `-t`/`-v`/`-T`/`-V`).

**First run against a FASTA also builds `<database>.fasta_idx/`** next to
it (verified: it persists numeric-suffixed files there and reuses them on
later runs against the same path). **Verified this does not detect
changes to the FASTA** -- editing/regenerating `<database>.fasta` in place
and re-running `toppic` silently reused the stale index (unchanged
timestamps) rather than rebuilding it. Delete `<database>.fasta_idx/`
whenever the FASTA content changes, or use a new filename.

## Reporting back

Give each step's real state in one word -- **running**, **finished**, or
**failed** -- plus the evidence (PID alive, log tail, files and sizes).
A test run on one file isn't the batch: say "test run on 1 of 8 files,
~60% done; full batch not started, ~32-48 h estimated", never a
"Complete ✅" heading over work that's still running. Use the terms
correctly: mzML is undeconvoluted input, and msalign is TopFD's
deconvoluted output.

## Anti-Patterns

| Pattern | Problem | Fix |
|---|---|---|
| Copying flag defaults/meanings from `doc/topfd_manual.md` or `doc/toppic_manual.md` | Verified stale against a real HEAD build (see Core Philosophy) -- wrong defaults and at least one flag whose default behavior flipped | Run `topfd --help`/`toppic --help` on the binary you actually built and read from that |
| Running `topfd`/`toppic` as a normal bash call, or with `&`/`nohup`, on a real (not test-fixture) file | A normal call is killed at 120s, and `&`/`nohup` children are killed with the call's process group when it returns. Either way TopFD dies partway and leaves MS1-only partial output. That's happened on every real file run this way on this project | Use the bash tool's `run_in_background: true` with the plain command (steps 2 and 3), from the start |
| Concluding "the data has no MS/MS" from TopFD's output | Seen twice on this project, both times on data with plenty of MS2: the output was partial because the run had been killed | Count MS2 in the input itself: `grep -c 'name="ms level" value="2"' <input>.mzML` |
| Running `topfd`/`toppic` straight from `build/../bin/` without `make install` or a `resources/` symlink | `getResourceDir()` looks next to the executable, then `/usr/share/toppic`; neither exists yet | `make install`, or symlink `skills/toppic_suite/vendor/resources` next to the binaries |
| Trusting `make install` alone and moving on | Verified: `/usr/local/bin/topfd`/`toppic` have no RPATH (a real bug -- the project's rpath flag targets shared libraries, never applied to these executables), so they fail with `error while loading shared libraries: libonnxruntime.so.1.14.1 ...` (exit 127) even though the build-tree copy worked | Register `/usr/local/lib/toppic` with `ldconfig` (or set `LD_LIBRARY_PATH`) right after every `make install`, as shown in Prerequisites |
| Editing/regenerating a FASTA in place and re-running `toppic` against it | Verified: the cached `<database>.fasta_idx/` isn't invalidated by a content change -- you silently search the old database | `rm -rf <database>.fasta_idx/` first, or search-and-replace to a new filename |
| Building the full `make install` (all six tools + six GUIs) when only TopFD/TopPIC are needed | Qt GUI compilation is the slow part and buys nothing for a command-line skill | `make -j$(nproc) topfd toppic` (add other console tools by name only if asked) |
| Treating TopFD/TopPIC's own "16 GB memory" note as boilerplate | It's the vendor's stated minimum for real LC-MS runs, not a formality | Check available memory before a large job, flag it to the user if short |
| Leaving `-u`/`--thread-number` at its default of 1 on a multi-core machine | Both tools default to single-threaded. On this project TopPIC ran on 1 of 16 cores | Check the machine per `skills/_shared/hardware_check.md` and pass `-u` explicitly |
| Starting TopFD/TopPIC on several files at once | They oversubscribe the CPU, and TopPIC runs sharing a FASTA compete for its index | One file at a time, each with the full `-u` |
| Passing a relative path to `docker run -v` | Docker requires an absolute host path for a bind mount; a relative one fails or silently mounts the wrong thing rather than erroring clearly | Resolve `<ms_dir>` to an absolute path first (`$(pwd)/<ms_dir>`, or the native `D:\...` form on Windows PowerShell) |
| Reaching for Docker on Ubuntu/macOS without checking for an existing build or trying the native build first | This skill's default on Ubuntu/macOS is the native build, verified more thoroughly than the (stale) Docker image -- Docker is specifically the fallback for everything else, not an equally-valid first choice everywhere | Check for an existing build, then the OS, per Prerequisites -- Docker only when the OS isn't Ubuntu/macOS |
| Attempting a native Windows build via `vendor/doc/windows_build.md` (MSYS2) because Docker isn't installed yet | This skill specifically routes Windows to Docker; the Windows build path exists upstream but is undocumented/unverified by this skill | Send the user to install Docker instead, wait for confirmation, re-check `docker info` |
| Trusting the Docker image's TopFD/TopPIC version matches this skill's `--help`-verified flag defaults | The image hasn't been updated in 5+ years; see the staleness note under Prerequisites | Run `--help` inside the container if a flag's behavior seems off, same as the Core Philosophy rule for a source build |
| Passing the msalign file before the FASTA to `toppic` (`toppic ... <input>_ms2.msalign <database>.fasta`) | The real usage is `toppic [options] database-file-name spectrum-file-name` -- FASTA must be first. This has already happened once on this project, in a session where the command was reconstructed from memory/context rather than read fresh from this file -- TopPIC then either errors immediately or silently tries to parse the wrong file as the database | Before running, check the argument order against step 3's example above (or a fresh `toppic --help`) -- don't trust a remembered or previously-typed version of this command |
| Running TopPIC on `<input>_ms1.msalign` because no `_ms2.msalign` was produced | MS1 spectra have no fragment ions, so TopPIC runs for hours without erroring and produces meaningless identifications | TopPIC input is always `_ms2.msalign`. If it's missing, go back to TopFD and report to the user |
| Concluding TopFD skipped or failed a step because an output file isn't there yet | TopFD writes its outputs as it runs. At ~5% progress the MS2 file legitimately doesn't exist | Wait for the background task to complete, then check the full output set |
| Explaining away TopFD output that doesn't match this skill's list (bare `.msalign`, split `.msalign_N` files, leftover `.sqlite`, missing `_ms2`) and carrying on | Most likely a killed run; otherwise a different TopFD version. Everything downstream depends on the exact filenames | Stop, show `ls -la`, the log tail and the `--help` version line, and ask before going on |
| Writing TopFD/TopPIC flags from memory or from the corpus parameter list (`-max_charge 30`, `-window 3`, `toppic -d ... -s ... -e`) | Those aren't the real CLI. Unknown flags error out or get misread | Map each value to a flag that `--help` actually lists; leave it at the default (and say so) if there isn't one |
| Picking `-f` by comparing same-species projects when the input file is itself in TopRepo's corpus | Another project's sample prep isn't this data's. `Tel2_1.mzML` is PXD027741's own file (`-f` none), but C57 got picked from PXD017265 | Run `param_precedents/scripts/lookup_file.py` on the input first. A hit decides `-f` |
| Reporting a running job as complete | The user stops checking on, and stops correcting, a job that's still in progress | State running/finished/failed with evidence (see "Reporting back") |
| Copying a flag's default straight into the Mode B plan without reasoning about whether it fits this run (e.g. leaving `-u` at 1, or picking `-f` without checking the sample prep) | A restated default isn't a recommendation -- defeats the point of Mode B, and for a no-default flag like `-f` it means silently guessing | Check the actual context first (core count, sample prep, presence of a `.feature` file) and state a recommended value with a reason, flagging when it differs from the default |

## Resources

**Vendored** (`skills/toppic_suite/vendor/`, from
`https://github.com/toppic-suite/toppic-suite` -- see
`vendor/VENDORED_COMMIT.txt` for the exact commit; `resources/topmsv/node_modules/`
was dropped when vendoring, it's upstream's own web-visualization frontend
tooling, unused by the CLI path this skill covers):
- `vendor/doc/topfd_manual.md`, `toppic_manual.md` -- useful for
  output-file descriptions and worked examples, **not** for exact flag
  defaults (see Core Philosophy)
- `vendor/doc/windows_build.md` -- upstream's own native-Windows (MSYS2)
  build guide. **Not the path this skill uses for Windows** -- this skill
  routes Windows to Docker instead (see Prerequisites); it's listed here
  only so it isn't mistaken for the current Windows path if someone goes
  looking for it.
- `vendor/tests/data/mzxml_test.mzXML`, `mzxml_test_no_ms1.mzXML` -- real
  bundled fixtures, good for a quick smoke test of a fresh build

**Not vendored** -- genuinely external:
- `toppicsuite/toppic` on Docker Hub -- the image this skill runs TopFD/TopPIC
  through on Windows or any other non-Ubuntu/macOS system; pulled on
  demand (Prerequisites, Docker Step 2), not vendored or rebuilt by this
  project

**Related skills**:
- `msconvert` -- the step before: raw vendor files -> centroided mzML
- `toprepo_pipeline` -- the next step: turns this skill's mzML + msalign +
  feature + PrSM-TSV output into TopRepo's merged/annotated files
- `ms_process`, `pdpred_pipeline` -- further downstream, unchanged by this skill

## Reporting back

- Report exact output file paths after each step, and the real `Version:`
  line from `--help`/a run -- same convention as `pdpred_pipeline` and
  `toprepo_pipeline`, and it's what makes the doc-drift issue above
  checkable later.
