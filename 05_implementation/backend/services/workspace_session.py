"""
Workspace Session Manager for Sage v4.
Manages working sessions: save, restore, and auto-restore context.
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from models_v4 import KnowledgeNode, Asset, Workspace

# Session file path
SESSION_FILE = "workspace_session.json"

class WorkspaceSessionManager:
    """Manages workspace working sessions."""
    
    def __init__(self, db: Session, workspace_id: str, session_file: str = SESSION_FILE):
        self.db = db
        self.workspace_id = workspace_id
        self.session_file = session_file
    
    def save_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save current working session."""
        session = {
            "workspace_id": self.workspace_id,
            "last_active": datetime.utcnow().isoformat(),
            "data": session_data,
        }
        
        # Write to file
        with open(self.session_file, "w") as f:
            json.dump(session, f, indent=2)
        
        return session
    
    def load_session(self) -> Optional[Dict[str, Any]]:
        """Load last working session if it exists."""
        if not os.path.exists(self.session_file):
            return None
        
        with open(self.session_file, "r") as f:
            return json.load(f)
    
    def generate_session_from_graph(self, open_node_ids: List[str] = None) -> Dict[str, Any]:
        """Auto-generate session from knowledge graph state."""
        # Get workspace
        workspace = self.db.query(Workspace).filter(
            Workspace.id == self.workspace_id
        ).first()
        
        # Active projects
        from models_v4 import NodeType
        project_type = self.db.query(NodeType).filter(
            NodeType.workspace_id == self.workspace_id,
            NodeType.name == "project"
        ).first()
        
        active_projects = []
        if project_type:
            projects = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == self.workspace_id,
                KnowledgeNode.node_type_id == project_type.id,
                KnowledgeNode.is_archived == False
            ).order_by(KnowledgeNode.updated_at.desc()).limit(3).all()
            
            active_projects = [{"id": p.id, "title": p.title, "slug": p.slug} for p in projects]
        
        # Open nodes (if provided, else recent nodes)
        open_nodes = []
        if open_node_ids:
            nodes = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.id.in_(open_node_ids),
                KnowledgeNode.is_archived == False
            ).all()
            open_nodes = [{"id": n.id, "title": n.title, "type": n.node_type.name if n.node_type else "unknown"} for n in nodes]
        else:
            # Recent nodes
            nodes = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == self.workspace_id,
                KnowledgeNode.is_archived == False
            ).order_by(KnowledgeNode.updated_at.desc()).limit(5).all()
            open_nodes = [{"id": n.id, "title": n.title, "type": n.node_type.name if n.node_type else "unknown"} for n in nodes]
        
        # Recent assets
        recent_assets = self.db.query(Asset).filter(
            Asset.workspace_id == self.workspace_id
        ).order_by(Asset.uploaded_at.desc()).limit(5).all()
        
        # Open questions
        question_type = self.db.query(NodeType).filter(
            NodeType.workspace_id == self.workspace_id,
            NodeType.name == "question"
        ).first()
        
        open_questions = []
        if question_type:
            questions = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == self.workspace_id,
                KnowledgeNode.node_type_id == question_type.id,
                KnowledgeNode.is_archived == False
            ).order_by(KnowledgeNode.updated_at.desc()).limit(5).all()
            
            open_questions = [{"id": q.id, "title": q.title} for q in questions]
        
        # Recent decisions
        decision_type = self.db.query(NodeType).filter(
            NodeType.workspace_id == self.workspace_id,
            NodeType.name == "decision"
        ).first()
        
        recent_decisions = []
        if decision_type:
            decisions = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == self.workspace_id,
                KnowledgeNode.node_type_id == decision_type.id,
                KnowledgeNode.is_archived == False
            ).order_by(KnowledgeNode.created_at.desc()).limit(5).all()
            
            recent_decisions = [{"id": d.id, "title": d.title} for d in decisions]
        
        # Tasks
        task_type = self.db.query(NodeType).filter(
            NodeType.workspace_id == self.workspace_id,
            NodeType.name == "task"
        ).first()
        
        next_tasks = []
        if task_type:
            tasks = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == self.workspace_id,
                KnowledgeNode.node_type_id == task_type.id,
                KnowledgeNode.is_archived == False
            ).order_by(KnowledgeNode.updated_at.desc()).limit(5).all()
            
            next_tasks = [{"id": t.id, "title": t.title} for t in tasks]
        
        session = {
            "workspace": workspace.name if workspace else "Unknown",
            "project": active_projects[0] if active_projects else None,
            "goal": None,  # Would come from state snapshot
            "open_nodes": open_nodes,
            "recent_assets": [{"id": a.id, "filename": a.original_filename, "type": a.asset_type} for a in recent_assets],
            "open_questions": open_questions,
            "recent_decisions": recent_decisions,
            "next_tasks": next_tasks,
            "blocked_by": [],
            "last_active": datetime.utcnow().isoformat(),
        }
        
        return session
    
    def get_new_since_last_session(self) -> Dict[str, List[Dict]]:
        """Get new items since last session."""
        last_session = self.load_session()
        if not last_session:
            return {}
        
        last_active = datetime.fromisoformat(last_session["last_active"])
        
        # New nodes
        new_nodes = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == self.workspace_id,
            KnowledgeNode.created_at > last_active,
            KnowledgeNode.is_archived == False
        ).order_by(KnowledgeNode.created_at.desc()).limit(20).all()
        
        # New assets
        new_assets = self.db.query(Asset).filter(
            Asset.workspace_id == self.workspace_id,
            Asset.uploaded_at > last_active
        ).order_by(Asset.uploaded_at.desc()).limit(10).all()
        
        return {
            "new_nodes": [{"id": n.id, "title": n.title, "type": n.node_type.name if n.node_type else "unknown"} for n in new_nodes],
            "new_assets": [{"id": a.id, "filename": a.original_filename} for a in new_assets],
            "count": len(new_nodes) + len(new_assets)
        }
    
    def get_current_session(self) -> Dict[str, Any]:
        """Get or create current session."""
        session = self.load_session()
        if session:
            return session
        
        # Create new session from graph state
        return self.generate_session_from_graph()

