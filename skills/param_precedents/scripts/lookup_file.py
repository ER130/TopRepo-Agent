#!/usr/bin/env python3
"""Find which TopRepo source dataset an input file came from.

Usage: python3 skills/param_precedents/scripts/lookup_file.py <file> [<file> ...]

Accepts raw/mzML/msalign/feature names, with or without the 8-hex
"<id>_" prefix server.py adds to web uploads. Exit 1 if nothing matched.
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FILE_INFO = ROOT / "skills/toprepo_pipeline/vendor/resources/toprepo_file_info_v1.2.1.tsv"
DATASETS = ROOT / "skills/param_precedents/resources/toprepo_datasets_phase1.tsv"
UPLOAD_PREFIX = re.compile(r"^[0-9a-f]{8}_")
FIELDS = ["species", "sample", "instrument", "dissociation_meta",
          "toppic_fixed_mod", "faims_meta", "publication", "flag"]


def stem(name: str) -> str:
    base = UPLOAD_PREFIX.sub("", Path(name).name)
    return base.split(".", 1)[0].lower()


def candidates(name: str) -> list[str]:
    # "Tel2_1_ms2" -> "tel2_1"; a FAIMS msalign like "x_tech3_0_ms2" also
    # carries a compensation-voltage index before _ms2 -> fall back to "x_tech3".
    # Only drop that trailing _<n> as a second try: in "Tel2_1" the _1 is
    # part of the real name.
    base = re.sub(r"_ms[12]$", "", stem(name))
    return [base, re.sub(r"_\d+$", "", base)]


def main(names: list[str]) -> int:
    # A stem can map to more than one dataset: 14 filenames in the corpus do
    # (generic names like F4_1 in two unrelated projects; one set of files
    # deposited under two accessions). Keep every distinct match.
    by_stem: dict[str, dict[tuple, dict]] = {}
    with FILE_INFO.open(newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            key = (row["DATASET id"], row["SUBDATASET id"])
            by_stem.setdefault(stem(row["MZML file name"]), {}).setdefault(key, row)
    with DATASETS.open(newline="") as f:
        subsets = {row["subdataset"]: row for row in csv.DictReader(f, delimiter="\t")}

    found_any = False
    for name in names:
        hits = next((list(by_stem[c].values()) for c in candidates(name) if c in by_stem), [])
        if not hits:
            print(f"{name}: no match in TopRepo's corpus")
            continue
        found_any = True
        if len(hits) > 1:
            print(f"{name}: AMBIGUOUS -- this filename appears in {len(hits)} datasets; "
                  "ask the user which one it came from before citing either")
        for hit in hits:
            sub = subsets.get(hit["SUBDATASET id"], {})
            print(f"{name}: dataset {hit['DATASET id']}, project {hit['PROJECT id']}, "
                  f"subdataset {hit['SUBDATASET id']} (TopRepo file {hit['MZML file name']})")
            for field in FIELDS:
                if sub.get(field):
                    print(f"  {field}: {sub[field]}")
    return 0 if found_any else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1:]))
