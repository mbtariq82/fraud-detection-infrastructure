from __future__ import annotations

from threading import RLock

from fraud_detection_infrastructure.domain import (
    FeedbackRun,
    FraudCase,
    NotFoundError,
    RiskAssessment,
    RuleSet,
    Transaction,
)


class FraudRepository:
    def __init__(self) -> None:
        self._transactions: dict[str, Transaction] = {}
        self._assessments: dict[str, RiskAssessment] = {}
        self._rule_sets: dict[str, RuleSet] = {}
        self._cases: dict[str, FraudCase] = {}
        self._feedback_runs: dict[str, FeedbackRun] = {}
        self._lock = RLock()

    def save_transaction(self, transaction: Transaction) -> Transaction:
        with self._lock:
            self._transactions[transaction.id] = transaction
            return transaction

    def list_transactions(self, customer_id: str | None = None) -> list[Transaction]:
        with self._lock:
            transactions = list(self._transactions.values())
        if customer_id:
            return [txn for txn in transactions if txn.customer_id == customer_id]
        return transactions

    def get_transaction(self, transaction_id: str) -> Transaction:
        with self._lock:
            try:
                return self._transactions[transaction_id]
            except KeyError as exc:
                raise NotFoundError(f"Transaction {transaction_id!r} was not found.") from exc

    def save_assessment(self, assessment: RiskAssessment) -> RiskAssessment:
        with self._lock:
            self._assessments[assessment.id] = assessment
            return assessment

    def get_assessment(self, assessment_id: str) -> RiskAssessment:
        with self._lock:
            try:
                return self._assessments[assessment_id]
            except KeyError as exc:
                raise NotFoundError(f"Assessment {assessment_id!r} was not found.") from exc

    def save_rule_set(self, rule_set: RuleSet) -> RuleSet:
        with self._lock:
            self._rule_sets[rule_set.version] = rule_set
            return rule_set

    def get_rule_set(self, version: str) -> RuleSet:
        with self._lock:
            try:
                return self._rule_sets[version]
            except KeyError as exc:
                raise NotFoundError(f"Rule set {version!r} was not found.") from exc

    def active_rule_sets(self) -> list[RuleSet]:
        with self._lock:
            return [rule_set for rule_set in self._rule_sets.values() if rule_set.active]

    def save_case(self, fraud_case: FraudCase) -> FraudCase:
        with self._lock:
            self._cases[fraud_case.id] = fraud_case
            return fraud_case

    def get_case(self, case_id: str) -> FraudCase:
        with self._lock:
            try:
                return self._cases[case_id]
            except KeyError as exc:
                raise NotFoundError(f"Case {case_id!r} was not found.") from exc

    def case_for_transaction(self, transaction_id: str) -> FraudCase | None:
        with self._lock:
            return next(
                (case for case in self._cases.values() if case.transaction_id == transaction_id),
                None,
            )

    def list_cases(self) -> list[FraudCase]:
        with self._lock:
            return list(self._cases.values())

    def save_feedback_run(self, run: FeedbackRun) -> FeedbackRun:
        with self._lock:
            self._feedback_runs[run.id] = run
            return run
