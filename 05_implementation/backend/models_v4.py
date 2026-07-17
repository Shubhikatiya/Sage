import datetime
import uuid
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())


class Workspace(Base):
    __tablename__ = "workspaces"
    id = Column(String, primary_key=True, default=generate_uuid)
    slug = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    owner_id = Column(String, ForeignKey("users.id"))
    settings = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime)
    deleted_by = Column(String)
    is_archived = Column(Boolean, default=False)


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    timezone = Column(String, default="Asia/Kolkata")
    preferences = Column(JSON, default=dict)
    role = Column(String, default="owner")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime)
    deleted_by = Column(String)
    is_archived = Column(Boolean, default=False)


class NodeType(Base):
    __tablename__ = "node_types"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    icon = Column(String, default="📄")
    color = Column(String, default="#6B7280")
    description = Column(Text)
    schema_version = Column(Integer, default=1)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    deleted_at = Column(DateTime)
    deleted_by = Column(String)
    is_archived = Column(Boolean, default=False)


class RelationshipType(Base):
    __tablename__ = "relationship_types"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    inverse_name = Column(String)
    description = Column(Text)
    directional = Column(Boolean, default=True)
    weight = Column(Float, default=1.0)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    deleted_at = Column(DateTime)
    deleted_by = Column(String)
    is_archived = Column(Boolean, default=False)


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    slug = Column(String, nullable=False)
    node_type_id = Column(String, ForeignKey("node_types.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text)
    layer = Column(String)
    status = Column(String, default="draft")
    priority = Column(String, default="medium")
    source_type = Column(String, default="manual")
    source_id = Column(String)
    confidence = Column(String, default="certain")
    created_by = Column(String, default="user")
    ai_summary = Column(Text)
    ai_short_summary = Column(Text)
    ai_keywords = Column(JSON)
    ai_entities = Column(JSON)
    ai_importance_score = Column(Float)
    ai_novelty_score = Column(Float)
    ai_missing_information = Column(Text)
    ai_suggested_questions = Column(JSON)
    ai_next_actions = Column(JSON)
    completeness = Column(JSON, default=dict)
    completeness_percent = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime)
    deleted_by = Column(String)
    is_archived = Column(Boolean, default=False)

    node_type = relationship("NodeType")
    outgoing_edges = relationship("KnowledgeEdge", foreign_keys="KnowledgeEdge.source_id")
    incoming_edges = relationship("KnowledgeEdge", foreign_keys="KnowledgeEdge.target_id")
    versions = relationship("Version", back_populates="node")
    snapshots = relationship("StateSnapshot", back_populates="node")
    timeline_events = relationship("TimelineEvent", back_populates="node")
    evidence_items = relationship("Evidence", back_populates="node")


class KnowledgeEdge(Base):
    __tablename__ = "knowledge_edges"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    source_id = Column(String, ForeignKey("knowledge_nodes.id"))
    target_id = Column(String, ForeignKey("knowledge_nodes.id"))
    relationship_type_id = Column(String, ForeignKey("relationship_types.id"))
    evidence = Column(Text)
    confidence = Column(Float, default=1.0)
    weight = Column(Float, default=1.0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime)
    deleted_by = Column(String)
    is_archived = Column(Boolean, default=False)


class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    node_id = Column(String, ForeignKey("knowledge_nodes.id"))
    title = Column(String, nullable=False)
    event_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    description = Column(Text)
    participants = Column(JSON)
    related_nodes = Column(JSON)
    importance = Column(String, default="medium")
    location = Column(String)
    evidence = Column(JSON)
    source_type = Column(String, default="manual")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    deleted_at = Column(DateTime)
    deleted_by = Column(String)
    is_archived = Column(Boolean, default=False)

    node = relationship("KnowledgeNode", back_populates="timeline_events")


class StateSnapshot(Base):
    __tablename__ = "state_snapshots"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    node_id = Column(String, ForeignKey("knowledge_nodes.id"))
    snapshot_date = Column(DateTime, default=datetime.datetime.utcnow)
    goals = Column(JSON)
    progress = Column(Text)
    risks = Column(JSON)
    priorities = Column(JSON)
    questions = Column(JSON)
    health_score = Column(Integer)
    summary = Column(Text)
    metrics = Column(JSON)
    source_type = Column(String, default="manual")
    source_id = Column(String)
    created_by = Column(String, default="user")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    deleted_at = Column(DateTime)
    deleted_by = Column(String)
    is_archived = Column(Boolean, default=False)

    node = relationship("KnowledgeNode", back_populates="snapshots")


class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    node_id = Column(String, ForeignKey("knowledge_nodes.id"))
    evidence_type = Column(String)
    title = Column(String)
    description = Column(Text)
    source_path = Column(String)
    extracted_text = Column(Text)
    confidence = Column(Float, default=1.0)
    verified_by = Column(String)
    verified_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    deleted_at = Column(DateTime)
    deleted_by = Column(String)
    is_archived = Column(Boolean, default=False)

    node = relationship("KnowledgeNode", back_populates="evidence_items")


class Asset(Base):
    __tablename__ = "assets"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    asset_type = Column(String)
    original_filename = Column(String)
    file_path = Column(String)
    mime_type = Column(String)
    extracted_text = Column(Text)
    extracted_entities = Column(JSON)
    summary = Column(Text)
    key_insights = Column(JSON)
    embedded_images = Column(JSON)
    linked_nodes = Column(JSON)
    uploaded_at = Column(DateTime)
    processed_at = Column(DateTime)
    processing_status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    deleted_at = Column(DateTime)
    deleted_by = Column(String)
    is_archived = Column(Boolean, default=False)


class Embedding(Base):
    __tablename__ = "embeddings"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    node_id = Column(String, ForeignKey("knowledge_nodes.id"))
    embedding_type = Column(String)
    model = Column(String)
    vector = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AIAnnotation(Base):
    __tablename__ = "ai_annotations"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    node_id = Column(String, ForeignKey("knowledge_nodes.id"))
    annotation_type = Column(String)
    value = Column(Text)
    confidence = Column(Float)
    model = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Tag(Base):
    __tablename__ = "tags"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    name = Column(String, nullable=False)
    color = Column(String)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    deleted_at = Column(DateTime)
    deleted_by = Column(String)
    is_archived = Column(Boolean, default=False)


class Collection(Base):
    __tablename__ = "collections"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    slug = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    query = Column(Text)
    auto_update = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime)
    deleted_by = Column(String)
    is_archived = Column(Boolean, default=False)


