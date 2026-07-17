"""
Timeline event engine for tracking temporal events.
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, List
from models_v4 import TimelineEvent, KnowledgeNode
from core.storage.repository import Repository
import datetime

class TimelineEngine:
    """Manages TimelineEvent entities."""
    
    def __init__(self, db: Session, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
        self.repo = Repository(db, TimelineEvent, workspace_id)
    
    def create_event(self, title: str, event_date: datetime.datetime,
                     node_id: str = None, description: str = None,
                     participants: list = None, related_nodes: list = None,
                     importance: str = "medium", location: str = None,
                     evidence: list = None, source_type: str = "manual") -> TimelineEvent:
        """Create a new timeline event."""
        data = {
            'title': title,
            'event_date': event_date,
            'node_id': node_id,
            'description': description,
            'participants': participants or [],
            'related_nodes': related_nodes or [],
            'importance': importance,
            'location': location,
            'evidence': evidence or [],
            'source_type': source_type
        }
        return self.repo.create(data)
    
    def get_events_for_node(self, node_id: str, limit: int = 50) -> List[TimelineEvent]:
        """Get timeline events for a node."""
        return self.db.query(TimelineEvent).filter(
            TimelineEvent.workspace_id == self.workspace_id,
            TimelineEvent.node_id == node_id,
            TimelineEvent.is_archived == False
        ).order_by(TimelineEvent.event_date.desc()).limit(limit).all()
    
    def get_events_in_range(self, start_date: datetime.datetime,
                           end_date: datetime.datetime) -> List[TimelineEvent]:
        """Get events within a date range."""
        return self.db.query(TimelineEvent).filter(
            TimelineEvent.workspace_id == self.workspace_id,
            TimelineEvent.event_date >= start_date,
            TimelineEvent.event_date <= end_date,
            TimelineEvent.is_archived == False
        ).order_by(TimelineEvent.event_date.desc()).all()
    
    def get_events_by_importance(self, importance: str = "high") -> List[TimelineEvent]:
        """Get events by importance level."""
        return self.db.query(TimelineEvent).filter(
            TimelineEvent.workspace_id == self.workspace_id,
            TimelineEvent.importance == importance,
            TimelineEvent.is_archived == False
        ).order_by(TimelineEvent.event_date.desc()).all()
    
    def reconstruct_timeline(self, node_ids: List[str] = None,
                            start_date: datetime.datetime = None,
                            end_date: datetime.datetime = None) -> List[Dict]:
        """Reconstruct a timeline from events.
        
        Returns chronological list of events with context.
        """
        query = self.db.query(TimelineEvent).filter(
            TimelineEvent.workspace_id == self.workspace_id,
            TimelineEvent.is_archived == False
        )
        
        if node_ids:
            query = query.filter(TimelineEvent.node_id.in_(node_ids))
        
        if start_date:
            query = query.filter(TimelineEvent.event_date >= start_date)
        if end_date:
            query = query.filter(TimelineEvent.event_date <= end_date)
        
        events = query.order_by(TimelineEvent.event_date.asc()).all()
        
        timeline = []
        for event in events:
            node = None
            if event.node_id:
                node = self.db.query(KnowledgeNode).filter(
                    KnowledgeNode.id == event.node_id
                ).first()
            
            timeline.append({
                'id': event.id,
                'title': event.title,
                'date': event.event_date.isoformat() if event.event_date else None,
                'end_date': event.end_date.isoformat() if event.end_date else None,
                'description': event.description,
                'importance': event.importance,
                'location': event.location,
                'node': {
                    'id': node.id,
                    'title': node.title,
                    'slug': node.slug
                } if node else None
            })
        
        return timeline
