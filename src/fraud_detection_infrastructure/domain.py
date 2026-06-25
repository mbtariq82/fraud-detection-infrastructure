from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class FraudError(Exception):
    pass


class NotFoundError(FraudError):
    pass


class ValidationError(FraudError):
    pass


class CaseStatus(StrEnum):
    OPEN = "open"
    APPROVED = "approved"
    REJECTED = "rejected"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FeedbackStatus(StrEnum):
    COLLECTED = "collected"
    TRAINED = "trained"
    CANARY = "canary"


@dataclass
class Transaction:
    customer_id: str
    amount: float
    merchant_id: str
    country: str
    occurred_at: datetime
    id: str = field(default_factory=lambda: new_id("txn"))


@dataclass
class RiskFeatures:
    velocity_1h: int
    amount_deviation: float
    geo_anomaly: bool


@dataclass
class Rule:
    name: str
    field: str
    operator: str
    value: float | bool | str
    score: int
    reason: str


@dataclass
class RuleSet:
    version: str
    rules: list[Rule]
    traffic_percentage: int = 100
    active: bool = True
    id: str = field(default_factory=lambda: new_id("rules"))
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class RiskAssessment:
    transaction_id: str
    rule_set_version: str
    features: RiskFeatures
    score: int
    risk_level: RiskLevel
    flagged: bool
    reasons: list[str]
    latency_ms: float
    id: str = field(default_factory=lambda: new_id("risk"))
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class CaseNote:
    author: str
    text: str
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class FraudCase:
    transaction_id: str
    assessment_id: str
    status: CaseStatus = CaseStatus.OPEN
    analyst: str | None = None
    notes: list[CaseNote] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("case"))
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class FeedbackRun:
    labels: dict[str, CaseStatus]
    status: FeedbackStatus = FeedbackStatus.COLLECTED
    precision_estimate: float | None = None
    deployed_rule_set_version: str | None = None
    id: str = field(default_factory=lambda: new_id("feedback"))
    created_at: datetime = field(default_factory=utcnow)
