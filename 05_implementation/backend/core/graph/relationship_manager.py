"""
Relationship manager for the Knowledge Graph.
Handles edge creation, traversal, and relationship queries.
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, List, Any
from models_v4 import KnowledgeEdge, KnowledgeNode, RelationshipType
from core.storage.repository import Repository
import datetime

class RelationshipManager:
    """Manages KnowledgeEdge entities (relationships between nodes)."""
    
    def __init__(self, db: Session, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
        self.repo = Repository(db, KnowledgeEdge, workspace_id)
    
    def create_relationship(self, source_id: str, target_id: str, 
                           relationship_type_id: str, evidence: str = None,
                           confidence: float = 1.0, weight: float = 1.0,
                           notes: str = None) -> KnowledgeEdge:
        """Create a new relationship (edge) between two nodes."""
        data = {
            'source_id': source_id,
            'target_id': target_id,
            'relationship_type_id': relationship_type_id,
            'evidence': evidence,
            'confidence': confidence,
            'weight': weight,
            'notes': notes
        }
        return self.repo.create(data)
    
    def get_relationships_for_node(self, node_id: str, direction: str = "both") -> Dict[str, List[Any]]:
        """Get all relationships for a node.
        
        Args:
            node_id: The node ID
            direction: 'outgoing', 'incoming', or 'both'
        
        Returns:
            Dict with 'outgoing' and 'incoming' lists of (edge, related_node) tuples
        """
        result = {'outgoing': [], 'incoming': []}
        
        if direction in ('outgoing', 'both'):
            edges = self.db.query(KnowledgeEdge).filter(
                KnowledgeEdge.workspace_id == self.workspace_id,
                KnowledgeEdge.source_id == node_id,
                KnowledgeEdge.is_archived == False
            ).all()
            
            for edge in edges:
                target = self.db.query(KnowledgeNode).filter(
                    KnowledgeNode.id == edge.target_id,
                    KnowledgeNode.is_archived == False
                ).first()
                if target:
                    rel_type = self.db.query(RelationshipType).filter(
                        RelationshipType.id == edge.relationship_type_id
                    ).first()
                    result['outgoing'].append({
                        'edge_id': edge.id,
                        'relationship_type': rel_type.name if rel_type else 'unknown',
                        'relationship_display': rel_type.display_name if rel_type else 'Unknown',
                        'target': {
                            'id': target.id,
                            'title': target.title,
                            'slug': target.slug,
                            'type': target.node_type.name if target.node_type else 'unknown'
                        },
                        'confidence': edge.confidence,
                        'weight': edge.weight,
                        'evidence': edge.evidence,
                        'notes': edge.notes
                    })
        
        if direction in ('incoming', 'both'):
            edges = self.db.query(KnowledgeEdge).filter(
                KnowledgeEdge.workspace_id == self.workspace_id,
                KnowledgeEdge.target_id == node_id,
                KnowledgeEdge.is_archived == False
            ).all()
            
            for edge in edges:
                source = self.db.query(KnowledgeNode).filter(
                    KnowledgeNode.id == edge.source_id,
                    KnowledgeNode.is_archived == False
                ).first()
                if source:
                    rel_type = self.db.query(RelationshipType).filter(
                        RelationshipType.id == edge.relationship_type_id
                    ).first()
                    result['incoming'].append({
                        'edge_id': edge.id,
                        'relationship_type': rel_type.name if rel_type else 'unknown',
                        'relationship_display': rel_type.display_name if rel_type else 'Unknown',
                        'source': {
                            'id': source.id,
                            'title': source.title,
                            'slug': source.slug,
                            'type': source.node_type.name if source.node_type else 'unknown'
                        },
                        'confidence': edge.confidence,
                        'weight': edge.weight,
                        'evidence': edge.evidence,
                        'notes': edge.notes
                    })
        
        return result
    
    def get_related_nodes(self, node_id: str, relationship_type_name: str = None,
                         max_depth: int = 1) -> List[Dict[str, Any]]:
        """Get all nodes related to a given node through graph traversal.
        
        Args:
            node_id: Starting node ID
            relationship_type_name: Optional filter by relationship type
            max_depth: How many hops to traverse (1 = direct neighbors)
        
        Returns:
            List of related nodes with relationship info
        """
        visited = set()
        results = []
        queue = [(node_id, 0)]
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if current_id in visited or depth > max_depth:
                continue
            
            visited.add(current_id)
            
            # Get outgoing edges
            edges = self.db.query(KnowledgeEdge).filter(
                KnowledgeEdge.workspace_id == self.workspace_id,
                KnowledgeEdge.source_id == current_id,
                KnowledgeEdge.is_archived == False
            )
            
            if relationship_type_name:
                rel_type = self.db.query(RelationshipType).filter(
                    RelationshipType.workspace_id == self.workspace_id,
                    RelationshipType.name == relationship_type_name.upper(),
                    RelationshipType.is_archived == False
                ).first()
                if rel_type:
                    edges = edges.filter(KnowledgeEdge.relationship_type_id == rel_type.id)
            
            for edge in edges.all():
                target = self.db.query(KnowledgeNode).filter(
                    KnowledgeNode.id == edge.target_id,
                    KnowledgeNode.is_archived == False
                ).first()
                
                if target and target.id not in visited:
                    rel_type = self.db.query(RelationshipType).filter(
                        RelationshipType.id == edge.relationship_type_id
                    ).first()
                    
                    results.append({
                        'node': {
                            'id': target.id,
                            'title': target.title,
                            'slug': target.slug,
                            'type': target.node_type.display_name if target.node_type else 'Unknown'
                        },
                        'relationship': rel_type.name if rel_type else 'unknown',
                        'depth': depth + 1,
                        'confidence': edge.confidence
                    })
                    
                    if depth + 1 < max_depth:
                        queue.append((target.id, depth + 1))
        
        return results
    
    def delete_relationship(self, edge_id: str, deleted_by: str = "user") -> bool:
        """Soft delete a relationship."""
        return self.repo.soft_delete(edge_id, deleted_by)
    
    def find_path(self, source_id: str, target_id: str, max_depth: int = 5) -> Optional[List[Dict[str, Any]]]:
        """Find a path between two nodes using BFS.
        
        Returns:
            List of edges forming the path, or None if no path found.
        """
        if source_id == target_id:
            return []
        
        visited = {source_id}
        queue = [(source_id, [])]
        
        while queue:
            current_id, path = queue.pop(0)
            
            if len(path) >= max_depth:
                continue
            
            edges = self.db.query(KnowledgeEdge).filter(
                KnowledgeEdge.workspace_id == self.workspace_id,
                KnowledgeEdge.source_id == current_id,
                KnowledgeEdge.is_archived == False
            ).all()
            
            for edge in edges:
                if edge.target_id == target_id:
                    # Found the target
                    rel_type = self.db.query(RelationshipType).filter(
                        RelationshipType.id == edge.relationship_type_id
                    ).first()
                    
                    final_path = path + [{
                        'source_id': current_id,
                        'target_id': edge.target_id,
                        'relationship': rel_type.name if rel_type else 'unknown',
                        'confidence': edge.confidence
                    }]
                    return final_path
                
                if edge.target_id not in visited:
                    visited.add(edge.target_id)
                    
                    rel_type = self.db.query(RelationshipType).filter(
                        RelationshipType.id == edge.relationship_type_id
                    ).first()
                    
                    queue.append((edge.target_id, path + [{
                        'source_id': current_id,
                        'target_id': edge.target_id,
                        'relationship': rel_type.name if rel_type else 'unknown',
                        'confidence': edge.confidence
                    }]))
        
        return None
