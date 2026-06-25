from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from fraud_detection_infrastructure.domain import CaseStatus, FeedbackStatus, RiskLevel


class HealthResponse(BaseModel):
    status: str


class RuleRequest(BaseModel):
    name: str = Field(min_length=1)
    field: str = Field(min_length=1)
    operator: str = Field(pattern=r"^(>|>=|==|!=)$")
    value: float | bool | str
    score: int = Field(ge=1, le=100)
    reason: str = Field(min_length=1)


class RuleSetRequest(BaseModel):
    version: str = Field(min_length=1)
    rules: list[RuleRequest]
    traffic_percentage: int = Field(default=100, ge=1, le=100)


class ScoreTransactionRequest(BaseModel):
    customer_id: str = Field(min_length=1)
    amount: float = Field(gt=0)
    merchant_id: str = Field(min_length=1)
    country: str = Field(min_length=2, max_length=2)
    occurred_at: datetime
    rule_set_version: str | None = None


class ReviewCaseRequest(BaseModel):
    status: CaseStatus
    analyst: str = Field(min_length=1)
    note: str | None = None


class CaseNoteRequest(BaseModel):
    author: str = Field(min_length=1)
    text: str = Field(min_length=1)


class DeployFeedbackRequest(BaseModel):
    rule_set_version: str


class RuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    field: str
    operator: str
    value: float | bool | str
    score: int
    reason: str


class RuleSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version: str
    rules: list[RuleResponse]
    traffic_percentage: int
    active: bool
    created_at: datetime


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    amount: float
    merchant_id: str
    country: str
    occurred_at: datetime


class RiskFeaturesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    velocity_1h: int
    amount_deviation: float
    geo_anomaly: bool


class RiskAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    transaction_id: str
    rule_set_version: str
    features: RiskFeaturesResponse
    score: int
    risk_level: RiskLevel
    flagged: bool
    reasons: list[str]
    latency_ms: float
    created_at: datetime


class CaseNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    author: str
    text: str
    created_at: datetime


class FraudCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    transaction_id: str
    assessment_id: str
    status: CaseStatus
    analyst: str | None
    notes: list[CaseNoteResponse]
    created_at: datetime
    updated_at: datetime


class ScoreTransactionResponse(BaseModel):
    transaction: TransactionResponse
    assessment: RiskAssessmentResponse
    case: FraudCaseResponse | None


class FeedbackRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    labels: dict[str, CaseStatus]
    status: FeedbackStatus
    precision_estimate: float | None
    deployed_rule_set_version: str | None
    created_at: datetime
