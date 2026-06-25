# Fraud Detection Infrastructure

Training implementation of a fraud detection API. It scores transactions in
real time, applies versioned rules, opens analyst cases for high-risk activity,
and feeds reviewed decisions back into a canary deployment workflow.

## Features

- Transaction feature extraction for velocity, amount deviation, and geo anomaly.
- Versioned rule sets with override support for testing a specific rules version.
- Risk assessments with low, medium, and high risk levels.
- Case management for flagged transactions with notes and analyst decisions.
- Feedback loop that collects labels, estimates precision, and deploys a rule set
  as a canary.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
uvicorn fraud_detection_infrastructure.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API docs.

## Test

```bash
pytest
```

## Key endpoints

- `POST /rule-sets`
- `POST /transactions/score`
- `GET /cases`
- `POST /cases/{case_id}/notes`
- `POST /cases/{case_id}/review`
- `POST /feedback/deploy-canary`
