"""
Sage Event Schemas
Versioned Pydantic schemas for every event type in the system.
Phase 01: Foundation — ensures type safety and documentation across subsystems.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from enum import Enum
import uuid


class EventType(str, Enum):
    """All event types in the Sage system."""
    # Memory events
    MEMORY_WRITTEN = "memory.written"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_CONSOLIDATED = "memory.consolidated"
    MEMORY_DECAYED = "memory.decayed"
    MEMORY_ACCESSED = "memory.accessed"
    
    # Knowledge Graph events
    GRAPH_ENTITY_CREATED = "graph.entity_created"
    GRAPH_ENTITY_UPDATED = "graph.entity_updated"
    GRAPH_ENTITY_RESOLVED = "graph.entity_resolved"
    GRAPH_ENTITY_MERGED = "graph.entity_merged"
    GRAPH_RELATIONSHIP_CREATED = "graph.relationship_created"
    GRAPH_RELATIONSHIP_UPDATED = "graph.relationship_updated"
    
    # Document/Asset events
    DOCUMENT_INGESTED = "document.ingested"
    DOCUMENT_EXTRACTED = "document.extracted"
    DOCUMENT_CHUNKED = "document.chunked"
    DOCUMENT_APPROVED = "document.approved"
    DOCUMENT_REJECTED = "document.rejected"
    
    # Conversation events
    CONVERSATION_TURN_STARTED = "conversation.turn_started"
    CONVERSATION_TURN_COMPLETED = "conversation.turn_completed"
    CONVERSATION_ENDED = "conversation.ended"
    INTENT_DETECTED = "conversation.intent_detected"
    
    # Reasoning events
    REASONING_STARTED = "reasoning.started"
    REASONING_COMPLETED = "reasoning.completed"
    REASONING_STEP = "reasoning.step"
    REASONING_CRITIQUE = "reasoning.critique"
    
    # Agent events
    AGENT_TASK_ASSIGNED = "agent.task_assigned"
    AGENT_TASK_STARTED = "agent.task_started"
    AGENT_TASK_COMPLETED = "agent.task_completed"
    AGENT_TASK_FAILED = "agent.task_failed"
    AGENT_TASK_ESCALATED = "agent.task_escalated"
    
    # Execution events
    TASK_PROPOSED = "execution.task_proposed"
    TASK_APPROVED = "execution.task_approved"
    TASK_REJECTED = "execution.task_rejected"
    TASK_EXECUTED = "execution.task_executed"
    TASK_CANCELLED = "execution.task_cancelled"
    
    # Learning events
    FEEDBACK_RECEIVED = "learning.feedback_received"
    CORRECTION_RECEIVED = "learning.correction_received"
    OUTCOME_LOGGED = "learning.outcome_logged"
    MODEL_UPDATED = "learning.model_updated"
    CALIBRATION_RUN = "learning.calibration_run"
    
    # Prediction events
    PREDICTION_GENERATED = "prediction.generated"
    PREDICTION_SURFACED = "prediction.surfaced"
    PREDICTION_SUPPRESSED = "prediction.suppressed"
    PREDICTION_FEEDBACK = "prediction.feedback"
    
    # System events
    SYSTEM_STARTED = "system.started"
    SYSTEM_DEGRADED = "system.degraded"
    SYSTEM_RECOVERED = "system.recovered"
    SYSTEM_HEALTH_CHECK = "system.health_check"
    
    # User events
    USER_CONNECTED = "user.connected"
    USER_DISCONNECTED = "user.disconnected"
    USER_PREFERENCES_UPDATED = "user.preferences_updated"


# ─── Base Event Schema ───

class BaseEvent(BaseModel):
    """Base schema for all events."""
    event_type: EventType = Field(..., description="Type of event")
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique event ID")
    correlation_id: Optional[str] = Field(None, description="Groups related events")
    source: str = Field(..., description="Subsystem that emitted the event")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp")
    version: str = Field("1.0", description="Schema version")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ─── Memory Events ───

class MemoryWrittenEvent(BaseEvent):
    """Emitted when a memory item is written."""
    event_type: Literal[EventType.MEMORY_WRITTEN] = EventType.MEMORY_WRITTEN
    memory_id: str = Field(..., description="ID of the written memory")
    memory_type: str = Field(..., description="Type: semantic, episodic, procedural, etc.")
    source_event_id: str = Field(..., description="Original source event")
    importance_score: float = Field(..., ge=0, le=1, description="Initial importance")
    embedding_id: Optional[str] = Field(None, description="Vector embedding ID")
    content_preview: str = Field(..., max_length=500, description="Truncated content")
    tags: List[str] = Field(default_factory=list)


class MemoryRetrievedEvent(BaseEvent):
    """Emitted when memories are retrieved."""
    event_type: Literal[EventType.MEMORY_RETRIEVED] = EventType.MEMORY_RETRIEVED
    query: str = Field(..., description="Original query")
    results_count: int = Field(..., ge=0)
    top_result_ids: List[str] = Field(default_factory=list)
    retrieval_mode: str = Field("hybrid", description="vector, graph, keyword, or hybrid")
    latency_ms: float = Field(..., ge=0)
    degraded: bool = Field(False, description="Was retrieval degraded?")


class MemoryConsolidatedEvent(BaseEvent):
    """Emitted when episodic memories are consolidated into long-term."""
    event_type: Literal[EventType.MEMORY_CONSOLIDATED] = EventType.MEMORY_CONSOLIDATED
    consolidated_memory_id: str = Field(...)
    source_memory_ids: List[str] = Field(..., description="IDs of source episodic memories")
    period_start: datetime = Field(...)
    period_end: datetime = Field(...)
    summary: str = Field(..., max_length=2000)


# ─── Knowledge Graph Events ───

class EntityCreatedEvent(BaseEvent):
    """Emitted when a Knowledge Graph entity is created."""
    event_type: Literal[EventType.GRAPH_ENTITY_CREATED] = EventType.GRAPH_ENTITY_CREATED
    entity_id: str = Field(...)
    entity_type: str = Field(..., description="Person, Organization, Project, etc.")
    canonical_name: str = Field(...)
    aliases: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)
    source_event_id: str = Field(...)
    extracted_from: Optional[str] = Field(None, description="Document/asset ID if extracted")


class EntityResolvedEvent(BaseEvent):
    """Emitted when entity resolution merges duplicates."""
    event_type: Literal[EventType.GRAPH_ENTITY_RESOLVED] = EventType.GRAPH_ENTITY_RESOLVED
    canonical_entity_id: str = Field(...)
    merged_entity_ids: List[str] = Field(...)
    resolution_method: str = Field(..., description="exact, embedding, guardian_review")
    confidence: float = Field(..., ge=0, le=1)


class RelationshipCreatedEvent(BaseEvent):
    """Emitted when a relationship is created."""
    event_type: Literal[EventType.GRAPH_RELATIONSHIP_CREATED] = EventType.GRAPH_RELATIONSHIP_CREATED
    edge_id: str = Field(...)
    source_entity_id: str = Field(...)
    target_entity_id: str = Field(...)
    relation_type: str = Field(...)
    relation_category: str = Field(..., description="structural, temporal, causal, social, epistemic, evaluative")
    valid_from: Optional[datetime] = Field(None)
    valid_until: Optional[datetime] = Field(None)
    confidence: float = Field(..., ge=0, le=1)
    weight: float = Field(1.0)


# ─── Document/Asset Events ───

class DocumentIngestedEvent(BaseEvent):
    """Emitted when a document is uploaded/connected."""
    event_type: Literal[EventType.DOCUMENT_INGESTED] = EventType.DOCUMENT_INGESTED
    asset_id: str = Field(...)
    source_type: str = Field(..., description="upload, github, notion, obsidian, email, calendar")
    filename: Optional[str] = Field(None)
    mime_type: str = Field(...)
    size_bytes: int = Field(..., ge=0)
    blob_storage_ref: str = Field(..., description="MinIO/S3 reference")
    auto_extract: bool = Field(True)


class DocumentExtractedEvent(BaseEvent):
    """Emitted after knowledge extraction runs."""
    event_type: Literal[EventType.DOCUMENT_EXTRACTED] = EventType.DOCUMENT_EXTRACTED
    asset_id: str = Field(...)
    extraction_status: str = Field(..., description="complete, partial, failed")
    entities_found: int = Field(0, ge=0)
    relationships_found: int = Field(0, ge=0)
    chunks_created: int = Field(0, ge=0)
    error_message: Optional[str] = Field(None)
    pending_review: bool = Field(False, description="Needs Guardian review")


class DocumentApprovedEvent(BaseEvent):
    """Emitted when extracted knowledge is approved."""
    event_type: Literal[EventType.DOCUMENT_APPROVED] = EventType.DOCUMENT_APPROVED
    asset_id: str = Field(...)
    approved_by: str = Field(..., description="user or standing_permission")
    approved_nodes: List[str] = Field(default_factory=list)
    approved_edges: List[str] = Field(default_factory=list)


# ─── Conversation Events ───

class ConversationTurnEvent(BaseEvent):
    """Emitted during a conversation turn."""
    event_type: Literal[EventType.CONVERSATION_TURN_STARTED] = EventType.CONVERSATION_TURN_STARTED
    session_id: str = Field(...)
    turn_number: int = Field(..., ge=0)
    layer: str = Field(..., description="general, life, project, knowledge, system")
    user_message: str = Field(..., max_length=10000)
    intent_type: Optional[str] = Field(None, description="Detected intent")
    activated_layers: List[str] = Field(default_factory=list)


class ConversationEndedEvent(BaseEvent):
    """Emitted when a session ends."""
    event_type: Literal[EventType.CONVERSATION_ENDED] = EventType.CONVERSATION_ENDED
    session_id: str = Field(...)
    total_turns: int = Field(..., ge=0)
    duration_seconds: int = Field(..., ge=0)
    trigger_reflection: bool = Field(True)


# ─── Reasoning Events ───

class ReasoningStartedEvent(BaseEvent):
    """Emitted when reasoning begins."""
    event_type: Literal[EventType.REASONING_STARTED] = EventType.REASONING_STARTED
    trace_id: str = Field(...)
    query: str = Field(...)
    mode: str = Field(..., description="chain, tree, graph, reflection, simulation")
    high_stakes: bool = Field(False)
    max_evidence_items: int = Field(10, ge=1)


class ReasoningCompletedEvent(BaseEvent):
    """Emitted when reasoning finishes."""
    event_type: Literal[EventType.REASONING_COMPLETED] = EventType.REASONING_COMPLETED
    trace_id: str = Field(...)
    final_answer: str = Field(...)
    overall_confidence: float = Field(..., ge=0, le=1)
    confidence_explanation: str = Field(...)
    critique_applied: bool = Field(False)
    steps_count: int = Field(0, ge=0)
    latency_ms: float = Field(..., ge=0)


class ReasoningStepEvent(BaseEvent):
    """Emitted for each reasoning step."""
    event_type: Literal[EventType.REASONING_STEP] = EventType.REASONING_STEP
    trace_id: str = Field(...)
    step_number: int = Field(..., ge=0)
    sub_question: str = Field(...)
    evidence_ids: List[str] = Field(default_factory=list)
    evidence_sources: List[str] = Field(default_factory=list)
    intermediate_conclusion: str = Field(...)
    step_confidence: float = Field(..., ge=0, le=1)


# ─── Agent Events ───

class AgentTaskAssignedEvent(BaseEvent):
    """Emitted when a task is assigned to an agent."""
    event_type: Literal[EventType.AGENT_TASK_ASSIGNED] = EventType.AGENT_TASK_ASSIGNED
    task_id: str = Field(...)
    agent_type: str = Field(..., description="planner, memory, knowledge, reflection, etc.")
    task_description: str = Field(...)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)


class AgentTaskCompletedEvent(BaseEvent):
    """Emitted when an agent completes a task."""
    event_type: Literal[EventType.AGENT_TASK_COMPLETED] = EventType.AGENT_TASK_COMPLETED
    task_id: str = Field(...)
    agent_type: str = Field(...)
    result_summary: str = Field(...)
    result_ref: Optional[str] = Field(None)
    latency_ms: float = Field(..., ge=0)


class AgentTaskFailedEvent(BaseEvent):
    """Emitted when an agent task fails."""
    event_type: Literal[EventType.AGENT_TASK_FAILED] = EventType.AGENT_TASK_FAILED
    task_id: str = Field(...)
    agent_type: str = Field(...)
    error_message: str = Field(...)
    retryable: bool = Field(True)
    escalation_reason: Optional[str] = Field(None)


# ─── Execution Events ───

class TaskProposedEvent(BaseEvent):
    """Emitted when Execution Engine proposes a task."""
    event_type: Literal[EventType.TASK_PROPOSED] = EventType.TASK_PROPOSED
    task_id: str = Field(...)
    description: str = Field(...)
    scope: Dict[str, Any] = Field(..., description="Structured scope definition")
    origin: str = Field(..., description="user_request, next_best_action, scheduled")
    origin_ref: Optional[str] = Field(None)
    approval_required: bool = Field(True)


class TaskApprovedEvent(BaseEvent):
    """Emitted when a task is approved."""
    event_type: Literal[EventType.TASK_APPROVED] = EventType.TASK_APPROVED
    task_id: str = Field(...)
    approved_by: str = Field(..., description="user or standing_permission")
    approval_scope: Dict[str, Any] = Field(...)
    standing_permission_ref: Optional[str] = Field(None)


class TaskExecutedEvent(BaseEvent):
    """Emitted when a task is executed."""
    event_type: Literal[EventType.TASK_EXECUTED] = EventType.TASK_EXECUTED
    task_id: str = Field(...)
    outcome: str = Field(..., description="success, failure, partial")
    external_reference: Optional[str] = Field(None)
    error_detail: Optional[str] = Field(None)


# ─── Learning Events ───

class FeedbackReceivedEvent(BaseEvent):
    """Emitted when user provides feedback."""
    event_type: Literal[EventType.FEEDBACK_RECEIVED] = EventType.FEEDBACK_RECEIVED
    target_entity_type: str = Field(..., description="memory, reasoning, prediction, etc.")
    target_entity_id: str = Field(...)
    feedback_type: str = Field(..., description="useful, not_useful, already_knew, wrong")
    user_comment: Optional[str] = Field(None)


class CorrectionReceivedEvent(BaseEvent):
    """Emitted when user corrects Sage."""
    event_type: Literal[EventType.CORRECTION_RECEIVED] = EventType.CORRECTION_RECEIVED
    original_claim: str = Field(...)
    corrected_value: str = Field(...)
    target_attribute: str = Field(...)
    source_event_id: str = Field(...)


class OutcomeLoggedEvent(BaseEvent):
    """Emitted when an outcome is logged."""
    event_type: Literal[EventType.OUTCOME_LOGGED] = EventType.OUTCOME_LOGGED
    prediction_id: Optional[str] = Field(None)
    task_id: Optional[str] = Field(None)
    outcome_type: str = Field(..., description="success, failure, partial, cancelled")
    outcome_value: Optional[float] = Field(None)
    notes: Optional[str] = Field(None)


class ModelUpdatedEvent(BaseEvent):
    """Emitted when Personal Model is updated."""
    event_type: Literal[EventType.MODEL_UPDATED] = EventType.MODEL_UPDATED
    attribute_path: str = Field(..., description="e.g., career.verified_skills")
    old_value: Optional[Any] = Field(None)
    new_value: Any = Field(...)
    confidence: float = Field(..., ge=0, le=1)
    evidence_count: int = Field(..., ge=0)
    triggering_signals: List[str] = Field(default_factory=list)


# ─── Prediction Events ───

class PredictionGeneratedEvent(BaseEvent):
    """Emitted when a prediction is generated."""
    event_type: Literal[EventType.PREDICTION_GENERATED] = EventType.PREDICTION_GENERATED
    prediction_id: str = Field(...)
    prediction_type: str = Field(..., description="forgotten_work, deadline_risk, bottleneck, opportunity")
    confidence: float = Field(..., ge=0, le=1)
    evidence_strength: float = Field(..., ge=0, le=1)
    description: str = Field(...)
    affected_entities: List[str] = Field(default_factory=list)


class PredictionSurfacedEvent(BaseEvent):
    """Emitted when a prediction is shown to the user."""
    event_type: Literal[EventType.PREDICTION_SURFACED] = EventType.PREDICTION_SURFACED
    prediction_id: str = Field(...)
    surface_channel: str = Field(..., description="chat, dashboard, notification")
    user_acknowledged: bool = Field(False)


class PredictionFeedbackEvent(BaseEvent):
    """Emitted when user responds to a prediction."""
    event_type: Literal[EventType.PREDICTION_FEEDBACK] = EventType.PREDICTION_FEEDBACK
    prediction_id: str = Field(...)
    feedback: str = Field(..., description="useful, not_useful, already_knew, wrong")


# ─── System Events ───

class SystemDegradedEvent(BaseEvent):
    """Emitted when a subsystem degrades."""
    event_type: Literal[EventType.SYSTEM_DEGRADED] = EventType.SYSTEM_DEGRADED
    subsystem: str = Field(...)
    reason: str = Field(...)
    fallback_activated: str = Field(..., description="What fallback is being used")
    severity: str = Field(..., description="warning, error, critical")


class SystemRecoveredEvent(BaseEvent):
    """Emitted when a subsystem recovers."""
    event_type: Literal[EventType.SYSTEM_RECOVERED] = EventType.SYSTEM_RECOVERED
    subsystem: str = Field(...)
    recovery_time_ms: float = Field(..., ge=0)
    previous_degradation_event_id: Optional[str] = Field(None)


# ─── Event Registry ───

EVENT_SCHEMAS = {
    # Memory
    EventType.MEMORY_WRITTEN: MemoryWrittenEvent,
    EventType.MEMORY_RETRIEVED: MemoryRetrievedEvent,
    EventType.MEMORY_CONSOLIDATED: MemoryConsolidatedEvent,
    
    # Knowledge Graph
    EventType.GRAPH_ENTITY_CREATED: EntityCreatedEvent,
    EventType.GRAPH_ENTITY_RESOLVED: EntityResolvedEvent,
    EventType.GRAPH_RELATIONSHIP_CREATED: RelationshipCreatedEvent,
    
    # Document
    EventType.DOCUMENT_INGESTED: DocumentIngestedEvent,
    EventType.DOCUMENT_EXTRACTED: DocumentExtractedEvent,
    EventType.DOCUMENT_APPROVED: DocumentApprovedEvent,
    
    # Conversation
    EventType.CONVERSATION_TURN_STARTED: ConversationTurnEvent,
    EventType.CONVERSATION_ENDED: ConversationEndedEvent,
    
    # Reasoning
    EventType.REASONING_STARTED: ReasoningStartedEvent,
    EventType.REASONING_COMPLETED: ReasoningCompletedEvent,
    EventType.REASONING_STEP: ReasoningStepEvent,
    
    # Agent
    EventType.AGENT_TASK_ASSIGNED: AgentTaskAssignedEvent,
    EventType.AGENT_TASK_COMPLETED: AgentTaskCompletedEvent,
    EventType.AGENT_TASK_FAILED: AgentTaskFailedEvent,
    
    # Execution
    EventType.TASK_PROPOSED: TaskProposedEvent,
    EventType.TASK_APPROVED: TaskApprovedEvent,
    EventType.TASK_EXECUTED: TaskExecutedEvent,
    
    # Learning
    EventType.FEEDBACK_RECEIVED: FeedbackReceivedEvent,
    EventType.CORRECTION_RECEIVED: CorrectionReceivedEvent,
    EventType.OUTCOME_LOGGED: OutcomeLoggedEvent,
    EventType.MODEL_UPDATED: ModelUpdatedEvent,
    
    # Prediction
    EventType.PREDICTION_GENERATED: PredictionGeneratedEvent,
    EventType.PREDICTION_SURFACED: PredictionSurfacedEvent,
    EventType.PREDICTION_FEEDBACK: PredictionFeedbackEvent,
    
    # System
    EventType.SYSTEM_DEGRADED: SystemDegradedEvent,
    EventType.SYSTEM_RECOVERED: SystemRecoveredEvent,
}


def get_schema_for_event(event_type: EventType) -> Optional[type]:
    """Get the Pydantic schema for a given event type."""
    return EVENT_SCHEMAS.get(event_type)


def validate_event(data: Dict[str, Any]) -> BaseEvent:
    """Validate raw event data against its schema."""
    event_type = EventType(data.get("event_type"))
    schema_class = get_schema_for_event(event_type)
    if schema_class:
        return schema_class(**data)
    return BaseEvent(**data)
