"""
Bring Me Back Engine for Sage v4.
Generates comprehensive briefings when founder returns after time away.
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from models_v4 import (
    KnowledgeNode, KnowledgeEdge, StateSnapshot, TimelineEvent,
    Asset, Workspace, Version, NodeType
)

class BringMeBackEngine:
    """Generates 'Bring Me Back' briefings from the knowledge graph."""
    
    def __init__(self, db: Session, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
        
        # Default: look back 7 days, or since last session
        self.since_date = datetime.utcnow() - timedelta(days=7)
    
    def generate_briefing(self, user_id: str = None, 
                         since_date: datetime = None) -> Dict[str, Any]:
        """Generate a comprehensive 'Bring Me Back' briefing.
        
        Returns structured briefing with projects, knowledge, unresolved items,
        current focus, and suggested next steps — now enriched with Memory Engine.
        """
        if since_date:
            self.since_date = since_date
        
        # Get workspace
        workspace = self.db.query(Workspace).filter(
            Workspace.id == self.workspace_id
        ).first()
        
        # Gather all briefing components
        briefing = {
            "greeting": self._generate_greeting(workspace),
            "time_away": self._calculate_time_away(),
            "projects": self._get_project_status(),
            "new_knowledge": self._get_new_knowledge(),
            "unresolved": self._get_unresolved_items(),
            "current_focus": self._get_current_focus(),
            "blocked_by": self._get_blocked_items(),
            "suggested_next_steps": self._suggest_next_steps(),
            "related_context": self._get_related_context(),
            # Phase 02: Memory Engine integration
            "memory_highlights": self._get_memory_highlights(),
            "conversation_summary": self._get_conversation_summary(),
            "recent_insights": self._get_recent_insights(),
        }
        
        return briefing
    
    def _generate_greeting(self, workspace: Workspace) -> str:
        """Generate a personalized greeting."""
        hour = datetime.utcnow().hour
        if 5 <= hour < 12:
            time_greeting = "morning"
        elif 12 <= hour < 17:
            time_greeting = "afternoon"
        else:
            time_greeting = "evening"
        
        return f"Good {time_greeting}. Welcome back to {workspace.name}."
    
    def _calculate_time_away(self) -> Dict[str, Any]:
        """Calculate how long since last activity."""
        # Find most recent node update
        latest_node = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == self.workspace_id,
            KnowledgeNode.is_archived == False
        ).order_by(KnowledgeNode.updated_at.desc()).first()
        
        if not latest_node or not latest_node.updated_at:
            return {"duration": "unknown", "days": 0}
        
        days_away = (datetime.utcnow() - latest_node.updated_at).days
        
        if days_away == 0:
            duration = "today"
        elif days_away == 1:
            duration = "1 day"
        elif days_away < 7:
            duration = f"{days_away} days"
        elif days_away < 30:
            weeks = days_away // 7
            duration = f"{weeks} week{'s' if weeks > 1 else ''}"
        else:
            months = days_away // 30
            duration = f"{months} month{'s' if months > 1 else ''}"
        
        return {
            "duration": duration,
            "days": days_away,
            "last_active": latest_node.updated_at.isoformat() if latest_node.updated_at else None
        }
    
    def _get_project_status(self) -> List[Dict[str, Any]]:
        """Get status of all active projects with progress."""
        # Find project node type
        project_type = self.db.query(NodeType).filter(
            NodeType.workspace_id == self.workspace_id,
            NodeType.name == "project",
            NodeType.is_archived == False
        ).first()
        
        if not project_type:
            return []
        
        projects = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == self.workspace_id,
            KnowledgeNode.node_type_id == project_type.id,
            KnowledgeNode.is_archived == False
        ).order_by(KnowledgeNode.updated_at.desc()).all()
        
        project_status = []
        for project in projects:
            # Calculate progress delta
            previous_snapshot = self.db.query(StateSnapshot).filter(
                StateSnapshot.node_id == project.id,
                StateSnapshot.snapshot_date < self.since_date
            ).order_by(StateSnapshot.snapshot_date.desc()).first()
            
            latest_snapshot = self.db.query(StateSnapshot).filter(
                StateSnapshot.node_id == project.id
            ).order_by(StateSnapshot.snapshot_date.desc()).first()
            
            # Count new items since last visit
            new_decisions = self._count_nodes_created_since(
                project.id, "decision", self.since_date
            )
            new_insights = self._count_nodes_created_since(
                project.id, "insight", self.since_date
            )
            new_questions = self._count_nodes_created_since(
                project.id, "question", self.since_date
            )
            
            project_status.append({
                "id": project.id,
                "title": project.title,
                "slug": project.slug,
                "completeness": project.completeness_percent or 0,
                "status": project.status,
                "last_updated": project.updated_at.isoformat() if project.updated_at else None,
                "new_since_last_visit": {
                    "decisions": new_decisions,
                    "insights": new_insights,
                    "questions": new_questions,
                },
                "health_score": latest_snapshot.health_score if latest_snapshot else None,
                "previous_health": previous_snapshot.health_score if previous_snapshot else None,
            })
        
        return project_status
    
    def _get_new_knowledge(self) -> Dict[str, int]:
        """Count new knowledge items since last visit."""
        # New nodes created since
        new_nodes = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == self.workspace_id,
            KnowledgeNode.created_at >= self.since_date,
            KnowledgeNode.is_archived == False
        ).count()
        
        # New edges
        new_edges = self.db.query(KnowledgeEdge).filter(
            KnowledgeEdge.workspace_id == self.workspace_id,
            KnowledgeEdge.created_at >= self.since_date,
            KnowledgeEdge.is_archived == False
        ).count()
        
        # New assets
        new_assets = self.db.query(Asset).filter(
            Asset.workspace_id == self.workspace_id,
            Asset.uploaded_at >= self.since_date
        ).count()
        
        # New timeline events
        new_events = self.db.query(TimelineEvent).filter(
            TimelineEvent.workspace_id == self.workspace_id,
            TimelineEvent.created_at >= self.since_date
        ).count()
        
        return {
            "nodes": new_nodes,
            "relationships": new_edges,
            "assets": new_assets,
            "events": new_events,
            "total": new_nodes + new_edges + new_assets + new_events
        }
    
    def _get_unresolved_items(self) -> Dict[str, List[Dict]]:
        """Get unresolved decisions and open questions."""
        # Find open questions
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
            ).order_by(KnowledgeNode.updated_at.desc()).limit(10).all()
            
            open_questions = [
                {"id": q.id, "title": q.title, "content": q.content[:200] if q.content else ""}
                for q in questions
            ]
        
        # Find recent decisions awaiting input
        decision_type = self.db.query(NodeType).filter(
            NodeType.workspace_id == self.workspace_id,
            NodeType.name == "decision"
        ).first()
        
        recent_decisions = []
        if decision_type:
            decisions = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == self.workspace_id,
                KnowledgeNode.node_type_id == decision_type.id,
                KnowledgeNode.created_at >= self.since_date - timedelta(days=30),
                KnowledgeNode.is_archived == False
            ).order_by(KnowledgeNode.created_at.desc()).limit(5).all()
            
            recent_decisions = [
                {"id": d.id, "title": d.title}
                for d in decisions
            ]
        
        return {
            "open_questions": open_questions,
            "recent_decisions": recent_decisions,
        }
    
    def _get_current_focus(self) -> Dict[str, Any]:
        """Determine current focus based on recent activity."""
        # Most recently updated project
        project_type = self.db.query(NodeType).filter(
            NodeType.workspace_id == self.workspace_id,
            NodeType.name == "project"
        ).first()
        
        if project_type:
            focus_project = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == self.workspace_id,
                KnowledgeNode.node_type_id == project_type.id,
                KnowledgeNode.is_archived == False
            ).order_by(KnowledgeNode.updated_at.desc()).first()
            
            if focus_project:
                # Get latest snapshot for context
                latest_snapshot = self.db.query(StateSnapshot).filter(
                    StateSnapshot.node_id == focus_project.id
                ).order_by(StateSnapshot.snapshot_date.desc()).first()
                
                return {
                    "project": {
                        "id": focus_project.id,
                        "title": focus_project.title,
                        "slug": focus_project.slug,
                    },
                    "current_goal": latest_snapshot.goals[0] if latest_snapshot and latest_snapshot.goals else None,
                    "summary": latest_snapshot.summary if latest_snapshot else None,
                }
        
        return {"project": None, "current_goal": None, "summary": None}
    
    def _get_blocked_items(self) -> List[Dict[str, Any]]:
        """Find items that are blocked or stalled."""
        blocked = []
        
        # Find tasks with no progress
        task_type = self.db.query(NodeType).filter(
            NodeType.workspace_id == self.workspace_id,
            NodeType.name == "task"
        ).first()
        
        if task_type:
            old_tasks = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == self.workspace_id,
                KnowledgeNode.node_type_id == task_type.id,
                KnowledgeNode.updated_at <= self.since_date - timedelta(days=14),
                KnowledgeNode.is_archived == False
            ).limit(5).all()
            
            for task in old_tasks:
                blocked.append({
                    "id": task.id,
                    "title": task.title,
                    "type": "task",
                    "reason": "No progress in 14+ days"
                })
        
        return blocked
    
    def _suggest_next_steps(self) -> List[Dict[str, str]]:
        """Suggest next steps based on knowledge gaps and current state."""
        suggestions = []
        
        # Find projects with low completeness
        low_completeness = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == self.workspace_id,
            KnowledgeNode.completeness_percent < 50,
            KnowledgeNode.is_archived == False
        ).limit(3).all()
        
        for project in low_completeness:
            suggestions.append({
                "type": "completeness",
                "message": f"Improve {project.title} documentation ({project.completeness_percent}% complete)",
                "node_id": project.id
            })
        
        # Find nodes with no relationships
        isolated_nodes = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == self.workspace_id,
            KnowledgeNode.is_archived == False
        ).all()
        
        isolated = []
        for node in isolated_nodes:
            edge_count = self.db.query(KnowledgeEdge).filter(
                (KnowledgeEdge.source_id == node.id) | (KnowledgeEdge.target_id == node.id),
                KnowledgeEdge.is_archived == False
            ).count()
            
            if edge_count == 0:
                isolated.append(node)
        
        if isolated:
            suggestions.append({
                "type": "relationship",
                "message": f"Connect {len(isolated[:3])} isolated nodes to the knowledge graph",
                "node_ids": [n.id for n in isolated[:3]]
            })
        
        # Find open questions
        question_type = self.db.query(NodeType).filter(
            NodeType.workspace_id == self.workspace_id,
            NodeType.name == "question"
        ).first()
        
        if question_type:
            open_q_count = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == self.workspace_id,
                KnowledgeNode.node_type_id == question_type.id,
                KnowledgeNode.is_archived == False
            ).count()
            
            if open_q_count > 0:
                suggestions.append({
                    "type": "question",
                    "message": f"Address {open_q_count} open question{'s' if open_q_count > 1 else ''}",
                })
        
        return suggestions
    
    def _get_related_context(self) -> List[Dict[str, str]]:
        """Get context related to current focus."""
        context = []
        
        # Get recent decisions
        decision_type = self.db.query(NodeType).filter(
            NodeType.workspace_id == self.workspace_id,
            NodeType.name == "decision"
        ).first()
        
        if decision_type:
            recent_decisions = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == self.workspace_id,
                KnowledgeNode.node_type_id == decision_type.id,
                KnowledgeNode.is_archived == False
            ).order_by(KnowledgeNode.created_at.desc()).limit(3).all()
            
            for decision in recent_decisions:
                context.append({
                    "type": "decision",
                    "title": decision.title,
                    "node_id": decision.id
                })
        
        return context
    
    # Phase 02: Memory Engine Integration
    
    def _get_memory_highlights(self) -> List[Dict[str, Any]]:
        """Retrieve important memories from the Memory Engine."""
        try:
            from services.memory_engine import MemoryQuery, MemoryType, get_memory_store
            store = get_memory_store()
            
            query = MemoryQuery(
                query_text="important work projects decisions",
                memory_types=[MemoryType.EPISODIC, MemoryType.SEMANTIC, MemoryType.EXTRACTED_INSIGHT],
                max_results=8,
                min_score=0.3,
                recency_weight=0.4,
                importance_weight=0.4,
                relevance_weight=0.2
            )
            
            result = store.search(query)
            highlights = []
            for mem in result.memories:
                highlights.append({
                    "id": mem.id,
                    "type": mem.memory_type.value,
                    "content_preview": mem.content[:200],
                    "score": mem.current_score,
                    "created_at": mem.created_at.isoformat() if mem.created_at else None,
                    "tags": mem.tags
                })
            return highlights
        except Exception as e:
            print(f"[BringMeBack] Memory highlights error: {e}")
            return []
    
    def _get_conversation_summary(self) -> Dict[str, Any]:
        """Summarize recent conversations from memory."""
        try:
            from services.memory_engine import MemoryQuery, MemoryType, get_memory_store
            store = get_memory_store()
            
            query = MemoryQuery(
                query_text="conversation chat discussion",
                memory_types=[MemoryType.EPISODIC],
                max_results=10,
                min_score=0.1,
                recency_weight=0.6,
                importance_weight=0.2,
                relevance_weight=0.2
            )
            
            result = store.search(query)
            conversations = []
            for mem in result.memories:
                conversations.append({
                    "content_preview": mem.content[:150],
                    "layer": mem.layer,
                    "created_at": mem.created_at.isoformat() if mem.created_at else None
                })
            
            return {
                "count": len(conversations),
                "conversations": conversations[:5],
                "total_available": result.total_available
            }
        except Exception as e:
            print(f"[BringMeBack] Conversation summary error: {e}")
            return {"count": 0, "conversations": [], "total_available": 0}
    
    def _get_recent_insights(self) -> List[Dict[str, Any]]:
        """Get recently extracted insights from documents and reasoning."""
        try:
            from services.memory_engine import MemoryQuery, MemoryType, get_memory_store
            store = get_memory_store()
            
            query = MemoryQuery(
                query_text="insight learning discovery important",
                memory_types=[MemoryType.EXTRACTED_INSIGHT, MemoryType.SEMANTIC],
                max_results=6,
                min_score=0.3,
                recency_weight=0.3,
                importance_weight=0.5,
                relevance_weight=0.2
            )
            
            result = store.search(query)
            insights = []
            for mem in result.memories:
                insights.append({
                    "id": mem.id,
                    "content_preview": mem.content[:250],
                    "score": mem.current_score,
                    "source_type": mem.source_type,
                    "tags": mem.tags
                })
            return insights
        except Exception as e:
            print(f"[BringMeBack] Recent insights error: {e}")
            return []
    
    def _count_nodes_created_since(self, project_id: str, node_type_name: str, since_date: datetime) -> int:
        """Count nodes of a specific type created since a date for a project."""
        node_type = self.db.query(NodeType).filter(
            NodeType.workspace_id == self.workspace_id,
            NodeType.name == node_type_name
        ).first()
        
        if not node_type:
            return 0
        
        # Find nodes linked to this project
        edges = self.db.query(KnowledgeEdge).filter(
            KnowledgeEdge.workspace_id == self.workspace_id,
            (KnowledgeEdge.source_id == project_id) | (KnowledgeEdge.target_id == project_id),
            KnowledgeEdge.is_archived == False
        ).all()
        
        related_ids = set()
        for edge in edges:
            if edge.source_id == project_id:
                related_ids.add(edge.target_id)
            else:
                related_ids.add(edge.source_id)
        
        if not related_ids:
            return 0
        
        return self.db.query(KnowledgeNode).filter(
            KnowledgeNode.id.in_(related_ids),
            KnowledgeNode.node_type_id == node_type.id,
            KnowledgeNode.created_at >= since_date,
            KnowledgeNode.is_archived == False
        ).count()
    
    def format_briefing_markdown(self, briefing: Dict[str, Any]) -> str:
        """Format briefing as markdown for display."""
        lines = []
        
        # Greeting
        lines.append(f"# {briefing['greeting']}")
        lines.append("")
        lines.append(f"**While you were away** ({briefing['time_away']['duration']}):")
        lines.append("")
        
        # New knowledge
        new = briefing['new_knowledge']
        lines.append("## New Knowledge")
        lines.append(f"- {new['nodes']} new nodes")
        lines.append(f"- {new['relationships']} new relationships")
        lines.append(f"- {new['assets']} new assets uploaded")
        lines.append(f"- {new['events']} new timeline events")
        lines.append("")
        
        # Phase 02: Memory highlights
        highlights = briefing.get('memory_highlights', [])
        if highlights:
            lines.append("## Memory Highlights")
            for mem in highlights[:5]:
                lines.append(f"- [{mem['type']}] {mem['content_preview']}")
            lines.append("")
        
        # Phase 02: Recent insights
        insights = briefing.get('recent_insights', [])
        if insights:
            lines.append("## Recent Insights")
            for ins in insights[:5]:
                lines.append(f"- {ins['content_preview']}")
            lines.append("")
        
        # Phase 02: Conversation summary
        conv_summary = briefing.get('conversation_summary', {})
        if conv_summary.get('conversations'):
            lines.append(f"## Recent Conversations ({conv_summary['count']} total)")
            for conv in conv_summary['conversations'][:3]:
                lines.append(f"- [{conv.get('layer', 'general')}] {conv['content_preview']}")
            lines.append("")
        
        # Projects
        lines.append("## Active Projects")
        lines.append("")
        for project in briefing['projects']:
            completeness = project['completeness']
            bar = "█" * (completeness // 10) + "░" * ((100 - completeness) // 10)
            lines.append(f"**{project['title']}** {bar} {completeness}%")
            
            new_items = project['new_since_last_visit']
            if any(new_items.values()):
                items = []
                if new_items['decisions']: items.append(f"{new_items['decisions']} decisions")
                if new_items['insights']: items.append(f"{new_items['insights']} insights")
                if new_items['questions']: items.append(f"{new_items['questions']} questions")
                lines.append(f"  → New: {', '.join(items)}")
            lines.append("")
        
        # Unresolved
        unresolved = briefing['unresolved']
        if unresolved['open_questions']:
            lines.append("## Open Questions")
            for q in unresolved['open_questions'][:5]:
                lines.append(f"- {q['title']}")
            lines.append("")
        
        # Current focus
        focus = briefing['current_focus']
        if focus['project']:
            lines.append("## Current Focus")
            lines.append(f"**{focus['project']['title']}**")
            if focus['current_goal']:
                lines.append(f"Goal: {focus['current_goal']}")
            if focus['summary']:
                lines.append(f"{focus['summary']}")
            lines.append("")
        
        # Blocked
        blocked = briefing['blocked_by']
        if blocked:
            lines.append("## Blocked")
            for item in blocked:
                lines.append(f"- {item['title']} — {item['reason']}")
            lines.append("")
        
        # Suggestions
        suggestions = briefing['suggested_next_steps']
        if suggestions:
            lines.append("## Suggested Next Steps")
            for suggestion in suggestions:
                lines.append(f"- {suggestion['message']}")
            lines.append("")
        
        # Related context
        context = briefing['related_context']
        if context:
            lines.append("## Related Context")
            for item in context:
                lines.append(f"- {item['title']}")
            lines.append("")
        
        return "\n".join(lines)
