from __future__ import annotations

from datetime import timedelta
from statistics import mean

from fraud_detection_infrastructure.domain import RiskFeatures, Transaction
from fraud_detection_infrastructure.repository import FraudRepository


class FeatureService:
    def __init__(self, repository: FraudRepository) -> None:
        self.repository = repository

    def compute(self, transaction: Transaction) -> RiskFeatures:
        customer_history = [
            txn
            for txn in self.repository.list_transactions(transaction.customer_id)
            if txn.id != transaction.id and txn.occurred_at <= transaction.occurred_at
        ]
        last_hour = transaction.occurred_at - timedelta(hours=1)
        velocity = sum(1 for txn in customer_history if txn.occurred_at >= last_hour)
        previous_amounts = [txn.amount for txn in customer_history]
        amount_deviation = 0.0
        if previous_amounts:
            baseline = mean(previous_amounts)
            amount_deviation = transaction.amount / baseline if baseline else 0.0
        countries = {txn.country.upper() for txn in customer_history[-10:]}
        geo_anomaly = bool(countries) and transaction.country.upper() not in countries
        return RiskFeatures(
            velocity_1h=velocity,
            amount_deviation=round(amount_deviation, 4),
            geo_anomaly=geo_anomaly,
        )
