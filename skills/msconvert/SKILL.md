---
name: msconvert
description: |
  Convert vendor raw mass-spec files (Thermo .raw, Bruker .d, Sciex .wiff,
  ...) to an open format -- mzML, mzXML, MGF, ... -- with ProteoWizard's
  msconvert. The output format and filters are the user's choice; when the
  data is headed into one of this project's pipelines (TopFD/TopPIC,
  TopRepo, PDpred), the default is what that pipeline needs (centroided
  mzML). Windows (WSL) only for now: uses the user's own Windows install
  of ProteoWizard, and tells them where to download it if it's missing.
  Use when users:
  (1) give you a .raw/.d/.wiff file, or ask to process raw data
  (2) ask to convert raw files to mzML/mzXML/MGF, or mention msconvert /
      MSConvertGUI / ProteoWizard / peak picking / centroiding
  (3) supply an mzML and you're about to run TopFD on it
  Keywords: raw, .raw, .d, .wiff, msconvert, MSConvertGUI, ProteoWizard,
  mzML, mzXML, MGF, centroid, peak picking, profile, vendor format, convert
requires: [pipeline_common]
---

# msconvert (vendor raw -> open formats)

## The Core Philosophy

> **The output is the user's choice -- unless the pipeline it feeds decides it.**

msconvert is a general converter: mzML, mzXML, MGF and more, with
filters for peak picking, MS level, scan range and so on. Which of these
is right depends entirely on what the file is for, so:

1. **The user names a format or settings** -> use exactly that.
2. **The user names a pipeline** (or the raw file is clearly headed into
   one -- e.g. "run TopPIC on this", "the whole TopRepo pipeline") -> use
   that pipeline's requirement from the table below, and say so in the
   plan.
3. **Neither** -> ask what the file is for, or which format they want,
   before converting. Don't pick one silently.

### What each pipeline needs

| Downstream | Format | Filter | Why |
|---|---|---|---|
| `toppic_suite` (TopFD -> TopPIC), and therefore `toprepo_pipeline`, `ms_process`, `pdpred_pipeline` | `--mzML` | `--filter "peakPicking vendor msLevel=1-"` | TopFD needs centroided spectra, MS1 and MS2; it deconvolutes profile data poorly |

When a new skill is added that reads msconvert output, add its row here.
A user's explicit choice still overrides the table -- but if it
conflicts with the pipeline they asked for (e.g. profile mzML for TopFD),
point out the conflict before converting.

### Windows only, for now

msconvert's vendor readers (Thermo, Bruker, Sciex, ...) are Windows-only.
This skill drives the user's own Windows install of ProteoWizard from WSL
(WSL can run Windows `.exe` files directly). **Mac and native Linux
aren't supported yet.**

## When to Use This

- The user has vendor raw files and wants them converted, or wants to run
  one of this project's pipelines on them -- this is the step before
  `toppic_suite`
- The user gives you an mzML to run TopFD on: no conversion, but do the
  output check (step 4) first
- **Not this skill**: deconvolution and identification -- that's
  `toppic_suite`

## Before You Start

Planning, long-running commands and reporting follow `pipeline_common`
(loaded with this skill). From the machine check, free disk space matters
most: an mzML is often several times the size of its raw file.

The plan names the files to convert, the output format and filters (and
where they came from: the user, or which pipeline's row above), and the
output folder:

- **Output folder**: if it's for a pipeline, use that pipeline's input
  folder -- for `toppic_suite`, its `<ms_dir>` (by default
  `runs/<run_name>/01_toppic_suite/`, see `skills/_shared/run_layout.md`).
  Otherwise ask, or put it next to the raw file.
- **Keep the raw file and output folder on a Windows drive**
  (`/mnt/c/...`, `/mnt/d/...`). `msconvert.exe` is a Windows program and
  may not read or write inside WSL's own filesystem (`/home/...`).

## Steps

### 1. Check this is Windows (WSL)

```
grep -qi microsoft /proc/version && echo WSL
```

No `WSL` -> Mac/Linux, not supported yet. Ask the user to convert on a
Windows PC with MSConvertGUI using the settings you worked out above, and
give you the output file. For TopFD that means: output format mzML, add
the **Peak Picking** filter (algorithm: vendor, MS levels: 1-).

### 2. Find msconvert.exe

```
command -v msconvert.exe
ls "/mnt/c/Program Files/ProteoWizard/"*/msconvert.exe \
   /mnt/c/Users/*/AppData/Local/Apps/ProteoWizard*/msconvert.exe 2>/dev/null
```

The second location is where the ProteoWizard installer puts a per-user
install by default. If several versions are listed, use the newest (the
version number is in the folder name).

**Nothing found** -> stop. Tell the user to install ProteoWizard (Windows
64-bit) from https://proteowizard.sourceforge.io/download.html, and wait
until they say it's done. **Never download or install it yourself**: the
installer asks the user to accept the instrument vendors' licenses. If
they say it's installed somewhere else, ask for the path.

Then confirm it runs and see which options this version has:

```
"<path to msconvert.exe>" --help
```

Build the command from that output, not from memory -- the same rule
`toppic_suite` follows for TopFD/TopPIC.

### 3. Convert

`msconvert.exe` needs Windows paths: convert each with `wslpath -w`.
General form:

```
"<msconvert.exe>" "$(wslpath -w <input>)" --<format> [--filter "<filter>" ...] \
    -o "$(wslpath -w <output dir>)"
```

- `<format>`: `mzML`, `mzXML`, `mgf`, ... -- check `--help` for the list.
- `--filter`: as chosen in the Core Philosophy. **`peakPicking` must be
  the first filter**, or the vendor's centroiding can't be used.
- A Bruker `.d` folder is passed the same way as a file.
- The output is named after the input (`<input>.mzML`, ...).

Run it in the background (`pipeline_common`) -- a real raw file takes
minutes. One file per call, one after another: files converted at once
compete for disk and memory, and a failure is harder to pin down.

### 4. Check the output

Confirm the file exists and isn't empty (`ls -la`), then check it fits
what it's for. For a TopFD-bound mzML (also run this on an mzML the user
gives you directly):

```
grep -c 'name="ms level" value="2"' <file>.mzML   # MS2 spectra: must be > 0
grep -c '"MS:1000128"' <file>.mzML                # profile: must be 0 (or 1, from the file header)
grep -c '"MS:1000127"' <file>.mzML                # centroid: about the spectrum count
```

- No MS2 -> stop and show the user. TopPIC can't identify anything
  without MS2.
- Profile spectra -> it wasn't centroided. Re-convert with peak picking
  (or ask the user to redo it with the Peak Picking filter added).

For other formats, at least count the spectra (e.g. `grep -c '^BEGIN
IONS' <file>.mgf`) and compare with what the user expects.

## Reporting back

Per file: the exact command you ran, the output path and size, and the
check results. If msconvert failed, quote its error output and stop --
don't hand a missing or partial file to the next step.

## Checklist before each conversion

- Format and filters from the user or the pipeline table -- otherwise ask.
- For TopFD: `peakPicking vendor msLevel=1-`, as the first filter.
- Options from this version's `msconvert.exe --help`; every path through
  `wslpath -w`.
- In the background, one file at a time; step 4's check before handing
  the file on (also for an mzML the user supplied).
- ProteoWizard missing -> the user installs it; never you.

## Resources

External: ProteoWizard (https://proteowizard.sourceforge.io), installed
by the user on Windows. Its own documentation of msconvert's options:
`msconvert.exe --help`.

Related skills: `toppic_suite` -- the next step for TopFD/TopPIC
(centroided mzML in, msalign/PrSM out).