class DocumentView(Base):
    __tablename__ = "document_views"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    view_type = Column(String)
    source_nodes = Column(JSON)
    view_model = Column(JSON)
    rendered_markdown = Column(Text)
    rendered_html = Column(Text)
    last_generated_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Version(Base):
    __tablename__ = "versions"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    node_id = Column(String, ForeignKey("knowledge_nodes.id"))
    version_number = Column(Integer, nullable=False)
    change_type = Column(String)
    change_summary = Column(Text)
    old_values = Column(JSON)
    new_values = Column(JSON)
    changed_by = Column(String, default="user")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    node = relationship("KnowledgeNode", back_populates="versions")


class ImportJob(Base):
    __tablename__ = "import_jobs"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    source_type = Column(String)
    status = Column(String, default="pending")
    config = Column(JSON)
    result_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime)


class ExportJob(Base):
    __tablename__ = "export_jobs"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    export_type = Column(String)
    status = Column(String, default="pending")
    config = Column(JSON)
    file_path = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime)


class AgentMemory(Base):
    __tablename__ = "agent_memories"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    memory_type = Column(String)
    content = Column(Text)
    importance = Column(Float)
    last_accessed = Column(DateTime)
    access_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    name = Column(String, nullable=False)
    purpose = Column(String)
    template = Column(Text, nullable=False)
    variables = Column(JSON)
    model = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class NodeTag(Base):
    __tablename__ = "node_tags"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    node_id = Column(String, ForeignKey("knowledge_nodes.id"))
    tag_id = Column(String, ForeignKey("tags.id"))


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    layer = Column(String, default="general")
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    context_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ReasoningTrace(Base):
    """Phase 04: Persisted reasoning traces."""
    __tablename__ = "reasoning_traces"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    query = Column(Text, nullable=False)
    mode = Column(String, default="chain")  # chain, tree, graph, simulation
    steps = Column(JSON, default=list)  # List of reasoning steps
    final_answer = Column(Text)
    overall_confidence = Column(Float, default=0.0)
    critique_applied = Column(Boolean, default=False)
    critique_notes = Column(Text)
    evidence_count = Column(Integer, default=0)
    query_duration_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
