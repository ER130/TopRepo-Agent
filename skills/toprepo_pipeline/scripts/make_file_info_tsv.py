#!/usr/bin/env python3
"""Build the small 'ms_file_info' TSV that TopRepo's own
merge_mzml_msalign_toppic_info.py (pipeline step 1.5) requires as its 4th
argument.

TopRepo ships resources/toprepo_file_info_v1.2.1.tsv, but that file only
lists the ~4,615 msalign files already in TopRepo's own published corpus
(verified: it has no row for a new dataset, or even for the generic
filenames used in TopRepo's own README walkthrough). Step 1.5 does an
*inner* join on (DATASET id, MSALIGN file name) against whatever file_info
TSV you point it at, so pointing it at the shipped registry for a dataset
that isn't already in TopRepo silently produces a 0-row combined_info.tsv
-- no error, just an empty file three steps later.

Nothing downstream of step 1.5 actually reads PROJECT id / SUBDATASET id
(checked merge_msalign_prsm.py's column usage), so the values only need to
be present, not meaningful.
"""
import argparse
import csv
from pathlib import Path

HEADER = ["DATASET id", "MSALIGN file name", "PROJECT id", "SUBDATASET id", "MZML file name"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset-id", required=True, help="Same --dataset_id/<dataset_id> value used in every other pipeline step for this dataset.")
    ap.add_argument("--msalign", action="append", required=True, metavar="NAME",
                     help="Basename of an msalign file for this dataset, as it will appear in "
                          "MSALIGN_FILE_NAME after msalign_preprocess.py (step 2.1) strips a leading "
                          "'<dataset_id>_' if present. Repeat --msalign for multiple runs.")
    ap.add_argument("--mzml", action="append", required=True, metavar="NAME",
                     help="Matching mzML basename for each --msalign, same order. Repeat --mzml once per --msalign.")
    ap.add_argument("--project-id", default="1", help="Placeholder only; nothing downstream reads it (default: 1).")
    ap.add_argument("--subdataset-id", default="1", help="Placeholder only; nothing downstream reads it (default: 1).")
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--append", action="store_true",
                     help="Append to --output instead of overwriting, so one file_info.tsv can "
                          "accumulate rows across multiple datasets/runs. Skips the header if the "
                          "file already exists.")
    args = ap.parse_args()

    if len(args.msalign) != len(args.mzml):
        raise SystemExit(f"Got {len(args.msalign)} --msalign but {len(args.mzml)} --mzml -- need one --mzml per --msalign, same order.")

    write_header = not (args.append and args.output.exists())
    mode = "a" if args.append else "w"
    with args.output.open(mode, newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        if write_header:
            writer.writerow(HEADER)
        for msalign_name, mzml_name in zip(args.msalign, args.mzml):
            writer.writerow([args.dataset_id, msalign_name, args.project_id, args.subdataset_id, mzml_name])

    print(f"Wrote {len(args.msalign)} row(s) for dataset {args.dataset_id} to {args.output}")


if __name__ == "__main__":
    main()
