import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.audit_nhamcs import (
    REQUIRED_COLUMNS,
    apply_label_mapping,
    audit,
    is_missing,
)


def _sha256(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def _write_manifest(tmp_path: Path, expected_rows: int = 5) -> Path:
    archive_contents = b"archive fixture"
    data_contents = b"data fixture"
    (tmp_path / "source.zip").write_bytes(archive_contents)
    (tmp_path / "source.dta").write_bytes(data_contents)

    manifest = {
        "archive": {
            "filename": "source.zip",
            "sha256": _sha256(archive_contents),
        },
        "extracted_file": {
            "filename": "source.dta",
            "sha256": _sha256(data_contents),
        },
        "expected_rows": expected_rows,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return manifest_path


def _audit_frame() -> pd.DataFrame:
    frame = pd.DataFrame({column: [1, 1, 1, 1, 1] for column in REQUIRED_COLUMNS})
    frame["IMMEDR"] = [-9, 1, 2, 3, 5]
    return frame


def test_label_mapping_preserves_order_and_excludes_invalid_codes() -> None:
    codes = pd.Series([-9, -8, 0, 1, 2, 3, 4, 5, 7])

    labels = apply_label_mapping(codes)

    assert labels.tolist()[3:8] == [
        "emergent",
        "emergent",
        "urgent",
        "lower_acuity",
        "lower_acuity",
    ]
    assert labels.iloc[[0, 1, 2, 8]].isna().all()


def test_missing_mask_recognizes_documented_sentinels() -> None:
    values = pd.Series([-9, -8, -7, 0, 1, None])

    assert is_missing(values).tolist() == [True, True, True, False, False, True]


def test_audit_validates_source_and_summarizes_eligible_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _write_manifest(tmp_path)
    monkeypatch.setattr(pd, "read_stata", lambda *args, **kwargs: _audit_frame())

    result = audit(manifest_path)

    assert result["source_rows"] == 5
    assert result["eligible_rows"] == 4
    assert result["excluded_rows"] == 1
    assert result["label_counts"] == {
        "emergent": 2,
        "urgent": 1,
        "lower_acuity": 1,
    }
    assert result["archive_sha256"] == _sha256(b"archive fixture")
    assert result["data_sha256"] == _sha256(b"data fixture")


def test_audit_rejects_archive_checksum_mismatch(tmp_path: Path) -> None:
    manifest_path = _write_manifest(tmp_path)
    (tmp_path / "source.zip").write_bytes(b"changed archive")

    with pytest.raises(ValueError, match="SHA-256 mismatch for source.zip"):
        audit(manifest_path)


def test_audit_rejects_missing_extracted_file(tmp_path: Path) -> None:
    manifest_path = _write_manifest(tmp_path)
    (tmp_path / "source.dta").unlink()

    with pytest.raises(FileNotFoundError, match="Missing .*source.dta"):
        audit(manifest_path)


def test_audit_rejects_incorrect_row_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _write_manifest(tmp_path, expected_rows=6)
    monkeypatch.setattr(pd, "read_stata", lambda *args, **kwargs: _audit_frame())

    with pytest.raises(ValueError, match="Expected 6 rows, found 5"):
        audit(manifest_path)


def test_audit_rejects_missing_required_columns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _write_manifest(tmp_path)
    frame = _audit_frame().drop(columns="POPCT")
    monkeypatch.setattr(pd, "read_stata", lambda *args, **kwargs: frame)

    with pytest.raises(ValueError, match="Missing required columns: POPCT"):
        audit(manifest_path)
