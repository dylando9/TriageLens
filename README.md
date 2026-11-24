# TriageLens

## Abbreviations

- Application programming interface (API)
- Exploratory data analysis (EDA)
- Large language model (LLM)
- Machine learning (ML)
- National Hospital Ambulatory Medical Care Survey (NHAMCS)

TriageLens is a portfolio project that classifies structured symptom information into one of three acuity tiers: `emergent`, `urgent`, or `lower_acuity`. The project will emphasize transparent evaluation, explainable predictions, and responsible use of language models.

> **Important:** TriageLens is a learning project, not a medical device or diagnostic tool. It must not be used to make healthcare decisions or replace evaluation by a qualified healthcare professional. If someone may be experiencing a medical emergency, they should contact local emergency services.

## Project objective

Build and deploy a full-stack machine-learning application that demonstrates:

- reproducible dataset construction and urgency labeling;
- class-sensitive model evaluation, especially recall for emergent cases;
- an explicit safety-rule layer separate from the classifier;
- interpretable model output and contributing factors;
- a constrained LLM explanation layer that cannot change the prediction;
- a FastAPI backend and a Next.js/TypeScript frontend.

## Initial scope

Version 1 accepts a structured symptom checklist and returns an educational urgency classification with confidence, contributing factors, and a disclaimer. The first ML milestone uses three labels:

| Label | Project definition |
| --- | --- |
| `emergent` | The educational ruleset flags the case for immediate emergency evaluation. |
| `urgent` | The educational ruleset flags the case for prompt, same-day evaluation. |
| `lower_acuity` | The source triage assessment is below the emergent and urgent tiers. This does not mean that care is unnecessary or can safely be delayed. |

These labels are project categories, not clinical determinations.

## Non-goals

TriageLens will not:

- diagnose diseases or recommend medication;
- process real patient data or protected health information;
- represent itself as clinically validated or approved;
- allow an LLM to independently assign or alter urgency;
- replace professional judgment, emergency services, or local triage protocols.

See [docs/project_scope.md](docs/project_scope.md) for the working boundaries and success criteria.

## Planned architecture

```text
Next.js + TypeScript frontend
            |
            v
       FastAPI service
            |
            v
Safety rules -> ML classifier -> feature explanation
                                  |
                                  v
                    constrained LLM wording layer
```

## Repository structure

```text
backend/       Python API and inference code
data/raw/      Original public or synthetic source data
data/processed Generated modeling datasets (not committed)
docs/          Data, labeling, safety, and design documentation
frontend/      Next.js application (added in a later phase)
models/        Generated model artifacts (not committed by default)
notebooks/     Exploration and model experiments
tests/         Automated tests
```

## Local setup

Python 3.11 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The repository currently includes reproducible data-audit and preprocessing
scripts with automated tests. Modeling, API, and frontend code will be added in
later milestones.

## Roadmap

- Week 1: data selection, labeling framework, EDA, preprocessing, and baseline model
- Week 2: model comparison, explainability, safety rules, FastAPI, and tests
- Week 3: text extraction, constrained LLM explanation, frontend, and deployment

## Current status

Day 1 complete: repository foundation, scope, disclaimer, and Python environment configuration.

Day 2 complete: data-source review and selection of the 2022 NHAMCS Emergency Department Public Use File. See [docs/data_source_review.md](docs/data_source_review.md).

Day 3 complete: the source file, schema, target distribution, missingness, exclusions, label mapping, and leakage-safe feature boundary have been audited. See [docs/day3_data_audit.md](docs/day3_data_audit.md).

Day 4 complete: eligible records are cleaned and divided into deterministic,
stratified, duplicate-group-safe training, validation, and test datasets. EDA is
limited to the training split, with an interactive review notebook for charts and
manual checks. See [docs/day4_preprocessing_eda.md](docs/day4_preprocessing_eda.md)
and [notebooks/day4_preprocessing_review.ipynb](notebooks/day4_preprocessing_review.ipynb).

## License and data provenance

A project license has not yet been selected. Dataset provenance and source-specific terms are documented in [docs/data_source_review.md](docs/data_source_review.md). Raw third-party data is not redistributed in this repository.
