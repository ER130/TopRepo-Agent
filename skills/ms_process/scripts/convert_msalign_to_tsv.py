#!/usr/bin/env python3
"""Parse an msalign file and extract per-scan metadata into a TSV file.

The TSV is td_pred.py's --input, so scans td_pred.py can't predict are
left out and counted by reason: no DATABASE_SEQUENCE (unidentified
spectrum -- td_pred.py crashes on the empty value), a sequence longer
than the model's --max-length, a residue letter the model has no mass
for, or a missing precursor charge / activation / instrument.

Usage: convert_msalign_to_tsv.py <input.msalign> <output.tsv> [--max-length 200]
"""

import argparse
import csv
from collections import Counter

FIELDS = [
    "DATASET_ID",
    "MZML_FILE_NAME",
    "MSALIGN_FILE_NAME",
    "MS2_SCAN",
    "DATABASE_SEQUENCE",
    "PRECURSOR_CHARGE",
    "INSTRUMENT",
    "ACTIVATION",
    "COLLISION_ENERGY",
]

# Residues with a mass in pdpred_pipeline's model_data.get_mono_mass_list().
KNOWN_RESIDUES = set("GASPVTCLIDQKEMmHFRYNWOU")


def skip_reason(scan: dict, max_length: int) -> str | None:
    seq = scan.get("DATABASE_SEQUENCE", "")
    if not seq:
        return "no DATABASE_SEQUENCE (unidentified)"
    if len(seq) > max_length:
        return f"sequence longer than {max_length}"
    if set(seq) - KNOWN_RESIDUES:
        return "unknown residue letter"
    if not scan.get("PRECURSOR_CHARGE", "").isdigit():
        return "missing PRECURSOR_CHARGE"
    if not scan.get("ACTIVATION") or not scan.get("INSTRUMENT"):
        return "missing ACTIVATION/INSTRUMENT"
    return None


def parse_msalign(input_path: str, output_path: str, max_length: int = 200) -> None:
    scans = []
    current: dict | None = None

    with open(input_path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line == "BEGIN IONS":
                current = {}
            elif line == "END IONS":
                if current is not None:
                    scans.append(current)
                current = None
            elif current is not None and "=" in line:
                key, _, value = line.partition("=")
                if key in FIELDS:
                    if key == "PRECURSOR_CHARGE":
                        parts = value.split(":")
                        value = parts[0]
                    current[key] = value

    kept = []
    skipped = Counter()
    for scan in scans:
        reason = skip_reason(scan, max_length)
        if reason:
            skipped[reason] += 1
        else:
            kept.append(scan)

    with open(output_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for scan in kept:
            writer.writerow({field: scan.get(field, "") for field in FIELDS})

    print(f"Wrote {len(kept)} of {len(scans)} scans to {output_path}")
    for reason, count in skipped.most_common():
        print(f"  skipped {count}: {reason}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("input", help="annotated .msalign file")
    parser.add_argument("output", help="output .tsv (td_pred.py --input)")
    parser.add_argument("--max-length", type=int, default=200,
                        help="longest sequence the model takes -- td_pred.py "
                             "hardcodes 200 (default: 200)")
    args = parser.parse_args()
    parse_msalign(args.input, args.output, args.max_length)
