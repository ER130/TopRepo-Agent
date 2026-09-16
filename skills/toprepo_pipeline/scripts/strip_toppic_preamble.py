#!/usr/bin/env python3
"""Strip TopPIC's run-parameters preamble AND its 'Number of identified ...'
summary lines from a raw *_toppic_prsm(_single).tsv / *_toppic_proteoform(_single).tsv
file, leaving a clean TSV that starts with the real header row.

TopRepo ships its own src/util/tsv/remove_params.py for this, but it only
strips the "********** Parameters **********"-delimited block -- verified
by running it on real TopPIC 1.9.0 output: its own output still has 2-3
leading summary lines ("Number of identified PrSMs: 0", "... proteoforms:
0", "... proteins: 0") before the real tab-separated header, which then
crashes toprepo's own prsm_preprocess.py with
"ValueError: dict contains fields not in fieldnames: None" (ends up
parsing "Number of identified PrSMs: 0" as a one-column header instead of
the real one). Use this instead of remove_params.py before step 1.4 of
the toprepo_pipeline skill.
"""
import argparse
from pathlib import Path


def strip_preamble(lines: list[str]) -> list[str]:
    delimiter_count = 0
    after_params_block = []
    in_params_block = False
    for line in lines:
        if "**********" in line and delimiter_count < 2:
            delimiter_count += 1
            in_params_block = not in_params_block
            continue
        if not in_params_block:
            after_params_block.append(line)

    header_index = next(
        (i for i, line in enumerate(after_params_block) if "\t" in line),
        None,
    )
    if header_index is None:
        raise SystemExit(
            "No tab-separated header row found after the Parameters block -- "
            "the file's format may not match what this script expects; check it by hand."
        )
    return after_params_block[header_index:]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path, help="Raw *_toppic_prsm(_single).tsv or *_toppic_proteoform(_single).tsv from TopPIC")
    ap.add_argument("output", type=Path)
    args = ap.parse_args()

    lines = args.input.read_text().splitlines(keepends=True)
    cleaned = strip_preamble(lines)
    args.output.write_text("".join(cleaned))
    print(f"Wrote {len(cleaned) - 1} data row(s) (plus header) to {args.output}")


if __name__ == "__main__":
    main()
