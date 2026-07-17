"""
Sage Personal Model — Phase 14
Structured, versioned model of the user with typed sub-models.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class IdentityModel:
    """Core identity attributes."""
    name: str = ""
    preferred_name: Optional[str] = None
    timezone: str = "UTC"
    language_preferences: List[str] = field(default_factory=lambda: ["en"])
    communication_style: str = ""  # "concise", "detailed", "formal", "casual"
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DecisionPattern:
    """How the user makes decisions."""
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context: str = ""  # "career", "technical", "social"
    pattern_description: str = ""
    evidence_count: int = 0
    confidence: float = 0.5
    examples: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CareerModel:
    """Career-related attributes."""
    current_role: Optional[str] = None
    current_organization: Optional[str] = None
    career_goals: List[str] = field(default_factory=list)
    verified_skills: List[str] = field(default_factory=list)
    aspirational_skills: List[str] = field(default_factory=list)
    projects: List[str] = field(default_factory=list)
    network_contacts: List[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class KnowledgeModel:
    """Knowledge domains the user has."""
    domain_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    domain_name: str = ""
    expertise_level: str = "beginner"  # beginner, intermediate, advanced, expert
    evidence_count: int = 0
    confidence: float = 0.5
    last_demonstrated: Optional[datetime] = None


@dataclass
class ProjectModel:
    """Projects the user is involved in."""
    project_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_name: str = ""
    role: str = ""
    status: str = "active"  # active, paused, completed, abandoned
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    goals: List[str] = field(default_factory=list)
    outcomes: List[str] = field(default_factory=list)


@dataclass
class CommunicationModel:
    """Communication preferences and patterns."""
    response_time_preference: str = "async"  # async, real_time, mixed
    preferred_channels: List[str] = field(default_factory=list)
    meeting_preferences: Dict[str, Any] = field(default_factory=dict)
    writing_style_notes: str = ""
    feedback_style: str = ""  # direct, diplomatic, etc.


@dataclass
class PersonalModelAttribute:
    """A single versioned attribute in the Personal Model."""
    attribute_path: str = ""  # e.g., "career.current_role"
    value: Any = None
    confidence: float = 0.0
    evidence_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version_history: List[Dict] = field(default_factory=list)


class PersonalModel:
    """
    Phase 14: Personal Model.
    Structured, versioned model of the user.
    """
    
    def __init__(self):
        self.identity = IdentityModel()
        self.decision_patterns: List[DecisionPattern] = []
        self.career = CareerModel()
        self.knowledge_domains: List[KnowledgeModel] = []
        self.projects: List[ProjectModel] = []
        self.communication = CommunicationModel()
        
        # Flat attribute store for easy access
        self.attributes: Dict[str, PersonalModelAttribute] = {}
    
    def set_attribute(self, path: str, value: Any, confidence: float = 0.5, evidence_count: int = 0):
        """
        Set an attribute with versioning.
        """
        if path in self.attributes:
            old = self.attributes[path]
            # Save version history
            old.version_history.append({
                "value": old.value,
                "confidence": old.confidence,
                "evidence_count": old.evidence_count,
                "updated_at": old.updated_at.isoformat()
            })
            
            old.value = value
            old.confidence = confidence
            old.evidence_count = evidence_count
            old.updated_at = datetime.utcnow()
        else:
            self.attributes[path] = PersonalModelAttribute(
                attribute_path=path,
                value=value,
                confidence=confidence,
                evidence_count=evidence_count
            )
        
        # Sync to typed models
        self._sync_to_models(path, value)
    
    def get_attribute(self, path: str) -> Optional[Any]:
        """Get an attribute value."""
        if path in self.attributes:
            return self.attributes[path].value
        return None
    
    def get_attribute_history(self, path: str) -> List[Dict]:
        """Get version history for an attribute."""
        if path in self.attributes:
            attr = self.attributes[path]
            history = [{"value": attr.value, "confidence": attr.confidence, "updated_at": attr.updated_at.isoformat()}]
            history.extend(reversed(attr.version_history))
            return history
        return []
    
    def _sync_to_models(self, path: str, value: Any):
        """Sync flat attributes to typed sub-models."""
        parts = path.split('.')
        
        if parts[0] == "identity" and len(parts) > 1:
            setattr(self.identity, parts[1], value)
        
        elif parts[0] == "career" and len(parts) > 1:
            if parts[1] in ["current_role", "current_organization"]:
                setattr(self.career, parts[1], value)
            elif parts[1] == "verified_skills" and isinstance(value, list):
                self.career.verified_skills = value
            elif parts[1] == "projects" and isinstance(value, list):
                self.career.projects = value
            self.career.updated_at = datetime.utcnow()
        
        elif parts[0] == "communication" and len(parts) > 1:
            setattr(self.communication, parts[1], value)
    
    def add_decision_pattern(self, context: str, description: str, confidence: float = 0.5):
        """Add a new decision pattern."""
        pattern = DecisionPattern(
            context=context,
            pattern_description=description,
            confidence=confidence
        )
        self.decision_patterns.append(pattern)
        return pattern.pattern_id
    
    def add_knowledge_domain(self, name: str, level: str = "beginner", confidence: float = 0.5):
        """Add a knowledge domain."""
        domain = KnowledgeModel(
            domain_name=name,
            expertise_level=level,
            confidence=confidence,
            last_demonstrated=datetime.utcnow()
        )
        self.knowledge_domains.append(domain)
        return domain.domain_id
    
    def add_project(self, name: str, role: str = "", status: str = "active"):
        """Add a project."""
        project = ProjectModel(
            project_name=name,
            role=role,
            status=status,
            start_date=datetime.utcnow()
        )
        self.projects.append(project)
        return project.project_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Export Personal Model as dictionary."""
        return {
            "identity": {
                "name": self.identity.name,
                "preferred_name": self.identity.preferred_name,
                "timezone": self.identity.timezone,
                "language_preferences": self.identity.language_preferences,
                "communication_style": self.identity.communication_style
            },
            "decision_patterns": [
                {
                    "context": p.context,
                    "description": p.pattern_description,
                    "confidence": p.confidence,
                    "evidence_count": p.evidence_count
                }
                for p in self.decision_patterns
            ],
            "career": {
                "current_role": self.career.current_role,
                "current_organization": self.career.current_organization,
                "verified_skills": self.career.verified_skills,
                "projects": self.career.projects
            },
            "knowledge_domains": [
                {
                    "name": d.domain_name,
                    "level": d.expertise_level,
                    "confidence": d.confidence
                }
                for d in self.knowledge_domains
            ],
            "projects": [
                {
                    "name": p.project_name,
                    "role": p.role,
                    "status": p.status
                }
                for p in self.projects
            ],
            "communication": {
                "response_time_preference": self.communication.response_time_preference,
                "preferred_channels": self.communication.preferred_channels,
                "feedback_style": self.communication.feedback_style
            },
            "attribute_count": len(self.attributes)
        }


# Singleton
_personal_model: Optional[PersonalModel] = None


def get_personal_model() -> PersonalModel:
    """Get or create the global Personal Model."""
    global _personal_model
    if _personal_model is None:
        _personal_model = PersonalModel()
    return _personal_model
