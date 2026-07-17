"""
Learning Engine API for Sage v4 — Phase 09
REST endpoints for signal ingestion, personal model, and learning stats.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from services.learning_engine import get_learning_engine, LearningSignal, SignalType
from api.utils.responses import create_response

router = APIRouter(prefix="/api/learning", tags=["learning"])


class CorrectionRequest(BaseModel):
    original_claim: str
    corrected_value: str
    target_attribute: str


class FeedbackRequest(BaseModel):
    target_type: str
    target_id: str
    is_positive: bool
    comment: Optional[str] = ""


class OutcomeRequest(BaseModel):
    prediction_id: Optional[str] = None
    task_id: Optional[str] = None
    outcome_type: str = "success"
    value: Optional[float] = None


@router.post("/correct")
def submit_correction(request: CorrectionRequest):
    """Submit a correction — strongest learning signal."""
    try:
        engine = get_learning_engine()
        triggered = engine.ingest_correction(
            original_claim=request.original_claim,
            corrected_value=request.corrected_value,
            target_attribute=request.target_attribute
        )
        
        return create_response(data={
            "submitted": True,
            "triggered_update": triggered,
            "signal_type": "correction"
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "LEARNING_ERROR"}])


@router.post("/feedback")
def submit_feedback(request: FeedbackRequest):
    """Submit feedback (thumbs up/down)."""
    try:
        engine = get_learning_engine()
        triggered = engine.ingest_feedback(
            target_type=request.target_type,
            target_id=request.target_id,
            is_positive=request.is_positive,
            comment=request.comment
        )
        
        return create_response(data={
            "submitted": True,
            "triggered_update": triggered,
            "signal_type": "feedback"
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "LEARNING_ERROR"}])


@router.post("/outcome")
def submit_outcome(request: OutcomeRequest):
    """Submit an outcome signal."""
    try:
        engine = get_learning_engine()
        triggered = engine.ingest_outcome(
            prediction_id=request.prediction_id,
            task_id=request.task_id,
            outcome_type=request.outcome_type,
            value=request.value
        )
        
        return create_response(data={
            "submitted": True,
            "triggered_update": triggered,
            "signal_type": "outcome"
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "LEARNING_ERROR"}])


@router.get("/personal-model")
def get_personal_model():
    """Get current personal model state."""
    try:
        engine = get_learning_engine()
        return create_response(data=engine.get_personal_model())
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])


@router.get("/stats")
def get_learning_stats():
    """Get learning statistics."""
    try:
        engine = get_learning_engine()
        return create_response(data=engine.get_stats())
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])
