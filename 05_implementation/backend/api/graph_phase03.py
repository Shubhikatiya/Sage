"""
Phase 03: Knowledge Graph — Missing endpoints
POST /graph/traverse — multi-hop traversal
POST /graph/hybrid_retrieve — combined vector + graph retrieval
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from database_v4 import get_db
from models_v4 import Workspace, KnowledgeNode, KnowledgeEdge, NodeType
from api.utils.responses import create_response

router = APIRouter(prefix="/api/graph", tags=["graph"])


def get_current_workspace(db: Session = Depends(get_db)):
    ws = db.query(Workspace).first()
    if not ws:
        raise HTTPException(status_code=404, detail="No workspace found")
    return ws


class TraverseRequest(BaseModel):
    start_node_id: str
    max_depth: int = 2
    relationship_types: Optional[List[str]] = None
    direction: str = "both"  # outgoing, incoming, both


class HybridRetrieveRequest(BaseModel):
    query: str
    seed_entities: Optional[List[str]] = None
    max_hops: int = 2
    top_k: int = 15
    alpha: float = 0.5   # weight for vector similarity
    beta: float = 0.3   # weight for graph proximity
    gamma: float = 0.2   # weight for importance


@router.post("/traverse")
def traverse_graph(request: TraverseRequest, db: Session = Depends(get_db), workspace: Workspace = Depends(get_current_workspace)):
    """Multi-hop traversal from a starting node. Phase 03 endpoint."""
    try:
        # Validate start node
        start = db.query(KnowledgeNode).filter(
            KnowledgeNode.id == request.start_node_id,
            KnowledgeNode.workspace_id == workspace.id,
            KnowledgeNode.is_archived == False
        ).first()
        if not start:
            return create_response(errors=[{"message": "Start node not found", "code": "NOT_FOUND"}])

        # BFS traversal up to max_depth
        visited = {request.start_node_id}
        frontier = [(request.start_node_id, 0)]
        results = []

        while frontier:
            current_id, depth = frontier.pop(0)
            if depth >= request.max_depth:
                continue

            # Query edges based on direction
            query = db.query(KnowledgeEdge).filter(KnowledgeEdge.workspace_id == workspace.id)
            if request.direction == "outgoing":
                query = query.filter(KnowledgeEdge.source_id == current_id)
            elif request.direction == "incoming":
                query = query.filter(KnowledgeEdge.target_id == current_id)
            else:
                query = query.filter(
                    (KnowledgeEdge.source_id == current_id) | (KnowledgeEdge.target_id == current_id)
                )

            if request.relationship_types:
                # Filter by relationship type name
                rel_type_ids = [rt.id for rt in db.query(NodeType).filter(NodeType.name.in_(request.relationship_types)).all()]
                query = query.filter(KnowledgeEdge.relationship_type_id.in_(rel_type_ids))

            edges = query.filter(KnowledgeEdge.is_archived == False).all()

            for edge in edges:
                other_id = edge.target_id if edge.source_id == current_id else edge.source_id
                if other_id not in visited:
                    visited.add(other_id)
                    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == other_id).first()
                    if node:
                        results.append({
                            "node_id": node.id,
                            "title": node.title,
                            "type": node.node_type.name if node.node_type else "unknown",
                            "hop_distance": depth + 1,
                            "relationship": edge.relationship_type.name if edge.relationship_type else "related",
                            "direction": "outgoing" if edge.source_id == current_id else "incoming"
                        })
                        frontier.append((other_id, depth + 1))

        return create_response(data={
            "start_node": {"id": start.id, "title": start.title},
            "max_depth": request.max_depth,
            "results": results[:50]  # cap for safety
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "TRAVERSE_ERROR"}])


@router.post("/hybrid_retrieve")
def hybrid_retrieve(request: HybridRetrieveRequest, db: Session = Depends(get_db), workspace: Workspace = Depends(get_current_workspace)):
    """Combined vector + graph retrieval. Phase 03 section 9."""
    try:
        import sqlite3
        import json

        # Step 1: Keyword-based vector search (MVP: keyword matching on content)
        nodes = db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == workspace.id,
            KnowledgeNode.is_archived == False
        ).all()

        query_words = set(request.query.lower().split())
        scored = []

        for node in nodes:
            content = f"{node.title} {node.content or ''}".lower()
            content_words = set(content.split())
            overlap = len(query_words & content_words) / max(len(query_words), 1)

            # Graph proximity: if seed entities given, compute hop distance
            graph_score = 0.0
            if request.seed_entities:
                # Simple: check if node is directly connected to any seed
                edges = db.query(KnowledgeEdge).filter(
                    KnowledgeEdge.workspace_id == workspace.id,
                    KnowledgeEdge.is_archived == False,
                    (KnowledgeEdge.source_id == node.id) | (KnowledgeEdge.target_id == node.id)
                ).all()
                for edge in edges:
                    other = edge.source_id if edge.target_id == node.id else edge.target_id
                    if other in request.seed_entities:
                        graph_score = max(graph_score, 1.0)
                        break

            # Importance from node fields
            importance = getattr(node, 'ai_importance_score', 0.5) or 0.5

            final_score = (
                request.alpha * overlap +
                request.beta * graph_score +
                request.gamma * importance
            )

            if final_score > 0.05:
                scored.append({
                    "node_id": node.id,
                    "title": node.title,
                    "type": node.node_type.name if node.node_type else "unknown",
                    "score": round(final_score, 4),
                    "vector_similarity": round(overlap, 4),
                    "graph_proximity": round(graph_score, 4),
                    "importance": round(importance, 4)
                })

        scored.sort(key=lambda x: x["score"], reverse=True)

        return create_response(data={
            "query": request.query,
            "seed_entities": request.seed_entities,
            "results": scored[:request.top_k],
            "total_candidates": len(scored),
            "weights": {"alpha": request.alpha, "beta": request.beta, "gamma": request.gamma}
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "HYBRID_ERROR"}])
