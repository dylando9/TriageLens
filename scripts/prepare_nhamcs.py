"""Create leakage-safe train, validation, and test splits for TriageLens."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.model_selection import train_test_split

try:
    from scripts.audit_nhamcs import LABEL_MAP, MISSING_SENTINELS, validate_checksum
except ModuleNotFoundError:  # Support `python scripts/prepare_nhamcs.py`.
    from audit_nhamcs import LABEL_MAP, MISSING_SENTINELS, validate_checksum


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data" / "raw" / "manifest.json"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "processed"
RANDOM_SEED = 42

PREDICTOR_COLUMNS = [
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
SURVEY_COLUMNS = ["PATWT", "CSTRATM", "CPSUM"]
MISSING_INDICATOR_COLUMNS = [column for column in PREDICTOR_COLUMNS if column != "AGE"]
NONNUMERIC_CODES = {
    "PULSE": {998},  # Doppler measurement
    "BPDIAS": {998},  # Palpation or Doppler measurement
}
REQUIRED_COLUMNS = ["IMMEDR", *PREDICTOR_COLUMNS, *SURVEY_COLUMNS]
TARGET_COLUMN = "triage_label"
ID_COLUMN = "source_row_id"
MISSING_INDICATOR_NAMES = [
    f"{column}_missing" for column in MISSING_INDICATOR_COLUMNS
]
MODEL_COLUMNS = [*PREDICTOR_COLUMNS, *MISSING_INDICATOR_NAMES, TARGET_COLUMN]
METADATA_COLUMNS = [ID_COLUMN, "source_immedr", *SURVEY_COLUMNS]

PLAUSIBILITY_RANGES = {
    "TEMPF": (90, 110),
    "PULSE": (20, 300),
    "RESPR": (4, 80),
    "BPSYS": (40, 300),
    "BPDIAS": (20, 200),
    "POPCT": (50, 100),
}


def load_source(manifest_path: Path) -> pd.DataFrame:
    """Validate the raw files, then load only fields needed for Day 4."""
    manifest = json.loads(manifest_path.read_text())
    raw_dir = manifest_path.parent
    archive_path = raw_dir / manifest["archive"]["filename"]
    data_path = raw_dir / manifest["extracted_file"]["filename"]

    validate_checksum(archive_path, manifest["archive"]["sha256"])
    validate_checksum(data_path, manifest["extracted_file"]["sha256"])

    frame = pd.read_stata(
        data_path,
        columns=REQUIRED_COLUMNS,
        convert_categoricals=False,
    )
    if len(frame) != manifest["expected_rows"]:
        raise ValueError(f"Expected {manifest['expected_rows']} rows, found {len(frame)}")
    return frame


def prepare_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Filter, label, and clean a copy without modifying the source frame."""
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    eligible = frame.loc[frame["IMMEDR"].isin(LABEL_MAP)].copy()
    eligible.insert(0, ID_COLUMN, eligible.index.astype("int64"))
    eligible[TARGET_COLUMN] = eligible["IMMEDR"].map(LABEL_MAP)
    eligible = eligible.rename(columns={"IMMEDR": "source_immedr"})

    for column in MISSING_INDICATOR_COLUMNS:
        missing_codes = MISSING_SENTINELS | NONNUMERIC_CODES.get(column, set())
        missing = eligible[column].isna() | eligible[column].isin(missing_codes)
        eligible[f"{column}_missing"] = missing.astype("int8")
        eligible.loc[missing, column] = pd.NA

    eligible["TEMPF"] = eligible["TEMPF"] / 10
    return eligible.reset_index(drop=True)


def split_frame(
    frame: pd.DataFrame, random_seed: int = RANDOM_SEED
) -> dict[str, pd.DataFrame]:
    """Make deterministic stratified splits while keeping duplicate rows together."""
    group_key = pd.util.hash_pandas_object(
        frame[PREDICTOR_COLUMNS], index=False
    ).rename("predictor_group")
    grouped = pd.DataFrame(
        {"predictor_group": group_key, TARGET_COLUMN: frame[TARGET_COLUMN]}
    )
    conflicting = grouped.groupby("predictor_group")[TARGET_COLUMN].nunique()
    if (conflicting > 1).any():
        raise ValueError("Identical predictor rows have conflicting target labels")

    unique_groups = grouped.drop_duplicates("predictor_group")
    train_groups, remainder_groups = train_test_split(
        unique_groups,
        test_size=0.30,
        random_state=random_seed,
        stratify=unique_groups[TARGET_COLUMN],
    )
    validation_groups, test_groups = train_test_split(
        remainder_groups,
        test_size=0.50,
        random_state=random_seed,
        stratify=remainder_groups[TARGET_COLUMN],
    )
    group_assignments = {
        "train": set(train_groups["predictor_group"]),
        "validation": set(validation_groups["predictor_group"]),
        "test": set(test_groups["predictor_group"]),
    }
    return {
        name: frame.loc[group_key.isin(keys)].sort_values(ID_COLUMN).reset_index(drop=True)
        for name, keys in group_assignments.items()
    }


