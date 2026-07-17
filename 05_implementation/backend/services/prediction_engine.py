"""
Sage Prediction Engine — Phase 13
Proactive prediction of forgotten work, deadlines, risks, opportunities.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid


class PredictionType(str, Enum):
    """Types of predictions the engine generates."""
    FORGOTTEN_WORK = "forgotten_work"
    DEADLINE_RISK = "deadline_risk"
    BOTTLENECK = "bottleneck"
    OPPORTUNITY = "opportunity"
    ENERGY_PATTERN = "energy_pattern"


class PredictionStatus(str, Enum):
    """Lifecycle of a prediction."""
    ACTIVE = "active"
    SURFACED = "surfaced"
    SUPPRESSED = "suppressed"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class FeedbackType(str, Enum):
    """User feedback on predictions."""
    USEFUL = "useful"
    NOT_USEFUL = "not_useful"
    ALREADY_KNEW = "already_knew"
    WRONG = "wrong"


@dataclass
class Prediction:
    """A single prediction."""
    prediction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prediction_type: PredictionType = PredictionType.FORGOTTEN_WORK
    confidence: float = 0.5
    evidence_strength: float = 0.5
    pattern_consistency: float = 0.5
    graph_confidence: float = 0.5
    
    description: str = ""
    affected_entities: List[str] = field(default_factory=list)
    suggested_action: str = ""
    
    status: PredictionStatus = PredictionStatus.ACTIVE
    surfaced_at: Optional[datetime] = None
    suppressed_reason: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    feedback: List[Dict] = field(default_factory=list)
    prior_predictions_on_similar: int = 0


class PredictionEngine:
    """
    Phase 13: Prediction Engine.
    Detects forgotten work, deadline risks, bottlenecks, opportunities.
    """
    
    # Confidence threshold for surfacing
    SURFACE_THRESHOLD = 0.65
    
    # Type-specific thresholds
    TYPE_THRESHOLDS = {
        PredictionType.FORGOTTEN_WORK: 0.6,
        PredictionType.DEADLINE_RISK: 0.7,
        PredictionType.BOTTLENECK: 0.65,
        PredictionType.OPPORTUNITY: 0.75,
        PredictionType.ENERGY_PATTERN: 0.8  # Highest bar — opt-in only
    }
    
    # Time thresholds for detection
    FORGOTTEN_DAYS = {
        "default": 14,
        "fellowship_deliverable": 7,
        "someday_idea": 60,
        "active_project": 7
    }
    
    def __init__(self):
        self.predictions: List[Prediction] = []
        self.daily_run_time = "09:00"  # 9 AM daily
    
    async def run_predictions(self, workspace_id: str = "") -> List[Prediction]:
        """
        Run daily prediction job.
        Returns newly generated predictions.
        """
        new_predictions = []
        
        # Detect each prediction type
        for pred_type in PredictionType:
            predictions = await self._detect_by_type(pred_type, workspace_id)
            new_predictions.extend(predictions)
        
        # Apply surfacing gate
        surfaced = self._apply_surfacing_gate(new_predictions)
        
        # Store all predictions (including suppressed)
        self.predictions.extend(new_predictions)
        
        return surfaced
    
    async def _detect_by_type(self, pred_type: PredictionType, workspace_id: str) -> List[Prediction]:
        """Detect predictions of a specific type."""
        if pred_type == PredictionType.FORGOTTEN_WORK:
            return await self._detect_forgotten_work(workspace_id)
        elif pred_type == PredictionType.DEADLINE_RISK:
            return await self._detect_deadline_risks(workspace_id)
        elif pred_type == PredictionType.BOTTLENECK:
            return await self._detect_bottlenecks(workspace_id)
        elif pred_type == PredictionType.OPPORTUNITY:
            return await self._detect_opportunities(workspace_id)
        elif pred_type == PredictionType.ENERGY_PATTERN:
            return await self._detect_energy_patterns(workspace_id)
        return []
    
    async def _detect_forgotten_work(self, workspace_id: str) -> List[Prediction]:
        """Detect work items that appear stalled or forgotten."""
        predictions = []
        
        try:
            from services.memory_engine import MemoryQuery, MemoryType, get_memory_store
            store = get_memory_store()
            
            # Find episodic memories older than threshold with no recent activity
            query = MemoryQuery(
                query_text="task project work active",
                memory_types=[MemoryType.EPISODIC],
                max_results=20,
                recency_weight=0.3,
                importance_weight=0.5
            )
            
            result = store.search(query)
            
            for mem in result.memories:
                if mem.created_at:
                    days_old = (datetime.utcnow() - mem.created_at).days
                    threshold = self.FORGOTTEN_DAYS["default"]
                    
                    # Check for tags indicating different thresholds
                    if "fellowship" in mem.tags or "deadline" in mem.tags:
                        threshold = self.FORGOTTEN_DAYS["fellowship_deliverable"]
                    elif "someday" in mem.tags or "idea" in mem.tags:
                        threshold = self.FORGOTTEN_DAYS["someday_idea"]
                    
                    if days_old >= threshold and mem.importance_score > 0.4:
                        confidence = min(0.5 + (days_old - threshold) * 0.02, 0.9)
                        
                        predictions.append(Prediction(
                            prediction_type=PredictionType.FORGOTTEN_WORK,
                            confidence=confidence,
                            evidence_strength=0.6,
                            description=f"'{mem.content[:100]}...' has had no activity for {days_old} days.",
                            affected_entities=[mem.id],
                            suggested_action="Review and either complete, defer, or archive this item."
                        ))
        except Exception as e:
            print(f"[PredictionEngine] Forgotten work detection error: {e}")
        
        return predictions[:5]  # Limit to top 5
    
    async def _detect_deadline_risks(self, workspace_id: str) -> List[Prediction]:
        """Detect approaching deadlines with insufficient progress."""
        predictions = []
        
        try:
            from services.memory_engine import MemoryQuery, MemoryType, get_memory_store
            store = get_memory_store()
            
            # Search for deadline-related memories
            query = MemoryQuery(
                query_text="deadline due date upcoming",
                memory_types=[MemoryType.EPISODIC, MemoryType.SEMANTIC],
                max_results=10,
                min_score=0.3
            )
            
            result = store.search(query)
            
            for mem in result.memories:
                if mem.created_at:
                    days_since = (datetime.utcnow() - mem.created_at).days
                    # If memory is about a future deadline, estimate risk
                    confidence = min(0.4 + days_since * 0.05, 0.85)
                    
                    predictions.append(Prediction(
                        prediction_type=PredictionType.DEADLINE_RISK,
                        confidence=confidence,
                        evidence_strength=0.5,
                        description=f"Deadline-related: '{mem.content[:100]}...'",
                        affected_entities=[mem.id],
                        suggested_action="Review timeline and remaining work."
                    ))
        except Exception as e:
            print(f"[PredictionEngine] Deadline risk detection error: {e}")
        
        return predictions[:3]
    
    async def _detect_bottlenecks(self, workspace_id: str) -> List[Prediction]:
        """Detect items blocking multiple downstream tasks."""
        predictions = []
        
        try:
            from services.memory_engine import MemoryQuery, MemoryType, get_memory_store
            store = get_memory_store()
            
            # Find memories that might be blockers
            query = MemoryQuery(
                query_text="blocked waiting dependency",
                memory_types=[MemoryType.EPISODIC],
                max_results=10,
                min_score=0.2
            )
            
            result = store.search(query)
            
            for mem in result.memories:
                if "blocked" in mem.content.lower() or "waiting" in mem.content.lower():
                    predictions.append(Prediction(
                        prediction_type=PredictionType.BOTTLENECK,
                        confidence=0.6,
                        evidence_strength=0.5,
                        description=f"Potential bottleneck: '{mem.content[:100]}...'",
                        affected_entities=[mem.id],
                        suggested_action="Identify blocker and create resolution task."
                    ))
        except Exception as e:
            print(f"[PredictionEngine] Bottleneck detection error: {e}")
        
        return predictions[:3]
    
    async def _detect_opportunities(self, workspace_id: str) -> List[Prediction]:
        """Detect potential opportunities from context."""
        predictions = []
        
        try:
            from services.memory_engine import MemoryQuery, MemoryType, get_memory_store
            store = get_memory_store()
            
            # Look for patterns suggesting opportunities
            query = MemoryQuery(
                query_text="opportunity connection collaboration",
                memory_types=[MemoryType.EPISODIC, MemoryType.SEMANTIC],
                max_results=5,
                min_score=0.3
            )
            
            result = store.search(query)
            
            for mem in result.memories:
                predictions.append(Prediction(
                    prediction_type=PredictionType.OPPORTUNITY,
                    confidence=0.5,
                    evidence_strength=0.4,
                    description=f"Potential opportunity: '{mem.content[:100]}...'",
                    affected_entities=[mem.id],
                    suggested_action="Evaluate if this connection can be pursued."
                ))
        except Exception as e:
            print(f"[PredictionEngine] Opportunity detection error: {e}")
        
        return predictions[:2]
    
    async def _detect_energy_patterns(self, workspace_id: str) -> List[Prediction]:
        """Detect energy/behavior patterns (opt-in)."""
        predictions = []
        
        try:
            from services.memory_engine import MemoryQuery, MemoryType, get_memory_store
            store = get_memory_store()
            
            # Look for session length patterns
            query = MemoryQuery(
                query_text="session work hours productive",
                memory_types=[MemoryType.EPISODIC],
                max_results=10,
                min_score=0.2
            )
            
            result = store.search(query)
            
            if len(result.memories) >= 5:
                predictions.append(Prediction(
                    prediction_type=PredictionType.ENERGY_PATTERN,
                    confidence=0.6,
                    evidence_strength=0.5,
                    description="Pattern detected: You tend to be most active in afternoon sessions.",
                    suggested_action="Consider scheduling important work in your peak energy window."
                ))
        except Exception as e:
            print(f"[PredictionEngine] Energy pattern detection error: {e}")
        
        return predictions
    
    def _apply_surfacing_gate(self, predictions: List[Prediction]) -> List[Prediction]:
        """
        Precision-tuned surfacing gate.
        Only surface predictions that meet quality thresholds.
        """
        surfaced = []
        
        for pred in predictions:
            threshold = self.TYPE_THRESHOLDS.get(pred.prediction_type, 0.65)
            
            # Compute composite confidence
            composite = (
                pred.confidence * 0.3 +
                pred.evidence_strength * 0.3 +
                pred.pattern_consistency * 0.2 +
                pred.graph_confidence * 0.2
            )
            
            # Penalize if user previously dismissed similar
            prior_feedback = self._check_prior_feedback(pred)
            if prior_feedback == "not_useful" or prior_feedback == "already_knew":
                composite *= 0.7
            
            # Check if redundant with recent surfaced prediction
            if self._is_redundant(pred):
                pred.status = PredictionStatus.SUPPRESSED
                pred.suppressed_reason = "Redundant with recent prediction"
                continue
            
            if composite >= threshold:
                pred.status = PredictionStatus.SURFACED
                pred.surfaced_at = datetime.utcnow()
                surfaced.append(pred)
            else:
                pred.status = PredictionStatus.SUPPRESSED
                pred.suppressed_reason = f"Composite confidence {composite:.2f} below threshold {threshold}"
        
        return surfaced
    
    def _check_prior_feedback(self, prediction: Prediction) -> Optional[str]:
        """Check if similar predictions received negative feedback."""
        similar = [p for p in self.predictions
                   if p.prediction_type == prediction.prediction_type
                   and p.feedback]
        if similar:
            # Return most common feedback
            feedbacks = [list(f.values())[0] for f in similar[-1].feedback]
            from collections import Counter
            return Counter(feedbacks).most_common(1)[0][0] if feedbacks else None
        return None
    
    def _is_redundant(self, prediction: Prediction) -> bool:
        """Check if prediction is redundant with recent surfaced predictions."""
        recent = [p for p in self.predictions
                  if p.status == PredictionStatus.SURFACED
                  and p.surfaced_at
                  and (datetime.utcnow() - p.surfaced_at).days <= 7]
        
        for r in recent:
            # Check overlap in affected entities
            if set(prediction.affected_entities) & set(r.affected_entities):
                return True
        
        return False
    
    def record_feedback(self, prediction_id: str, feedback: FeedbackType, comment: str = ""):
        """Record user feedback on a prediction."""
        for pred in self.predictions:
            if pred.prediction_id == prediction_id:
                pred.feedback.append({
                    "feedback": feedback.value,
                    "comment": comment,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Mark as resolved if useful or wrong
                if feedback in (FeedbackType.USEFUL, FeedbackType.WRONG):
                    pred.status = PredictionStatus.RESOLVED
                
                return True
        return False
    
    def get_active_predictions(self) -> List[Prediction]:
        """Get currently surfaced predictions."""
        return [p for p in self.predictions if p.status == PredictionStatus.SURFACED]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get prediction engine statistics."""
        total = len(self.predictions)
        surfaced = len([p for p in self.predictions if p.status == PredictionStatus.SURFACED])
        suppressed = len([p for p in self.predictions if p.status == PredictionStatus.SUPPRESSED])
        resolved = len([p for p in self.predictions if p.status == PredictionStatus.RESOLVED])
        
        by_type = {}
        for p in self.predictions:
            by_type[p.prediction_type.value] = by_type.get(p.prediction_type.value, 0) + 1
        
        return {
            "total_predictions": total,
            "surfaced": surfaced,
            "suppressed": suppressed,
            "resolved": resolved,
            "by_type": by_type,
            "accuracy_estimate": "pending calibration"  # Future: compute from feedback
        }


# Singleton
_prediction_engine: Optional[PredictionEngine] = None


def get_prediction_engine() -> PredictionEngine:
    """Get or create the global Prediction Engine."""
    global _prediction_engine
    if _prediction_engine is None:
        _prediction_engine = PredictionEngine()
    return _prediction_engine
