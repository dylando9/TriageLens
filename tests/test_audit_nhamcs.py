import pandas as pd

from scripts.audit_nhamcs import apply_label_mapping, is_missing


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
