#!/usr/bin/env bash
# Convert one vendor raw file (Thermo .raw, Bruker .d, ...) to centroided
# mzML with the Windows msconvert.exe, from inside WSL, then check it.
# Usage: run_msconvert.sh <input raw file or .d folder> <output dir>
# Writes <output dir>/<input name without extension>.mzML.
# Run it with the bash tool's run_in_background: true -- a real raw file
# takes minutes, longer than a normal bash call is allowed.
set -euo pipefail
in=${1:?usage: run_msconvert.sh <input> <output dir>}
out=${2:?usage: run_msconvert.sh <input> <output dir>}
here=$(cd "$(dirname "$0")" && pwd)

exe=$("$here/find_msconvert.sh") || exit $?
[ -e "$in" ] || { echo "MISSING: input $in does not exist" >&2; exit 1; }
mkdir -p "$out"
in=$(realpath "$in"); out=$(realpath "$out")

for path in "$in" "$out"; do
  case "$path" in
    /mnt/[a-z]/*) ;;
    *) echo "WARNING: $path is inside the Linux filesystem, not on a Windows drive" \
            "(/mnt/c, /mnt/d, ...). Windows programs reach it only through a" \
            "\\\\wsl.localhost path, which vendor readers may not handle." >&2 ;;
  esac
done

stem=$(basename "$in"); stem=${stem%.*}
echo "msconvert: $exe"
echo "input:     $in"
echo "output:    $out/$stem.mzML"
# peakPicking must be the first filter, or the vendor centroiding
# algorithm can't be used.
"$exe" "$(wslpath -w "$in")" --mzML \
  --filter "peakPicking vendor msLevel=1-" \
  -o "$(wslpath -w "$out")"

"$here/check_mzml.sh" "$out/$stem.mzML"
