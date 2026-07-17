"""
Knowledge API routes for Sage v4.
Exposes Knowledge Operations via REST.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict, List, Any
from database_v4 import get_db
from models_v4 import Workspace
from services.knowledge_service import KnowledgeService
from api.utils.responses import create_response, create_error_response, create_paginated_response
import datetime

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

def get_current_workspace(db: Session = Depends(get_db)):
    """Get the current workspace (for now, returns the first one)."""
    ws = db.query(Workspace).first()
    if not ws:
        raise HTTPException(status_code=404, detail="No workspace found")
    return ws

@router.post("/create")
def create_knowledge_object(
    node_type: str,
    title: str,
    content: str = "",
    layer: Optional[str] = None,
    status: Optional[str] = "draft",
    priority: Optional[str] = "medium",
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Create a new knowledge object."""
    service = KnowledgeService(db, workspace.id)
    result = service.create_knowledge_object(
        node_type_name=node_type,
        title=title,
        content=content,
        layer=layer,
        status=status,
        priority=priority
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return create_response(data=result)

@router.get("/{node_id}")
def get_knowledge_object(
    node_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Get a knowledge object by ID."""
    service = KnowledgeService(db, workspace.id)
    node = service.get_node(node_id)
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    return create_response(data=node)

@router.patch("/{node_id}")
def update_knowledge_object(
    node_id: str,
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Update a knowledge object."""
    service = KnowledgeService(db, workspace.id)
    result = service.update_knowledge_object(node_id, data)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return create_response(data=result)

@router.post("/{node_id}/archive")
def archive_knowledge_object(
    node_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Archive (soft delete) a knowledge object."""
    service = KnowledgeService(db, workspace.id)
    result = service.archive_knowledge_object(node_id)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return create_response(data=result)

@router.post("/{node_id}/restore")
def restore_knowledge_object(
    node_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Restore an archived knowledge object."""
    service = KnowledgeService(db, workspace.id)
    result = service.restore_knowledge_object(node_id)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return create_response(data=result)

@router.get("/{node_id}/identity")
def get_identity_card(
    node_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Get the Identity Card for a node."""
    service = KnowledgeService(db, workspace.id)
    result = service.get_identity_card(node_id)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return create_response(data=result["identity_card"])

@router.post("/{node_id}/merge")
def merge_nodes(
    node_id: str,
    target_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Merge a node into another node."""
    service = KnowledgeService(db, workspace.id)
    result = service.merge_nodes(node_id, target_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return create_response(data=result)

@router.post("/{node_id}/split")
def split_node(
    node_id: str,
    new_titles: List[str],
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Split a node into multiple nodes."""
    service = KnowledgeService(db, workspace.id)
    result = service.split_node(node_id, new_titles)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return create_response(data=result)

@router.post("/{node_id}/change-type")
def change_node_type(
    node_id: str,
    new_type: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Change the type of a node."""
    service = KnowledgeService(db, workspace.id)
    result = service.change_node_type(node_id, new_type)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return create_response(data=result)

@router.get("/")
def search_knowledge(
    q: Optional[str] = None,
    node_type: Optional[str] = None,
    layer: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Search for knowledge objects with filters."""
    service = KnowledgeService(db, workspace.id)
    results = service.search_nodes(q, node_type, layer, status)
    
    # Manual pagination
    total = len(results)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_results = results[start:end]
    
    return create_paginated_response(
        items=paginated_results,
        total=total,
        page=page,
        per_page=per_page
    )

@router.get("/types/list")
def get_node_types(
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Get all available node types."""
    service = KnowledgeService(db, workspace.id)
    types = service.get_node_types()
    
    return create_response(data=types)
