from __future__ import annotations

from fraud_detection_infrastructure.domain import CaseNote, CaseStatus, FraudCase, ValidationError, utcnow
from fraud_detection_infrastructure.repository import FraudRepository


class CaseService:
    def __init__(self, repository: FraudRepository) -> None:
        self.repository = repository

    def open_for_assessment(self, assessment_id: str) -> FraudCase | None:
        assessment = self.repository.get_assessment(assessment_id)
        if not assessment.flagged:
            return None
        existing = self.repository.case_for_transaction(assessment.transaction_id)
        if existing:
            return existing
        return self.repository.save_case(
            FraudCase(
                transaction_id=assessment.transaction_id,
                assessment_id=assessment.id,
            )
        )

    def review(
        self,
        case_id: str,
        status: CaseStatus,
        analyst: str,
        note: str | None = None,
    ) -> FraudCase:
        if status is CaseStatus.OPEN:
            raise ValidationError("Review status must approve or reject the case.")
        fraud_case = self.repository.get_case(case_id)
        fraud_case.status = status
        fraud_case.analyst = analyst
        fraud_case.updated_at = utcnow()
        if note:
            fraud_case.notes.append(CaseNote(author=analyst, text=note))
        return self.repository.save_case(fraud_case)

    def add_note(self, case_id: str, author: str, text: str) -> FraudCase:
        fraud_case = self.repository.get_case(case_id)
        fraud_case.notes.append(CaseNote(author=author, text=text))
        fraud_case.updated_at = utcnow()
        return self.repository.save_case(fraud_case)
