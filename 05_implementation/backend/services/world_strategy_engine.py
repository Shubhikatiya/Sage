"""
Sage World Model, Opportunity Detection & Strategy Engine — Phase 15
Continuous observation of external developments, strategic decision support.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class ObservationType(str, Enum):
    """Types of external observations."""
    MARKET_TREND = "market_trend"
    TECHNOLOGY_SHIFT = "technology_shift"
    REGULATORY_CHANGE = "regulatory_change"
    COMPETITOR_ACTION = "competitor_action"
    NETWORK_UPDATE = "network_update"
    OPPORTUNITY_SIGNAL = "opportunity_signal"


@dataclass
class WorldObservation:
    """A single observation about the external world."""
    observation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    observation_type: ObservationType = ObservationType.MARKET_TREND
    source: str = ""  # Where this observation came from
    title: str = ""
    description: str = ""
    relevance_score: float = 0.5
    personal_model_connections: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


@dataclass
class Opportunity:
    """A detected opportunity."""
    opportunity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    opportunity_type: str = ""  # "career", "project", "learning", "network"
    urgency: str = "medium"  # low, medium, high
    confidence: float = 0.5
    required_action: str = ""
    connected_observations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StrategicDecision:
    """A structured strategic decision."""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_question: str = ""
    context_summary: str = ""
    options: List[Dict[str, Any]] = field(default_factory=list)
    recommendation: str = ""
    confidence: float = 0.5
    reasoning_trace_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class WorldModelEngine:
    """
    Phase 15: World Model, Opportunity Detection & Strategy Engine.
    """
    
    def __init__(self):
        self.observations: List[WorldObservation] = []
        self.opportunities: List[Opportunity] = []
        self.decisions: List[StrategicDecision] = []
    
    def add_observation(
        self,
        observation_type: ObservationType,
        title: str,
        description: str,
        source: str = "",
        relevance_score: float = 0.5,
        personal_connections: List[str] = None
    ) -> WorldObservation:
        """Add a new world observation."""
        obs = WorldObservation(
            observation_type=observation_type,
            title=title,
            description=description,
            source=source,
            relevance_score=relevance_score,
            personal_model_connections=personal_connections or [],
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        self.observations.append(obs)
        
        # Check if this observation creates an opportunity
        self._check_opportunity_from_observation(obs)
        
        return obs
    
    def _check_opportunity_from_observation(self, observation: WorldObservation):
        """Check if an observation implies an opportunity."""
        if observation.relevance_score > 0.7:
            opp = Opportunity(
                title=f"Opportunity from: {observation.title}",
                description=observation.description,
                opportunity_type="project" if observation.observation_type == ObservationType.TECHNOLOGY_SHIFT else "career",
                urgency="high" if observation.relevance_score > 0.85 else "medium",
                confidence=observation.relevance_score,
                required_action="Evaluate relevance to current projects",
                connected_observations=[observation.observation_id]
            )
            self.opportunities.append(opp)
    
    def generate_strategic_decision(
        self,
        question: str,
        context: Optional[Dict] = None
    ) -> StrategicDecision:
        """
        Generate structured strategic decision support.
        """
        # Gather relevant observations
        relevant_obs = [o for o in self.observations if o.relevance_score > 0.4]
        
        # Get personal model context
        try:
            from services.personal_model import get_personal_model
            pm = get_personal_model()
            personal_context = pm.to_dict()
        except:
            personal_context = {}
        
        # Generate options
        options = [
            {"label": "Option A", "description": "Pursue aggressively", "pros": ["High potential"], "cons": ["High risk"]},
            {"label": "Option B", "description": "Pursue cautiously", "pros": ["Balanced"], "cons": ["Slower progress"]},
            {"label": "Option C", "description": "Wait and observe", "pros": ["Low risk"], "cons": ["Missed opportunity"]}
        ]
        
        decision = StrategicDecision(
            decision_question=question,
            context_summary=f"Based on {len(relevant_obs)} relevant observations and personal model.",
            options=options,
            recommendation="Evaluate Option B (cautious pursuit) as the balanced approach.",
            confidence=0.6
        )
        
        self.decisions.append(decision)
        return decision
    
    def get_opportunities(self, min_confidence: float = 0.5) -> List[Opportunity]:
        """Get high-confidence opportunities."""
        return [o for o in self.opportunities if o.confidence >= min_confidence]
    
    def get_recent_observations(self, days: int = 7) -> List[WorldObservation]:
        """Get recent observations."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        return [o for o in self.observations if o.created_at >= cutoff]
    
    def to_dict(self) -> Dict[str, Any]:
        """Export world model state."""
        return {
            "observations_count": len(self.observations),
            "opportunities_count": len(self.opportunities),
            "decisions_count": len(self.decisions),
            "recent_observations": [
                {"type": o.observation_type.value, "title": o.title, "relevance": o.relevance_score}
                for o in self.get_recent_observations(days=7)
            ],
            "top_opportunities": [
                {"title": o.title, "confidence": o.confidence, "urgency": o.urgency}
                for o in self.get_opportunities(min_confidence=0.6)
            ]
        }


# Handle missing timedelta import
from datetime import timedelta


# Singleton
_world_engine: Optional[WorldModelEngine] = None


def get_world_model_engine() -> WorldModelEngine:
    """Get or create the global World Model Engine."""
    global _world_engine
    if _world_engine is None:
        _world_engine = WorldModelEngine()
    return _world_engine
