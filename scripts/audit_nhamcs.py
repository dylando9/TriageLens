"""Validate and summarize the locally downloaded 2022 NHAMCS ED file."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data" / "raw" / "manifest.json"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "day3_audit.json"

VALID_TRIAGE_CODES = {1, 2, 3, 4, 5}
LABEL_MAP = {
    1: "emergent",
    2: "emergent",
    3: "urgent",
    4: "lower_acuity",
    5: "lower_acuity",
}
MISSING_SENTINELS = {-9, -8, -7}
CANDIDATE_FEATURES = [
    "AGE",
    "ARREMS",
    "TEMPF",
    "PULSE",
    "RESPR",
    "BPSYS",
    "BPDIAS",
    "POPCT",
    "PAINSCALE",
    "SEEN72",
    "EPISODE",
    "RFV1",
    "RFV2",
    "RFV3",
    "RFV4",
    "RFV5",
]
REQUIRED_COLUMNS = ["IMMEDR", "PATWT", "CSTRATM", "CPSUM", *CANDIDATE_FEATURES]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_missing(series: pd.Series) -> pd.Series:
    """Return the NHAMCS missing-value mask without changing the raw values."""
    return series.isna() | series.isin(MISSING_SENTINELS)


def apply_label_mapping(series: pd.Series) -> pd.Series:
    """Map valid five-level NHAMCS triage codes to TriageLens classes."""
    return series.map(LABEL_MAP)


def count_values(series: pd.Series) -> dict[str, int]:
    counts = series.value_counts(dropna=False).sort_index()
    return {str(key): int(value) for key, value in counts.items()}


def validate_checksum(path: Path, expected_hash: str) -> str:
    """Require a manifest file and verify its SHA-256 checksum."""
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}.")

    actual_hash = sha256(path)
    if actual_hash != expected_hash:
        raise ValueError(f"SHA-256 mismatch for {path.name}: {actual_hash}")
    return actual_hash


def audit(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text())
    archive_path = manifest_path.parent / manifest["archive"]["filename"]
    data_path = manifest_path.parent / manifest["extracted_file"]["filename"]

    archive_hash = validate_checksum(archive_path, manifest["archive"]["sha256"])
    data_hash = validate_checksum(data_path, manifest["extracted_file"]["sha256"])

    frame = pd.read_stata(data_path, convert_categoricals=False)
    if len(frame) != manifest["expected_rows"]:
        raise ValueError(f"Expected {manifest['expected_rows']} rows, found {len(frame)}")

    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    eligible = frame[frame["IMMEDR"].isin(VALID_TRIAGE_CODES)].copy()
    eligible["triage_label"] = apply_label_mapping(eligible["IMMEDR"])
    label_counts = eligible["triage_label"].value_counts()

    feature_missingness = {}
    for column in CANDIDATE_FEATURES:
        count = int(is_missing(eligible[column]).sum())
        feature_missingness[column] = {
            "count": count,
            "percent": round(count / len(eligible) * 100, 2),
        }

    return {
        "source_rows": len(frame),
        "source_columns": len(frame.columns),
        "exact_duplicate_rows": int(frame.duplicated().sum()),
        "triage_code_counts": count_values(frame["IMMEDR"]),
        "eligible_rows": len(eligible),
        "excluded_rows": len(frame) - len(eligible),
        "eligible_percent": round(len(eligible) / len(frame) * 100, 2),
        "label_counts": {key: int(value) for key, value in label_counts.items()},
        "label_percent": {
            key: round(value / len(eligible) * 100, 2)
            for key, value in label_counts.items()
        },
        "feature_missingness": feature_missingness,
        "archive_sha256": archive_hash,
        "data_sha256": data_hash,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    result = audit(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    print(f"\nWrote audit report to {args.output}")


if __name__ == "__main__":
    main()
