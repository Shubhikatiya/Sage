"""
Sage Learning Engine — Phase 09
Signal ingestion, evidence accumulator, update threshold gate.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class SignalType(str, Enum):
    """Four signal types that drive learning."""
    CORRECTION = "correction"      # User says Sage is wrong — strongest signal
    FEEDBACK = "feedback"          # Explicit thumbs up/down
    BEHAVIOR = "behavior"          # Implicit interaction patterns
    OUTCOME = "outcome"            # What happened after Sage acted


class UpdateTarget(str, Enum):
    """What gets updated by learning."""
    MEMORY_IMPORTANCE = "memory_importance"
    PERSONAL_MODEL = "personal_model"
    CONFIDENCE_CALIBRATION = "confidence_calibration"


@dataclass
class LearningSignal:
    """A single signal that can drive learning."""
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    signal_type: SignalType = SignalType.FEEDBACK
    target_type: str = ""  # memory, reasoning, prediction, etc.
    target_id: Optional[str] = None
    value: float = 0.0  # -1 (strongly negative) to +1 (strongly positive)
    user_comment: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed: bool = False


@dataclass
class EvidenceRecord:
    """Accumulated evidence for a specific attribute."""
    attribute_path: str = ""  # e.g., "career.verified_skills"
    signals: List[LearningSignal] = field(default_factory=list)
    cumulative_weight: float = 0.0
    confidence: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class VersionedUpdate:
    """A versioned write to the Personal Model."""
    update_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    attribute_path: str = ""
    old_value: Optional[Any] = None
    new_value: Any = None
    confidence: float = 0.0
    evidence_count: int = 0
    reason: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    rolled_back: bool = False


class LearningEngine:
    """
    Phase 09: Learning Engine.
    Processes signals into calibrated updates.
    """
    
    # Signal weights by type
    SIGNAL_WEIGHTS = {
        SignalType.CORRECTION: 1.0,
        SignalType.FEEDBACK: 0.6,
        SignalType.BEHAVIOR: 0.3,
        SignalType.OUTCOME: 0.7
    }
    
    # Thresholds for different update targets
    THRESHOLDS = {
        UpdateTarget.MEMORY_IMPORTANCE: 0.5,
        UpdateTarget.PERSONAL_MODEL: 1.5,
        UpdateTarget.CONFIDENCE_CALIBRATION: 1.0
    }
    
    def __init__(self):
        self.signals: List[LearningSignal] = []
        self.evidence: Dict[str, EvidenceRecord] = {}  # attribute_path -> Evidence
        self.updates: List[VersionedUpdate] = []
        self.personal_model: Dict[str, Any] = {}
    
    def ingest_signal(self, signal: LearningSignal) -> bool:
        """
        Ingest a new learning signal.
        Returns True if signal triggers an update.
        """
        self.signals.append(signal)
        
        # Route to appropriate accumulator
        if signal.target_id:
            attribute_path = f"{signal.target_type}.{signal.target_id}"
            
            if attribute_path not in self.evidence:
                self.evidence[attribute_path] = EvidenceRecord(attribute_path=attribute_path)
            
            record = self.evidence[attribute_path]
            record.signals.append(signal)
            
            # Update cumulative weight
            weight = self.SIGNAL_WEIGHTS.get(signal.signal_type, 0.5)
            record.cumulative_weight += weight * abs(signal.value)
            record.last_updated = datetime.utcnow()
            
            # Check threshold
            threshold = self._get_threshold(signal.target_type)
            
            if record.cumulative_weight >= threshold:
                # Trigger update
                self._apply_update(record, signal.target_type)
                record.cumulative_weight = 0  # Reset after update
                return True
        
        return False
    
    def ingest_correction(self, original_claim: str, corrected_value: str, target_attribute: str) -> bool:
        """
        High-level helper for correction signals.
        Corrections are the strongest signal type.
        """
        signal = LearningSignal(
            signal_type=SignalType.CORRECTION,
            target_type=target_attribute.split('.')[0] if '.' in target_attribute else "general",
            target_id=target_attribute,
            value=-1.0,  # Strong negative
            user_comment=f"Correction: '{original_claim}' → '{corrected_value}'",
            context={
                "original": original_claim,
                "corrected": corrected_value,
                "attribute": target_attribute
            }
        )
        return self.ingest_signal(signal)
    
    def ingest_feedback(self, target_type: str, target_id: str, is_positive: bool, comment: str = "") -> bool:
        """
        High-level helper for feedback signals.
        """
        signal = LearningSignal(
            signal_type=SignalType.FEEDBACK,
            target_type=target_type,
            target_id=target_id,
            value=1.0 if is_positive else -0.5,
            user_comment=comment
        )
        return self.ingest_signal(signal)
    
    def ingest_outcome(self, prediction_id: Optional[str], task_id: Optional[str], outcome_type: str, value: Optional[float] = None) -> bool:
        """
        High-level helper for outcome signals.
        """
        signal = LearningSignal(
            signal_type=SignalType.OUTCOME,
            target_type="prediction" if prediction_id else "task",
            target_id=prediction_id or task_id,
            value=value or (1.0 if outcome_type == "success" else -0.5),
            context={
                "outcome_type": outcome_type,
                "prediction_id": prediction_id,
                "task_id": task_id
            }
        )
        return self.ingest_signal(signal)
    
    def _get_threshold(self, target_type: str) -> float:
        """Get threshold for a target type."""
        if "memory" in target_type:
            return self.THRESHOLDS[UpdateTarget.MEMORY_IMPORTANCE]
        elif "personal" in target_type:
            return self.THRESHOLDS[UpdateTarget.PERSONAL_MODEL]
        elif "confidence" in target_type or "reasoning" in target_type:
            return self.THRESHOLDS[UpdateTarget.CONFIDENCE_CALIBRATION]
        return 1.0
    
    def _apply_update(self, record: EvidenceRecord, target_type: str):
        """Apply a versioned update to the Personal Model or memory."""
        # Compute new value from signals
        weighted_sum = sum(s.value * self.SIGNAL_WEIGHTS.get(s.signal_type, 0.5) for s in record.signals)
        total_weight = sum(self.SIGNAL_WEIGHTS.get(s.signal_type, 0.5) for s in record.signals)
        
        if total_weight == 0:
            return
        
        new_value = weighted_sum / total_weight
        confidence = min(total_weight / 3.0, 0.95)  # Cap confidence
        
        # Create versioned update
        old_value = self.personal_model.get(record.attribute_path)
        
        update = VersionedUpdate(
            attribute_path=record.attribute_path,
            old_value=old_value,
            new_value=new_value,
            confidence=confidence,
            evidence_count=len(record.signals),
            reason=f"Updated from {len(record.signals)} signals (latest: {record.signals[-1].signal_type.value})"
        )
        self.updates.append(update)
        
        # Apply to personal model
        self.personal_model[record.attribute_path] = new_value
        
        print(f"[LearningEngine] Updated {record.attribute_path}: {old_value} → {new_value} (confidence: {confidence:.2f})")
    
    def rollback_update(self, update_id: str) -> bool:
        """Rollback a specific update."""
        for update in self.updates:
            if update.update_id == update_id and not update.rolled_back:
                # Restore old value
                if update.old_value is not None:
                    self.personal_model[update.attribute_path] = update.old_value
                else:
                    self.personal_model.pop(update.attribute_path, None)
                
                update.rolled_back = True
                return True
        return False
    
    def get_personal_model(self) -> Dict[str, Any]:
        """Get current personal model state."""
        return self.personal_model.copy()
    
    def get_attribute_history(self, attribute_path: str) -> List[VersionedUpdate]:
        """Get update history for a specific attribute."""
        return [u for u in self.updates if u.attribute_path == attribute_path and not u.rolled_back]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning statistics."""
        return {
            "total_signals": len(self.signals),
            "signals_by_type": {
                t.value: len([s for s in self.signals if s.signal_type == t])
                for t in SignalType
            },
            "total_updates": len(self.updates),
            "rolled_back_updates": len([u for u in self.updates if u.rolled_back]),
            "accumulating_evidence": len(self.evidence),
            "personal_model_attributes": len(self.personal_model)
        }


# Singleton
_learning_engine: Optional[LearningEngine] = None


def get_learning_engine() -> LearningEngine:
    """Get or create the global Learning Engine."""
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = LearningEngine()
    return _learning_engine