def _counts(series: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in series.value_counts().items()}


def build_summary(
    prepared: pd.DataFrame, splits: dict[str, pd.DataFrame], random_seed: int
) -> dict[str, Any]:
    """Build reproducible EDA metadata without changing any split."""
    split_summary = {}
    all_ids: list[int] = []
    for name, split in splits.items():
        ids = split[ID_COLUMN].astype(int).tolist()
        all_ids.extend(ids)
        split_summary[name] = {
            "rows": len(split),
            "percent": round(len(split) / len(prepared) * 100, 2),
            "label_counts": _counts(split[TARGET_COLUMN]),
        }

    training = splits["train"]
    missingness = {}
    missingness_by_label = {}
    for column in PREDICTOR_COLUMNS:
        missingness[column] = {
            "count": int(training[column].isna().sum()),
            "percent": round(float(training[column].isna().mean() * 100), 2),
        }
        missingness_by_label[column] = {
            str(label): round(float(group[column].isna().mean() * 100), 2)
            for label, group in training.groupby(TARGET_COLUMN, observed=True)
        }

    numeric_ranges = {
        column: {
            "min": float(training[column].min()),
            "max": float(training[column].max()),
        }
        for column in [
            "AGE",
            "TEMPF",
            "PULSE",
            "RESPR",
            "BPSYS",
            "BPDIAS",
            "POPCT",
            "PAINSCALE",
        ]
    }
    suspicious_values = {}
    for column, (minimum, maximum) in PLAUSIBILITY_RANGES.items():
        values = training[column].dropna()
        suspicious_values[column] = int(((values < minimum) | (values > maximum)).sum())

    rfv_columns = [f"RFV{number}" for number in range(1, 6)]
    top_rfv_codes = {
        column: {
            str(code): int(count)
            for code, count in training[column].value_counts().head(10).items()
        }
        for column in rfv_columns
    }

    return {
        "random_seed": random_seed,
        "split_strategy": "stratified 70/15/15",
        "eligible_rows": len(prepared),
        "predictor_columns": PREDICTOR_COLUMNS,
        "survey_metadata_columns": SURVEY_COLUMNS,
        "missing_indicator_columns": MISSING_INDICATOR_NAMES,
        "label_counts": _counts(prepared[TARGET_COLUMN]),
        "splits": split_summary,
        "split_ids_unique": len(all_ids) == len(set(all_ids)) == len(prepared),
        "predictor_groups_unique_across_splits": all(
            set(
                pd.util.hash_pandas_object(left[PREDICTOR_COLUMNS], index=False)
            ).isdisjoint(
                set(pd.util.hash_pandas_object(right[PREDICTOR_COLUMNS], index=False))
            )
            for index, left in enumerate(splits.values())
            for right in list(splits.values())[index + 1 :]
        ),
        "rows_in_exact_duplicate_predictor_groups": int(
            prepared.duplicated(subset=PREDICTOR_COLUMNS, keep=False).sum()
        ),
        "training_eda": {
            "missingness": missingness,
            "missingness_percent_by_label": missingness_by_label,
            "numeric_ranges": numeric_ranges,
            "plausibility_ranges_for_review": {
                key: list(value) for key, value in PLAUSIBILITY_RANGES.items()
            },
            "values_outside_review_ranges": suspicious_values,
            "categorical_cardinality": {
                column: int(training[column].nunique(dropna=True))
                for column in ["ARREMS", "SEEN72", "EPISODE", *rfv_columns]
            },
            "top_rfv_codes": top_rfv_codes,
        },
    }


def write_outputs(
    splits: dict[str, pd.DataFrame], summary: dict[str, Any], output_dir: Path
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = []
    for name, split in splits.items():
        split[MODEL_COLUMNS].to_csv(output_dir / f"{name}.csv", index=False)
        split_metadata = split[METADATA_COLUMNS].copy()
        split_metadata.insert(1, "split", name)
        metadata.append(split_metadata)
    pd.concat(metadata, ignore_index=True).sort_values(ID_COLUMN).to_csv(
        output_dir / "split_metadata.csv", index=False
    )
    (output_dir / "day4_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--random-seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()

    source = load_source(args.manifest)
    prepared = prepare_frame(source)
    splits = split_frame(prepared, args.random_seed)
    summary = build_summary(prepared, splits, args.random_seed)
    write_outputs(splits, summary, args.output_dir)

    print(json.dumps(summary["splits"], indent=2))
    print(f"\nWrote Day 4 outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
