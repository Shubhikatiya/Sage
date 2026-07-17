"""
Execution Engine API for Sage v4 — Phase 10
REST endpoints for tasks, approvals, and audit log.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from services.execution_engine import get_execution_engine, TaskOrigin
from api.utils.responses import create_response

router = APIRouter(prefix="/api/execute", tags=["execution"])


class ProposeTaskRequest(BaseModel):
    description: str
    scope: str
    origin: str = "user_request"
    due_date: Optional[str] = None


class ApproveTaskRequest(BaseModel):
    task_id: str
    approved_by: str = "user"
    approval_scope: str = ""


class StandingPermissionRequest(BaseModel):
    name: str
    scope: str
    allowed_actions: List[str]
    max_frequency: str = "daily"


@router.post("/tasks/propose")
def propose_task(request: ProposeTaskRequest):
    """Propose a new task for approval."""
    try:
        engine = get_execution_engine()
        
        try:
            origin = TaskOrigin(request.origin)
        except ValueError:
            origin = TaskOrigin.USER_REQUEST
        
        task = engine.propose_task(
            description=request.description,
            scope=request.scope,
            origin=origin
        )
        
        return create_response(data={
            "task_id": task.id,
            "status": task.status.value,
            "description": task.description,
            "scope": task.scope,
            "requires_approval": True
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "EXECUTION_ERROR"}])


@router.post("/tasks/approve")
def approve_task(request: ApproveTaskRequest):
    """Approve a proposed task."""
    try:
        engine = get_execution_engine()
        success = engine.approve_task(
            task_id=request.task_id,
            approved_by=request.approved_by,
            approval_scope=request.approval_scope
        )
        
        if not success:
            return create_response(errors=[{"message": "Approval failed or scope mismatch", "code": "APPROVAL_FAILED"}])
        
        return create_response(data={"approved": True, "task_id": request.task_id})
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "EXECUTION_ERROR"}])


@router.post("/tasks/{task_id}/execute")
def execute_task(task_id: str):
    """Execute an approved task."""
    try:
        engine = get_execution_engine()
        success = engine.execute_task(task_id)
        
        task = engine.get_task(task_id)
        return create_response(data={
            "executed": success,
            "task_id": task_id,
            "status": task.status.value if task else "unknown"
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "EXECUTION_ERROR"}])


@router.post("/tasks/{task_id}/reject")
def reject_task(task_id: str, reason: str = ""):
    """Reject a proposed task."""
    try:
        engine = get_execution_engine()
        success = engine.reject_task(task_id, reason)
        return create_response(data={"rejected": success, "task_id": task_id})
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "EXECUTION_ERROR"}])


@router.get("/tasks/pending")
def get_pending_tasks():
    """Get tasks awaiting approval."""
    try:
        engine = get_execution_engine()
        tasks = engine.get_pending_tasks()
        
        return create_response(data=[
            {
                "task_id": t.id,
                "description": t.description,
                "scope": t.scope,
                "origin": t.origin.value,
                "created_at": t.created_at.isoformat()
            }
            for t in tasks
        ])
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])


@router.get("/tasks/active")
def get_active_tasks():
    """Get approved or in-progress tasks."""
    try:
        engine = get_execution_engine()
        tasks = engine.get_active_tasks()
        
        return create_response(data=[
            {
                "task_id": t.id,
                "description": t.description,
                "status": t.status.value,
                "scope": t.scope
            }
            for t in tasks
        ])
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])


@router.post("/permissions/create")
def create_standing_permission(request: StandingPermissionRequest):
    """Create a pre-authorized standing permission."""
    try:
        engine = get_execution_engine()
        perm = engine.create_standing_permission(
            name=request.name,
            scope=request.scope,
            allowed_actions=request.allowed_actions,
            max_frequency=request.max_frequency
        )
        
        return create_response(data={
            "permission_id": perm.permission_id,
            "name": perm.name,
            "scope": perm.scope,
            "active": perm.active
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "EXECUTION_ERROR"}])


@router.get("/audit-log")
def get_audit_log(limit: int = 100):
    """Get execution audit log."""
    try:
        engine = get_execution_engine()
        return create_response(data=engine.get_audit_log(limit=limit))
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])


@router.get("/stats")
def get_execution_stats():
    """Get execution engine statistics."""
    try:
        engine = get_execution_engine()
        return create_response(data=engine.get_stats())
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])
