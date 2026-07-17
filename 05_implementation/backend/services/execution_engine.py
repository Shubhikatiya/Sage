"""
Sage Execution Engine — Phase 10
Task model, approval workflow, audit logging, external actions.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class TaskStatus(str, Enum):
    """Task lifecycle states."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class TaskOrigin(str, Enum):
    """Where tasks come from."""
    USER_REQUEST = "user_request"
    NEXT_BEST_ACTION = "next_best_action"
    SCHEDULED_AUTOMATION = "scheduled_automation"
    REASONING_ENGINE = "reasoning_engine"


@dataclass
class ApprovalRecord:
    """Approval boundary for tasks."""
    approved_by: str = ""  # "user" or "standing_permission"
    approved_at: Optional[datetime] = None
    approval_scope: str = ""  # What exactly was approved
    standing_permission_ref: Optional[str] = None


@dataclass
class ExecutionLogEntry:
    """One entry in the execution audit log."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    action: str = ""  # "started", "completed", "failed", "scope_checked"
    actor: str = ""  # "user", "agent", "system"
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StandingPermission:
    """Pre-authorized, narrowly-scoped permission."""
    permission_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    scope: str = ""  # Explicit bounds
    allowed_actions: List[str] = field(default_factory=list)
    max_frequency: str = "daily"  # daily, weekly, per_request
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Task:
    """Phase 10 Task model."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    status: TaskStatus = TaskStatus.PROPOSED
    origin: TaskOrigin = TaskOrigin.USER_REQUEST
    origin_ref: Optional[str] = None  # Reasoning trace or schedule that produced it
    approval: Optional[ApprovalRecord] = None
    scope: str = ""  # Explicit bounds
    due_date: Optional[datetime] = None
    depends_on: List[str] = field(default_factory=list)
    execution_log: List[ExecutionLogEntry] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class ExecutionEngine:
    """
    Phase 10: Execution Engine.
    Manages tasks, approval workflow, and external actions.
    """
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.standing_permissions: Dict[str, StandingPermission] = {}
        self.audit_log: List[ExecutionLogEntry] = []
    
    def propose_task(
        self,
        description: str,
        scope: str,
        origin: TaskOrigin = TaskOrigin.USER_REQUEST,
        origin_ref: Optional[str] = None,
        due_date: Optional[datetime] = None
    ) -> Task:
        """
        Propose a new task.
        Every task starts as "proposed" and requires approval.
        """
        task = Task(
            description=description,
            origin=origin,
            origin_ref=origin_ref,
            scope=scope,
            due_date=due_date
        )
        
        # Log proposal
        task.execution_log.append(ExecutionLogEntry(
            action="proposed",
            actor="system",
            details={"scope": scope, "origin": origin.value}
        ))
        
        self.tasks[task.id] = task
        self._audit("task_proposed", {"task_id": task.id, "description": description})
        
        return task
    
    def approve_task(
        self,
        task_id: str,
        approved_by: str = "user",
        approval_scope: str = "",
        standing_permission_id: Optional[str] = None
    ) -> bool:
        """
        Approve a task for execution.
        Must explicitly match the task's scope.
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        # Verify scope matches
        effective_scope = approval_scope or task.scope
        if effective_scope != task.scope:
            self._audit("approval_scope_mismatch", {
                "task_id": task_id,
                "task_scope": task.scope,
                "approval_scope": effective_scope
            })
            return False
        
        # Create approval record
        task.approval = ApprovalRecord(
            approved_by=approved_by,
            approved_at=datetime.utcnow(),
            approval_scope=effective_scope,
            standing_permission_ref=standing_permission_id
        )
        
        task.status = TaskStatus.APPROVED
        
        task.execution_log.append(ExecutionLogEntry(
            action="approved",
            actor=approved_by,
            details={"scope": effective_scope, "standing_permission": standing_permission_id}
        ))
        
        self._audit("task_approved", {"task_id": task_id, "by": approved_by})
        return True
    
    def execute_task(self, task_id: str) -> bool:
        """
        Execute an approved task.
        Returns success/failure.
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        # Verify approval
        if task.status != TaskStatus.APPROVED and not self._has_standing_permission(task):
            task.status = TaskStatus.FAILED
            task.execution_log.append(ExecutionLogEntry(
                action="failed",
                actor="system",
                details={"reason": "No approval record"}
            ))
            self._audit("task_failed_unapproved", {"task_id": task_id})
            return False
        
        # Check dependencies
        for dep_id in task.depends_on:
            dep = self.tasks.get(dep_id)
            if not dep or dep.status != TaskStatus.COMPLETED:
                task.execution_log.append(ExecutionLogEntry(
                    action="blocked",
                    actor="system",
                    details={"reason": f"Dependency {dep_id} not complete"}
                ))
                return False
        
        # Execute
        task.status = TaskStatus.IN_PROGRESS
        task.execution_log.append(ExecutionLogEntry(
            action="started",
            actor="system",
            details={"scope": task.scope}
        ))
        
        try:
            # Phase 10 MVP: Simulate execution
            # Future: Actually call external APIs (calendar, email, etc.)
            result = self._perform_action(task)
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.execution_log.append(ExecutionLogEntry(
                action="completed",
                actor="system",
                details={"result": result}
            ))
            
            self._audit("task_executed", {"task_id": task_id, "status": "success"})
            return True
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.execution_log.append(ExecutionLogEntry(
                action="failed",
                actor="system",
                details={"error": str(e)}
            ))
            
            self._audit("task_failed", {"task_id": task_id, "error": str(e)})
            return False
    
    def reject_task(self, task_id: str, reason: str = "") -> bool:
        """Reject a proposed task."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        task.status = TaskStatus.REJECTED
        task.execution_log.append(ExecutionLogEntry(
            action="rejected",
            actor="user",
            details={"reason": reason}
        ))
        
        self._audit("task_rejected", {"task_id": task_id, "reason": reason})
        return True
    
    def cancel_task(self, task_id: str, reason: str = "") -> bool:
        """Cancel an in-progress or approved task."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        task.status = TaskStatus.CANCELLED
        task.execution_log.append(ExecutionLogEntry(
            action="cancelled",
            actor="user",
            details={"reason": reason}
        ))
        
        self._audit("task_cancelled", {"task_id": task_id, "reason": reason})
        return True
    
    def create_standing_permission(
        self,
        name: str,
        scope: str,
        allowed_actions: List[str],
        max_frequency: str = "daily"
    ) -> StandingPermission:
        """Create a pre-authorized, narrowly-scoped permission."""
        perm = StandingPermission(
            name=name,
            scope=scope,
            allowed_actions=allowed_actions,
            max_frequency=max_frequency
        )
        self.standing_permissions[perm.permission_id] = perm
        self._audit("standing_permission_created", {
            "permission_id": perm.permission_id,
            "name": name,
            "scope": scope
        })
        return perm
    
    def _has_standing_permission(self, task: Task) -> bool:
        """Check if task has valid standing permission."""
        if not task.approval or not task.approval.standing_permission_ref:
            return False
        
        perm = self.standing_permissions.get(task.approval.standing_permission_ref)
        if not perm or not perm.active:
            return False
        
        # Check scope matches
        if task.scope != perm.scope:
            return False
        
        return True
    
    def _perform_action(self, task: Task) -> str:
        """Actually perform the task action."""
        # Phase 10 MVP: Return simulated result
        return f"Simulated execution: {task.description[:50]}"
    
    def _audit(self, action: str, details: Dict[str, Any]):
        """Write to execution audit log."""
        self.audit_log.append(ExecutionLogEntry(
            action=action,
            actor="execution_engine",
            details=details
        ))
    
    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)
    
    def get_pending_tasks(self) -> List[Task]:
        """Get tasks awaiting approval."""
        return [t for t in self.tasks.values() if t.status == TaskStatus.PROPOSED]
    
    def get_active_tasks(self) -> List[Task]:
        """Get approved or in-progress tasks."""
        return [t for t in self.tasks.values() if t.status in (TaskStatus.APPROVED, TaskStatus.IN_PROGRESS)]
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get execution audit log."""
        return [
            {
                "timestamp": entry.timestamp.isoformat(),
                "action": entry.action,
                "actor": entry.actor,
                "details": entry.details
            }
            for entry in reversed(self.audit_log[-limit:])
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        statuses = {}
        for t in self.tasks.values():
            statuses[t.status.value] = statuses.get(t.status.value, 0) + 1
        
        return {
            "total_tasks": len(self.tasks),
            "by_status": statuses,
            "pending_approval": len(self.get_pending_tasks()),
            "active": len(self.get_active_tasks()),
            "standing_permissions": len(self.standing_permissions),
            "audit_entries": len(self.audit_log)
        }


# Singleton
_execution_engine: Optional[ExecutionEngine] = None


def get_execution_engine() -> ExecutionEngine:
    """Get or create the global Execution Engine."""
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = ExecutionEngine()
    return _execution_engine
