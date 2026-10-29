#!/usr/bin/env bash
# Check that an mzML file is ready for TopFD: centroided, with MS2 spectra.
# Usage: check_mzml.sh <file.mzML>
# Exit 0 = OK, 3 = has profile spectra (re-convert with peak picking),
# 4 = no MS2 spectra, 1 = file missing.
set -u
f=${1:?usage: check_mzml.sh <file.mzML>}
[ -f "$f" ] || { echo "MISSING: $f does not exist" >&2; exit 1; }

# Count only inside <spectrumList>, so the file-level <fileContent>
# summary at the top isn't counted as a spectrum.
read -r ms1 ms2 centroid profile < <(awk '
  /<spectrumList/   { s = 1 }
  /<\/spectrumList>/ { s = 0 }
  s && /name="ms level"/ { if (/value="1"/) ms1++; else if (/value="2"/) ms2++ }
  s && /"MS:1000127"/ { c++ }
  s && /"MS:1000128"/ { p++ }
  END { print ms1+0, ms2+0, c+0, p+0 }' "$f")

echo "$f: MS1=$ms1 MS2=$ms2 centroid=$centroid profile=$profile"
if [ "$profile" -gt 0 ]; then
  echo "PROFILE: $profile spectra are profile, not centroid. TopFD needs centroided input --" \
       "re-convert with --filter \"peakPicking vendor msLevel=1-\"."
  exit 3
fi
if [ "$ms2" -eq 0 ]; then
  echo "NO_MS2: no MS2 spectra, so TopPIC has nothing to identify. Check the raw file" \
       "and the conversion settings with the user before going on."
  exit 4
fi
echo "OK: centroided, with MS2 spectra -- ready for TopFD."
