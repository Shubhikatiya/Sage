"""
Graph Operations Service for Sage v4.
High-level operations for graph traversal, relationships, and analysis.
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, List, Any
from models_v4 import KnowledgeNode, KnowledgeEdge, NodeType, RelationshipType
from core.graph.relationship_manager import RelationshipManager
from core.storage.repository import Repository

class GraphService:
    """Provides Graph Operations for the Capability Layer."""
    
    def __init__(self, db: Session, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
        self.relationship_manager = RelationshipManager(db, workspace_id)
    
    # ── Create Relationship ──
    def create_relationship(self, source_id: str, target_id: str,
                           relationship_type_name: str, evidence: str = None,
                           confidence: float = 1.0, weight: float = 1.0,
                           notes: str = None) -> Dict[str, Any]:
        """Create a relationship between two nodes."""
        # Validate nodes exist
        source = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.id == source_id,
            KnowledgeNode.workspace_id == self.workspace_id,
            KnowledgeNode.is_archived == False
        ).first()
        
        target = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.id == target_id,
            KnowledgeNode.workspace_id == self.workspace_id,
            KnowledgeNode.is_archived == False
        ).first()
        
        if not source or not target:
            missing = []
            if not source: missing.append(source_id)
            if not target: missing.append(target_id)
            return {"success": False, "error": f"Nodes not found: {missing}"}
        
        # Find relationship type
        rel_type = self.db.query(RelationshipType).filter(
            RelationshipType.workspace_id == self.workspace_id,
            RelationshipType.name == relationship_type_name.upper(),
            RelationshipType.is_archived == False
        ).first()
        
        if not rel_type:
            return {"success": False, "error": f"Relationship type '{relationship_type_name}' not found"}
        
        edge = self.relationship_manager.create_relationship(
            source_id=source_id,
            target_id=target_id,
            relationship_type_id=rel_type.id,
            evidence=evidence,
            confidence=confidence,
            weight=weight,
            notes=notes
        )
        
        return {
            "success": True,
            "relationship": {
                "id": edge.id,
                "source_id": source_id,
                "source_title": source.title,
                "target_id": target_id,
                "target_title": target.title,
                "type": rel_type.name,
                "confidence": confidence
            }
        }
    
    # ── Remove Relationship ──
    def remove_relationship(self, edge_id: str, deleted_by: str = "user") -> Dict[str, Any]:
        """Remove a relationship (soft delete)."""
        result = self.relationship_manager.delete_relationship(edge_id, deleted_by)
        
        if not result:
            return {"success": False, "error": f"Relationship '{edge_id}' not found"}
        
        return {"success": True, "message": f"Relationship '{edge_id}' removed"}
    
    # ── Traverse Neighbors ──
    def get_neighbors(self, node_id: str, direction: str = "both",
                     relationship_type: str = None) -> Dict[str, Any]:
        """Get all neighbors of a node."""
        node = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.id == node_id,
            KnowledgeNode.workspace_id == self.workspace_id,
            KnowledgeNode.is_archived == False
        ).first()
        
        if not node:
            return {"success": False, "error": f"Node '{node_id}' not found"}
        
        relationships = self.relationship_manager.get_relationships_for_node(node_id, direction)
        
        return {
            "success": True,
            "node_id": node_id,
            "node_title": node.title,
            "outgoing": relationships.get("outgoing", []),
            "incoming": relationships.get("incoming", []),
            "total_connections": len(relationships.get("outgoing", [])) + len(relationships.get("incoming", []))
        }
    
    # ── Find Path ──
    def find_path(self, source_id: str, target_id: str, max_depth: int = 5) -> Dict[str, Any]:
        """Find shortest path between two nodes."""
        path = self.relationship_manager.find_path(source_id, target_id, max_depth)
        
        if path is None:
            return {
                "success": True,
                "path_exists": False,
                "message": "No path found between nodes"
            }
        
        # Get node details for each step
        path_nodes = []
        for step in path:
            source = self.db.query(KnowledgeNode).filter(KnowledgeNode.id == step["source_id"]).first()
            target = self.db.query(KnowledgeNode).filter(KnowledgeNode.id == step["target_id"]).first()
            
            path_nodes.append({
                "source": {"id": step["source_id"], "title": source.title if source else "Unknown"},
                "target": {"id": step["target_id"], "title": target.title if target else "Unknown"},
                "relationship": step["relationship"],
                "confidence": step["confidence"]
            })
        
        return {
            "success": True,
            "path_exists": True,
            "path_length": len(path),
            "path": path_nodes
        }
    
    # ── Build Subgraph ──
    def build_subgraph(self, node_ids: List[str], depth: int = 1) -> Dict[str, Any]:
        """Extract a subgraph around specified nodes."""
        nodes = {}
        edges = []
        
        for node_id in node_ids:
            node = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.id == node_id,
                KnowledgeNode.workspace_id == self.workspace_id,
                KnowledgeNode.is_archived == False
            ).first()
            
            if node:
                nt = self.db.query(NodeType).filter(NodeType.id == node.node_type_id).first()
                nodes[node_id] = {
                    "id": node.id,
                    "title": node.title,
                    "slug": node.slug,
                    "type": nt.name if nt else "unknown",
                    "type_display": nt.display_name if nt else "Unknown"
                }
                
                # Get neighbors within depth
                related = self.relationship_manager.get_related_nodes(node_id, max_depth=depth)
                for rel in related:
                    if rel["node"]["id"] not in nodes:
                        nodes[rel["node"]["id"]] = rel["node"]
        
        return {
            "success": True,
            "node_count": len(nodes),
            "nodes": list(nodes.values()),
            "edges": edges
        }
    
    # ── Related Nodes ──
    def get_related_nodes(self, node_id: str, relationship_type: str = None,
                         max_depth: int = 1) -> Dict[str, Any]:
        """Get nodes related to a given node."""
        node = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.id == node_id,
            KnowledgeNode.workspace_id == self.workspace_id,
            KnowledgeNode.is_archived == False
        ).first()
        
        if not node:
            return {"success": False, "error": f"Node '{node_id}' not found"}
        
        related = self.relationship_manager.get_related_nodes(node_id, relationship_type, max_depth)
        
        return {
            "success": True,
            "node_id": node_id,
            "node_title": node.title,
            "related_nodes": related,
            "total_related": len(related)
        }
    
    # ── Backlinks ──
    def get_backlinks(self, node_id: str) -> Dict[str, Any]:
        """Get all nodes that point to this node."""
        relationships = self.relationship_manager.get_relationships_for_node(node_id, "incoming")
        
        return {
            "success": True,
            "node_id": node_id,
            "backlinks": relationships.get("incoming", []),
            "total_backlinks": len(relationships.get("incoming", []))
        }
    
    # ── Forward Links ──
    def get_forward_links(self, node_id: str) -> Dict[str, Any]:
        """Get all nodes that this node points to."""
        relationships = self.relationship_manager.get_relationships_for_node(node_id, "outgoing")
        
        return {
            "success": True,
            "node_id": node_id,
            "forward_links": relationships.get("outgoing", []),
            "total_forward_links": len(relationships.get("outgoing", []))
        }
    
    # ── Degree Analysis ──
    def get_degree_analysis(self, node_id: str) -> Dict[str, Any]:
        """Analyze connection degrees for a node."""
        outgoing = self.relationship_manager.get_relationships_for_node(node_id, "outgoing")
        incoming = self.relationship_manager.get_relationships_for_node(node_id, "incoming")
        
        out_degree = len(outgoing.get("outgoing", []))
        in_degree = len(incoming.get("incoming", []))
        
        return {
            "success": True,
            "node_id": node_id,
            "out_degree": out_degree,
            "in_degree": in_degree,
            "total_degree": out_degree + in_degree,
            "is_source": out_degree > 0,
            "is_target": in_degree > 0,
            "is_hub": out_degree > 3 and in_degree > 3
        }
    
    # ── Dependency Analysis ──
    def get_dependencies(self, node_id: str) -> Dict[str, Any]:
        """Find what depends on this node (nodes that have edges pointing TO this node)."""
        return self.get_backlinks(node_id)
    
    # ── Impact Analysis ──
    def get_impact(self, node_id: str) -> Dict[str, Any]:
        """Find what would be affected if this node changed (nodes this node points to)."""
        return self.get_forward_links(node_id)
    
    # ── Query Graph (Natural Language) ──
    def query_graph(self, query: str) -> Dict[str, Any]:
        """Execute a natural language query against the graph.
        
        For now, this maps to simple graph traversals. Later, LLM will translate queries.
        """
        query_lower = query.lower()
        
        # Simple pattern matching for MVP
        if "influenced" in query_lower or "influences" in query_lower:
            # Find nodes that are targets of INFLUENCES edges
            rel_type = self.db.query(RelationshipType).filter(
                RelationshipType.workspace_id == self.workspace_id,
                RelationshipType.name == "INFLUENCES"
            ).first()
            
            if rel_type:
                edges = self.db.query(KnowledgeEdge).filter(
                    KnowledgeEdge.workspace_id == self.workspace_id,
                    KnowledgeEdge.relationship_type_id == rel_type.id,
                    KnowledgeEdge.is_archived == False
                ).all()
                
                results = []
                for edge in edges:
                    source = self.db.query(KnowledgeNode).filter(KnowledgeNode.id == edge.source_id).first()
                    target = self.db.query(KnowledgeNode).filter(KnowledgeNode.id == edge.target_id).first()
                    if source and target:
                        results.append({
                            "source": {"id": source.id, "title": source.title},
                            "target": {"id": target.id, "title": target.title}
                        })
                
                return {
                    "success": True,
                    "query": query,
                    "interpretation": "Nodes that influence other nodes",
                    "results": results
                }
        
        elif "depends" in query_lower:
            # Find DEPENDS_ON relationships
            rel_type = self.db.query(RelationshipType).filter(
                RelationshipType.workspace_id == self.workspace_id,
                RelationshipType.name == "DEPENDS_ON"
            ).first()
            
            if rel_type:
                edges = self.db.query(KnowledgeEdge).filter(
                    KnowledgeEdge.workspace_id == self.workspace_id,
                    KnowledgeEdge.relationship_type_id == rel_type.id,
                    KnowledgeEdge.is_archived == False
                ).all()
                
                results = []
                for edge in edges:
                    source = self.db.query(KnowledgeNode).filter(KnowledgeNode.id == edge.source_id).first()
                    target = self.db.query(KnowledgeNode).filter(KnowledgeNode.id == edge.target_id).first()
                    if source and target:
                        results.append({
                            "source": {"id": source.id, "title": source.title},
                            "target": {"id": target.id, "title": target.title}
                        })
                
                return {
                    "success": True,
                    "query": query,
                    "interpretation": "Dependency relationships",
                    "results": results
                }
        
        # Default: keyword search
        nodes = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == self.workspace_id,
            KnowledgeNode.is_archived == False,
            KnowledgeNode.title.ilike(f"%{query}%")
        ).all()
        
        return {
            "success": True,
            "query": query,
            "interpretation": "Keyword search",
            "results": [
                {"id": n.id, "title": n.title, "slug": n.slug}
                for n in nodes[:20]
            ]
        }
    
    # ── Get Relationship Types ──
    def get_relationship_types(self) -> List[Dict[str, Any]]:
        """Get all available relationship types."""
        types = self.db.query(RelationshipType).filter(
            RelationshipType.workspace_id == self.workspace_id,
            RelationshipType.is_archived == False
        ).all()
        
        return [
            {
                "id": t.id,
                "name": t.name,
                "display_name": t.display_name,
                "inverse_name": t.inverse_name,
                "description": t.description,
                "directional": t.directional,
                "is_system": t.is_system
            }
            for t in types
        ]
