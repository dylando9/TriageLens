# Day 4 Preprocessing and Exploratory Data Analysis

## Abbreviations

- Comma-separated values (CSV)
- Exploratory data analysis (EDA)
- National Hospital Ambulatory Medical Care Survey (NHAMCS)
- Reason for Visit (RFV)

## Source field names

- Age (AGE)
- Arrival by ambulance (ARREMS)
- Diastolic blood pressure (BPDIAS)
- Episode of care (EPISODE)
- Heart rate (PULSE)
- Immediacy with which the patient should be seen (IMMEDR)
- Masked primary sampling unit (CPSUM)
- Masked stratum (CSTRATM)
- Pain scale (PAINSCALE)
- Patient visit weight (PATWT)
- Pulse oximetry percentage (POPCT)
- Reason for visit positions 1 through 5 (RFV1–RFV5)
- Respiratory rate (RESPR)
- Seen in the emergency department within the prior 72 hours (SEEN72)
- Systolic blood pressure (BPSYS)
- Temperature in degrees Fahrenheit (TEMPF)

## Outcome

The audited NHAMCS records are now converted into reproducible, leakage-safe
training, validation, and test files. The preparation script retains 10,207
eligible visits, cleans documented missing and nonnumeric codes, converts
temperature to degrees Fahrenheit, and makes stratified 70/15/15 splits using
random seed 42.

Exact duplicate predictor rows are assigned as a group, so an identical feature
vector cannot appear in more than one split. The raw source file is never edited.

## Reproduction

Run from the repository root with the project environment activated:

```bash
python scripts/prepare_nhamcs.py
pytest
```

The script writes ignored, reproducible artifacts to `data/processed/`:

- `train.csv`
- `validation.csv`
- `test.csv`
- `split_metadata.csv`
- `day4_summary.json`

The companion notebook at
[`notebooks/day4_preprocessing_review.ipynb`](../notebooks/day4_preprocessing_review.ipynb)
provides charts and manual review checks using training features only. It does not
replace the automated test suite.

## Split results

| Split | Rows | Share | Emergent | Urgent | Lower acuity |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 7,144 | 69.99% | 1,214 | 3,737 | 2,193 |
| Validation | 1,532 | 15.01% | 260 | 802 | 470 |
| Test | 1,531 | 15.00% | 260 | 801 | 470 |

All 10,207 eligible source row IDs occur exactly once. All three labels are
represented in every split. Six records belong to three exact duplicate
predictor pairs; grouping those pairs before splitting prevents cross-split
leakage.

## Cleaning decisions

- Only `IMMEDR` codes 1 through 5 are retained.
- The Day 3 mapping creates `emergent`, `urgent`, and `lower_acuity`.
- `-9`, `-8`, and `-7` are converted to missing values in the processed copy.
- `PULSE=998` and `BPDIAS=998` are documented Doppler or palpation codes and
  are converted to missing values.
- `TEMPF` is divided by 10 so that, for example, `982` becomes 98.2°F.
- A missingness indicator is retained for every predictor that may be missing.
- `PATWT`, `CSTRATM`, and `CPSUM` remain available as survey metadata but are
  explicitly excluded from the predictor list.
- No imputer, scaler, encoder, feature selector, or model is fit on Day 4. Those
  transformations must be learned from the training split only on Day 5.

The three modeling CSV files contain only approved predictors, missingness
indicators, and `triage_label`. Direct target information, identifiers, and survey
fields are kept out of those files. `split_metadata.csv` separately retains
`source_row_id`, `source_immedr`, survey fields, and split membership for
reproducibility and auditing. This separation prevents an accidental
"drop-the-label" workflow from training on the original target code.

## Training-set EDA

Feature-level exploration is intentionally limited to the training split. The
validation and test features remain isolated from preprocessing decisions.

### Missingness

The largest training-set missingness rates are:

| Feature | Missing |
| --- | ---: |
| `RFV5` | 84.13% |
| `RFV4` | 72.13% |
| `RFV3` | 54.94% |
| `RFV2` | 30.94% |
| `PAINSCALE` | 28.93% |
| `BPDIAS` | 7.98% |
| `BPSYS` | 7.84% |
| `EPISODE` | 7.53% |

Optional RFV fields indicate that fewer complaints were recorded, so their
missingness must not cause row deletion. Pain and blood-pressure missingness also
varies by label, reinforcing the decision to retain explicit indicators.

### Range review

After documented nonnumeric codes are removed, the training data still contains
values outside broad review ranges:

| Feature | Observed training range | Values flagged for review |
| --- | ---: | ---: |
| Temperature | 91.8–104.9°F | 0 |
| Pulse | 6–217/min | 6 |
| Respiratory rate | 1–150/min | 11 |
| Systolic pressure | 43–289 mmHg | 0 |
| Diastolic pressure | 25–190 mmHg | 0 |
| Pulse oximetry | 0–100% | 23 |

These flags are deliberately not removed or clipped. Extreme observations can be
valid in emergency care, and plausibility thresholds are not clinical validation
rules. Day 5 should compare a transparent missing/imputation strategy and inspect
whether extreme values dominate the baseline model.

### Reason-for-visit fields

The five RFV positions have high cardinality in the training set: 424, 454, 401,
351, and 266 observed codes respectively. Treating each position as an unrelated
continuous number would be incorrect. The baseline pipeline should encode RFV
codes categorically and handle unseen validation/test codes safely. A later model
may compare code grouping or a position-independent multi-hot representation.

## Day 5 entry criteria

Day 5 may begin because:

- source files and checksums are validated before preparation;
- target exclusions and mappings are reproducible;
- splits are deterministic, stratified, complete, and non-overlapping;
- duplicate predictor groups cannot cross split boundaries;
- training-only EDA is recorded;
- survey metadata and non-predictive audit fields are separated from features;
- automated tests cover filtering, cleaning, schema boundaries, reproducibility,
  stratification, duplicate grouping, non-overlap, and output creation.

The test set must remain untouched until the final selected model is evaluated.
