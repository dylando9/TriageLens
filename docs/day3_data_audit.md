# Day 3 Data Audit and Label Framework

## Outcome

The 2022 NHAMCS Emergency Department public-use file is suitable for the first TriageLens modeling iteration, subject to the limitations below. The audit found 16,025 rows and 913 columns, matching the official documentation. There are no exact duplicate rows.

The five valid nurse-triage levels produce 10,207 eligible records after excluding blank, unknown, no-triage, and non-triaging-facility codes. This leaves enough examples of every proposed class for stratified development, validation, and test sets.

## Reproduction

The raw archive and extracted dataset are intentionally ignored by Git. Their source, retrieval date, checksums, and expected row count are recorded in [`data/raw/manifest.json`](../data/raw/manifest.json).

After downloading and extracting the official archive as described in the manifest, run:

```bash
python scripts/audit_nhamcs.py
pytest
```

The audit validates the archive and extracted-file checksums, row count, and required columns before writing a generated report to `data/processed/day3_audit.json`.

## Target audit

| Raw `IMMEDR` code | Meaning | Rows | Treatment |
| --- | --- | ---: | --- |
| `-9` | Blank | 364 | Exclude |
| `-8` | Unknown | 3,788 | Exclude |
| `0` | No triage despite facility conducting triage | 587 | Exclude |
| `1` | Immediate | 139 | `emergent` |
| `2` | Emergent | 1,595 | `emergent` |
| `3` | Urgent | 5,340 | `urgent` |
| `4` | Semi-urgent | 2,826 | `lower_acuity` |
| `5` | Nonurgent | 307 | `lower_acuity` |
| `7` | Facility does not conduct nursing triage | 1,079 | Exclude |

Total eligible rows: **10,207 (63.69%)**. Total excluded rows: **5,818 (36.31%)**.

## Final Version 1 labels

| TriageLens label | Source codes | Rows | Share |
| --- | --- | ---: | ---: |
| `emergent` | Immediate + emergent (`1`, `2`) | 1,734 | 16.99% |
| `urgent` | Urgent (`3`) | 5,340 | 52.32% |
| `lower_acuity` | Semi-urgent + nonurgent (`4`, `5`) | 3,133 | 30.69% |

The former label `routine` is replaced with `lower_acuity`. A semi-urgent emergency-department presentation should not be described as routine, and this project cannot infer that delaying care is safe. The new term is comparative: it means lower acuity than the other source levels, not “no care needed.”

A 70/15/15 stratified split would contain approximately 1,214/260/260 emergent examples, so emergent-class evaluation is viable. The exact split and random seed belong to the preprocessing milestone.

## Initial leakage-safe feature boundary

Version 1 may evaluate these fields because they are available at or near triage:

- `AGE`
- `ARREMS` (arrival by ambulance)
- `TEMPF`, `PULSE`, `RESPR`, `BPSYS`, `BPDIAS`, `POPCT`
- `PAINSCALE`
- `SEEN72`, `EPISODE`
- `RFV1` through `RFV5`

Race, ethnicity, sex, payment source, geography, and facility identifiers are retained only for bias and subgroup auditing in the first iteration; they are not initial prediction features. Their later inclusion would require a specific justification.

Never use post-triage fields such as diagnosis, testing, procedures, medications, wait time, length of visit, disposition, admission, or outcome as predictors. Those values reveal decisions or events occurring after the target assessment.

## Missingness among eligible rows

| Field | Missing/unknown |
| --- | ---: |
| `AGE` | 0.00% |
| `ARREMS` | 1.62% |
| `TEMPF` | 2.93% |
| `PULSE` | 1.65% |
| `RESPR` | 2.34% |
| `BPSYS` | 8.11% |
| `BPDIAS` | 8.26% |
| `POPCT` | 2.15% |
| `PAINSCALE` | 29.23% |
| `SEEN72` | 6.24% |
| `EPISODE` | 7.63% |
| `RFV1` | 0.06% |
| `RFV2`–`RFV5` | 30.80%–83.87% |

Missing optional reason-for-visit fields generally mean that fewer complaints were recorded, so they require an explicit “not recorded” representation rather than row deletion. Pain needs a missingness indicator and careful evaluation because nearly three in ten eligible records lack a usable value. Numeric vital-sign imputation must be learned from training data only.

## Survey weights

`PATWT`, `CSTRATM`, and `CPSUM` must be retained for survey-aware descriptive statistics. `PATWT` is not a patient characteristic and must not be used as a model input. Initial model training and record-level predictive metrics will be unweighted; weighted sensitivity analyses can be reported separately and must account for the survey design.

## Exclusion rules

Exclude a record from supervised modeling when:

- `IMMEDR` is `-9`, `-8`, `0`, or `7`;
- the target is otherwise outside codes `1`–`5`;
- future validation identifies an impossible or corrupted target value.

Do not exclude a row merely because an optional predictor is missing. Predictor-specific handling will be implemented in a train-only preprocessing pipeline to avoid leakage.

## Remaining limitations

- The model will reproduce an observed nurse-triage assessment, not medical truth or patient outcome.
- The eligible subset may differ systematically from records with missing or unavailable triage.
- Source data cover people who arrived at an ED, not the broader population considering whether to seek care.
- The target collapse hides differences between immediate and emergent, and between semi-urgent and nonurgent visits.
- Coded presenting reasons do not directly match a future consumer-facing symptom checklist.
- A single year cannot measure performance stability over time.

These limitations require prominent documentation and subgroup/error analysis throughout model development.
