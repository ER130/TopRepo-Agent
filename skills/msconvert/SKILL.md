---
name: msconvert
description: |
  Convert vendor raw mass-spec files (Thermo .raw, Bruker .d, ...) to
  centroided mzML with ProteoWizard's msconvert, the first step before
  TopFD/TopPIC (toppic_suite). Windows (WSL) only for now: uses the
  user's own Windows install of ProteoWizard, and tells them where to
  download it if it's missing. Also checks any mzML (converted here or
  supplied by the user) is centroided and has MS2 spectra.
  Use when users:
  (1) give you a .raw/.d/.wiff file, or ask to process raw data
  (2) ask to convert raw to mzML, or mention msconvert / MSConvertGUI /
      ProteoWizard / peak picking / centroiding
  (3) supply an mzML and you're about to run TopFD on it
  Keywords: raw, .raw, .d, msconvert, MSConvertGUI, ProteoWizard, mzML,
  centroid, peak picking, profile, vendor format, convert
---

# msconvert (raw -> centroided mzML)

## The Core Philosophy

> **TopFD needs centroided mzML with MS2 spectra -- check it, don't assume it.**

msconvert's default output keeps the vendor's profile data. TopFD
deconvolutes profile spectra poorly, so every conversion here adds the
peak-picking filter, and every mzML -- converted here or handed over by
the user -- goes through `check_mzml.sh` before TopFD.

msconvert's vendor readers (Thermo, Bruker, ...) are Windows-only. This
skill therefore drives the user's own Windows install of ProteoWizard
from WSL (WSL can run Windows `.exe` files directly). **Mac and native
Linux aren't supported yet.**

The scripts were tested against a stand-in for `msconvert.exe`, not the
real program. On a real run, report exactly what happened -- including
any error text -- rather than assuming it worked.

## When to Use This

- The user has vendor raw files and wants to run TopFD/TopPIC, TopRepo or
  PDpred on them -- this is the step before `toppic_suite`
- The user gives you an mzML: skip the conversion, but run the check
  (step 3) before handing it to TopFD
- **Not this skill**: deconvolution and identification -- that's
  `toppic_suite`, which reads this skill's mzML output

## Before You Start

- **Where the files go**: the mzML belongs in the same `<ms_dir>` that
  `toppic_suite` will use (by default `runs/<run_name>/01_toppic_suite/`,
  see `skills/_shared/run_layout.md`). Resolve it once and reuse it.
- **Keep the raw file and `<ms_dir>` on a Windows drive** (`/mnt/c/...`,
  `/mnt/d/...`). `msconvert.exe` is a Windows program and may not read or
  write inside WSL's own filesystem (`/home/...`). If the project folder
  is inside WSL's filesystem, ask the user where on a Windows drive to put
  the output.
- Tell the user which files you'll convert and where the mzML will go,
  and wait for them to confirm before starting.

## Steps

### 1. Find msconvert

```
bash skills/msconvert/scripts/find_msconvert.sh
```

It looks on `PATH`, under `C:\Program Files\ProteoWizard\`, and in the
installer's default per-user location
`C:\Users\<name>\AppData\Local\Apps\ProteoWizard*\`, and prints the newest
`msconvert.exe` it finds.

| Exit | Meaning | What to do |
|---|---|---|
| 0 | Prints the path | Go to step 2 |
| 1 `NOT_FOUND` | ProteoWizard isn't installed | Stop. Tell the user to install it (Windows 64-bit) from https://proteowizard.sourceforge.io/download.html and wait until they say it's done, then re-run this step. **Never download or install it yourself** -- the installer asks the user to accept the instrument vendors' licenses. If they say it's installed somewhere unusual, re-run with `MSCONVERT=/mnt/<drive>/.../msconvert.exe` |
| 2 `NOT_WSL` | Not a Windows machine | Mac/Linux aren't supported yet. Ask the user to convert on a Windows PC with MSConvertGUI -- output format mzML, add the **Peak Picking** filter (algorithm: vendor, MS levels: 1-) -- and give you the mzML. Then go to step 3 |

### 2. Convert

One raw file per call, **with the bash tool's `run_in_background: true`**
(a real raw file takes minutes; a normal call is killed after 120s). Run
several files one after another, not all at once:

```
bash skills/msconvert/scripts/run_msconvert.sh <input>.raw <ms_dir>
```

A Bruker `.d` folder is passed the same way. The script runs:

```
msconvert.exe <input> --mzML --filter "peakPicking vendor msLevel=1-" -o <ms_dir>
```

(`peakPicking` must be the first filter, or the vendor's centroiding
can't be used), writes `<ms_dir>/<input name>.mzML`, then runs step 3 on
it. Wait for the background task's `completed` notification before
reading the result.

### 3. Check the mzML

`run_msconvert.sh` does this itself. Run it by hand on an mzML the user
supplied:

```
bash skills/msconvert/scripts/check_mzml.sh <ms_dir>/<input>.mzML
```

It prints `MS1=<n> MS2=<n> centroid=<n> profile=<n>`, then:

| Exit | Meaning | What to do |
|---|---|---|
| 0 `OK` | Centroided, has MS2 | Hand the mzML to `toppic_suite` (TopFD) |
| 3 `PROFILE` | Some spectra are profile | Re-convert with step 2 (or ask the user to redo it with Peak Picking added) |
| 4 `NO_MS2` | No MS2 spectra at all | Stop and show the user the counts. TopPIC can't identify anything without MS2 |
| 1 `MISSING` | No mzML at that path | The conversion failed -- show the user the msconvert output |

## Reporting back

Per file: the mzML path, the counts line from `check_mzml.sh`, and its
verdict. If msconvert failed, quote its error output and stop there --
don't move on to TopFD with a missing or partial mzML.

## Anti-Patterns

| Pattern | Problem | Fix |
|---|---|---|
| Writing the msconvert command by hand, without the peak-picking filter | Profile mzML, which TopFD handles poorly | Use `run_msconvert.sh` |
| Passing an mzML the user supplied straight to TopFD | It may be profile, or have no MS2 | Run `check_mzml.sh` first |
| Downloading or installing ProteoWizard for the user | The installer requires the user to accept the vendors' licenses | Give them the link and wait |
| Running the conversion as a normal bash call, or with `&`/`nohup` | Killed after 120s, or when the call returns, leaving a partial mzML | `run_in_background: true`, plain command |
| Converting several raw files at once | They compete for disk and memory, and a failure is harder to pin down | One after another |
| Writing the mzML inside WSL's own filesystem | `msconvert.exe` may not be able to write there | Use a `/mnt/<drive>/...` folder |

## Resources

Scripts (`skills/msconvert/scripts/`):
- `find_msconvert.sh` -- finds the user's Windows `msconvert.exe`
- `run_msconvert.sh` -- raw -> centroided mzML, then checks it
- `check_mzml.sh` -- counts MS1/MS2 and centroid/profile spectra in an mzML

External: ProteoWizard (https://proteowizard.sourceforge.io), installed
by the user on Windows.

Related skills: `toppic_suite` -- the next step (TopFD -> TopPIC).
