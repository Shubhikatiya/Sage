"""
State snapshot engine for tracking node state over time.
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, List
from models_v4 import StateSnapshot, KnowledgeNode
from core.storage.repository import Repository
import datetime

class StateEngine:
    """Manages StateSnapshot entities for time-series state tracking."""
    
    def __init__(self, db: Session, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
        self.repo = Repository(db, StateSnapshot, workspace_id)
    
    def create_snapshot(self, node_id: str, goals: list = None, progress: str = None,
                       risks: list = None, priorities: list = None,
                       questions: list = None, health_score: int = None,
                       summary: str = None, metrics: dict = None,
                       source_type: str = "manual", created_by: str = "user") -> StateSnapshot:
        """Create a new state snapshot for a node."""
        data = {
            'node_id': node_id,
            'goals': goals or [],
            'progress': progress,
            'risks': risks or [],
            'priorities': priorities or [],
            'questions': questions or [],
            'health_score': health_score,
            'summary': summary,
            'metrics': metrics or {},
            'source_type': source_type,
            'created_by': created_by
        }
        return self.repo.create(data)
    
    def get_snapshots_for_node(self, node_id: str, limit: int = 10) -> List[StateSnapshot]:
        """Get state snapshots for a node, newest first."""
        return self.db.query(StateSnapshot).filter(
            StateSnapshot.workspace_id == self.workspace_id,
            StateSnapshot.node_id == node_id,
            StateSnapshot.is_archived == False
        ).order_by(StateSnapshot.snapshot_date.desc()).limit(limit).all()
    
    def get_latest_snapshot(self, node_id: str) -> Optional[StateSnapshot]:
        """Get the most recent snapshot for a node."""
        return self.db.query(StateSnapshot).filter(
            StateSnapshot.workspace_id == self.workspace_id,
            StateSnapshot.node_id == node_id,
            StateSnapshot.is_archived == False
        ).order_by(StateSnapshot.snapshot_date.desc()).first()
    
    def compare_snapshots(self, node_id: str, snapshot_id_1: str, snapshot_id_2: str) -> Dict[str, any]:
        """Compare two snapshots and show what changed."""
        snap1 = self.repo.get_by_id(snapshot_id_1)
        snap2 = self.repo.get_by_id(snapshot_id_2)
        
        if not snap1 or not snap2:
            return None
        
        changes = {}
        
        fields = ['goals', 'progress', 'risks', 'priorities', 'questions', 'health_score', 'summary']
        for field in fields:
            old_val = getattr(snap1, field)
            new_val = getattr(snap2, field)
            if old_val != new_val:
                changes[field] = {
                    'from': old_val,
                    'to': new_val
                }
        
        return changes
    
    def get_state_trend(self, node_id: str, metric_key: str, periods: int = 5) -> List[Dict]:
        """Get trend data for a specific metric over time."""
        snapshots = self.get_snapshots_for_node(node_id, limit=periods)
        
        trend = []
        for snap in snapshots:
            value = None
            if metric_key == 'health_score':
                value = snap.health_score
            elif snap.metrics and metric_key in snap.metrics:
                value = snap.metrics[metric_key]
            
            trend.append({
                'date': snap.snapshot_date.isoformat() if snap.snapshot_date else None,
                'value': value,
                'summary': snap.summary
            })
        
        return trend
