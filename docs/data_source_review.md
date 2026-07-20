# Day 2 Data Source Review

## Decision

Using the **2022 National Hospital Ambulatory Medical Care Survey (NHAMCS) Emergency Department Public Use File** as the provisional Version 1 data source.

This is a data-source decision, not approval of a final modeling target. Day 3 will validate the label mapping, quantify exclusions and missingness, and confirm that the selected predictors are available at triage time.

## Dataset requirements

The Version 1 source should provide:

- one row per encounter or presentation;
- structured presenting symptoms or reasons for visit;
- patient context such as age;
- measurements available at initial triage, preferably vital signs and pain;
- an existing, auditable urgency or acuity assessment;
- enough records to evaluate three classes separately;
- public documentation, clear provenance, and reproducible access;
- no direct patient identifiers or need to handle protected health information;
- terms compatible with a public portfolio repository.

Convenience datasets without an authoritative data dictionary, provenance, or usage terms are out of scope even if they are easy to download.

## Candidate comparison

| Candidate | Strengths | Blocking limitations | Decision |
| --- | --- | --- | --- |
| 2022 NHAMCS ED public-use file | CDC/NCHS source; 16,025 sampled ED visits; structured reasons for visit, initial vital signs, pain, age, and nurse-triage immediacy; public-use download and extensive documentation | Survey represents visits rather than people; target is an operational triage assessment, not a patient outcome; `IMMEDR` has 27.8% nonresponse and is not imputed; symptom reasons are coded rather than free text | **Select provisionally** |
| MIMIC-IV-ED v2.2 | Detailed ED data; numeric vital signs, pain, free-text chief complaint, and 1–5 acuity | Credentialing, CITI training, a signed data-use agreement, and restricted redistribution make onboarding and a reproducible public portfolio harder; single-center data | Reject for Version 1; reconsider for private follow-up research |
| Synthea | Fully synthetic records; no real-patient privacy risk; reproducible generator; Apache-2.0 licensed | A simulated record is not evidence that an urgency label reflects real triage practice; additional authored rules would determine both cases and labels, creating circular evaluation | Keep only as a demo/test-data fallback |

## Selected source

**Publisher:** National Center for Health Statistics (NCHS), Centers for Disease Control and Prevention (CDC)

**Survey:** National Hospital Ambulatory Medical Care Survey, Emergency Department component

**Year:** 2022, the final NHAMCS collection year

**Unit of analysis:** A sampled visit to an emergency department, not a unique patient

**Record count:** 16,025 electronic patient-record forms

**Coverage:** A national probability sample of visits to emergency departments in nonfederal, general, and short-stay hospitals in the 50 states and District of Columbia. Federal, military, and Veterans Administration hospitals are excluded.

**Official resources:**

