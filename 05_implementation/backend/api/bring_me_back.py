"""
Bring Me Back API for Sage v4 — Phase 06
Exposes timeline reconstruction via dedicated REST endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database_v4 import get_db
from models_v4 import Workspace
from api.utils.responses import create_response

router = APIRouter(prefix="/api/bring_me_back", tags=["bring_me_back"])


def get_current_workspace(db: Session = Depends(get_db)):
    ws = db.query(Workspace).first()
    if not ws:
        raise HTTPException(status_code=404, detail="No workspace found")
    return ws


class BringMeBackRequest(BaseModel):
    since: Optional[str] = None  # ISO datetime, default: last session
    granularity: Optional[str] = None  # raw, daily, weekly, monthly — auto if not provided
    focus_areas: Optional[list] = None  # project IDs to focus on
    max_actions: int = 4


@router.post("")
def bring_me_back(request: BringMeBackRequest = None, db: Session = Depends(get_db), workspace: Workspace = Depends(get_current_workspace)):
    """
    Generate a 'Bring Me Back' reconstruction.
    Phase 06 endpoint — reconstructs what happened since last visit.
    """
    try:
        from services.bring_me_back_v2 import BringMeBackEngineV2

        engine = BringMeBackEngineV2(db, workspace.id)

        # If since is provided, override the engine's default
        if request and request.since:
            try:
                from datetime import datetime as dt
                engine.last_visit = dt.fromisoformat(request.since)
            except Exception:
                pass

        reconstruction = engine.reconstruct()

        # Format response
        response_data = {
            "greeting": reconstruction.greeting,
            "time_away": {
                "days": reconstruction.time_away_days,
                "hours": reconstruction.time_away_hours,
                "last_visit": reconstruction.last_visit.isoformat() if reconstruction.last_visit else None
            },
            "reconstruction": {
                "granularity": reconstruction.timeline_segments[0].granularity if reconstruction.timeline_segments else "unknown",
                "confidence": round(reconstruction.reconstruction_confidence, 2),
                "segments": [
                    {
                        "period": seg.period,
                        "granularity": seg.granularity,
                        "events": seg.events,
                        "themes": seg.themes
                    }
                    for seg in reconstruction.timeline_segments[:10]
                ],
                "priority_items": [
                    {
                        "item": item.item,
                        "score": round(item.score, 2),
                        "category": item.category,
                        "reason": item.reason
                    }
                    for item in reconstruction.priority_items[:10]
                ],
                "missing_information": [
                    {"type": mi.type, "description": mi.description, "severity": mi.severity}
                    for mi in reconstruction.missing_information[:5]
                ],
                "next_best_actions": [
                    {
                        "action": action.action,
                        "rationale": action.rationale,
                        "effort": action.effort,
                        "priority": action.priority
                    }
                    for action in reconstruction.next_best_actions[:request.max_actions if request else 4]
                ]
            },
            "generated_at": datetime.utcnow().isoformat()
        }

        return create_response(data=response_data)
    except Exception as e:
        # Fallback to v1
        try:
            from services.bring_me_back import BringMeBackEngine
            engine = BringMeBackEngine(db, workspace.id)
            briefing = engine.generate_briefing()
            markdown = engine.format_briefing_markdown(briefing)
            return create_response(data={
                "greeting": "Welcome back!",
                "reconstruction": {"markdown": markdown},
                "fallback": "v1_engine",
                "generated_at": datetime.utcnow().isoformat()
            })
        except Exception as e2:
            return create_response(errors=[{"message": f"v2: {e}; v1: {e2}", "code": "BMB_ERROR"}])


@router.get("/status")
def bring_me_back_status(db: Session = Depends(get_db), workspace: Workspace = Depends(get_current_workspace)):
    """Get Bring Me Back engine status and last reconstruction time."""
    try:
        from services.bring_me_back_v2 import BringMeBackEngineV2
        engine = BringMeBackEngineV2(db, workspace.id)
        return create_response(data={
            "last_visit": engine.last_visit.isoformat() if engine.last_visit else None,
            "workspace_id": workspace.id,
            "engine_version": "v2"
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "BMB_STATUS_ERROR"}])
