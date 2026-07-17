"""
Sage Security Layer — Phase 17
Data sensitivity classification, encryption, permission model, audit logging.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class SensitivityTier(str, Enum):
    """Data sensitivity classification."""
    PUBLIC = "public"        # Can be shared freely
    INTERNAL = "internal"    # Workspace-internal
    CONFIDENTIAL = "confidential"  # Sensitive personal/professional
    RESTRICTED = "restricted"    # Highest sensitivity


class PermissionLevel(str, Enum):
    """Permission levels."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


@dataclass
class SecurityClassification:
    """Classification for a data item."""
    item_id: str = ""
    item_type: str = ""  # memory, knowledge_node, document, etc.
    sensitivity: SensitivityTier = SensitivityTier.INTERNAL
    owner: str = ""  # user_id
    encryption_required: bool = False
    classification_reason: str = ""
    classified_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AuditEntry:
    """Security audit log entry."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    subject: str = ""  # Who performed the action
    action: str = ""   # What was done
    resource_tier: int = 0
    resource_ref: Optional[str] = None
    outcome: str = ""  # success, failure, denied
    context: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None


class SecurityEngine:
    """
    Phase 17: Security Layer.
    Data classification, permission model, audit logging.
    """
    
    # Classification rules
    SENSITIVE_KEYWORDS = {
        SensitivityTier.RESTRICTED: ["password", "secret", "api_key", "token", "ssn", "bank"],
        SensitivityTier.CONFIDENTIAL: ["salary", "compensation", "health", "medical", "private"],
        SensitivityTier.INTERNAL: ["internal", "draft", "prototype"]
    }
    
    def __init__(self):
        self.classifications: Dict[str, SecurityClassification] = {}
        self.audit_log: List[AuditEntry] = []
        self.permissions: Dict[str, List[PermissionLevel]] = {}  # resource -> permissions
    
    def classify_content(self, item_id: str, content: str, item_type: str = "memory") -> SecurityClassification:
        """
        Automatically classify content based on keywords and patterns.
        """
        content_lower = content.lower()
        
        # Determine sensitivity
        sensitivity = SensitivityTier.PUBLIC
        reason = "Default classification"
        encryption = False
        
        for tier, keywords in self.SENSITIVE_KEYWORDS.items():
            if any(kw in content_lower for kw in keywords):
                sensitivity = tier
                reason = f"Matched sensitive keywords: {[k for k in keywords if k in content_lower][:3]}"
                encryption = tier in (SensitivityTier.CONFIDENTIAL, SensitivityTier.RESTRICTED)
                break
        
        classification = SecurityClassification(
            item_id=item_id,
            item_type=item_type,
            sensitivity=sensitivity,
            encryption_required=encryption,
            classification_reason=reason
        )
        
        self.classifications[item_id] = classification
        return classification
    
    def check_permission(self, subject: str, resource: str, action: PermissionLevel) -> bool:
        """
        Check if subject has permission to perform action on resource.
        """
        # Phase 17 MVP: Simple permission check
        # Future: Role-based access control (RBAC)
        
        # Get resource classification
        classification = self.classifications.get(resource)
        if not classification:
            return True  # No classification = default allow
        
        # Restricted items require explicit permission
        if classification.sensitivity == SensitivityTier.RESTRICTED:
            resource_perms = self.permissions.get(resource, [])
            return action in resource_perms
        
        # Confidential items allow read by default, write/delete restricted
        if classification.sensitivity == SensitivityTier.CONFIDENTIAL:
            if action in (PermissionLevel.READ, PermissionLevel.WRITE):
                return True
            return action in self.permissions.get(resource, [])
        
        return True
    
    def log_access(
        self,
        subject: str,
        action: str,
        resource: Optional[str] = None,
        outcome: str = "success",
        context: Optional[Dict] = None
    ):
        """
        Log an access event to the security audit log.
        """
        entry = AuditEntry(
            subject=subject,
            action=action,
            resource_ref=resource,
            outcome=outcome,
            context=context or {}
        )
        
        self.audit_log.append(entry)
    
    def get_audit_log(self, since: Optional[datetime] = None, limit: int = 100) -> List[AuditEntry]:
        """Get security audit log entries."""
        entries = self.audit_log
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        return entries[-limit:]
    
    def get_classification(self, item_id: str) -> Optional[SecurityClassification]:
        """Get classification for an item."""
        return self.classifications.get(item_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get security statistics."""
        by_tier = {}
        for c in self.classifications.values():
            by_tier[c.sensitivity.value] = by_tier.get(c.sensitivity.value, 0) + 1
        
        return {
            "total_classifications": len(self.classifications),
            "by_tier": by_tier,
            "encryption_required": len([c for c in self.classifications.values() if c.encryption_required]),
            "audit_entries": len(self.audit_log)
        }


# Singleton
_security_engine: Optional[SecurityEngine] = None


def get_security_engine() -> SecurityEngine:
    """Get or create the global Security Engine."""
    global _security_engine
    if _security_engine is None:
        _security_engine = SecurityEngine()
    return _security_engine
