# Project Scope

## Problem statement

People commonly describe symptoms in inconsistent language. TriageLens explores whether a supervised classifier can map a controlled, structured set of symptom and context features to broad urgency categories while exposing the factors that influenced its output.

The project is intended to demonstrate an end-to-end ML workflow. It is not intended to establish clinical efficacy.

## Intended user and use

The intended audience is portfolio reviewers, interviewers, and learners exploring responsible healthcare ML. Inputs must be fictional, public, or synthetic. The application output is an educational model demonstration only.

## Version 1 boundary

Version 1 will:

1. use a documented public or synthetic dataset;
2. construct reproducible urgency labels with clearly cited assumptions;
3. accept a finite structured feature set;
4. compare an interpretable baseline with selected candidate models;
5. report per-class metrics and prioritize emergent-class recall;
6. keep deterministic safety rules separate from learned behavior;
7. expose predictions through a tested API.

Free-text extraction, LLM-generated wording, and the web frontend are later milestones. They must not conceal weaknesses in the underlying dataset or classifier.

## Safety constraints

- Never collect names, contact details, medical-record identifiers, or other protected health information.
- Never describe model output as medical advice, a diagnosis, or clinical validation.
- Never let generative output introduce symptoms, modify urgency, or recommend medication.
- Display a prominent disclaimer at input and result stages.
- Document false negatives, class imbalance, dataset bias, and labeling uncertainty.
- Use fictional examples in screenshots, tests, and demos.

## Initial success criteria

- A new contributor can reproduce data preparation and model training from documented steps.
- The test set remains isolated from preprocessing decisions and tuning.
- Evaluation includes macro F1, per-class precision/recall, confusion matrices, and emergent recall.
- Every urgency label has an auditable source or rule.
- Safety-rule overrides and prediction outputs have automated tests.
- The deployed demo clearly communicates limitations and handles failures safely.

## Open questions for Day 2 and Day 3

- Which dataset has acceptable licensing, provenance, coverage, and feature quality?
- Does it contain urgency labels, or must labels be derived?
- Which authoritative triage references can support the labeling framework?
- Which records are too ambiguous to label responsibly and should be excluded?
- What minimum feature set can be supported by the chosen data?

