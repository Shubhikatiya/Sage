"""
Knowledge Operations Service for Sage v4.
High-level operations for managing knowledge objects in the graph.
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, List, Any
from models_v4 import KnowledgeNode, NodeType, Version
from core.graph.entity_manager import EntityManager
from core.storage.repository import Repository
import datetime

class KnowledgeService:
    """Provides Knowledge Operations for the Capability Layer."""
    
    def __init__(self, db: Session, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
        self.entity_manager = EntityManager(db, workspace_id)
    
    # ── Create ──
    def create_knowledge_object(self, node_type_name: str, title: str, 
                                 content: str = "", layer: str = None,
                                 **kwargs) -> Dict[str, Any]:
        """Create a new knowledge object."""
        # Find node type
        node_type = self.db.query(NodeType).filter(
            NodeType.workspace_id == self.workspace_id,
            NodeType.name == node_type_name.lower(),
            NodeType.is_archived == False
        ).first()
        
        if not node_type:
            return {"success": False, "error": f"Node type '{node_type_name}' not found"}
        
        node = self.entity_manager.create_node(
            node_type_id=node_type.id,
            title=title,
            content=content,
            layer=layer,
            **kwargs
        )
        
        return {
            "success": True,
            "node": {
                "id": node.id,
                "slug": node.slug,
                "title": node.title,
                "type": node_type.name,
                "layer": node.layer,
                "status": node.status
            }
        }
    
    # ── Update ──
    def update_knowledge_object(self, node_id: str, data: Dict[str, Any],
                                changed_by: str = "user") -> Dict[str, Any]:
        """Update a knowledge object and create version."""
        node = self.entity_manager.update_node(node_id, data, changed_by)
        
        if not node:
            return {"success": False, "error": f"Node '{node_id}' not found"}
        
        return {
            "success": True,
            "node": {
                "id": node.id,
                "slug": node.slug,
                "title": node.title,
                "status": node.status,
                "updated_at": node.updated_at.isoformat() if node.updated_at else None
            }
        }
    
    # ── Archive (Soft Delete) ──
    def archive_knowledge_object(self, node_id: str, deleted_by: str = "user") -> Dict[str, Any]:
        """Soft delete a knowledge object."""
        result = self.entity_manager.repo.soft_delete(node_id, deleted_by)
        
        if not result:
            return {"success": False, "error": f"Node '{node_id}' not found"}
        
        return {"success": True, "message": f"Node '{node_id}' archived"}
    
    # ── Restore ──
    def restore_knowledge_object(self, node_id: str) -> Dict[str, Any]:
        """Restore an archived knowledge object."""
        node = self.entity_manager.repo.restore(node_id)
        
        if not node:
            return {"success": False, "error": f"Node '{node_id}' not found"}
        
        return {
            "success": True,
            "node": {
                "id": node.id,
                "slug": node.slug,
                "title": node.title
            }
        }
    
    # ── Get Identity Card ──
    def get_identity_card(self, node_id: str) -> Dict[str, Any]:
        """Get the Identity Card for a node."""
        identity = self.entity_manager.get_node_identity_card(node_id)
        
        if not identity:
            return {"success": False, "error": f"Node '{node_id}' not found"}
        
        return {"success": True, "identity_card": identity}
    
    # ── Get Node ──
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a node by ID."""
        node = self.entity_manager.repo.get_by_id(node_id)
        if not node:
            return None
        
        node_type = self.db.query(NodeType).filter(NodeType.id == node.node_type_id).first()
        
        return {
            "id": node.id,
            "slug": node.slug,
            "title": node.title,
            "type": node_type.name if node_type else "unknown",
            "type_display": node_type.display_name if node_type else "Unknown",
            "content": node.content,
            "layer": node.layer,
            "status": node.status,
            "priority": node.priority,
            "completeness_percent": node.completeness_percent,
            "created_at": node.created_at.isoformat() if node.created_at else None,
            "updated_at": node.updated_at.isoformat() if node.updated_at else None,
        }
    
    # ── Merge Nodes ──
    def merge_nodes(self, source_id: str, target_id: str, 
                   merged_by: str = "user") -> Dict[str, Any]:
        """Merge two nodes. Source node is archived, relationships redirected to target."""
        source = self.entity_manager.repo.get_by_id(source_id)
        target = self.entity_manager.repo.get_by_id(target_id)
        
        if not source or not target:
            missing = []
            if not source: missing.append(source_id)
            if not target: missing.append(target_id)
            return {"success": False, "error": f"Nodes not found: {missing}"}
        
        # Redirect outgoing edges from source to target
        from models_v4 import KnowledgeEdge
        edges = self.db.query(KnowledgeEdge).filter(
            KnowledgeEdge.workspace_id == self.workspace_id,
            KnowledgeEdge.source_id == source_id,
            KnowledgeEdge.is_archived == False
        ).all()
        
        for edge in edges:
            edge.source_id = target_id
        
        # Redirect incoming edges to source to target
        edges = self.db.query(KnowledgeEdge).filter(
            KnowledgeEdge.workspace_id == self.workspace_id,
            KnowledgeEdge.target_id == source_id,
            KnowledgeEdge.is_archived == False
        ).all()
        
        for edge in edges:
            edge.target_id = target_id
        
        # Merge content
        if source.content and target.content:
            target.content = f"{target.content}\n\n[Merged from {source.title}]:\n{source.content}"
        elif source.content:
            target.content = source.content
        
        # Archive source
        source.is_archived = True
        source.deleted_at = datetime.datetime.utcnow()
        source.deleted_by = merged_by
        
        self.db.commit()
        
        return {
            "success": True,
            "message": f"Merged '{source.title}' into '{target.title}'",
            "target_id": target_id
        }
    
    # ── Split Node ──
    def split_node(self, node_id: str, new_titles: List[str],
                   split_by: str = "user") -> Dict[str, Any]:
        """Split one node into multiple nodes."""
        original = self.entity_manager.repo.get_by_id(node_id)
        if not original:
            return {"success": False, "error": f"Node '{node_id}' not found"}
        
        node_type = self.db.query(NodeType).filter(NodeType.id == original.node_type_id).first()
        if not node_type:
            return {"success": False, "error": "Node type not found"}
        
        new_nodes = []
        for title in new_titles:
            node = self.entity_manager.create_node(
                node_type_id=original.node_type_id,
                title=title,
                content=f"Split from {original.title}",
                layer=original.layer
            )
            new_nodes.append({
                "id": node.id,
                "slug": node.slug,
                "title": node.title
            })
        
        return {
            "success": True,
            "original_id": node_id,
            "new_nodes": new_nodes
        }
    
    # ── Change Node Type ──
    def change_node_type(self, node_id: str, new_type_name: str) -> Dict[str, Any]:
        """Change the type of a node."""
        node = self.entity_manager.repo.get_by_id(node_id)
        if not node:
            return {"success": False, "error": f"Node '{node_id}' not found"}
        
        new_type = self.db.query(NodeType).filter(
            NodeType.workspace_id == self.workspace_id,
            NodeType.name == new_type_name.lower(),
            NodeType.is_archived == False
        ).first()
        
        if not new_type:
            return {"success": False, "error": f"Node type '{new_type_name}' not found"}
        
        node.node_type_id = new_type.id
        self.db.commit()
        
        return {
            "success": True,
            "node_id": node_id,
            "new_type": new_type_name,
            "message": f"Changed type to '{new_type_name}'"
        }
    
    # ── Search ──
    def search_nodes(self, query: str = None, node_type: str = None,
                    layer: str = None, status: str = None) -> List[Dict[str, Any]]:
        """Search for knowledge objects."""
        nodes = self.entity_manager.search_nodes(query, None, layer, status)
        
        results = []
        for node in nodes:
            nt = self.db.query(NodeType).filter(NodeType.id == node.node_type_id).first()
            results.append({
                "id": node.id,
                "slug": node.slug,
                "title": node.title,
                "type": nt.name if nt else "unknown",
                "type_display": nt.display_name if nt else "Unknown",
                "layer": node.layer,
                "status": node.status,
                "completeness_percent": node.completeness_percent,
                "updated_at": node.updated_at.isoformat() if node.updated_at else None
            })
        
        return results
    
    # ── Get by Type ──
    def get_nodes_by_type(self, node_type_name: str) -> List[Dict[str, Any]]:
        """Get all nodes of a specific type."""
        nodes = self.entity_manager.get_nodes_by_type(node_type_name)
        
        results = []
        for node in nodes:
            nt = self.db.query(NodeType).filter(NodeType.id == node.node_type_id).first()
            results.append({
                "id": node.id,
                "slug": node.slug,
                "title": node.title,
                "type": nt.name if nt else "unknown",
                "type_display": nt.display_name if nt else "Unknown",
                "layer": node.layer,
                "status": node.status,
                "completeness_percent": node.completeness_percent,
                "updated_at": node.updated_at.isoformat() if node.updated_at else None
            })
        
        return results
    
    # ── Get Node Types ──
    def get_node_types(self) -> List[Dict[str, Any]]:
        """Get all available node types."""
        types = self.db.query(NodeType).filter(
            NodeType.workspace_id == self.workspace_id,
            NodeType.is_archived == False
        ).all()
        
        return [
            {
                "id": t.id,
                "name": t.name,
                "display_name": t.display_name,
                "icon": t.icon,
                "color": t.color,
                "description": t.description,
                "is_system": t.is_system
            }
            for t in types
        ]