- [CDC dataset and documentation page](https://www.cdc.gov/nchs/nhamcs/documentation/index.html)
- [2022 technical documentation and codebook](https://ftp.cdc.gov/pub/health_statistics/nchs/dataset_documentation/NHAMCS/doc22-ed-508.pdf)
- [2022 Stata public-use archive](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHAMCS/stata/ed2022-stata.zip)
- [2022 emergency-department patient record form](https://www.cdc.gov/nchs/data/nhamcs/2022-nhamcs-ed-prf-sample-card-508.pdf)

## Candidate modeling fields

Only information plausibly available at or before triage should be considered as input features. The initial candidate set is:

| Role | Fields | Notes |
| --- | --- | --- |
| Target candidate | `IMMEDR` | Unimputed immediacy with which the patient should be seen: immediate, emergent, urgent, semi-urgent, or nonurgent |
| Presenting complaint | `RFV1`–`RFV5` | Patient reasons for visit encoded with the NCHS Reason for Visit Classification; retain the codebook mapping |
| Demographics/context | `AGE`, potentially `SEX` | Age is top-coded at 94; protected attributes require a documented inclusion and fairness rationale |
| Initial measurements | `TEMPF`, `PULSE`, `RESPR`, `BPSYS`, `BPDIAS`, `POPCT` | Initial temperature, heart rate, respiratory rate, blood pressure, and pulse oximetry |
| Reported severity | `PAINSCALE` | Numeric 0–10 scale with substantial missingness |
| Visit context | `ARREMS`, `SEEN72`, `EPISODE`, selected injury indicators | Include only if known at triage and appropriate for the eventual user input contract |
| Survey analysis | `PATWT`, masked design variables | Preserve for descriptive population estimates; do not automatically use weights as predictive features |

Fields created after triage—diagnoses, procedures, medications, disposition, admission, wait time, and length of visit—must not be model inputs because they leak downstream information.

## Provisional label mapping for Day 3 review

The source has five valid triage levels. TriageLens needs three educational project categories. The simplest auditable mapping to test is:

| NHAMCS `IMMEDR` | Proposed project label |
| --- | --- |
| `1` Immediate | `emergent` |
| `2` Emergent | `emergent` |
| `3` Urgent | `urgent` |
| `4` Semi-urgent | `routine` |
| `5` Nonurgent | `routine` |

Values for blank (`-9`), unknown (`-8`), no triage (`0`), and facilities without nursing triage (`7`) should be excluded from supervised training rather than guessed.

This mapping is provisional. In particular, the project term `routine` may overstate the safety of an ED visit labeled semi-urgent. Day 3 must either justify the terminology, rename the project class, or document a more conservative mapping before any model is trained.

## Access, licensing, and redistribution

NCHS publishes the selected file as a public-use dataset and states that potentially identifiable information has been removed. The technical documentation includes a separate Cerner Multum license for drug-database content. Version 1 does not need medication or Multum-derived fields, so those fields should be excluded to avoid unnecessary licensing complexity.

The repository should not redistribute the raw archive by default. Instead, keep a reproducible download URL, checksum, retrieval date, and preparation script. This preserves provenance and avoids silently republishing third-party material. Before any processed extract is published, recheck the source terms and include the required NCHS citation and notices.

## Known limitations and risks

- The data describe people who reached a U.S. emergency department; they do not represent all people deciding whether or where to seek care.
- The label records the assigned triage level, not a diagnosis, outcome, or independently validated ground truth.
- Triage practices can vary across facilities and staff.
- `IMMEDR` is unimputed and has 27.8% nonresponse in the 2022 file, so complete-case filtering may introduce selection bias.
- Pain has 44.0% nonresponse; vital-sign nonresponse ranges from roughly 5% to 11% in the documentation.
- The file contains coded reasons for visit, not the natural-language symptom descriptions envisioned for a later frontend.
- Race, ethnicity, sex, age, payment, geography, and access patterns may encode structural inequities. Subgroup evaluation is required even if some protected attributes are excluded from prediction.
- NHAMCS ended in 2022, so future refreshes would require a different survey such as NHCS and a compatibility study.
- Combining years requires care because collection and processing of `IMMEDR` changed over time.

## Reproducible acquisition plan

Do not manually edit the source file.

1. Download `ed2022-stata.zip` from the official CDC URL into `data/raw/`.
2. Record the retrieval date and SHA-256 checksum in a data manifest.
3. Extract the Stata `.dta` file locally.
4. Load it with `pandas.read_stata` and verify the row count is 16,025.
5. Preserve raw coded values and attach human-readable labels in derived columns.
6. Write all cleaned outputs to `data/processed/`, which is ignored by Git.
7. Commit only acquisition/preparation code, the manifest, and documentation—not generated data unless redistribution is explicitly approved.

## Day 3 entry criteria

Day 3 should not begin modeling until it has:

- downloaded and checksummed the official archive;
- profiled target counts and missingness without changing the raw file;
- verified exact column names and dtypes;
- documented inclusion and exclusion rules;
- resolved whether `routine` is an acceptable name for combined semi-urgent/nonurgent visits;
- checked whether a three-class split leaves enough emergent examples for stratified train/validation/test sets;
- defined a leakage-safe, structured Version 1 feature set;
- documented how survey weights will and will not be used.

## Sources reviewed

- [CDC: NHAMCS questionnaires, datasets, and documentation](https://www.cdc.gov/nchs/nhamcs/documentation/index.html), accessed 2026-07-17.
- [CDC/NCHS: 2022 NHAMCS micro-data file documentation](https://ftp.cdc.gov/pub/health_statistics/nchs/dataset_documentation/NHAMCS/doc22-ed-508.pdf), accessed 2026-07-17.
- [PhysioNet: MIMIC-IV-ED v2.2](https://physionet.org/content/mimic-iv-ed/2.2/), accessed 2026-07-17.
- [Synthea repository and license](https://github.com/synthetichealth/synthea), accessed 2026-07-17.
