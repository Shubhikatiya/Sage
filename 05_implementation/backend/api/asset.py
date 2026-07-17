"""
Asset API for Sage v4.
Handles asset upload, processing, and knowledge extraction approval.
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, Dict, List
from database_v4 import get_db
from models_v4 import Workspace, Asset, KnowledgeNode, NodeType, KnowledgeEdge
from services.asset_pipeline import AssetPipeline
from services.knowledge_extraction import KnowledgeExtractionEngine
from core.graph.entity_manager import EntityManager
from core.graph.relationship_manager import RelationshipManager
from api.utils.responses import create_response, create_error_response
import datetime
import os

router = APIRouter(prefix="/api/asset", tags=["asset"])

class ApproveRequest(BaseModel):
    approve_all: bool = False
    suggestion_indices: List[int] = None

def get_current_workspace(db: Session = Depends(get_db)):
    ws = db.query(Workspace).first()
    if not ws:
        raise HTTPException(status_code=404, detail="No workspace found")
    return ws

# Initialize pipeline
pipeline = AssetPipeline(upload_dir="uploads")
extraction_engine = KnowledgeExtractionEngine()

@router.post("/upload")
async def upload_asset(
    file: UploadFile = File(...),
    auto_extract: bool = Form(True),
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Upload an asset and optionally trigger knowledge extraction."""
    try:
        # Read file content
        file_content = await file.read()
        
        # Process through pipeline
        result = pipeline.process_asset(file_content, file.filename)
        
        # Create Asset record
        asset = Asset(
            workspace_id=workspace.id,
            asset_type=result["type_info"]["asset_type"],
            original_filename=file.filename,
            file_path=result["file_path"],
            mime_type=result["type_info"]["mime_type"],
            extracted_text=result["extraction"]["text"] if result["extraction"]["success"] else None,
            summary=extraction_engine.generate_summary(result["extraction"]["text"]) if result["extraction"]["success"] else None,
            uploaded_at=datetime.datetime.utcnow(),
            processing_status="complete" if result["extraction"]["success"] else "error"
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        # Extract knowledge if requested and extraction succeeded
        extracted_knowledge = None
        if auto_extract and result["extraction"]["success"]:
            # Use the NEW extract_document pipeline
            extraction_result = extraction_engine.extract_document(
                result["extraction"]["text"],
                metadata={
                    "filename": file.filename,
                    "asset_type": result["type_info"]["asset_type"],
                    "file_size": result["metadata"].get("file_size_human", "unknown"),
                }
            )
            
            # Create primary node + child nodes structure
            node_structure = extraction_engine.create_knowledge_nodes(
                extraction_result, source_asset_id=asset.id
            )
            
            # Find existing nodes for relationship suggestions
            existing_nodes = db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == workspace.id,
                KnowledgeNode.is_archived == False
            ).all()
            
            existing_node_data = [
                {"id": n.id, "title": n.title, "slug": n.slug}
                for n in existing_nodes
            ]
            
            relationship_suggestions = extraction_engine.suggest_relationships(
                extraction_result["extractions"]["entities"], existing_node_data
            )
            
            extracted_knowledge = {
                "primary_node": node_structure["primary_node"],
                "child_nodes": node_structure["child_nodes"],
                "relationships": node_structure["relationships"],
                "relationship_suggestions": relationship_suggestions,
                "summary": extraction_result["summary"],
                "key_themes": extraction_result["key_themes"],
                "stats": extraction_result["stats"],
            }
        
        return create_response(data={
            "asset": {
                "id": asset.id,
                "type": asset.asset_type,
                "filename": asset.original_filename,
                "status": asset.processing_status,
            },
            "extraction": {
                "success": result["extraction"]["success"],
                "text_length": len(result["extraction"]["text"]) if result["extraction"]["text"] else 0,
                "chunks": len(result["extraction"]["chunks"]),
                "error": result["extraction"]["error"],
            },
            "extracted_knowledge": extracted_knowledge,
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{asset_id}")
def get_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Get asset details with extraction results."""
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.workspace_id == workspace.id
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    return create_response(data={
        "id": asset.id,
        "type": asset.asset_type,
        "filename": asset.original_filename,
        "mime_type": asset.mime_type,
        "status": asset.processing_status,
        "extracted_text": asset.extracted_text[:500] + "..." if asset.extracted_text and len(asset.extracted_text) > 500 else asset.extracted_text,
        "summary": asset.summary,
        "linked_nodes": asset.linked_nodes,
        "uploaded_at": asset.uploaded_at.isoformat() if asset.uploaded_at else None,
    })

@router.get("/{asset_id}/knowledge")
def get_asset_knowledge(
    asset_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Get extracted knowledge from an asset."""
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.workspace_id == workspace.id
    ).first()
    
    if not asset or not asset.extracted_text:
        raise HTTPException(status_code=404, detail="Asset or extracted text not found")
    
    # Re-run extraction with new pipeline
    extraction_result = extraction_engine.extract_document(asset.extracted_text)
    node_structure = extraction_engine.create_knowledge_nodes(extraction_result, asset.id)
    
    return create_response(data={
        "asset_id": asset_id,
        "primary_node": node_structure["primary_node"],
        "child_nodes": node_structure["child_nodes"],
        "stats": extraction_result["stats"],
    })

@router.post("/{asset_id}/approve")
def approve_extracted_knowledge(
    asset_id: str,
    approve_all: bool = False,
    suggestion_indices: List[int] = None,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Approve extracted knowledge and create KnowledgeNodes."""
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.workspace_id == workspace.id
    ).first()
    
    if not asset or not asset.extracted_text:
        raise HTTPException(status_code=404, detail="Asset or extracted text not found")
    
    # Re-extract to get the full structure
    extraction_result = extraction_engine.extract_document(asset.extracted_text)
    node_structure = extraction_engine.create_knowledge_nodes(extraction_result, asset.id)
    
    # Create nodes
    entity_manager = EntityManager(db, workspace.id)
    relationship_manager = RelationshipManager(db, workspace.id)
    
    created_nodes = []
    
    # Find node types
    document_type = db.query(NodeType).filter(
        NodeType.workspace_id == workspace.id,
        NodeType.name == "document",
        NodeType.is_archived == False
    ).first()
    
    if not document_type:
        # Try to find any node type for documents
        document_type = db.query(NodeType).filter(
            NodeType.workspace_id == workspace.id,
            NodeType.is_archived == False
        ).first()
    
    # Create primary document node
    primary = node_structure["primary_node"]
    if document_type:
        primary_node = entity_manager.create_node(
            node_type_id=document_type.id,
            title=primary["title"][:200],  # Limit title length
            content=primary["content"],  # FULL TEXT
            source_type="asset_extraction",
            source_id=asset_id,
            confidence="certain"
        )
        created_nodes.append({
            "id": primary_node.id,
            "title": primary_node.title,
            "type": "document",
            "is_primary": True
        })
    
    # Determine which child nodes to create
    indices_to_create = suggestion_indices or []
    if approve_all:
        indices_to_create = list(range(len(node_structure["child_nodes"])))
    
    # Create child nodes with relationships to primary
    for idx in indices_to_create:
        if idx < 0 or idx >= len(node_structure["child_nodes"]):
            continue
        
        child = node_structure["child_nodes"][idx]
        
        # Find appropriate node type
        node_type = db.query(NodeType).filter(
            NodeType.workspace_id == workspace.id,
            NodeType.name == child["node_type"],
            NodeType.is_archived == False
        ).first()
        
        if not node_type:
            continue
        
        child_node = entity_manager.create_node(
            node_type_id=node_type.id,
            title=child["title"][:200],
            content=child["content"],
            source_type="asset_extraction",
            source_id=asset_id,
            confidence="likely" if child["confidence"] < 0.8 else "certain"
        )
        
        created_nodes.append({
            "id": child_node.id,
            "title": child_node.title,
            "type": child["node_type"],
            "is_primary": False
        })
        
        # Create relationship to primary document if it exists
        if document_type and primary_node:
            from models_v4 import RelationshipType
            rel_type = db.query(RelationshipType).filter(
                RelationshipType.workspace_id == workspace.id,
                RelationshipType.name == "CONTAINS"
            ).first()
            
            if rel_type:
                db.add(KnowledgeEdge(
                    workspace_id=workspace.id,
                    source_id=primary_node.id,
                    target_id=child_node.id,
                    relationship_type_id=rel_type.id,
                    evidence=f"Extracted from {asset.original_filename}",
                    confidence=child["confidence"]
                ))
    
    # Update asset linked nodes
    asset.linked_nodes = [n["id"] for n in created_nodes]
    db.commit()
    
    return create_response(data={
        "approved": len(created_nodes),
        "created_nodes": created_nodes,
        "primary_node_id": created_nodes[0]["id"] if created_nodes else None,
    })