# ─── Phase 09: Learning Engine Tables ───

class LearningSignal(Base):
    __tablename__ = "learning_signals"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    signal_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    source_event_id = Column(String)
    target_type = Column(String, default="memory_importance")
    confidence = Column(Float, default=0.7)
    user_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    signal_id = Column(String, ForeignKey("learning_signals.id"))
    evidence_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    weight = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class VersionedUpdate(Base):
    __tablename__ = "versioned_updates"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    target_type = Column(String, nullable=False)
    target_id = Column(String)
    update_data = Column(JSON, default=dict)
    evidence_score = Column(Float, default=0.0)
    applied = Column(Boolean, default=False)
    rolled_back = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ─── Phase 10: Execution Engine Tables ───

class ExecutionTask(Base):
    __tablename__ = "execution_tasks"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    description = Column(Text, nullable=False)
    action_type = Column(String, default="manual")
    parameters = Column(JSON, default=dict)
    status = Column(String, default="proposed")
    proposed_by = Column(String, default="user")
    approved_by = Column(String)
    approved_at = Column(DateTime)
    executed_at = Column(DateTime)
    completed_at = Column(DateTime)
    result = Column(Text)
    error = Column(Text)
    audit_log = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ApprovalRecord(Base):
    __tablename__ = "approval_records"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    task_id = Column(String, ForeignKey("execution_tasks.id"))
    approver = Column(String, nullable=False)
    decision = Column(String, nullable=False)
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class StandingPermission(Base):
    __tablename__ = "standing_permissions"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    action_type = Column(String, nullable=False)
    scope = Column(String, nullable=False)
    max_risk_level = Column(String, default="medium")
    granted_to = Column(String, nullable=False)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ─── Phase 11: Conversation Engine Tables ───

class ConversationSession(Base):
    __tablename__ = "conversation_sessions"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    title = Column(String, default="New Conversation")
    active_project_hint = Column(String)
    attention_state = Column(String, default="focused")
    context_window_tokens = Column(Integer, default=0)
    max_context_tokens = Column(Integer, default=4000)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    ended_at = Column(DateTime)


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"
    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("conversation_sessions.id"), nullable=False)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    user_message = Column(Text, nullable=False)
    turn_type = Column(String, default="question")
    tool_calls = Column(JSON, default=list)
    assistant_response = Column(Text)
    tone_used = Column(String, default="conversational")
    tokens_used = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ─── Phase 12: Knowledge Pipeline Tables ───

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    source_type = Column(String, nullable=False)
    source_url = Column(String)
    status = Column(String, default="pending")
    raw_content_length = Column(Integer, default=0)
    blocks_extracted = Column(Integer, default=0)
    entities_extracted = Column(Integer, default=0)
    errors = Column(JSON, default=list)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime)


