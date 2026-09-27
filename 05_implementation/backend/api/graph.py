"""
Graph API routes for Sage v4.
Exposes Graph Operations via REST.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from database_v4 import get_db
from models_v4 import Workspace
from services.graph_service import GraphService
from api.utils.responses import create_response

router = APIRouter(prefix="/api/graph", tags=["graph"])

def get_current_workspace(db: Session = Depends(get_db)):
    """Get the current workspace."""
    ws = db.query(Workspace).first()
    if not ws:
        raise HTTPException(status_code=404, detail="No workspace found")
    return ws

@router.post("/relationship")
def create_relationship(
    source_id: str,
    target_id: str,
    relationship_type: str,
    evidence: Optional[str] = None,
    confidence: float = 1.0,
    weight: float = 1.0,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Create a relationship between two nodes."""
    service = GraphService(db, workspace.id)
    result = service.create_relationship(
        source_id=source_id,
        target_id=target_id,
        relationship_type_name=relationship_type,
        evidence=evidence,
        confidence=confidence,
        weight=weight,
        notes=notes
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return create_response(data=result)

@router.delete("/relationship/{edge_id}")
def remove_relationship(
    edge_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Remove a relationship."""
    service = GraphService(db, workspace.id)
    result = service.remove_relationship(edge_id)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return create_response(data=result)

@router.get("/neighbors/{node_id}")
def get_neighbors(
    node_id: str,
    direction: str = "both",
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Get all neighbors of a node."""
    service = GraphService(db, workspace.id)
    result = service.get_neighbors(node_id, direction)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return create_response(data=result)

@router.get("/path")
def find_path(
    source_id: str,
    target_id: str,
    max_depth: int = 5,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Find shortest path between two nodes."""
    service = GraphService(db, workspace.id)
    result = service.find_path(source_id, target_id, max_depth)
    
    return create_response(data=result)

@router.get("/subgraph")
def build_subgraph(
    node_ids: str,  # Comma-separated list
    depth: int = 1,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Build a subgraph around specified nodes."""
    ids = [id.strip() for id in node_ids.split(",")]
    service = GraphService(db, workspace.id)
    result = service.build_subgraph(ids, depth)
    
    return create_response(data=result)

@router.get("/full")
def get_full_graph(
    max_nodes: int = 200,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Return the full knowledge graph for Obsidian-style visualization."""
    service = GraphService(db, workspace.id)
    result = service.get_full_graph(max_nodes=max_nodes)
    return create_response(data=result)

@router.get("/related/{node_id}")
def get_related_nodes(
    node_id: str,
    relationship_type: Optional[str] = None,
    max_depth: int = 1,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Get nodes related to a given node."""
    service = GraphService(db, workspace.id)
    result = service.get_related_nodes(node_id, relationship_type, max_depth)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return create_response(data=result)

@router.get("/backlinks/{node_id}")
def get_backlinks(
    node_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Get all nodes that point to this node."""
    service = GraphService(db, workspace.id)
    result = service.get_backlinks(node_id)
    
    return create_response(data=result)

@router.get("/forwardlinks/{node_id}")
def get_forward_links(
    node_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Get all nodes that this node points to."""
    service = GraphService(db, workspace.id)
    result = service.get_forward_links(node_id)
    
    return create_response(data=result)

@router.get("/degree/{node_id}")
def get_degree_analysis(
    node_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Analyze connection degrees for a node."""
    service = GraphService(db, workspace.id)
    result = service.get_degree_analysis(node_id)
    
    return create_response(data=result)

@router.get("/dependencies/{node_id}")
def get_dependencies(
    node_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Find what depends on this node."""
    service = GraphService(db, workspace.id)
    result = service.get_dependencies(node_id)
    
    return create_response(data=result)

@router.get("/impact/{node_id}")
def get_impact(
    node_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Find what would be affected if this node changed."""
    service = GraphService(db, workspace.id)
    result = service.get_impact(node_id)
    
    return create_response(data=result)

@router.post("/query")
def query_graph(
    query: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Execute a natural language query against the graph."""
    service = GraphService(db, workspace.id)
    result = service.query_graph(query)
    
    return create_response(data=result)

@router.get("/types")
def get_relationship_types(
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Get all available relationship types."""
    service = GraphService(db, workspace.id)
    types = service.get_relationship_types()
    
    return create_response(data=types)
