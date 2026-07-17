"""
Context Engine API for Sage v4 — Phase 05
Exposes context resolution as a standalone REST endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from database_v4 import get_db
from models_v4 import Workspace, ChatMessage
from api.utils.responses import create_response

router = APIRouter(prefix="/api/context", tags=["context"])


def get_current_workspace(db: Session = Depends(get_db)):
    ws = db.query(Workspace).first()
    if not ws:
        raise HTTPException(status_code=404, detail="No workspace found")
    return ws


class ContextResolveRequest(BaseModel):
    message: str
    conversation_history: Optional[List[Dict[str, Any]]] = None
    system_prompt: Optional[str] = None
    include_temporal: bool = True
    include_projects: bool = True
    include_memories: bool = True


@router.post("/resolve")
def resolve_context(request: ContextResolveRequest, db: Session = Depends(get_db), workspace: Workspace = Depends(get_current_workspace)):
    """
    Resolve context for a given message.
    Returns: intent, context layers, merged context, and attention budget.
    Phase 05 endpoint.
    """
    try:
        from services.context_engine import build_context_for_chat, ContextMerger

        # Format conversation history if provided
        hist = request.conversation_history or []

        # Build structured context
        context_result = build_context_for_chat(
            user_message=request.message,
            conversation_history=hist,
            system_prompt=request.system_prompt or "",
            workspace_id=workspace.id
        )

        # Get active projects
        active_projects = []
        if request.include_projects:
            from models_v4 import KnowledgeNode
            projects = db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == workspace.id,
                KnowledgeNode.is_archived == False
            ).order_by(KnowledgeNode.updated_at.desc()).limit(5).all()
            active_projects = [
                {"id": p.id, "title": p.title, "status": p.status, "updated_at": p.updated_at.isoformat() if p.updated_at else None}
                for p in projects
            ]

        # Get recent memories
        recent_memories = []
        if request.include_memories:
            try:
                from services.memory_engine import get_memory_store, MemoryQuery
                mem_store = get_memory_store()
                mem_result = mem_store.search(MemoryQuery(
                    query_text=request.message,
                    max_results=5
                ))
                recent_memories = [
                    {"id": m.id, "type": m.memory_type.value, "content_preview": m.content[:200], "score": m.current_score}
                    for m in mem_result.memories
                ]
            except Exception as e:
                print(f"[ContextResolve] Memory retrieval failed: {e}")

        # Temporal context
        temporal_context = {}
        if request.include_temporal:
            from services.context_engine import get_temporal_context
            temporal_context = get_temporal_context()

        # Compute attention budget
        merger = ContextMerger(total_budget=4000)
        total_chars = len(request.message) + sum(len(str(m)) for m in recent_memories)
        estimated_tokens = total_chars // 4
        remaining_budget = max(0, merger.total_budget - estimated_tokens)
        budget_used_percent = min(100, (estimated_tokens / merger.total_budget) * 100)

        return create_response(data={
            "intent": context_result.get("intent"),
            "layers": context_result.get("layers_used", []),
            "merged_context": context_result.get("context_prompt", ""),
            "attention_budget": {
                "total_tokens": merger.total_budget,
                "estimated_used": estimated_tokens,
                "remaining": remaining_budget,
                "used_percent": round(budget_used_percent, 1)
            },
            "active_projects": active_projects,
            "recent_memories": recent_memories,
            "temporal_context": temporal_context,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "CONTEXT_RESOLVE_ERROR"}])


@router.get("/layers")
def get_context_layers():
    """Get the defined context layers and their descriptions."""
    return create_response(data={
        "layers": [
            {"name": "system_prompt", "description": "Core persona and constraints", "priority": 10},
            {"name": "conversation_history", "description": "Recent user-assistant turns", "priority": 9},
            {"name": "retrieved_memories", "description": "Relevant past memories", "priority": 8},
            {"name": "active_project", "description": "Current project context", "priority": 7},
            {"name": "user_profile", "description": "User preferences and patterns", "priority": 6},
            {"name": "temporal_context", "description": "Time-of-day, deadlines, calendar", "priority": 5},
            {"name": "reasoning_trace", "description": "Recent reasoning steps", "priority": 4}
        ],
        "merger_strategy": "Truncate from lowest priority upward when budget exceeded"
    })
