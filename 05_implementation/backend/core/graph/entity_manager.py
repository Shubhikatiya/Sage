"""
KnowledgeNode lifecycle manager.
Handles node creation, updates, versioning, and Identity Card generation.
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, List, Any
from models_v4 import KnowledgeNode, NodeType, Version
from core.storage.repository import Repository
import datetime
import re

def slugify(title: str) -> str:
    """Convert a title to a URL-friendly slug."""
    slug = re.sub(r'[^\w\s-]', '', title.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')

class EntityManager:
    """Manages KnowledgeNode entities with versioning and Identity Card support."""
    
    def __init__(self, db: Session, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
        self.repo = Repository(db, KnowledgeNode, workspace_id)
    
    def create_node(self, node_type_id: str, title: str, content: str = "", 
                   layer: str = None, status: str = "draft", 
                   source_type: str = "manual", **kwargs) -> KnowledgeNode:
        """Create a new knowledge node with automatic slug generation."""
        slug = slugify(title)
        
        # Ensure unique slug by appending number if needed
        existing = self.repo.get_by_slug(slug)
        counter = 1
        original_slug = slug
        while existing:
            slug = f"{original_slug}-{counter}"
            existing = self.repo.get_by_slug(slug)
            counter += 1
        
        data = {
            'node_type_id': node_type_id,
            'title': title,
            'content': content,
            'slug': slug,
            'layer': layer,
            'status': status,
            'source_type': source_type,
            **kwargs
        }
        
        node = self.repo.create(data)
        
        # Create initial version record
        version = Version(
            workspace_id=self.workspace_id,
            node_id=node.id,
            version_number=1,
            change_type="created",
            change_summary=f"Created {title}",
            new_values=data,
            changed_by="user"
        )
        self.db.add(version)
        self.db.commit()
        
        return node
    
    def update_node(self, node_id: str, data: Dict[str, Any], changed_by: str = "user") -> Optional[KnowledgeNode]:
        """Update a node and create a version record."""
        node = self.repo.get_by_id(node_id)
        if not node:
            return None
        
        # Store old values for version
        old_values = {
            'title': node.title,
            'content': node.content,
            'status': node.status,
            'layer': node.layer
        }
        
        # Update
        result = self.repo.update(node_id, data)
        
        # Get latest version number
        latest_version = self.db.query(Version).filter(
            Version.node_id == node_id
        ).order_by(Version.version_number.desc()).first()
        
        version_number = (latest_version.version_number + 1) if latest_version else 1
        
        # Create version record
        version = Version(
            workspace_id=self.workspace_id,
            node_id=node_id,
            version_number=version_number,
            change_type="updated",
            change_summary=data.get('change_summary', 'Updated node'),
            old_values=old_values,
            new_values=data,
            changed_by=changed_by
        )
        self.db.add(version)
        self.db.commit()
        
        return result
    
    def get_node_identity_card(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Generate an Identity Card for any node."""
        node = self.repo.get_by_id(node_id)
        if not node:
            return None
        
        # Get node type info
        node_type = self.db.query(NodeType).filter(NodeType.id == node.node_type_id).first()
        
        # Get related nodes
        outgoing = []
        incoming = []
        if hasattr(node, 'outgoing_edges'):
            outgoing = [edge.target for edge in node.outgoing_edges if hasattr(edge, 'target') and edge.target and not edge.target.is_archived]
        if hasattr(node, 'incoming_edges'):
            incoming = [edge.source for edge in node.incoming_edges if hasattr(edge, 'source') and edge.source and not edge.source.is_archived]
        
        # Get latest state snapshot
        latest_snapshot = None
        if hasattr(node, 'snapshots') and node.snapshots:
            latest_snapshot = max(node.snapshots, key=lambda s: s.snapshot_date, default=None)
        
        # Get timeline events
        timeline_events = []
        if hasattr(node, 'timeline_events'):
            timeline_events = sorted(node.timeline_events, key=lambda e: e.event_date, reverse=True)[:10]
        
        # Get versions
        versions = []
        if hasattr(node, 'versions'):
            versions = sorted(node.versions, key=lambda v: v.version_number, reverse=True)[:5]
        
        return {
            'identity': {
                'uuid': node.id,
                'slug': node.slug,
                'type': node_type.name if node_type else 'unknown',
                'type_display': node_type.display_name if node_type else 'Unknown',
                'title': node.title,
            },
            'overview': {
                'summary': node.ai_summary or (node.content[:200] if node.content else ''),
                'description': node.content or '',
            },
            'context': {
                'current_state': node.status,
                'layer': node.layer,
                'priority': node.priority,
                'timeline_events': [
                    {'date': e.event_date.isoformat() if e.event_date else None, 'title': e.title, 'importance': e.importance}
                    for e in timeline_events
                ],
                'relationships': {
                    'outgoing': [{'id': n.id, 'title': n.title, 'slug': n.slug} for n in outgoing[:5]],
                    'incoming': [{'id': n.id, 'title': n.title, 'slug': n.slug} for n in incoming[:5]],
                }
            },
            'knowledge': {
                'insights': [],
                'research': [],
                'evidence': [
                    {'id': e.id, 'title': e.title, 'type': e.evidence_type}
                    for e in (node.evidence_items or [])[:5]
                ],
                'assets': [],
            },
            'activity': {
                'recent_changes': [
                    {'version': v.version_number, 'type': v.change_type, 'summary': v.change_summary, 'date': v.created_at.isoformat() if v.created_at else None}
                    for v in versions
                ],
                'state_history': {
                    'latest_snapshot': {
                        'date': latest_snapshot.snapshot_date.isoformat() if latest_snapshot.snapshot_date else None,
                        'summary': latest_snapshot.summary,
                        'health_score': latest_snapshot.health_score
                    } if latest_snapshot else None
                }
            },
            'ai': {
                'summary': node.ai_short_summary or node.ai_summary,
                'suggestions': node.ai_suggested_questions or [],
                'missing_information': node.ai_missing_information,
                'questions': node.ai_suggested_questions or [],
                'next_actions': node.ai_next_actions or [],
            },
            'metrics': {
                'completeness': node.completeness_percent,
                'completeness_breakdown': node.completeness or {},
                'importance': node.ai_importance_score,
                'confidence': node.confidence,
                'last_updated': node.updated_at.isoformat() if node.updated_at else None,
            }
        }
    
    def search_nodes(self, query: str = None, node_type_id: str = None, 
                    layer: str = None, status: str = None) -> List[KnowledgeNode]:
        """Search nodes with filters."""
        q = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == self.workspace_id,
            KnowledgeNode.is_archived == False,
            KnowledgeNode.source_type.not_in(["extracted_entity", "asset_extraction"])
        )
        
        if query:
            q = q.filter(
                KnowledgeNode.title.ilike(f"%{query}%") |
                KnowledgeNode.content.ilike(f"%{query}%") |
                KnowledgeNode.ai_summary.ilike(f"%{query}%")
            )
        
        if node_type_id:
            q = q.filter(KnowledgeNode.node_type_id == node_type_id)
        
        if layer:
            q = q.filter(KnowledgeNode.layer == layer)
        
        if status:
            q = q.filter(KnowledgeNode.status == status)
        
        return q.order_by(KnowledgeNode.updated_at.desc()).all()
    
    def get_nodes_by_type(self, node_type_name: str) -> List[KnowledgeNode]:
        """Get all nodes of a specific type."""
        node_type = self.db.query(NodeType).filter(
            NodeType.workspace_id == self.workspace_id,
            NodeType.name == node_type_name.lower(),
            NodeType.is_archived == False
        ).first()
        
        if not node_type:
            return []
        
        return self.db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == self.workspace_id,
            KnowledgeNode.node_type_id == node_type.id,
            KnowledgeNode.is_archived == False,
            KnowledgeNode.source_type.not_in(["extracted_entity", "asset_extraction"])
        ).order_by(KnowledgeNode.updated_at.desc()).all()
