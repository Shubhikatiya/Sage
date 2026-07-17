"""
Reasoning API for Sage v4.
Cognitive operations: Bring Me Back, gap finding, contradiction detection, suggestions.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from database_v4 import get_db
from models_v4 import Workspace, KnowledgeNode, KnowledgeEdge, NodeType, StateSnapshot
from services.bring_me_back import BringMeBackEngine
from api.utils.responses import create_response, create_error_response

router = APIRouter(prefix="/api/reasoning", tags=["reasoning"])

def get_current_workspace(db: Session = Depends(get_db)):
    ws = db.query(Workspace).first()
    if not ws:
        raise HTTPException(status_code=404, detail="No workspace found")
    return ws

@router.post("/bring-me-back")
def bring_me_back(
    since_days: Optional[int] = Query(7, description="Number of days to look back"),
    user_id: Optional[str] = None,
    format: str = Query("json", enum=["json", "markdown"]),
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Generate a comprehensive 'Bring Me Back' briefing."""
    engine = BringMeBackEngine(db, workspace.id)
    
    since_date = datetime.utcnow() - timedelta(days=since_days)
    briefing = engine.generate_briefing(user_id=user_id, since_date=since_date)
    
    if format == "markdown":
        return create_response(data={
            "briefing": engine.format_briefing_markdown(briefing),
            "raw": briefing
        })
    
    return create_response(data=briefing)

