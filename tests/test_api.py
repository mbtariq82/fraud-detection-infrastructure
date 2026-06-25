from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from fraud_detection_infrastructure.main import create_app


def create_rules(client: TestClient) -> None:
    response = client.post(
        "/rule-sets",
        json={
            "version": "v1",
            "rules": [
                {
                    "name": "large-amount",
                    "field": "amount",
                    "operator": ">",
                    "value": 1000,
                    "score": 80,
                    "reason": "Large transaction.",
                }
            ],
        },
    )
    assert response.status_code == 201


def score_transaction(client: TestClient, amount: float) -> dict:
    response = client.post(
        "/transactions/score",
        json={
            "customer_id": "customer-1",
            "amount": amount,
            "merchant_id": "merchant-1",
            "country": "GB",
            "occurred_at": datetime(2026, 1, 1, 12, 0, tzinfo=UTC).isoformat(),
        },
    )
    assert response.status_code == 200
    return response.json()


def test_api_scores_transaction_and_opens_case() -> None:
    client = TestClient(create_app())
    create_rules(client)

    payload = score_transaction(client, 1500)

    assert payload["assessment"]["flagged"] is True
    assert payload["case"]["status"] == "open"
    assert payload["assessment"]["latency_ms"] < 100


def test_api_reviews_case_and_deploys_feedback_canary() -> None:
    client = TestClient(create_app())
    create_rules(client)
    payload = score_transaction(client, 1500)
    case_id = payload["case"]["id"]

    note = client.post(
        f"/cases/{case_id}/notes",
        json={"author": "analyst-1", "text": "Requesting evidence."},
    )
    review = client.post(
        f"/cases/{case_id}/review",
        json={
            "status": "rejected",
            "analyst": "analyst-1",
            "note": "Confirmed fraud.",
        },
    )
    feedback = client.post(
        "/feedback/deploy-canary",
        json={"rule_set_version": "v1"},
    )

    assert note.status_code == 200
    assert review.status_code == 200
    assert review.json()["status"] == "rejected"
    assert feedback.status_code == 200
    assert feedback.json()["status"] == "canary"


def test_api_uses_transaction_history_for_velocity_features() -> None:
    client = TestClient(create_app())
    create_rules(client)
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    for index in range(3):
        client.post(
            "/transactions/score",
            json={
                "customer_id": "customer-1",
                "amount": 100,
                "merchant_id": f"merchant-{index}",
                "country": "GB",
                "occurred_at": (now - timedelta(minutes=10 + index)).isoformat(),
            },
        )

    payload = score_transaction(client, 1500)

    assert payload["assessment"]["features"]["velocity_1h"] == 3
