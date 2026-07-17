"""
Memory API Routes for Sage v4
Phase 02: Memory Engine — REST endpoints for memory CRUD and retrieval.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

from services.memory_engine import (
    MemoryStore, Memory, MemoryQuery, MemoryType,
    get_memory_store, compute_memory_score
)
from api.utils.responses import create_response, create_error_response

router = APIRouter(prefix="/api/memory", tags=["Memory"])


class WriteMemoryRequest(BaseModel):
    content: str
    memory_type: str = "episodic"
    source_event_id: str = ""
    source_type: str = "conversation"
    workspace_id: Optional[str] = None
    layer: Optional[str] = None
    importance_score: float = 0.5
    tags: List[str] = []
    related_memory_ids: List[str] = []


class SearchMemoryRequest(BaseModel):
    query: str
    memory_types: Optional[List[str]] = None
    layers: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    max_results: int = 10
    min_score: float = 0.1


@router.post("/write")
def write_memory(request: WriteMemoryRequest):
    """Write a new memory."""
    try:
        store = get_memory_store()
        
        # Validate memory type
        try:
            mem_type = MemoryType(request.memory_type)
        except ValueError:
            return create_response(errors=[{"message": f"Invalid memory_type: {request.memory_type}", "code": "INVALID_TYPE"}])
        
        memory = Memory(
            memory_type=mem_type,
            content=request.content,
            source_event_id=request.source_event_id or "manual",
            source_type=request.source_type,
            workspace_id=request.workspace_id,
            layer=request.layer,
            importance_score=min(max(request.importance_score, 0), 1),
            tags=request.tags,
            related_memory_ids=request.related_memory_ids
        )
        
        memory_id = store.write(memory)
        
        return create_response(data={
            "memory_id": memory_id,
            "memory_type": memory.memory_type.value,
            "content_preview": memory.content[:200]
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "WRITE_ERROR"}])


@router.get("/{memory_id}")
def get_memory(memory_id: str):
    """Get a memory by ID."""
    try:
        store = get_memory_store()
        memory = store.get(memory_id)
        
        if not memory:
            return create_response(errors=[{"message": "Memory not found", "code": "NOT_FOUND"}])
        
        return create_response(data={
            "id": memory.id,
            "type": memory.memory_type.value,
            "content": memory.content,
            "source_type": memory.source_type,
            "created_at": memory.created_at.isoformat(),
            "importance_score": memory.importance_score,
            "reinforcement_count": memory.reinforcement_count,
            "tags": memory.tags,
            "state": memory.state.value
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])


@router.post("/search")
def search_memories(request: SearchMemoryRequest):
    """Search memories with ranking."""
    try:
        store = get_memory_store()
        
        # Parse memory types
        mem_types = None
        if request.memory_types:
            mem_types = [MemoryType(mt) for mt in request.memory_types if mt in [t.value for t in MemoryType]]
        
        query = MemoryQuery(
            query_text=request.query,
            memory_types=mem_types,
            layers=request.layers,
            tags=request.tags,
            max_results=min(request.max_results, 100),
            min_score=request.min_score
        )
        
        result = store.search(query)
        
        return create_response(data={
            "memories": [
                {
                    "id": m.id,
                    "type": m.memory_type.value,
                    "content_preview": m.content[:300],
                    "score": m.current_score,
                    "created_at": m.created_at.isoformat(),
                    "reinforcement_count": m.reinforcement_count,
                    "tags": m.tags
                }
                for m in result.memories
            ],
            "total_available": result.total_available,
            "query_time_ms": result.query_time_ms,
            "retrieval_mode": result.retrieval_mode,
            "degraded": result.degraded
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "SEARCH_ERROR"}])


@router.post("/{memory_id}/reinforce")
def reinforce_memory(memory_id: str):
    """Reinforce a memory (increment recall count)."""
    try:
        store = get_memory_store()
        success = store.reinforce(memory_id)
        
        if not success:
            return create_response(errors=[{"message": "Memory not found", "code": "NOT_FOUND"}])
        
        return create_response(data={"reinforced": True, "memory_id": memory_id})
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "REINFORCE_ERROR"}])


@router.post("/forget")
def forget_memory(memory_id: str):
    """Soft-forget a memory (mark as archived, not deleted)."""
    try:
        from services.memory_engine import MemoryState
        store = get_memory_store()
        success = store.update_state(memory_id, MemoryState.ARCHIVED)

        if not success:
            return create_response(errors=[{"message": "Memory not found", "code": "NOT_FOUND"}])

        return create_response(data={"forgotten": True, "memory_id": memory_id})
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FORGET_ERROR"}])


@router.post("/retrieve")
def retrieve_memories(request: SearchMemoryRequest):
    """Unified retrieval API — Phase 02 spec endpoint.
    All consumers call this one endpoint. Type-specific writes exist,
    but retrieval is unified so ranking improvements are global.
    """
    try:
        store = get_memory_store()

        mem_types = None
        if request.memory_types:
            mem_types = [MemoryType(mt) for mt in request.memory_types if mt in [t.value for t in MemoryType]]

        query = MemoryQuery(
            query_text=request.query,
            memory_types=mem_types,
            layers=request.layers,
            tags=request.tags,
            max_results=min(request.max_results, 100),
            min_score=request.min_score
        )

        result = store.search(query)

        return create_response(data={
            "items": [
                {
                    "id": m.id,
                    "type": m.memory_type.value,
                    "content": m.content,
                    "score": m.current_score,
                    "confidence": m.confidence,
                    "source_event_id": m.source_event_id,
                    "created_at": m.created_at.isoformat(),
                    "reinforcement_count": m.reinforcement_count,
                    "tags": m.tags
                }
                for m in result.memories
            ],
            "total_available": result.total_available,
            "query_time_ms": result.query_time_ms,
            "retrieval_mode": result.retrieval_mode,
            "degraded": result.degraded
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "RETRIEVE_ERROR"}])
def list_memory_types():
    """List available memory types."""
    return create_response(data={
        "types": [
            {
                "value": t.value,
                "description": {
                    "working": "Short-term, 3-7 items, current session",
                    "episodic": "Events with temporal context, auto-consolidates",
                    "semantic": "Facts, concepts, stable knowledge",
                    "procedural": "How-to knowledge, workflows",
                    "source_document": "Uploaded document reference",
                    "extracted_insight": "LLM-extracted knowledge"
                }[t.value]
            }
            for t in MemoryType
        ]
    })


@router.get("/stats/overview")
def memory_stats():
    """Get memory statistics."""
    try:
        store = get_memory_store()
        # Simple counts by type
        import sqlite3
        conn = sqlite3.connect(store.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT memory_type, COUNT(*) as count 
            FROM memories 
            WHERE state IN ('active', 'consolidating')
            GROUP BY memory_type
        """)
        
        type_counts = {row[0]: row[1] for row in cur.fetchall()}
        
        cur.execute("SELECT COUNT(*) FROM memories WHERE state = 'active'")
        active_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM memories")
        total_count = cur.fetchone()[0]
        
        conn.close()
        
        return create_response(data={
            "total_memories": total_count,
            "active_memories": active_count,
            "by_type": type_counts
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "STATS_ERROR"}])
