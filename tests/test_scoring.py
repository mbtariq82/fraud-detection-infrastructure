from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fraud_detection_infrastructure.domain import Rule, RiskLevel, Transaction
from fraud_detection_infrastructure.features import FeatureService
from fraud_detection_infrastructure.repository import FraudRepository
from fraud_detection_infrastructure.rules import RuleEngine


def build_engine() -> tuple[FraudRepository, RuleEngine]:
    repository = FraudRepository()
    engine = RuleEngine(repository, FeatureService(repository))
    engine.create_rule_set(
        "v1",
        [
            Rule(
                name="high-velocity",
                field="velocity_1h",
                operator=">=",
                value=3,
                score=40,
                reason="High transaction velocity.",
            ),
            Rule(
                name="amount-spike",
                field="amount_deviation",
                operator=">",
                value=3.0,
                score=35,
                reason="Amount is above customer baseline.",
            ),
            Rule(
                name="geo-anomaly",
                field="geo_anomaly",
                operator="==",
                value=True,
                score=35,
                reason="Transaction country differs from recent activity.",
            ),
        ],
    )
    return repository, engine


def test_transaction_scoring_computes_features_and_flags_high_risk() -> None:
    repository, engine = build_engine()
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    for index in range(3):
        repository.save_transaction(
            Transaction(
                customer_id="customer-1",
                amount=100,
                merchant_id=f"merchant-{index}",
                country="GB",
                occurred_at=now - timedelta(minutes=30 - index),
            )
        )
    transaction = repository.save_transaction(
        Transaction(
            customer_id="customer-1",
            amount=500,
            merchant_id="merchant-risky",
            country="US",
            occurred_at=now,
        )
    )

    assessment = engine.score(transaction)

    assert assessment.flagged is True
    assert assessment.risk_level is RiskLevel.HIGH
    assert assessment.features.velocity_1h == 3
    assert assessment.features.geo_anomaly is True
    assert set(assessment.reasons) == {
        "High transaction velocity.",
        "Amount is above customer baseline.",
        "Transaction country differs from recent activity.",
    }
    assert assessment.latency_ms < 100


def test_rule_set_override_scores_against_specific_version() -> None:
    repository, engine = build_engine()
    engine.create_rule_set(
        "v2",
        [
            Rule(
                name="large-amount",
                field="amount",
                operator=">",
                value=1000,
                score=80,
                reason="Large transaction.",
            )
        ],
        traffic_percentage=1,
    )
    transaction = repository.save_transaction(
        Transaction(
            customer_id="customer-1",
            amount=1500,
            merchant_id="merchant-1",
            country="GB",
            occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )
    )

    assessment = engine.score(transaction, override_rule_set_version="v2")

    assert assessment.rule_set_version == "v2"
    assert assessment.flagged is True
    assert assessment.reasons == ["Large transaction."]
