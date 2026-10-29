#!/usr/bin/env bash
# Print the path (as a WSL path) of the newest msconvert.exe installed on
# the Windows side of this WSL machine, and exit 0.
# Exit 1 (with a message on stderr) if ProteoWizard isn't installed.
# Exit 2 if this isn't WSL: msconvert support is Windows-only for now.
# Set MSCONVERT=/path/to/msconvert.exe to skip the search.
set -u

if [ -n "${MSCONVERT:-}" ]; then
  if [ -f "$MSCONVERT" ]; then echo "$MSCONVERT"; exit 0; fi
  echo "MSCONVERT is set to '$MSCONVERT', but no such file exists." >&2
  exit 1
fi

if ! grep -qi microsoft /proc/version 2>/dev/null; then
  echo "NOT_WSL: this machine isn't Windows/WSL. msconvert support is Windows-only for now --" >&2
  echo "ask the user to convert the raw file to centroided mzML on a Windows PC (MSConvertGUI)." >&2
  exit 2
fi

shopt -s nullglob
candidates=()
if p=$(command -v msconvert.exe 2>/dev/null); then candidates+=("$p"); fi
# Machine-wide installs, then the per-user install the ProteoWizard
# installer uses by default (C:\Users\<name>\AppData\Local\Apps\...).
for p in "/mnt/c/Program Files/ProteoWizard/"*/msconvert.exe \
         "/mnt/c/Program Files (x86)/ProteoWizard/"*/msconvert.exe \
         /mnt/c/Users/*/AppData/Local/Apps/ProteoWizard*/msconvert.exe; do
  candidates+=("$p")
done

if [ ${#candidates[@]} -eq 0 ]; then
  echo "NOT_FOUND: no msconvert.exe on this Windows machine." >&2
  echo "The user needs to install ProteoWizard (Windows 64-bit) themselves from" >&2
  echo "https://proteowizard.sourceforge.io/download.html -- the installer asks them to" >&2
  echo "accept the instrument vendors' licenses, so it can't be installed for them." >&2
  echo "If it's installed somewhere unusual, set MSCONVERT=/mnt/<drive>/.../msconvert.exe." >&2
  exit 1
fi

printf '%s\n' "${candidates[@]}" | sort -V | tail -1
