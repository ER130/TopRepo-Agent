#!/usr/bin/env python3
"""
split_ms_file.py -- Split an annotated (TopRepo-processed) MS file into
train / val sets, grouped by proteoform (or protein) so the same
proteoform never appears on both sides -- this avoids leaking
information across the split, which a naive spectrum-level random split
would not protect against.

Works on the common block-based annotated MS text formats used by the
TopFD / TopPIC / TopRepo toolchain: each spectrum is one block delimited
by a BEGIN/END tag pair, with "KEY=VALUE" (or "KEY: VALUE") header lines
inside the block. Examples: msalign-style "BEGIN SPECTRUM / END SPECTRUM",
or MGF-style "BEGIN IONS / END IONS".

If your TopRepo export uses a different delimiter pair, or the grouping
key is not literally in every spectrum header, pass --begin-tag/--end-tag
and --group-field explicitly (see --help).

Usage:
    python split_ms_file.py \
        --input sample_annotated.msalign \
        --group-field PROTEOFORM_ID \
        --train-ratio 0.8 \
        --seed 42 \
        --output-dir ./split_out
"""
import argparse
import random
import re
from collections import defaultdict
from pathlib import Path


def detect_tags(text: str):
    """Best-effort detection of the block delimiter style."""
    candidates = [
        ("BEGIN IONS", "END IONS"),          # MGF-style
        ("BEGIN SPECTRUM", "END SPECTRUM"),  # msalign-style
        ("BEGIN PRSM", "END PRSM"),          # PrSM-annotated style
    ]
    for b, e in candidates:
        if b in text and e in text:
            return b, e
    raise ValueError(
        "Could not auto-detect block delimiters (looked for BEGIN/END "
        "IONS, SPECTRUM, PRSM). Pass --begin-tag/--end-tag explicitly."
    )


def parse_blocks(text: str, begin_tag: str, end_tag: str):
    pattern = re.compile(
        rf"^{re.escape(begin_tag)}\s*$.*?^{re.escape(end_tag)}\s*$",
        re.MULTILINE | re.DOTALL,
    )
    return [m.group(0) for m in pattern.finditer(text)]


def extract_field(block: str, field: str):
    """Matches 'FIELD=value' or 'FIELD: value' (case-insensitive)."""
    m = re.search(
        rf"^{re.escape(field)}\s*[:=]\s*(.+)$", block, re.MULTILINE | re.IGNORECASE
    )
    return m.group(1).strip() if m else None


def greedy_assign(groups, keys, targets, seed):
    """Assign each group key to one of the buckets in `targets` (name ->
    target spectra count), greedily. Keys are shuffled (for reproducible
    tie-breaking) then processed largest-group-first; each group goes to
    whichever bucket is currently furthest below its target spectra count.
    This keeps the realized spectra-count ratio close to the requested
    ratio even when group sizes are highly skewed, unlike slicing the
    shuffled key list by group count alone."""
    rng = random.Random(seed)
    rng.shuffle(keys)
    keys.sort(key=lambda k: len(groups[k]), reverse=True)

    assigned = {name: 0 for name in targets}
    bucket_keys = {name: [] for name in targets}
    for key in keys:
        name = max(targets, key=lambda n: targets[n] - assigned[n])
        bucket_keys[name].append(key)
        assigned[name] += len(groups[key])
    return bucket_keys


def group_split(blocks, group_field, train_ratio, seed):
    groups = defaultdict(list)
    ungrouped = []
    for block in blocks:
        key = extract_field(block, group_field)
        if key is None:
            ungrouped.append(block)
        else:
            groups[key].append(block)

    keys = list(groups.keys())
    total_spectra = sum(len(blist) for blist in groups.values())
    targets = {"train": train_ratio * total_spectra,
               "val": (1 - train_ratio) * total_spectra}
    bucket_keys = greedy_assign(groups, keys, targets, seed)

    train_blocks = [b for k in bucket_keys["train"] for b in groups[k]]
    val_blocks = [b for k in bucket_keys["val"] for b in groups[k]]

    return train_blocks, val_blocks, ungrouped, len(keys), len(bucket_keys["train"])


