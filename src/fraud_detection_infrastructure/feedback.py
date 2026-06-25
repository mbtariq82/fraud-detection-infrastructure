from __future__ import annotations

from fraud_detection_infrastructure.domain import CaseStatus, FeedbackRun, FeedbackStatus
from fraud_detection_infrastructure.repository import FraudRepository


class FeedbackService:
    def __init__(self, repository: FraudRepository) -> None:
        self.repository = repository

    def collect_labels(self) -> FeedbackRun:
        labels = {
            case.transaction_id: case.status
            for case in self.repository.list_cases()
            if case.status is not CaseStatus.OPEN
        }
        return self.repository.save_feedback_run(FeedbackRun(labels=labels))

    def train(self, run: FeedbackRun) -> FeedbackRun:
        positives = sum(1 for label in run.labels.values() if label is CaseStatus.REJECTED)
        total = len(run.labels) or 1
        run.precision_estimate = round(positives / total, 4)
        run.status = FeedbackStatus.TRAINED
        return self.repository.save_feedback_run(run)

    def deploy_canary(self, run: FeedbackRun, rule_set_version: str) -> FeedbackRun:
        self.repository.get_rule_set(rule_set_version)
        run.deployed_rule_set_version = rule_set_version
        run.status = FeedbackStatus.CANARY
        return self.repository.save_feedback_run(run)
