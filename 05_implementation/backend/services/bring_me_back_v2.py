"""
Sage Bring Me Back Engine — Phase 06
Full reconstruction orchestration with priority scoring, dependency analysis,
missing-information flagging, and next-best-action generation.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json


class ReconstructionGranularity(str, Enum):
    """Granularity adapts to gap length."""
    RAW_EPISODIC = "raw_episodic"      # 1-3 days: raw events
    DAILY = "daily"                    # 4-14 days: daily summaries
    WEEKLY = "weekly"                  # 15-90 days: weekly summaries
    MONTHLY = "monthly"                # 90+ days: monthly summaries + recent 2 weeks daily


@dataclass
class TimelineSegment:
    """One segment of the reconstructed timeline."""
    period_start: datetime
    period_end: datetime
    granularity: ReconstructionGranularity
    events: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    importance_score: float = 0.5


@dataclass
class PriorityItem:
    """An item scored for priority surfacing."""
    item_id: str
    item_type: str  # project, task, decision, question, memory
    title: str
    content: str
    priority_score: float = 0.0
    urgency_reason: str = ""
    last_activity: Optional[datetime] = None
    blocked_by: List[str] = field(default_factory=list)
    blocking: List[str] = field(default_factory=list)


@dataclass
class MissingInformation:
    """Flagged gap in reconstruction confidence."""
    category: str  # project_status, timeline_gap, relationship_unknown
    description: str
    confidence_impact: float  # How much this missing info affects reconstruction
    suggested_action: str = ""


@dataclass
class NextBestAction:
    """Concrete next step generated from reconstruction."""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str = ""  # review, complete, decide, schedule, investigate
    description: str = ""
    target_item_id: Optional[str] = None
    target_item_type: Optional[str] = None
    estimated_effort: str = "small"  # small, medium, large
    priority_score: float = 0.5
    rationale: str = ""
    depends_on: List[str] = field(default_factory=list)


@dataclass
class ReconstructionResult:
    """Full reconstruction output."""
    reconstruction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    gap_start: Optional[datetime] = None
    gap_end: datetime = field(default_factory=datetime.utcnow)
    gap_days: int = 0
    granularity: ReconstructionGranularity = ReconstructionGranularity.DAILY
    greeting: str = ""
    timeline_segments: List[TimelineSegment] = field(default_factory=list)
    priority_items: List[PriorityItem] = field(default_factory=list)
    blocked_items: List[PriorityItem] = field(default_factory=list)
    missing_info: List[MissingInformation] = field(default_factory=list)
    next_best_actions: List[NextBestAction] = field(default_factory=list)
    overall_confidence: float = 0.5
    degraded: bool = False


class BringMeBackEngineV2:
    """
    Phase 06: Bring Me Back Engine.
    Orchestrates reconstruction from Memory Engine, Knowledge Graph, and Reasoning Engine.
    """
    
    def __init__(self, db_session, workspace_id: str):
        self.db = db_session
        self.workspace_id = workspace_id
    
    def reconstruct(self, since_date: Optional[datetime] = None) -> ReconstructionResult:
        """
        Main entry point: Generate full reconstruction.
        """
        result = ReconstructionResult()
        result.gap_end = datetime.utcnow()
        
        # Determine gap length and granularity
        if since_date:
            result.gap_start = since_date
        else:
            # Default: find last activity
            result.gap_start = self._find_last_activity()
        
        result.gap_days = (result.gap_end - result.gap_start).days
        result.granularity = self._determine_granularity(result.gap_days)
        result.greeting = self._generate_greeting(result.gap_days)
        
        # 1. Timeline Reconstruction
        result.timeline_segments = self._reconstruct_timeline(
            result.gap_start, result.gap_end, result.granularity
        )
        
        # 2. Priority Scoring
        result.priority_items = self._score_priorities(result.gap_start)
        
        # 3. Dependency Graph Analysis
        result.blocked_items = self._analyze_dependencies(result.priority_items)
        
        # 4. Missing Information Detection
        result.missing_info = self._detect_missing_information(
            result.timeline_segments, result.priority_items
        )
        
        # 5. Next-Best-Action Generation
        result.next_best_actions = self._generate_next_best_actions(
            result.priority_items, result.blocked_items, result.missing_info
        )
        
        # 6. Overall Confidence
        result.overall_confidence = self._compute_overall_confidence(result)
        
        return result
    
    def _find_last_activity(self) -> datetime:
        """Find the most recent user activity."""
        try:
            from models_v4 import ChatMessage, KnowledgeNode
            
            # Check last chat message
            last_chat = self.db.query(ChatMessage).filter(
                ChatMessage.workspace_id == self.workspace_id
            ).order_by(ChatMessage.created_at.desc()).first()
            
            # Check last node update
            last_node = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == self.workspace_id
            ).order_by(KnowledgeNode.updated_at.desc()).first()
            
            dates = []
            if last_chat and last_chat.created_at:
                dates.append(last_chat.created_at)
            if last_node and last_node.updated_at:
                dates.append(last_node.updated_at)
            
            if dates:
                return max(dates)
        except Exception as e:
            print(f"[BringMeBackV2] Error finding last activity: {e}")
        
        # Default: 7 days ago
        return datetime.utcnow() - timedelta(days=7)
    
    def _determine_granularity(self, gap_days: int) -> ReconstructionGranularity:
        """Map gap length to reconstruction granularity."""
        if gap_days <= 3:
            return ReconstructionGranularity.RAW_EPISODIC
        elif gap_days <= 14:
            return ReconstructionGranularity.DAILY
        elif gap_days <= 90:
            return ReconstructionGranularity.WEEKLY
        else:
            return ReconstructionGranularity.MONTHLY
    
    def _generate_greeting(self, gap_days: int) -> str:
        """Generate personalized greeting based on gap length."""
        hour = datetime.utcnow().hour
        if 5 <= hour < 12:
            time_greeting = "morning"
        elif 12 <= hour < 17:
            time_greeting = "afternoon"
        else:
            time_greeting = "evening"
        
        if gap_days == 0:
            gap_text = "a few hours"
        elif gap_days == 1:
            gap_text = "1 day"
        elif gap_days < 7:
            gap_text = f"{gap_days} days"
        elif gap_days < 30:
            weeks = gap_days // 7
            gap_text = f"{weeks} week{'s' if weeks > 1 else ''}"
        elif gap_days < 365:
            months = gap_days // 30
            gap_text = f"{months} month{'s' if months > 1 else ''}"
        else:
            years = gap_days // 365
            gap_text = f"{years} year{'s' if years > 1 else ''}"
        
        return f"Good {time_greeting}. You've been away for {gap_text}. Here's what matters."
    
    def _reconstruct_timeline(
        self,
        gap_start: datetime,
        gap_end: datetime,
        granularity: ReconstructionGranularity
    ) -> List[TimelineSegment]:
        """Reconstruct timeline with adaptive granularity."""
        segments = []
        
        try:
            from services.memory_engine import MemoryQuery, MemoryType, get_memory_store
            store = get_memory_store()
            
            if granularity == ReconstructionGranularity.RAW_EPISODIC:
                # Pull raw episodic memories
                query = MemoryQuery(
                    query_text="*",
                    memory_types=[MemoryType.EPISODIC],
                    max_results=50,
                    since=gap_start
                )
                result = store.search(query)
                
                events = [{
                    "id": m.id,
                    "type": m.memory_type.value,
                    "content": m.content[:300],
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "layer": m.layer,
                    "importance_score": m.importance_score
                } for m in result.memories]
                
                segments.append(TimelineSegment(
                    period_start=gap_start,
                    period_end=gap_end,
                    granularity=granularity,
                    events=events,
                    summary=f"{len(events)} events recorded during your absence."
                ))
            
            elif granularity in (ReconstructionGranularity.DAILY, ReconstructionGranularity.WEEKLY):
                # Use daily/weekly consolidated summaries
                query = MemoryQuery(
                    query_text="important activity project",
                    memory_types=[MemoryType.EPISODIC, MemoryType.SEMANTIC],
                    max_results=30,
                    since=gap_start,
                    recency_weight=0.5,
                    importance_weight=0.5
                )
                result = store.search(query)
                
                events = [{
                    "id": m.id,
                    "type": m.memory_type.value,
                    "content": m.content[:300],
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "layer": m.layer
                } for m in result.memories]
                
                period_name = "week" if granularity == ReconstructionGranularity.WEEKLY else "day"
                segments.append(TimelineSegment(
                    period_start=gap_start,
                    period_end=gap_end,
                    granularity=granularity,
                    events=events,
                    summary=f"{len(events)} significant items from your {period_name}-long absence."
                ))
            
            else:  # MONTHLY
                # Monthly summaries + recent 2 weeks daily
                query = MemoryQuery(
                    query_text="important activity",
                    memory_types=[MemoryType.EPISODIC, MemoryType.SEMANTIC],
                    max_results=40,
                    since=gap_start,
                    recency_weight=0.6,
                    importance_weight=0.4
                )
                result = store.search(query)
                
                # Split into monthly + recent
                recent_cutoff = gap_end - timedelta(days=14)
                monthly_events = []
                recent_events = []
                
                for m in result.memories:
                    event = {
                        "id": m.id,
                        "type": m.memory_type.value,
                        "content": m.content[:250],
                        "created_at": m.created_at.isoformat() if m.created_at else None
                    }
                    if m.created_at and m.created_at >= recent_cutoff:
                        recent_events.append(event)
                    else:
                        monthly_events.append(event)
                
                if monthly_events:
                    segments.append(TimelineSegment(
                        period_start=gap_start,
                        period_end=recent_cutoff,
                        granularity=ReconstructionGranularity.MONTHLY,
                        events=monthly_events[:10],
                        summary=f"{len(monthly_events)} items from the past months."
                    ))
                
                if recent_events:
                    segments.append(TimelineSegment(
                        period_start=recent_cutoff,
                        period_end=gap_end,
                        granularity=ReconstructionGranularity.DAILY,
                        events=recent_events[:15],
                        summary=f"{len(recent_events)} items from the past 2 weeks."
                    ))
        
        except Exception as e:
            print(f"[BringMeBackV2] Timeline reconstruction error: {e}")
        
        return segments
    
    def _score_priorities(self, since_date: datetime) -> List[PriorityItem]:
        """Score items by importance, urgency, and activity."""
        items = []
        
        try:
            from models_v4 import KnowledgeNode, KnowledgeEdge
            
            # Get active projects
            active_nodes = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == self.workspace_id,
                KnowledgeNode.is_archived == False
            ).order_by(KnowledgeNode.updated_at.desc()).limit(20).all()
            
            for node in active_nodes:
                # Calculate priority score
                recency_score = self._calculate_recency_score(node.updated_at)
                completeness_penalty = (100 - (node.completeness_percent or 0)) / 100
                importance_score = self._estimate_importance(node)
                
                priority_score = (recency_score * 0.3 + completeness_penalty * 0.3 + importance_score * 0.4)
                
                items.append(PriorityItem(
                    item_id=node.id,
                    item_type="project",
                    title=node.title,
                    content=node.content[:200] if node.content else "",
                    priority_score=priority_score,
                    urgency_reason=f"Last updated {self._format_time_ago(node.updated_at)}",
                    last_activity=node.updated_at
                ))
            
            # Sort by priority score
            items.sort(key=lambda x: x.priority_score, reverse=True)
        except Exception as e:
            print(f"[BringMeBackV2] Priority scoring error: {e}")
        
        return items[:10]
    
    def _analyze_dependencies(self, priority_items: List[PriorityItem]) -> List[PriorityItem]:
        """Find blocked items using dependency graph."""
        blocked = []
        
        try:
            from models_v4 import KnowledgeEdge
            
            for item in priority_items:
                # Find incoming "blocked_by" edges
                blockers = self.db.query(KnowledgeEdge).filter(
                    KnowledgeEdge.workspace_id == self.workspace_id,
                    KnowledgeEdge.target_id == item.item_id,
                    KnowledgeEdge.edge_type == "blocked_by",
                    KnowledgeEdge.is_archived == False
                ).all()
                
                if blockers:
                    blocker_ids = [e.source_id for e in blockers]
                    item.blocked_by = blocker_ids
                    item.priority_score *= 1.2  # Boost blocked items
                    blocked.append(item)
        except Exception as e:
            print(f"[BringMeBackV2] Dependency analysis error: {e}")
        
        return blocked
    
    def _detect_missing_information(
        self,
        timeline_segments: List[TimelineSegment],
        priority_items: List[PriorityItem]
    ) -> List[MissingInformation]:
        """Identify gaps in reconstruction confidence."""
        missing = []
        
        # Flag if no timeline segments
        if not timeline_segments or not any(s.events for s in timeline_segments):
            missing.append(MissingInformation(
                category="timeline_gap",
                description="No activity recorded during absence period.",
                confidence_impact=0.3,
                suggested_action="Ask user what they've been working on."
            ))
        
        # Flag if no priority items
        if not priority_items:
            missing.append(MissingInformation(
                category="project_status",
                description="Unable to determine current project priorities.",
                confidence_impact=0.5,
                suggested_action="Review active projects with user."
            ))
        
        # Flag low-confidence reconstructions
        if len(priority_items) < 3 and len(timeline_segments) > 0:
            missing.append(MissingInformation(
                category="insufficient_data",
                description="Limited data for full reconstruction.",
                confidence_impact=0.2,
                suggested_action="Continue building memory with ongoing conversations."
            ))
        
        return missing
    
    def _generate_next_best_actions(
        self,
        priority_items: List[PriorityItem],
        blocked_items: List[PriorityItem],
        missing_info: List[MissingInformation]
    ) -> List[NextBestAction]:
        """Generate concrete next steps."""
        actions = []
        
        # Action 1: Review top priority item
        if priority_items:
            top = priority_items[0]
            actions.append(NextBestAction(
                action_type="review",
                description=f"Review: {top.title}",
                target_item_id=top.item_id,
                target_item_type=top.item_type,
                estimated_effort="small",
                priority_score=top.priority_score,
                rationale=f"Highest priority item (score: {top.priority_score:.2f}). {top.urgency_reason}"
            ))
        
        # Action 2: Address blocked items
        if blocked_items:
            blocked = blocked_items[0]
            actions.append(NextBestAction(
                action_type="complete",
                description=f"Unblock: {blocked.title}",
                target_item_id=blocked.item_id,
                target_item_type=blocked.item_type,
                estimated_effort="medium",
                priority_score=blocked.priority_score,
                rationale=f"Blocked by {len(blocked.blocked_by)} item(s). Resolving this unlocks downstream work."
            ))
        
        # Action 3: Address missing information
        if missing_info:
            mi = missing_info[0]
            actions.append(NextBestAction(
                action_type="investigate",
                description=mi.suggested_action,
                estimated_effort="small",
                priority_score=0.6,
                rationale=mi.description
            ))
        
        # Action 4: Quick win — low-completeness item
        low_completion = [i for i in priority_items if i.item_type == "project"]
        if low_completion and len(actions) < 4:
            actions.append(NextBestAction(
                action_type="complete",
                description=f"Progress on: {low_completion[0].title}",
                target_item_id=low_completion[0].item_id,
                estimated_effort="medium",
                priority_score=0.5,
                rationale="Quick win — advance an active project."
            ))
        
        return actions[:4]
    
    def _compute_overall_confidence(self, result: ReconstructionResult) -> float:
        """Compute overall reconstruction confidence."""
        factors = []
        
        # Timeline coverage
        if result.timeline_segments and any(s.events for s in result.timeline_segments):
            factors.append(0.3)
        
        # Priority clarity
        if result.priority_items:
            avg_priority = sum(i.priority_score for i in result.priority_items) / len(result.priority_items)
            factors.append(avg_priority * 0.3)
        
        # Missing info penalty
        if result.missing_info:
            penalty = sum(m.confidence_impact for m in result.missing_info)
            factors.append(max(0, 0.4 - penalty))
        else:
            factors.append(0.4)
        
        return min(sum(factors), 0.95)
    
    def _calculate_recency_score(self, updated_at: Optional[datetime]) -> float:
        """Score recency from 0 (old) to 1 (very recent)."""
        if not updated_at:
            return 0.1
        
        days_ago = (datetime.utcnow() - updated_at).days
        return max(0, min(1, 1 - (days_ago / 30)))
    
    def _estimate_importance(self, node) -> float:
        """Estimate node importance from metadata."""
        # Use completeness as inverse indicator (incomplete = more important)
        if node.completeness_percent is not None:
            return (100 - node.completeness_percent) / 100
        return 0.5
    
    def _format_time_ago(self, dt: Optional[datetime]) -> str:
        """Format datetime as human-readable time ago."""
        if not dt:
            return "unknown time"
        
        delta = datetime.utcnow() - dt
        if delta.days == 0:
            hours = delta.seconds // 3600
            if hours == 0:
                return "just now"
            return f"{hours}h ago"
        elif delta.days == 1:
            return "1 day ago"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"{weeks}w ago"
        else:
            months = delta.days // 30
            return f"{months}mo ago"
    
    def format_reconstruction_markdown(self, result: ReconstructionResult) -> str:
        """Format reconstruction as markdown for chat display."""
        lines = [f"# {result.greeting}", ""]
        
        # Timeline
        if result.timeline_segments:
            lines.append("## Timeline")
            for seg in result.timeline_segments:
                lines.append(f"\n**{seg.granularity.value.title()}** ({seg.period_start.strftime('%Y-%m-%d')} to {seg.period_end.strftime('%Y-%m-%d')})")
                lines.append(f"*{seg.summary}*")
                for event in seg.events[:5]:
                    lines.append(f"- [{event.get('type', 'event')}] {event.get('content', '')[:120]}...")
            lines.append("")
        
        # Priority Items
        if result.priority_items:
            lines.append("## Priority Items")
            for item in result.priority_items[:5]:
                bar = "█" * int(item.priority_score * 10) + "░" * (10 - int(item.priority_score * 10))
                lines.append(f"{bar} **{item.title}** ({item.priority_score:.0%})")
                if item.blocked_by:
                    lines.append(f"  ⚠️ Blocked by {len(item.blocked_by)} item(s)")
            lines.append("")
        
        # Blocked Items
        if result.blocked_items:
            lines.append("## Blocked")
            for item in result.blocked_items[:3]:
                lines.append(f"- **{item.title}** — {item.urgency_reason}")
            lines.append("")
        
        # Missing Information
        if result.missing_info:
            lines.append("## ⚠️ Reconstruction Gaps")
            for mi in result.missing_info:
                lines.append(f"- **{mi.category}**: {mi.description}")
                if mi.suggested_action:
                    lines.append(f"  → {mi.suggested_action}")
            lines.append("")
        
        # Next Best Actions
        if result.next_best_actions:
            lines.append("## Next Best Actions")
            for action in result.next_best_actions:
                emoji = {"review": "👁️", "complete": "✅", "decide": "🤔", "schedule": "📅", "investigate": "🔍"}.get(action.action_type, "▶️")
                lines.append(f"{emoji} **{action.description}** ({action.estimated_effort})")
                lines.append(f"   {action.rationale}")
            lines.append("")
        
        # Confidence
        confidence_emoji = "🟢" if result.overall_confidence > 0.7 else "🟡" if result.overall_confidence > 0.4 else "🔴"
        lines.append(f"---\n*{confidence_emoji} Reconstruction confidence: {result.overall_confidence:.0%}*")
        
        return "\n".join(lines)
