from __future__ import annotations

from hashlib import sha256
from time import perf_counter

from fraud_detection_infrastructure.domain import (
    RiskAssessment,
    RiskLevel,
    Rule,
    RuleSet,
    Transaction,
    ValidationError,
)
from fraud_detection_infrastructure.features import FeatureService
from fraud_detection_infrastructure.repository import FraudRepository


class RuleEngine:
    def __init__(self, repository: FraudRepository, feature_service: FeatureService) -> None:
        self.repository = repository
        self.feature_service = feature_service

    def create_rule_set(
        self,
        version: str,
        rules: list[Rule],
        traffic_percentage: int = 100,
    ) -> RuleSet:
        if not version.strip():
            raise ValidationError("version is required.")
        if not rules:
            raise ValidationError("At least one rule is required.")
        if traffic_percentage < 1 or traffic_percentage > 100:
            raise ValidationError("traffic_percentage must be between 1 and 100.")
        return self.repository.save_rule_set(
            RuleSet(version=version, rules=rules, traffic_percentage=traffic_percentage)
        )

    def score(
        self,
        transaction: Transaction,
        override_rule_set_version: str | None = None,
    ) -> RiskAssessment:
        started = perf_counter()
        rule_set = (
            self.repository.get_rule_set(override_rule_set_version)
            if override_rule_set_version
            else self._select_rule_set(transaction.id)
        )
        features = self.feature_service.compute(transaction)
        reasons: list[str] = []
        score = 0
        for rule in rule_set.rules:
            if self._matches(rule, features, transaction):
                score += rule.score
                reasons.append(rule.reason)

        score = min(score, 100)
        risk_level = RiskLevel.HIGH if score >= 70 else RiskLevel.MEDIUM if score >= 40 else RiskLevel.LOW
        assessment = RiskAssessment(
            transaction_id=transaction.id,
            rule_set_version=rule_set.version,
            features=features,
            score=score,
            risk_level=risk_level,
            flagged=score >= 70,
            reasons=reasons,
            latency_ms=round((perf_counter() - started) * 1000, 4),
        )
        return self.repository.save_assessment(assessment)

    def _select_rule_set(self, transaction_id: str) -> RuleSet:
        active = sorted(self.repository.active_rule_sets(), key=lambda rules: rules.version)
        if not active:
            raise ValidationError("No active rule sets are configured.")
        if len(active) == 1:
            return active[0]
        bucket = int(sha256(transaction_id.encode()).hexdigest(), 16) % 100
        running_total = 0
        for rule_set in active:
            running_total += rule_set.traffic_percentage
            if bucket < running_total:
                return rule_set
        return active[-1]

    @staticmethod
    def _matches(rule: Rule, features, transaction: Transaction) -> bool:
        source = features if hasattr(features, rule.field) else transaction
        actual = getattr(source, rule.field)
        if rule.operator == ">":
            return actual > rule.value
        if rule.operator == ">=":
            return actual >= rule.value
        if rule.operator == "==":
            return actual == rule.value
        if rule.operator == "!=":
            return actual != rule.value
        raise ValidationError(f"Unsupported rule operator {rule.operator!r}.")
