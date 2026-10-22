---
name: toppic_suite
description: |
  Run the raw-data-to-identification chain that sits upstream of
  toprepo_pipeline -- by default compiling locally on Ubuntu/macOS, per
  toppic-suite's own build instructions, or through the official
  `toppicsuite/toppic` Docker image on Windows or any other OS: msconvert (vendor raw file -> mzML, a
  separate ProteoWizard tool), TopFD (mzML -> deconvoluted msalign + LC-MS
  feature files, from https://github.com/toppic-suite/toppic-suite), and
  TopPIC (msalign + feature + FASTA -> PrSM identification TSV, same repo).
  Use when users:
  (1) ask to build, install, compile, or run TopFD, TopPIC, or "toppic-suite"
  (2) have a raw vendor MS file (.raw/.d/etc.) or a centroided mzML/mzXML
      file and want it deconvoluted and/or searched against a protein
      database, rather than already having TopFD/TopPIC output
  (3) ask what topfd/toppic flags do, or hit a build error for this repo
  (4) mention PrSM, proteoform identification, spectral deconvolution,
      isotopic envelope, or msconvert while preparing data for TopRepo/TD-Pred
  Keywords: msconvert, ProteoWizard, TopFD, TopPIC, toppic-suite, deconvolution,
  isotopic envelope, feature detection, PrSM, FASTA search, EnvCNN, MIScore
---

# TopPIC Suite (msconvert -> TopFD -> TopPIC)

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

**msconvert is a different project** (ProteoWizard, not toppic-suite) and
this skill's msconvert guidance below is **not verified the way TopFD/TopPIC
are** -- this sandbox's network policy blocks proteowizard.sourceforge.io
and has no working Docker daemon, so it could only be written from general
knowledge. Confirm it against ProteoWizard's own docs before relying on it,
and say so if you can't reach them either.

## When to Use This

- The user has raw vendor files or mzML/mzXML that hasn't been through
  TopFD/TopPIC yet -- this is the step **before** `toprepo_pipeline`
- The user wants to build/install TopFD or TopPIC, or asks what a flag does
- The user already has TopFD `.msalign`/`.feature` output and a FASTA, and
  wants proteoform identification (PrSM) results
- **Not this skill**: once you have `*_toppic_prsm_single.tsv` and the
  matching mzML/msalign/feature files, move on to `toprepo_pipeline`

## Before You Start

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
  the right value on a real machine -- check available cores and recommend
  near that number instead of repeating the default.
- `-a`/`-o`/`-g` on TopFD: recommend `-o` only once you've checked the
  input actually lacks MS1 spectra; recommend `-g` only if the user has
  said the HTML output isn't needed; otherwise recommend leaving `-a` at
  its default (reads activation per-spectrum from the input).
- `-f` on TopPIC has no default -- this isn't a keep-or-change question,
  it's a real decision to make from the sample prep (standard
  iodoacetamide alkylation -> C57; iodoacetic acid -> C58). Check the
  `param_precedents` skill for a matching species/instrument/method
  before asking -- if a close precedent exists, lead with it (e.g.
  "TopRepo's comparable E. coli datasets mostly used no fixed
  modification unless alkylated -- was yours?") rather than a blind
  yes/no question. Only about 19% of that corpus is alkylated, so a
  precedent is never a reason to default toward C57 either -- recommend
  based on what you actually know about the sample prep; say plainly if
  you don't know and need to ask, rather than picking one silently.
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
letting it OOM partway through. Applies the same way whichever path below
you're on.

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

**msconvert (unverified this session -- see Core Philosophy)**: raw
vendor files (Thermo `.raw`, Bruker `.d`, etc.) need MSConvertGUI/msconvert
from ProteoWizard (https://proteowizard.sourceforge.io), not toppic-suite,
to become mzML/mzXML. From general knowledge: msconvert's vendor-format
readers are Windows-only DLLs, so ProteoWizard publishes a Linux/Mac route
as a Docker image (historically
`chambm/pwiz-skyline-i-agree-to-the-vendor-licenses` on Docker Hub -- the
name itself flags that using it means accepting the vendor libraries'
license terms) that runs the Windows build under Wine, alongside native
Windows binaries for direct use. If the user already has mzML/mzXML, skip
this entirely and start at TopFD below.

## Pipeline

Keep a dataset's raw file, mzML, and TopFD/TopPIC output together in one
directory, referred to below as `<ms_dir>` -- `toprepo_pipeline`'s Phase 1
reads directly from whatever ends up here, so wherever you pick, use it
consistently for the whole dataset.

**Resolving `<ms_dir>`**: don't assume a name -- check first. If the user
already has a folder for this dataset (they mentioned a path, or one
already exists with matching files in it), use that. If you're starting
fresh and nothing says otherwise, `runs/<run_name>/01_toppic_suite/` at the
project root is this project's own default (sibling to `skills/`,
`code.py`) -- `<run_name>` is the same identifier `toprepo_pipeline` calls
`<dataset_id>` (its own accession, e.g. `PXD029703`, or any stable name
you'll reuse everywhere), since this dataset's output from every stage of
the pipeline lives together under one `runs/<run_name>/`. Check `runs/`
for a folder already matching this dataset before creating a new one.
Treat the default as a suggestion, not a requirement: a local setup may
already keep raw MS data somewhere else entirely (a data drive, a folder
per instrument run, whatever the user's lab already uses). Resolve it
once (ask if genuinely ambiguous) and reuse the same path for every step
below, rather than re-deriving or renaming mid-run.

When you create `<ms_dir>` for the first time this run, also append one
line to `runs/<run_name>/run_log.txt` noting the date, this skill's name,
and the raw file(s)/key TopFD-TopPIC settings used, e.g.
`echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)  toppic_suite  <summary>" >>
runs/<run_name>/run_log.txt`.

### 1. msconvert -- raw file to mzML (see Prerequisites' caveat)

General form (unverified this session, see above):
```
msconvert <input>.raw --mzML -o <ms_dir>
```
Skip this step if the input is already mzML/mzXML.

### 2. TopFD -- deconvolute mzML/mzXML to msalign + feature files

**If you're on the native-build path (Ubuntu/macOS, per Prerequisites),**
run the installed binary directly from `<ms_dir>` (or give it an absolute
path):
```
cd <ms_dir>
topfd -u <threads> <input>.mzML > topfd_<input>.log 2>&1 &
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
    topfd -u <threads> /data/<input>.mzML > topfd_<input>.log 2>&1 &
```
Either form: **launch in the background, as shown above, not in the
foreground.** On a real mzML file this routinely runs past a single
foreground command's
timeout (observed: multiple fresh sessions each hit a ~120s timeout running
this in the foreground first, before separately discovering the background
form) -- redirect output to a log file, background it with `&`, and poll
that log (`tail`) or `wait` on the PID rather than blocking on the command
itself.

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

Useful flags (from the real `--help`, not the manual -- see Core
Philosophy): `-a` activation method (default `FILE`, i.e. read per-spectrum
from the input -- don't override this unless the input genuinely lacks
it), `-u` thread count (default 1 -- always set this explicitly on a
multi-core machine), `-g` to skip HTML generation if you don't need
visualization. `-o`/`--missing-level-one` if the input has no MS1 spectra
(the tests/data mzxml_test_no_ms1.mzXML fixture is exactly this case).

### 3. TopPIC -- search msalign against a FASTA for proteoform identification

**Native-build path (Ubuntu/macOS):** run from `<ms_dir>`, where the
msalign/feature files from step 2 and the FASTA already live:
```
cd <ms_dir>
toppic -u <threads> -f C57 <database>.fasta <input>_ms2.msalign \
    > toppic_<input>.log 2>&1 &
```

**Docker path (Windows, or any other OS):** the FASTA has to live under
the same mounted directory as the msalign -- put it in `<ms_dir>` too (or
mount a second `-v` for it) so both paths resolve inside the container:
```
docker run --rm -v <absolute path to ms_dir>:/data toppicsuite/toppic \
    toppic -u <threads> -f C57 /data/<database>.fasta /data/<input>_ms2.msalign \
    > toppic_<input>.log 2>&1 &
```

Either form: **launch in the background, as shown above, not in the
foreground** -- same reason as TopFD: TopPIC on a real msalign file
routinely runs past a single foreground command's timeout. Redirect to a
log file, background it, poll or `wait`, as with TopFD above. Also
**confirm `<database>.fasta` has
actually finished writing** before this runs if TopFD just produced the
msalign/feature pair in the background -- don't launch TopPIC until the
TopFD background job has actually exited (check `docker ps`/the PID, not
just that some output file exists).

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

## Anti-Patterns

| Pattern | Problem | Fix |
|---|---|---|
| Copying flag defaults/meanings from `doc/topfd_manual.md` or `doc/toppic_manual.md` | Verified stale against a real HEAD build (see Core Philosophy) -- wrong defaults and at least one flag whose default behavior flipped | Run `topfd --help`/`toppic --help` on the binary you actually built and read from that |
| Running `topfd`/`toppic` in the foreground on a real (not test-fixture) file | Observed repeatedly, across multiple fresh sessions: a foreground `docker run` hits a ~120s command timeout before the tool finishes, forcing a second attempt | Launch in the background with output redirected to a log file from the start (see steps 2 and 3 above), not as a recovery after the first one times out |
| Running `topfd`/`toppic` straight from `build/../bin/` without `make install` or a `resources/` symlink | `getResourceDir()` looks next to the executable, then `/usr/share/toppic`; neither exists yet | `make install`, or symlink `skills/toppic_suite/vendor/resources` next to the binaries |
| Trusting `make install` alone and moving on | Verified: `/usr/local/bin/topfd`/`toppic` have no RPATH (a real bug -- the project's rpath flag targets shared libraries, never applied to these executables), so they fail with `error while loading shared libraries: libonnxruntime.so.1.14.1 ...` (exit 127) even though the build-tree copy worked | Register `/usr/local/lib/toppic` with `ldconfig` (or set `LD_LIBRARY_PATH`) right after every `make install`, as shown in Prerequisites |
| Editing/regenerating a FASTA in place and re-running `toppic` against it | Verified: the cached `<database>.fasta_idx/` isn't invalidated by a content change -- you silently search the old database | `rm -rf <database>.fasta_idx/` first, or search-and-replace to a new filename |
| Building the full `make install` (all six tools + six GUIs) when only TopFD/TopPIC are needed | Qt GUI compilation is the slow part and buys nothing for a command-line skill | `make -j$(nproc) topfd toppic` (add other console tools by name only if asked) |
| Assuming msconvert's exact install/flags from this skill without checking | Written from general knowledge only -- this sandbox couldn't reach ProteoWizard's docs or run Docker to verify (see Core Philosophy) | Confirm against proteowizard.sourceforge.io, or ask the user how they normally run it |
| Treating TopFD/TopPIC's own "16 GB memory" note as boilerplate | It's the vendor's stated minimum for real LC-MS runs, not a formality | Check available memory before a large job, flag it to the user if short |
| Leaving `-u`/`--thread-number` at its default of 1 on a multi-core machine | Both tools default to single-threaded; real datasets are far slower than the ~4.5s/~2s smoke tests here | Pass `-u <nproc>` explicitly, as shown above |
| Passing a relative path to `docker run -v` | Docker requires an absolute host path for a bind mount; a relative one fails or silently mounts the wrong thing rather than erroring clearly | Resolve `<ms_dir>` to an absolute path first (`$(pwd)/<ms_dir>`, or the native `D:\...` form on Windows PowerShell) |
| Reaching for Docker on Ubuntu/macOS without checking for an existing build or trying the native build first | This skill's default on Ubuntu/macOS is the native build, verified more thoroughly than the (stale) Docker image -- Docker is specifically the fallback for everything else, not an equally-valid first choice everywhere | Check for an existing build, then the OS, per Prerequisites -- Docker only when the OS isn't Ubuntu/macOS |
| Attempting a native Windows build via `vendor/doc/windows_build.md` (MSYS2) because Docker isn't installed yet | This skill specifically routes Windows to Docker; the Windows build path exists upstream but is undocumented/unverified by this skill | Send the user to install Docker instead, wait for confirmation, re-check `docker info` |
| Trusting the Docker image's TopFD/TopPIC version matches this skill's `--help`-verified flag defaults | The image hasn't been updated in 5+ years; see the staleness note under Prerequisites | Run `--help` inside the container if a flag's behavior seems off, same as the Core Philosophy rule for a source build |
| Passing the msalign file before the FASTA to `toppic` (`toppic ... <input>_ms2.msalign <database>.fasta`) | The real usage is `toppic [options] database-file-name spectrum-file-name` -- FASTA must be first. This has already happened once on this project, in a session where the command was reconstructed from memory/context rather than read fresh from this file -- TopPIC then either errors immediately or silently tries to parse the wrong file as the database | Before running, check the argument order against step 3's example above (or a fresh `toppic --help`) -- don't trust a remembered or previously-typed version of this command |
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
- ProteoWizard (`https://proteowizard.sourceforge.io`) -- msconvert itself,
  a separate project (see Core Philosophy/Prerequisites)
- `toppicsuite/toppic` on Docker Hub -- the image this skill runs TopFD/TopPIC
  through on Windows or any other non-Ubuntu/macOS system; pulled on
  demand (Prerequisites, Docker Step 2), not vendored or rebuilt by this
  project

**Related skills**:
- `toprepo_pipeline` -- the next step: turns this skill's mzML + msalign +
  feature + PrSM-TSV output into TopRepo's merged/annotated files
- `ms_process`, `pdpred_pipeline` -- further downstream, unchanged by this skill

## Reporting back

- Report exact output file paths after each step, and the real `Version:`
  line from `--help`/a run -- same convention as `pdpred_pipeline` and
  `toprepo_pipeline`, and it's what makes the doc-drift issue above
  checkable later.