def group_split_three(blocks, group_field, test_ratio, seed):
    """Like group_split, but assigns each group to one of three buckets:
    train gets (1 - 2*test_ratio), val and test each get test_ratio
    (symmetric val/test, e.g. test_ratio=0.15 -> 70:15:15 of spectra)."""
    groups = defaultdict(list)
    ungrouped = []
    for block in blocks:
        key = extract_field(block, group_field)
        if key is None:
            ungrouped.append(block)
        else:
            groups[key].append(block)

    keys = list(groups.keys())
    total_spectra = sum(len(blist) for blist in groups.values())
    targets = {"train": (1 - 2 * test_ratio) * total_spectra,
               "val": test_ratio * total_spectra,
               "test": test_ratio * total_spectra}
    bucket_keys = greedy_assign(groups, keys, targets, seed)

    train_blocks = [b for k in bucket_keys["train"] for b in groups[k]]
    val_blocks = [b for k in bucket_keys["val"] for b in groups[k]]
    test_blocks = [b for k in bucket_keys["test"] for b in groups[k]]

    return (train_blocks, val_blocks, test_blocks, ungrouped, len(keys),
            len(bucket_keys["train"]), len(bucket_keys["val"]), len(bucket_keys["test"]))


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--input", required=True, type=Path, help="Annotated MS file (full, unsplit).")
    ap.add_argument(
        "--group-field",
        default="PROTEOFORM_ID",
        help="Header field to group spectra by (default: PROTEOFORM_ID). "
        "Use PROTEIN_ACCESSION (or your file's equivalent) to group at the "
        "protein level instead of the proteoform level.",
    )
    ap.add_argument("--train-ratio", type=float, default=0.8)
    ap.add_argument(
        "--test-ratio", type=float, default=0.15,
        help="Only used when no test set exists yet for this input in "
        "--val-file-dir (see below): splits into train/val/test with "
        "val and test each getting this fraction (default 0.15 -> "
        "70:15:15). Ignored when a test set already exists -- that case "
        "uses --train-ratio for a plain train/val split instead.",
    )
    ap.add_argument(
        "--val-file-dir", type=Path, default=Path("Val_File"),
        help="Where to look for an existing <input>_test<ext> file, and "
        "where to write one if this run creates it (default: Val_File).",
    )
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--begin-tag", default=None)
    ap.add_argument("--end-tag", default=None)
    ap.add_argument("--output-dir", type=Path, default=Path("."))
    args = ap.parse_args()

    text = args.input.read_text()
    begin_tag, end_tag = (
        (args.begin_tag, args.end_tag) if args.begin_tag else detect_tags(text)
    )
    blocks = parse_blocks(text, begin_tag, end_tag)
    if not blocks:
        raise SystemExit(f"No blocks found with tags {begin_tag!r}/{end_tag!r}.")

    existing_test_path = args.val_file_dir / f"{args.input.stem}_test{args.input.suffix}"
    has_existing_test = existing_test_path.exists()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    train_path = args.output_dir / f"{args.input.stem}_train{args.input.suffix}"
    val_path = args.output_dir / f"{args.input.stem}_val{args.input.suffix}"

    if has_existing_test:
        print(f"Found existing test set at {existing_test_path} -- "
              f"doing a plain train/val split (test-ratio ignored).")
        train_blocks, val_blocks, ungrouped, n_groups, n_train_groups = group_split(
            blocks, args.group_field, args.train_ratio, args.seed
        )

        if ungrouped:
            print(
                f"[warn] {len(ungrouped)} / {len(blocks)} spectra had no "
                f"'{args.group_field}' field and were EXCLUDED from the split. "
                f"Check --group-field against your file's actual header keys."
            )

        train_path.write_text("\n".join(train_blocks) + ("\n" if train_blocks else ""))
        val_path.write_text("\n".join(val_blocks) + ("\n" if val_blocks else ""))

        print(f"Groups ({args.group_field}): {n_groups} total -> "
              f"{n_train_groups} train / {n_groups - n_train_groups} val")
        print(f"Spectra: {len(train_blocks)} train / {len(val_blocks)} val "
              f"(target ratio {args.train_ratio}, actual "
              f"{len(train_blocks)/max(1, len(train_blocks)+len(val_blocks)):.3f})")
        print(f"Wrote: {train_path}")
        print(f"Wrote: {val_path}")
    else:
        print(f"No existing test set at {existing_test_path} -- "
              f"doing a train/val/test split (train-ratio ignored, "
              f"test-ratio={args.test_ratio} -> "
              f"{1 - 2*args.test_ratio:.2f}:{args.test_ratio}:{args.test_ratio}).")
        (train_blocks, val_blocks, test_blocks, ungrouped, n_groups,
         n_train_groups, n_val_groups, n_test_groups) = group_split_three(
            blocks, args.group_field, args.test_ratio, args.seed
        )

        if ungrouped:
            print(
                f"[warn] {len(ungrouped)} / {len(blocks)} spectra had no "
                f"'{args.group_field}' field and were EXCLUDED from the split. "
                f"Check --group-field against your file's actual header keys."
            )

        args.val_file_dir.mkdir(parents=True, exist_ok=True)
        train_path.write_text("\n".join(train_blocks) + ("\n" if train_blocks else ""))
        val_path.write_text("\n".join(val_blocks) + ("\n" if val_blocks else ""))
        existing_test_path.write_text("\n".join(test_blocks) + ("\n" if test_blocks else ""))

        print(f"Groups ({args.group_field}): {n_groups} total -> "
              f"{n_train_groups} train / {n_val_groups} val / {n_test_groups} test")
        total_spectra = max(1, len(train_blocks) + len(val_blocks) + len(test_blocks))
        print(f"Spectra: {len(train_blocks)} train / {len(val_blocks)} val / "
              f"{len(test_blocks)} test (actual "
              f"{len(train_blocks)/total_spectra:.3f}:"
              f"{len(val_blocks)/total_spectra:.3f}:"
              f"{len(test_blocks)/total_spectra:.3f})")
        print(f"Wrote: {train_path}")
        print(f"Wrote: {val_path}")
        print(f"Wrote: {existing_test_path}")


if __name__ == "__main__":
    main()