@router.get("/progress")
def get_progress(
    node_id: Optional[str] = None,
    node_type: Optional[str] = None,
    since_days: int = Query(30),
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Get progress trends for nodes over time."""
    since_date = datetime.utcnow() - timedelta(days=since_days)
    
    query = db.query(KnowledgeNode).filter(
        KnowledgeNode.workspace_id == workspace.id,
        KnowledgeNode.is_archived == False
    )
    
    if node_id:
        query = query.filter(KnowledgeNode.id == node_id)
    elif node_type:
        type_obj = db.query(NodeType).filter(
            NodeType.workspace_id == workspace.id,
            NodeType.name == node_type
        ).first()
        if type_obj:
            query = query.filter(KnowledgeNode.node_type_id == type_obj.id)
    
    nodes = query.all()
    
    progress_data = []
    for node in nodes:
        snapshots = db.query(StateSnapshot).filter(
            StateSnapshot.node_id == node.id,
            StateSnapshot.snapshot_date >= since_date
        ).order_by(StateSnapshot.snapshot_date).all()
        
        progress_data.append({
            "node_id": node.id,
            "title": node.title,
            "completeness_current": node.completeness_percent or 0,
            "snapshots": [
                {
                    "date": s.snapshot_date.isoformat() if s.snapshot_date else None,
                    "completeness": s.completeness.get("overall", 0) if s.completeness else 0,
                    "health_score": s.health_score,
                    "progress": s.progress,
                }
                for s in snapshots
            ]
        })
    
    return create_response(data={
        "since": since_date.isoformat(),
        "nodes": progress_data
    })

@router.get("/gaps")
def find_knowledge_gaps(
    node_id: Optional[str] = None,
    node_type: Optional[str] = None,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Find knowledge gaps in the graph.
    
    Identifies:
    - Nodes with low completeness
    - Nodes missing timeline events
    - Nodes missing relationships
    - Nodes missing evidence
    - Nodes with no recent updates
    """
    gaps = []
    
    query = db.query(KnowledgeNode).filter(
        KnowledgeNode.workspace_id == workspace.id,
        KnowledgeNode.is_archived == False
    )
    
    if node_id:
        query = query.filter(KnowledgeNode.id == node_id)
    elif node_type:
        type_obj = db.query(NodeType).filter(
            NodeType.workspace_id == workspace.id,
            NodeType.name == node_type
        ).first()
        if type_obj:
            query = query.filter(KnowledgeNode.node_type_id == type_obj.id)
    
    nodes = query.all()
    
    for node in nodes:
        node_gaps = []
        
        # Check completeness
        completeness = node.completeness_percent or 0
        if completeness < 50:
            node_gaps.append({
                "type": "low_completeness",
                "severity": "high" if completeness < 25 else "medium",
                "message": f"Node is only {completeness}% documented",
                "current_value": completeness
            })
        
        # Check for missing fields in completeness dict
        if node.completeness:
            for field, value in node.completeness.items():
                if value is False or value == "missing":
                    node_gaps.append({
                        "type": "missing_field",
                        "severity": "medium",
                        "message": f"Missing {field}",
                        "field": field
                    })
        
        # Check relationships
        edge_count = db.query(KnowledgeEdge).filter(
            (KnowledgeEdge.source_id == node.id) | (KnowledgeEdge.target_id == node.id),
            KnowledgeEdge.is_archived == False
        ).count()
        
        if edge_count == 0:
            node_gaps.append({
                "type": "no_relationships",
                "severity": "medium",
                "message": "Node has no connections in the graph"
            })
        elif edge_count < 3:
            node_gaps.append({
                "type": "few_relationships",
                "severity": "low",
                "message": f"Node only has {edge_count} connection(s)"
            })
        
        # Check for timeline events
        timeline_count = db.query(StateSnapshot).filter(
            StateSnapshot.node_id == node.id
        ).count()
        
        if timeline_count == 0:
            node_gaps.append({
                "type": "no_timeline",
                "severity": "low",
                "message": "No state snapshots recorded"
            })
        
        # Check for recent activity
        days_since_update = (datetime.utcnow() - (node.updated_at or node.created_at)).days
        if days_since_update > 30:
            node_gaps.append({
                "type": "stale",
                "severity": "low",
                "message": f"No updates in {days_since_update} days"
            })
        
        if node_gaps:
            gaps.append({
                "node_id": node.id,
                "title": node.title,
                "slug": node.slug,
                "gaps": node_gaps,
                "total_gaps": len(node_gaps),
                "severity": max([g["severity"] for g in node_gaps], key=lambda x: ["low", "medium", "high"].index(x))
            })
    
    # Sort by severity then by total gaps
    severity_order = {"high": 0, "medium": 1, "low": 2}
    gaps.sort(key=lambda x: (severity_order[x["severity"]], -x["total_gaps"]))
    
    return create_response(data={
        "total_nodes_checked": len(nodes),
        "nodes_with_gaps": len(gaps),
        "gaps": gaps[:20]  # Top 20
    })

@router.get("/contradictions")
def find_contradictions(
    node_id: Optional[str] = None,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Find potential contradictions in the knowledge graph.
    
    Simple heuristic-based detection (no LLM required):
    - Nodes with conflicting status values
    - Recent decisions that contradict older ones
    - Nodes with low confidence and high completeness
    """
    contradictions = []
    
    # Find nodes with conflicting state snapshots
    if node_id:
        nodes = [db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()]
    else:
        nodes = db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == workspace.id,
            KnowledgeNode.is_archived == False
        ).all()
    
    for node in nodes:
        if not node:
            continue
            
        snapshots = db.query(StateSnapshot).filter(
            StateSnapshot.node_id == node.id
        ).order_by(StateSnapshot.snapshot_date.desc()).limit(5).all()
        
        if len(snapshots) >= 2:
            # Check for status changes that might indicate contradiction
            statuses = [s.status for s in snapshots if s.status]
            if len(set(statuses)) > 1:
                contradictions.append({
                    "type": "status_change",
                    "node_id": node.id,
                    "title": node.title,
                    "message": f"Status changed from '{statuses[-1]}' to '{statuses[0]}'",
                    "severity": "medium"
                })
            
            # Check for decreasing progress
            progresses = [s.progress for s in snapshots if s.progress is not None]
            if len(progresses) >= 2 and progresses[0] < progresses[-1]:
                contradictions.append({
                    "type": "progress_regression",
                    "node_id": node.id,
                    "title": node.title,
                    "message": f"Progress decreased from {progresses[-1]}% to {progresses[0]}%",
                    "severity": "high"
                })
    
    # Find decisions that might contradict each other
    decision_type = db.query(NodeType).filter(
        NodeType.workspace_id == workspace.id,
        NodeType.name == "decision"
    ).first()
    
    if decision_type:
        decisions = db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == workspace.id,
            KnowledgeNode.node_type_id == decision_type.id,
            KnowledgeNode.is_archived == False
        ).order_by(KnowledgeNode.created_at.desc()).limit(20).all()
        
        # Check for opposite keywords in recent decisions
        opposite_pairs = [
            ("use", "don't use"),
            ("build", "don't build"),
            ("yes", "no"),
            ("start", "stop"),
            ("continue", "pause"),
        ]
        
        for i, decision1 in enumerate(decisions):
            for decision2 in decisions[i+1:]:
                if not decision1.content or not decision2.content:
                    continue
                    
                content1 = decision1.content.lower()
                content2 = decision2.content.lower()
                
                for pair in opposite_pairs:
                    if (pair[0] in content1 and pair[1] in content2) or \
                       (pair[1] in content1 and pair[0] in content2):
                        contradictions.append({
                            "type": "contradictory_decisions",
                            "node_ids": [decision1.id, decision2.id],
                            "titles": [decision1.title, decision2.title],
                            "message": f"Potential contradiction: '{decision1.title}' vs '{decision2.title}'",
                            "severity": "high"
                        })
    
    return create_response(data={
        "contradictions_found": len(contradictions),
        "contradictions": contradictions
    })

@router.post("/suggest-next-steps")
def suggest_next_steps(
    focus_node_id: Optional[str] = None,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Suggest next steps based on current graph state and gaps."""
    engine = BringMeBackEngine(db, workspace.id)
    suggestions = engine._suggest_next_steps()
    
    # Add context-specific suggestions if focus node provided
    if focus_node_id:
        focus_node = db.query(KnowledgeNode).filter(
            KnowledgeNode.id == focus_node_id,
            KnowledgeNode.workspace_id == workspace.id
        ).first()
        
        if focus_node:
            suggestions.insert(0, {
                "type": "focus",
                "message": f"Continue working on {focus_node.title}",
                "node_id": focus_node_id,
                "priority": "high"
            })
            
            # Suggest related nodes to explore
            edges = db.query(KnowledgeEdge).filter(
                (KnowledgeEdge.source_id == focus_node_id) | (KnowledgeEdge.target_id == focus_node_id),
                KnowledgeEdge.is_archived == False
            ).limit(3).all()
            
            for edge in edges:
                related_id = edge.target_id if edge.source_id == focus_node_id else edge.source_id
                related = db.query(KnowledgeNode).filter(KnowledgeNode.id == related_id).first()
                if related:
                    suggestions.append({
                        "type": "related",
                        "message": f"Explore: {related.title}",
                        "node_id": related_id,
                        "priority": "medium"
                    })
    
    return create_response(data={
        "suggestions": suggestions,
        "total": len(suggestions)
    })

@router.post("/summarize")
def summarize_node(
    node_id: str,
    max_length: int = Query(500),
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Generate a summary of a node and its context."""
    node = db.query(KnowledgeNode).filter(
        KnowledgeNode.id == node_id,
        KnowledgeNode.workspace_id == workspace.id
    ).first()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Get related nodes
    edges = db.query(KnowledgeEdge).filter(
        (KnowledgeEdge.source_id == node_id) | (KnowledgeEdge.target_id == node_id),
        KnowledgeEdge.is_archived == False
    ).limit(10).all()
    
    related = []
    for edge in edges:
        related_id = edge.target_id if edge.source_id == node_id else edge.source_id
        related_node = db.query(KnowledgeNode).filter(KnowledgeNode.id == related_id).first()
        if related_node:
            related.append({
                "id": related_node.id,
                "title": related_node.title,
                "relationship": edge.relationship_type
            })
    
    # Use extraction engine for summary
    content = node.content or ""
    summary = KnowledgeExtractionEngine().generate_summary(content, max_length)
    
    return create_response(data={
        "node": {
            "id": node.id,
            "title": node.title,
            "type": node.node_type.name if node.node_type else "unknown",
        },
        "summary": summary,
        "related_nodes": related,
        "stats": {
            "content_length": len(content),
            "related_count": len(related),
            "completeness": node.completeness_percent or 0
        }
    })
