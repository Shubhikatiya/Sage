"""
Reasoning API for Sage v4 — Phase 04
Exposes multi-mode reasoning via REST endpoints.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from services.reasoning_engine import get_reasoning_engine, ReasoningMode
from api.utils.responses import create_response

router = APIRouter(prefix="/api/reasoning", tags=["reasoning"])


class ReasonRequest(BaseModel):
    query: str
    mode: str = "chain"  # chain, tree, graph, reflection, simulation
    context: Optional[Dict[str, Any]] = None
    max_evidence_items: int = 10
    high_stakes: bool = False


@router.post("/reason")
async def reason(request: ReasonRequest):
    """Execute multi-mode reasoning on a query."""
    try:
        engine = get_reasoning_engine()
        
        # Parse mode
        try:
            mode = ReasoningMode(request.mode)
        except ValueError:
            return create_response(errors=[{
                "message": f"Invalid mode: {request.mode}. Use: chain, tree, graph, reflection, simulation",
                "code": "INVALID_MODE"
            }])
        
        trace = await engine.reason(
            query=request.query,
            mode=mode,
            context=request.context,
            max_evidence_items=request.max_evidence_items,
            high_stakes=request.high_stakes
        )
        
        return create_response(data={
            "trace_id": trace.trace_id,
            "query": trace.query,
            "mode": trace.mode.value,
            "steps": [
                {
                    "step_number": s.step_number,
                    "sub_question": s.sub_question,
                    "intermediate_conclusion": s.intermediate_conclusion,
                    "confidence": s.step_confidence,
                    "evidence_count": len(s.evidence_ids),
                    "critique": s.critique
                }
                for s in trace.steps
            ],
            "final_answer": trace.final_answer,
            "overall_confidence": trace.overall_confidence,
            "confidence_explanation": trace.confidence_explanation,
            "critique_applied": trace.critique_applied,
            "latency_ms": trace.latency_ms,
            "degraded": trace.degraded
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "REASONING_ERROR"}])


@router.post("/reason-and-chat")
async def reason_and_chat(request: ReasonRequest):
    """Execute reasoning and return a chat-friendly response."""
    try:
        engine = get_reasoning_engine()
        
        try:
            mode = ReasoningMode(request.mode)
        except ValueError:
            mode = ReasoningMode.CHAIN
        
        trace = await engine.reason(
            query=request.query,
            mode=mode,
            context=request.context,
            max_evidence_items=request.max_evidence_items,
            high_stakes=request.high_stakes
        )
        
        # Format as chat message
        confidence_emoji = "🟢" if trace.overall_confidence > 0.7 else "🟡" if trace.overall_confidence > 0.4 else "🔴"
        
        response_text = f"{trace.final_answer}\n\n---\n*{confidence_emoji} Confidence: {trace.overall_confidence:.0%} | Mode: {trace.mode.value} | {len(trace.steps)} reasoning steps*"
        
        if trace.critique_applied:
            response_text += " | Self-critiqued"
        
        return create_response(data={
            "message": {
                "role": "assistant",
                "content": response_text,
                "trace_id": trace.trace_id,
                "mode": trace.mode.value,
                "confidence": trace.overall_confidence
            }
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "REASONING_ERROR"}])


@router.get("/traces")
def get_recent_traces(limit: int = 10):
    """Get recent reasoning traces for review."""
    try:
        engine = get_reasoning_engine()
        traces = engine.get_recent_traces(limit=limit)
        
        return create_response(data=[
            {
                "trace_id": t.trace_id,
                "query": t.query,
                "mode": t.mode.value,
                "steps_count": len(t.steps),
                "overall_confidence": t.overall_confidence,
                "latency_ms": t.latency_ms,
                "degraded": t.degraded
            }
            for t in traces
        ])
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])


@router.get("/modes")
def list_reasoning_modes():
    """List available reasoning modes with descriptions."""
    return create_response(data=[
        {
            "value": "chain",
            "name": "Chain of Thought",
            "description": "Sequential step-by-step reasoning. Best for: clear, logical problems.",
            "icon": "🔗"
        },
        {
            "value": "tree",
            "name": "Tree Search",
            "description": "Explore multiple hypotheses in parallel. Best for: ambiguous or complex questions.",
            "icon": "🌳"
        },
        {
            "value": "graph",
            "name": "Graph Traversal",
            "description": "Navigate knowledge graph relationships. Best for: questions about connected knowledge.",
            "icon": "🕸️"
        },
        {
            "value": "reflection",
            "name": "Self-Reflection",
            "description": "Generate answer, then critique and improve. Best for: high-stakes decisions.",
            "icon": "🪞"
        },
        {
            "value": "simulation",
            "name": "Scenario Simulation",
            "description": "Explore what-if scenarios. Best for: planning and forecasting.",
            "icon": "🔮"
        }
    ])
