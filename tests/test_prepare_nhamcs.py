from pathlib import Path

import pandas as pd
import pytest

from scripts.prepare_nhamcs import (
    ID_COLUMN,
    MISSING_INDICATOR_COLUMNS,
    MODEL_COLUMNS,
    PREDICTOR_COLUMNS,
    REQUIRED_COLUMNS,
    SURVEY_COLUMNS,
    TARGET_COLUMN,
    build_summary,
    prepare_frame,
    split_frame,
    write_outputs,
)


def _source_frame(rows_per_code: int = 20) -> pd.DataFrame:
    records = []
    for code in [-9, 0, 1, 2, 3, 4, 5, 7]:
        for offset in range(rows_per_code):
            record = {column: offset + 1 for column in REQUIRED_COLUMNS}
            record["IMMEDR"] = code
            record["AGE"] = 20 + offset
            record["RFV1"] = code * 1000 + offset
            record["PAINSCALE"] = -9 if offset == 0 else offset % 11
            record["RFV2"] = -8 if offset == 1 else 1000 + offset
            record["PULSE"] = 998 if offset == 2 else 60 + offset
            record["BPDIAS"] = 998 if offset == 3 else 70 + offset
            record["TEMPF"] = 982
            records.append(record)
    return pd.DataFrame(records)


def test_prepare_frame_filters_labels_and_preserves_source() -> None:
    source = _source_frame()
    original = source.copy(deep=True)

    prepared = prepare_frame(source)

    pd.testing.assert_frame_equal(source, original)
    assert len(prepared) == 5 * 20
    assert set(prepared[TARGET_COLUMN]) == {"emergent", "urgent", "lower_acuity"}
    assert set(prepared["source_immedr"]) == {1, 2, 3, 4, 5}
    assert prepared.loc[prepared["PAINSCALE_missing"] == 1, "PAINSCALE"].isna().all()
    assert prepared.loc[prepared["RFV2_missing"] == 1, "RFV2"].isna().all()
    assert prepared.loc[prepared["PULSE_missing"] == 1, "PULSE"].isna().all()
    assert prepared.loc[prepared["BPDIAS_missing"] == 1, "BPDIAS"].isna().all()
    assert set(prepared["TEMPF"]) == {98.2}


def test_prepared_schema_separates_predictors_and_survey_metadata() -> None:
    prepared = prepare_frame(_source_frame())

    expected = {
        ID_COLUMN,
        "source_immedr",
        TARGET_COLUMN,
        *PREDICTOR_COLUMNS,
        *SURVEY_COLUMNS,
        *(f"{column}_missing" for column in MISSING_INDICATOR_COLUMNS),
    }
    assert set(prepared.columns) == expected
    assert not set(SURVEY_COLUMNS) & set(PREDICTOR_COLUMNS)


def test_split_is_deterministic_stratified_and_non_overlapping() -> None:
    prepared = prepare_frame(_source_frame(rows_per_code=40))
    duplicate = prepared.iloc[[0]].copy()
    duplicate[ID_COLUMN] = 99999
    prepared = pd.concat([prepared, duplicate], ignore_index=True)

    first = split_frame(prepared)
    second = split_frame(prepared)

    assert sum(len(split) for split in first.values()) == 201
    for name in first:
        assert first[name][ID_COLUMN].tolist() == second[name][ID_COLUMN].tolist()
        assert set(first[name][TARGET_COLUMN]) == {
            "emergent",
            "urgent",
            "lower_acuity",
        }

    id_sets = [set(split[ID_COLUMN]) for split in first.values()]
    assert id_sets[0].isdisjoint(id_sets[1])
    assert id_sets[0].isdisjoint(id_sets[2])
    assert id_sets[1].isdisjoint(id_sets[2])
    assert set.union(*id_sets) == set(prepared[ID_COLUMN])
    original_split = next(
        name
        for name, split in first.items()
        if prepared.iloc[0][ID_COLUMN] in set(split[ID_COLUMN])
    )
    assert 99999 in set(first[original_split][ID_COLUMN])


def test_split_rejects_identical_predictors_with_conflicting_labels() -> None:
    prepared = prepare_frame(_source_frame(rows_per_code=40))
    conflicting = prepared.iloc[[0]].copy()
    conflicting[ID_COLUMN] = 99999
    conflicting[TARGET_COLUMN] = "urgent"
    prepared = pd.concat([prepared, conflicting], ignore_index=True)

    with pytest.raises(
        ValueError, match="Identical predictor rows have conflicting target labels"
    ):
        split_frame(prepared)


def test_summary_and_outputs_are_reproducible(tmp_path: Path) -> None:
    prepared = prepare_frame(_source_frame(rows_per_code=40))
    splits = split_frame(prepared)
    summary = build_summary(prepared, splits, random_seed=42)

    write_outputs(splits, summary, tmp_path)

    assert summary["split_ids_unique"] is True
    assert summary["predictor_groups_unique_across_splits"] is True
    assert summary["random_seed"] == 42
    assert summary["splits"]["train"]["percent"] == 70.0
    assert summary["splits"]["validation"]["percent"] == 15.0
    assert summary["splits"]["test"]["percent"] == 15.0
    assert {path.name for path in tmp_path.iterdir()} == {
        "train.csv",
        "validation.csv",
        "test.csv",
        "split_metadata.csv",
        "day4_summary.json",
    }
    train_output = pd.read_csv(tmp_path / "train.csv")
    assert train_output.columns.tolist() == MODEL_COLUMNS
    assert "source_immedr" not in train_output
    assert ID_COLUMN not in train_output
    assert not set(SURVEY_COLUMNS) & set(train_output.columns)

    metadata = pd.read_csv(tmp_path / "split_metadata.csv")
    assert set(metadata["split"]) == {"train", "validation", "test"}
    assert set(metadata[ID_COLUMN]) == set(prepared[ID_COLUMN])