class ExtractedEntity(Base):
    __tablename__ = "extracted_entities"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    pipeline_run_id = Column(String, ForeignKey("pipeline_runs.id"))
    entity_type = Column(String, nullable=False)
    canonical_name = Column(String, nullable=False)
    aliases = Column(JSON, default=list)
    attributes = Column(JSON, default=dict)
    confidence = Column(Float, default=0.7)
    status = Column(String, default="tentative")
    source_event_id = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SyncSchedule(Base):
    __tablename__ = "sync_schedules"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    source_type = Column(String, nullable=False)
    source_url = Column(String)
    sync_frequency = Column(String, default="daily")
    last_sync_at = Column(DateTime)
    next_sync_at = Column(DateTime)
    last_run_id = Column(String, ForeignKey("pipeline_runs.id"))
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# --- Phase 13: Predictions & Simulation Tables ---

class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    prediction_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    confidence = Column(Float, default=0.5)
    status = Column(String, default="active")
    evidence = Column(JSON, default=list)
    triggered_actions = Column(JSON, default=list)
    resolved_at = Column(DateTime)
    resolution_outcome = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    scenario_name = Column(String, nullable=False)
    parameters = Column(JSON, default=dict)
    outcomes = Column(JSON, default=list)
    confidence_range = Column(JSON, default=dict)
    run_duration_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# --- Phase 14: Personal Model Tables ---

class PersonalModel(Base):
    __tablename__ = "personal_models"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    attribute_path = Column(String, nullable=False)
    value = Column(JSON, default=dict)
    confidence = Column(Float, default=0.7)
    version = Column(Integer, default=1)
    version_history = Column(JSON, default=list)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


# --- Phase 15: World Model Tables ---

class WorldObservation(Base):
    __tablename__ = "world_observations"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    observation_type = Column(String, nullable=False)
    source = Column(String)
    content = Column(Text, nullable=False)
    relevance_score = Column(Float, default=0.5)
    extracted_at = Column(DateTime, default=datetime.datetime.utcnow)


class Opportunity(Base):
    __tablename__ = "opportunities"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    source_observation_id = Column(String, ForeignKey("world_observations.id"))
    urgency = Column(String, default="medium")
    confidence = Column(Float, default=0.5)
    estimated_impact = Column(String)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# --- Phase 16: Dashboard Cache Table ---

class DashboardPanelCache(Base):
    __tablename__ = "dashboard_panel_caches"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    panel_id = Column(String, nullable=False)
    data = Column(JSON, default=dict)
    cached_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime)

# --- Phase 17: Security Tables ---

class SecurityClassification(Base):
    __tablename__ = "security_classifications"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    content_id = Column(String, nullable=False)
    tier = Column(String, default="internal")
    auto_classified = Column(Boolean, default=True)
    confidence = Column(Float, default=0.8)
    keywords_matched = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AuditLogEntry(Base):
    __tablename__ = "audit_log_entries"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    subject = Column(String, nullable=False)
    action = Column(String, nullable=False)
    resource = Column(String)
    outcome = Column(String, default="allowed")
    context = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class SecurityPermission(Base):
    __tablename__ = "security_permissions"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    resource_id = Column(String, nullable=False)
    subject_id = Column(String, nullable=False)
    level = Column(String, default="read")
    granted_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime)


# --- Phase 19: Technology Decisions Table ---

class TechDecision(Base):
    __tablename__ = "tech_decisions"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    phase = Column(String, nullable=False)
    component = Column(String, nullable=False)
    chosen = Column(String, nullable=False)
    alternatives = Column(JSON, default=list)
    rationale = Column(Text)
    tradeoffs = Column(JSON, default=list)
    confidence = Column(Float, default=0.8)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


# --- Phase 20: Implementation Roadmap Table ---

class RoadmapMilestone(Base):
    __tablename__ = "roadmap_milestones"
    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    phase = Column(String, nullable=False)
    step_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="pending")
    priority = Column(String, default="medium")
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    progress_pct = Column(Float, default=0.0)
    dependencies = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
