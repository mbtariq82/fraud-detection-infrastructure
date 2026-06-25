from __future__ import annotations

from datetime import UTC, datetime

from fraud_detection_infrastructure.cases import CaseService
from fraud_detection_infrastructure.domain import CaseStatus, Rule, Transaction
from fraud_detection_infrastructure.features import FeatureService
from fraud_detection_infrastructure.repository import FraudRepository
from fraud_detection_infrastructure.rules import RuleEngine


def test_flagged_assessment_opens_case_and_accepts_review() -> None:
    repository = FraudRepository()
    engine = RuleEngine(repository, FeatureService(repository))
    cases = CaseService(repository)
    engine.create_rule_set(
        "v1",
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
    assessment = engine.score(transaction)

    fraud_case = cases.open_for_assessment(assessment.id)
    assert fraud_case is not None
    cases.add_note(fraud_case.id, "analyst-1", "Requesting merchant evidence.")
    reviewed = cases.review(
        fraud_case.id,
        CaseStatus.REJECTED,
        "analyst-1",
        "Confirmed fraud.",
    )

    assert reviewed.status is CaseStatus.REJECTED
    assert reviewed.analyst == "analyst-1"
    assert [note.text for note in reviewed.notes] == [
        "Requesting merchant evidence.",
        "Confirmed fraud.",
    ]


def test_low_risk_assessment_does_not_open_case() -> None:
    repository = FraudRepository()
    engine = RuleEngine(repository, FeatureService(repository))
    cases = CaseService(repository)
    engine.create_rule_set(
        "v1",
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
    )
    transaction = repository.save_transaction(
        Transaction(
            customer_id="customer-1",
            amount=100,
            merchant_id="merchant-1",
            country="GB",
            occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )
    )
    assessment = engine.score(transaction)

    assert cases.open_for_assessment(assessment.id) is None
