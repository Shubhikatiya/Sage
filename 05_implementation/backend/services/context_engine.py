"""
Sage Context Engine — Phase 05 MVP
Resolves "what's relevant right now" — merges current conversation, active project,
time of day, recent events, and retrieved memories into a structured context payload.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import re


class IntentType(str, Enum):
    """Classified user intents."""
    BRING_ME_BACK = "bring_me_back"      # "what did I miss"
    PROJECT_QUERY = "project_query"       # Asking about a specific project
    GENERAL_CHAT = "general_chat"         # Casual conversation
    KNOWLEDGE_LOOKUP = "knowledge_lookup"  # Looking for stored info
    ACTION_REQUEST = "action_request"     # "schedule", "remind", "do"
    REFLECTION = "reflection"            # "how did I do", "review"
    LEARNING = "learning"                # "teach me", "explain"
    PLANNING = "planning"              # "plan", "schedule", "when"
    CREATIVE = "creative"              # "write", "draft", "idea"
    SYSTEM = "system"                  # Settings, help, status


class DetectedIntent(BaseModel):
    """Result of intent classification."""
    intent_type: IntentType
    confidence: float = Field(..., ge=0, le=1)
    extracted_entities: List[str] = Field(default_factory=list)
    referenced_project: Optional[str] = None
    urgency_signal: bool = Field(False)  # "urgent", "asap", "deadline"


class ContextLayer(BaseModel):
    """One layer of context (e.g., conversation history, project state)."""
    layer_name: str
    content: str
    relevance_score: float = Field(0.5, ge=0, le=1)
    source: str = Field("", description="Where this context came from")
    token_estimate: int = Field(0)


class MergedContext(BaseModel):
    """Final merged context ready for LLM consumption."""
    layers: List[ContextLayer]
    total_tokens: int
    budget_used: float = Field(0, ge=0, le=1)
    intents: List[DetectedIntent]
    retrieval_mode: str = "hybrid"
    degraded: bool = False
    notes: List[str] = Field(default_factory=list)


# ─── Intent Detection ───

INTENT_PATTERNS = {
    IntentType.BRING_ME_BACK: [
        r"\bbring me back\b", r"\bwhat did i miss\b", r"\bcatch me up\b",
        r"\bwhere were we\b", r"\bwhat happened\b", r"\bsummary of\b",
        r"\bupdate me\b", r"\bwhat\'s new\b"
    ],
    IntentType.PROJECT_QUERY: [
        r"\b(project|sage|chefbot|mcp)\b", r"\bstatus of\b", r"\bhow is.*going\b",
        r"\bprogress on\b", r"\bupdate on\b", r"\bwhat about.*(project|work)\b"
    ],
    IntentType.ACTION_REQUEST: [
        r"\b(schedule|remind|set|create|add).*(task|reminder|event|meeting)\b",
        r"\b(do|make|send|write).*(this|that|email|message)\b",
        r"\bhelp me (with|do|plan)\b"
    ],
    IntentType.REFLECTION: [
        r"\b(how did|review|reflect|retrospective|what went)\b",
        r"\b(what worked|what didn't|lessons learned)\b",
        r"\bevaluate\b"
    ],
    IntentType.PLANNING: [
        r"\b(plan|roadmap|timeline|schedule|when|deadline|due)\b",
        r"\b(next steps|what should i do|priority)\b",
        r"\bhow (do|should|can) i\b"
    ],
    IntentType.KNOWLEDGE_LOOKUP: [
        r"\b(what is|who is|where is|when did|how does)\b",
        r"\b(remind me|what was|tell me about)\b",
        r"\b(remember|recall|find|search for)\b"
    ],
    IntentType.LEARNING: [
        r"\b(teach me|explain|how to|learn|understand)\b",
        r"\b(what does|why does|how does)\b"
    ],
    IntentType.CREATIVE: [
        r"\b(write|draft|generate|create|brainstorm|idea)\b",
        r"\b(can you write|help me write|draft a)\b"
    ],
    IntentType.SYSTEM: [
        r"\b(settings|config|help|status|version|bug|error)\b",
        r"\b(how do i|how to use|what can you)\b"
    ],
}

URGENCY_PATTERNS = [
    r"\b(urgent|asap|immediately|deadline|due|overdue|late)\b",
    r"\b(quick|fast|hurry|rush|emergency)\b"
]


def detect_intent(user_message: str, conversation_history: List[Dict] = None) -> DetectedIntent:
    """
    Phase 05 MVP: Keyword + pattern based intent detection.
    Future: LLM-based classification.
    """
    message_lower = user_message.lower()
    
    scores = {}
    for intent_type, patterns in INTENT_PATTERNS.items():
        match_count = 0
        for pattern in patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                match_count += 1
        scores[intent_type] = min(match_count / max(len(patterns) * 0.3, 1), 1.0)
    
    # Boost bring_me_back for very short messages
    if len(user_message.strip()) < 15:
        scores[IntentType.BRING_ME_BACK] += 0.1
    
    # Default to general_chat if no strong signal
    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]
    
    if best_score < 0.15:
        best_intent = IntentType.GENERAL_CHAT
        best_score = 0.5
    
    # Extract entities (simple noun phrase extraction)
    entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', user_message)
    
    # Check for urgency
    urgency = any(re.search(p, message_lower, re.IGNORECASE) for p in URGENCY_PATTERNS)
    
    # Try to identify referenced project
    referenced_project = None
    project_keywords = {
        "sage": "Sage",
        "chefbot": "ChefBot",
        "mcp": "MCP Server",
        "resume": "Resume",
        "portfolio": "Portfolio"
    }
    for kw, project in project_keywords.items():
        if kw in message_lower:
            referenced_project = project
            break
    
    return DetectedIntent(
        intent_type=best_intent,
        confidence=best_score,
        extracted_entities=list(set(entities))[:5],
        referenced_project=referenced_project,
        urgency_signal=urgency
    )


# ─── Context Merger ───

class ContextMerger:
    """
    Merges multiple context layers within a token budget.
    Phase 05 MVP: Fixed budget allocation.
    Future: Dynamic attention-weighted allocation.
    """
    
    # Token budget per layer type (approximate, for 4K context window)
    DEFAULT_BUDGETS = {
        "system_prompt": 800,      # Sage personality + rules
        "conversation_history": 600,  # Recent messages
        "retrieved_memories": 800,    # Semantic search results
        "active_project": 600,        # Current project document
        "user_profile": 400,          # Personal model data
        "temporal_context": 200,      # Time of day, recent events
        "reasoning_trace": 600        # For complex queries
    }
    
    TOTAL_BUDGET = 4000
    
    def __init__(self, total_budget: int = None):
        self.total_budget = total_budget or self.TOTAL_BUDGET
    
    def merge(
        self,
        system_prompt: str = "",
        conversation_history: List[Dict] = None,
        retrieved_memories: List[Dict] = None,
        active_project: Optional[Dict] = None,
        user_profile: Optional[Dict] = None,
        temporal_notes: Optional[str] = None,
        reasoning_trace: Optional[str] = None,
        intent: Optional[DetectedIntent] = None
    ) -> MergedContext:
        """
        Merge all context layers into a single payload.
        Respects token budget with intelligent truncation.
        """
        layers = []
        total_tokens = 0
        notes = []
        
        # Layer 1: System prompt (always included, full)
        if system_prompt:
            est_tokens = len(system_prompt.split()) * 1.3
            layers.append(ContextLayer(
                layer_name="system_prompt",
                content=system_prompt,
                relevance_score=1.0,
                source="sage_config",
                token_estimate=int(est_tokens)
            ))
            total_tokens += int(est_tokens)
        
        # Layer 2: Conversation history
        if conversation_history:
            hist_text = self._format_conversation(conversation_history)
            est_tokens = len(hist_text.split()) * 1.3
            if total_tokens + est_tokens > self.total_budget * 0.6:
                # Truncate: keep last 2 messages
                hist_text = self._format_conversation(conversation_history[-2:])
                est_tokens = len(hist_text.split()) * 1.3
                notes.append("Conversation history truncated to last 2 messages")
            
            layers.append(ContextLayer(
                layer_name="conversation_history",
                content=hist_text,
                relevance_score=0.9,
                source="chat_session",
                token_estimate=int(est_tokens)
            ))
            total_tokens += int(est_tokens)
        
        # Layer 3: Retrieved memories (prioritized by intent)
        if retrieved_memories:
            mem_text = self._format_memories(retrieved_memories, intent)
            est_tokens = len(mem_text.split()) * 1.3
            
            # Memories are high priority for knowledge lookups
            priority = 0.8 if intent and intent.intent_type == IntentType.KNOWLEDGE_LOOKUP else 0.6
            
            if total_tokens + est_tokens > self.total_budget * 0.8:
                # Truncate: keep top 3 memories
                mem_text = self._format_memories(retrieved_memories[:3], intent)
                est_tokens = len(mem_text.split()) * 1.3
                notes.append("Retrieved memories truncated to top 3")
            
            layers.append(ContextLayer(
                layer_name="retrieved_memories",
                content=mem_text,
                relevance_score=priority,
                source="memory_engine",
                token_estimate=int(est_tokens)
            ))
            total_tokens += int(est_tokens)
        
        # Layer 4: Active project (if referenced)
        if active_project and intent and intent.referenced_project:
            proj_text = self._format_project(active_project)
            est_tokens = len(proj_text.split()) * 1.3
            
            layers.append(ContextLayer(
                layer_name="active_project",
                content=proj_text,
                relevance_score=0.85,
                source="knowledge_graph",
                token_estimate=int(est_tokens)
            ))
            total_tokens += int(est_tokens)
        
        # Layer 5: Temporal context
        if temporal_notes:
            est_tokens = len(temporal_notes.split()) * 1.3
            layers.append(ContextLayer(
                layer_name="temporal_context",
                content=temporal_notes,
                relevance_score=0.4,
                source="system_clock",
                token_estimate=int(est_tokens)
            ))
            total_tokens += int(est_tokens)
        
        # Check budget
        budget_used = total_tokens / self.total_budget
        if budget_used > 1.0:
            notes.append(f"Context exceeded budget: {total_tokens}/{self.total_budget} tokens")
        
        return MergedContext(
            layers=layers,
            total_tokens=total_tokens,
            budget_used=budget_used,
            intents=[intent] if intent else [],
            retrieval_mode="hybrid",
            degraded=budget_used > 1.0,
            notes=notes
        )
    
    def _format_conversation(self, messages: List[Dict]) -> str:
        """Format conversation history for LLM."""
        parts = []
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            parts.append(f"{role.capitalize()}: {content}")
        return "\n\n".join(parts)
    
    def _format_memories(self, memories: List[Dict], intent: Optional[DetectedIntent] = None) -> str:
        """Format retrieved memories."""
        if not memories:
            return ""
        
        parts = ["Relevant context from memory:"]
        for mem in memories:
            mem_type = mem.get('type', 'note')
            content = mem.get('content_preview', mem.get('content', ''))
            score = mem.get('score', 0)
            parts.append(f"  [{mem_type}] {content[:200]} (relevance: {score:.2f})")
        
        return "\n".join(parts)
    
    def _format_project(self, project: Dict) -> str:
        """Format project context."""
        parts = [f"Project: {project.get('name', 'Unknown')}"]
        if 'document' in project:
            parts.append(f"Document:\n{project['document'][:1000]}")
        return "\n".join(parts)
    
    def to_prompt(self, merged: MergedContext) -> str:
        """Convert merged context to a single prompt string."""
        sections = []
        for layer in merged.layers:
            if layer.layer_name == "system_prompt":
                sections.append(layer.content)
            else:
                sections.append(f"--- {layer.layer_name.replace('_', ' ').title()} ---\n{layer.content}")
        
        return "\n\n".join(sections)


def get_temporal_context() -> str:
    """Generate temporal context string."""
    now = datetime.utcnow()
    
    # Time of day
    hour = now.hour
    if 5 <= hour < 12:
        time_of_day = "morning"
    elif 12 <= hour < 17:
        time_of_day = "afternoon"
    elif 17 <= hour < 21:
        time_of_day = "evening"
    else:
        time_of_day = "night"
    
    # Day of week
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_name = days[now.weekday()]
    
    return f"Current time: {now.strftime('%Y-%m-%d %H:%M')} UTC ({day_name} {time_of_day})"


def build_context_for_chat(
    user_message: str,
    conversation_history: List[Dict] = None,
    system_prompt: str = "",
    workspace_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main entry point: Build complete context for a chat turn.
    Returns structured context data for the LLM service.
    """
    # Detect intent
    intent = detect_intent(user_message, conversation_history)
    
    # Build context merger
    merger = ContextMerger()
    
    # Get temporal context
    temporal = get_temporal_context()
    
    # Merge everything
    merged = merger.merge(
        system_prompt=system_prompt,
        conversation_history=conversation_history,
        temporal_notes=temporal,
        intent=intent
    )
    
    return {
        "intent": {
            "type": intent.intent_type.value,
            "confidence": intent.confidence,
            "referenced_project": intent.referenced_project,
            "urgency": intent.urgency_signal
        },
        "context_prompt": merger.to_prompt(merged),
        "layers_used": [l.layer_name for l in merged.layers],
        "total_tokens": merged.total_tokens,
        "budget_used": merged.budget_used,
        "degraded": merged.degraded,
        "notes": merged.notes
    }
