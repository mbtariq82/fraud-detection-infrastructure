from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from fraud_detection_infrastructure.cases import CaseService
from fraud_detection_infrastructure.domain import (
    FraudError,
    NotFoundError,
    Rule,
    Transaction,
    ValidationError,
)
from fraud_detection_infrastructure.features import FeatureService
from fraud_detection_infrastructure.feedback import FeedbackService
from fraud_detection_infrastructure.repository import FraudRepository
from fraud_detection_infrastructure.rules import RuleEngine
from fraud_detection_infrastructure.schemas import (
    CaseNoteRequest,
    DeployFeedbackRequest,
    FeedbackRunResponse,
    FraudCaseResponse,
    HealthResponse,
    ReviewCaseRequest,
    RiskAssessmentResponse,
    RuleRequest,
    RuleSetRequest,
    RuleSetResponse,
    ScoreTransactionRequest,
    ScoreTransactionResponse,
    TransactionResponse,
)


def create_app(repository: FraudRepository | None = None) -> FastAPI:
    repository = repository or FraudRepository()
    feature_service = FeatureService(repository)
    rule_engine = RuleEngine(repository, feature_service)
    case_service = CaseService(repository)
    feedback_service = FeedbackService(repository)

    app = FastAPI(
        title="Fraud Detection Infrastructure",
        version="0.1.0",
        summary="Real-time transaction scoring, cases, and fraud feedback API.",
    )
    app.state.repository = repository
    app.state.rule_engine = rule_engine
    app.state.case_service = case_service
    app.state.feedback_service = feedback_service

    @app.exception_handler(FraudError)
    async def handle_fraud_error(_request: Request, exc: FraudError) -> JSONResponse:
        status_code = status.HTTP_400_BAD_REQUEST
        if isinstance(exc, NotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, ValidationError):
            status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.post("/rule-sets", status_code=status.HTTP_201_CREATED, response_model=RuleSetResponse)
    def create_rule_set(payload: RuleSetRequest) -> RuleSetResponse:
        rule_set = rule_engine.create_rule_set(
            payload.version,
            [_rule_from_request(rule) for rule in payload.rules],
            traffic_percentage=payload.traffic_percentage,
        )
        return RuleSetResponse.model_validate(rule_set)

    @app.post("/transactions/score", response_model=ScoreTransactionResponse)
    def score_transaction(payload: ScoreTransactionRequest) -> ScoreTransactionResponse:
        transaction = repository.save_transaction(
            Transaction(
                customer_id=payload.customer_id,
                amount=payload.amount,
                merchant_id=payload.merchant_id,
                country=payload.country,
                occurred_at=payload.occurred_at,
            )
        )
        assessment = rule_engine.score(transaction, payload.rule_set_version)
        fraud_case = case_service.open_for_assessment(assessment.id)
        return ScoreTransactionResponse(
            transaction=TransactionResponse.model_validate(transaction),
            assessment=RiskAssessmentResponse.model_validate(assessment),
            case=FraudCaseResponse.model_validate(fraud_case) if fraud_case else None,
        )

    @app.get("/cases", response_model=list[FraudCaseResponse])
    def list_cases() -> list[FraudCaseResponse]:
        return [FraudCaseResponse.model_validate(case) for case in repository.list_cases()]

    @app.get("/cases/{case_id}", response_model=FraudCaseResponse)
    def get_case(case_id: str) -> FraudCaseResponse:
        return FraudCaseResponse.model_validate(repository.get_case(case_id))

    @app.post("/cases/{case_id}/notes", response_model=FraudCaseResponse)
    def add_case_note(case_id: str, payload: CaseNoteRequest) -> FraudCaseResponse:
        return FraudCaseResponse.model_validate(
            case_service.add_note(case_id, payload.author, payload.text)
        )

    @app.post("/cases/{case_id}/review", response_model=FraudCaseResponse)
    def review_case(case_id: str, payload: ReviewCaseRequest) -> FraudCaseResponse:
        return FraudCaseResponse.model_validate(
            case_service.review(case_id, payload.status, payload.analyst, payload.note)
        )

    @app.post("/feedback/deploy-canary", response_model=FeedbackRunResponse)
    def deploy_feedback(payload: DeployFeedbackRequest) -> FeedbackRunResponse:
        collected = feedback_service.collect_labels()
        trained = feedback_service.train(collected)
        return FeedbackRunResponse.model_validate(
            feedback_service.deploy_canary(trained, payload.rule_set_version)
        )

    return app


def _rule_from_request(payload: RuleRequest) -> Rule:
    return Rule(
        name=payload.name,
        field=payload.field,
        operator=payload.operator,
        value=payload.value,
        score=payload.score,
        reason=payload.reason,
    )


app = create_app()
