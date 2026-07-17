"""
Multi-Agent System API for Sage v4 — Phase 08
REST endpoints for agent orchestration, planning, and dispatch.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from services.agent_system import get_orchestrator, AgentRegistry
from api.utils.responses import create_response

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentRequest(BaseModel):
    request: str
    context: Optional[Dict[str, Any]] = None


@router.post("/process")
async def process_request(request: AgentRequest):
    """Process a request through the multi-agent system."""
    try:
        orchestrator = get_orchestrator()
        result = await orchestrator.process_request(request.request, request.context)
        
        return create_response(data=result)
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "AGENT_ERROR"}])


@router.get("/registry")
def get_agent_registry():
    """Get all agent types and their mandates."""
    try:
        registry = AgentRegistry()
        return create_response(data=registry.list_agents())
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])


@router.get("/status")
def get_agent_status():
    """Get current agent orchestrator status."""
    try:
        orchestrator = get_orchestrator()
        return create_response(data={
            "active_tasks": len(orchestrator.active_tasks),
            "completed_tasks": len(orchestrator.completed_tasks)
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])
