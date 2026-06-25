from __future__ import annotations

from datetime import UTC, datetime

from fraud_detection_infrastructure.cases import CaseService
from fraud_detection_infrastructure.domain import CaseStatus, FeedbackStatus, Rule, Transaction
from fraud_detection_infrastructure.features import FeatureService
from fraud_detection_infrastructure.feedback import FeedbackService
from fraud_detection_infrastructure.repository import FraudRepository
from fraud_detection_infrastructure.rules import RuleEngine


def test_feedback_loop_collects_labels_trains_and_deploys_canary() -> None:
    repository = FraudRepository()
    engine = RuleEngine(repository, FeatureService(repository))
    cases = CaseService(repository)
    feedback = FeedbackService(repository)
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
    cases.review(fraud_case.id, CaseStatus.REJECTED, "analyst-1", "Confirmed fraud.")

    collected = feedback.collect_labels()
    trained = feedback.train(collected)
    canary = feedback.deploy_canary(trained, "v1")

    assert collected.labels == {transaction.id: CaseStatus.REJECTED}
    assert trained.precision_estimate == 1.0
    assert canary.status is FeedbackStatus.CANARY
    assert canary.deployed_rule_set_version == "v1"
