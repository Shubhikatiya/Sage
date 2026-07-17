"""
Sage Memory Engine — Phase 02 MVP
Stores and retrieves typed memories with ranking, decay, and consolidation.

Memory Types:
- working: Temporary, 3-7 items, current session
- episodic: Events with temporal context, auto-consolidates after 24h
- semantic: Facts, concepts, stable knowledge
- procedural: How-to knowledge, workflows
- source_document: Reference to uploaded documents
- extracted_insight: LLM-extracted knowledge from documents
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json
import math


class MemoryType(str, Enum):
    """Phase 02 Memory Taxonomy — 5 core types."""
    WORKING = "working"           # Short-term, 3-7 items, current session
    EPISODIC = "episodic"         # Events with temporal context
    SEMANTIC = "semantic"         # Facts, concepts, stable knowledge
    PROCEDURAL = "procedural"     # How-to knowledge, workflows
    SOURCE_DOCUMENT = "source_document"  # Uploaded document reference
    EXTRACTED_INSIGHT = "extracted_insight"  # LLM-extracted knowledge


class MemoryState(str, Enum):
    """Memory lifecycle states."""
    ACTIVE = "active"
    CONSOLIDATING = "consolidating"  # Being merged into long-term
    ARCHIVED = "archived"            # Rarely accessed, kept for completeness
    QUARANTINE = "quarantine"        # Flagged for review


class Memory(BaseModel):
    """Core memory model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    memory_type: MemoryType
    content: str = Field(..., min_length=1, max_length=10000)
    
    # Attribution
    source_event_id: str = Field(..., description="Original event that created this memory")
    source_type: str = Field("conversation", description="conversation, document, reasoning, user_edit")
    
    # Temporal
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="When this memory should auto-expire")
    last_accessed_at: Optional[datetime] = Field(None)
    
    # Importance & Ranking
    importance_score: float = Field(0.5, ge=0, le=1, description="Initial importance (0-1)")
    reinforcement_count: int = Field(0, ge=0, description="Times recalled/referenced")
    confidence: float = Field(0.7, ge=0, le=1, description="Extraction confidence")
    
    # Context
    workspace_id: Optional[str] = Field(None)
    layer: Optional[str] = Field(None, description="general, life, project, knowledge, system")
    tags: List[str] = Field(default_factory=list)
    
    # Links
    related_memory_ids: List[str] = Field(default_factory=list)
    knowledge_graph_node_id: Optional[str] = Field(None)
    
    # State
    state: MemoryState = Field(MemoryState.ACTIVE)
    
    # Computed at retrieval time
    current_score: Optional[float] = Field(None, description="Computed relevance score")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MemoryQuery(BaseModel):
    """Query for memory retrieval."""
    query_text: str = Field(..., description="Natural language query")
    memory_types: Optional[List[MemoryType]] = Field(None, description="Filter by types")
    layers: Optional[List[str]] = Field(None)
    tags: Optional[List[str]] = Field(None)
    
    # Ranking parameters
    recency_weight: float = Field(0.3, ge=0, le=1)
    importance_weight: float = Field(0.3, ge=0, le=1)
    relevance_weight: float = Field(0.4, ge=0, le=1)
    
    # Filters
    max_results: int = Field(10, ge=1, le=100)
    min_score: float = Field(0.1, ge=0, le=1)
    include_archived: bool = Field(False)
    since: Optional[datetime] = Field(None, description="Only memories after this date")


class MemoryRetrievalResult(BaseModel):
    """Result of a memory query."""
    memories: List[Memory]
    total_available: int
    query_time_ms: float
    retrieval_mode: str = Field("hybrid", description="vector, graph, keyword, or hybrid")
    degraded: bool = Field(False)


# ─── Decay Algorithm ───

def compute_memory_score(
    memory: Memory,
    now: datetime,
    recency_weight: float = 0.3,
    importance_weight: float = 0.3,
    relevance_weight: float = 0.4,
    semantic_similarity: float = 0.5
) -> float:
    """
    Compute dynamic relevance score for a memory.
    
    Formula: weighted combination of:
    - Recency (exponential decay since creation)
    - Importance (base + reinforcement bonus)
    - Semantic relevance (external input)
    """
    
    # Recency score: exponential decay since creation
    age_hours = max(0, (now - memory.created_at).total_seconds() / 3600)
    
    # Decay rate varies by memory type
    if memory.memory_type == MemoryType.WORKING:
        decay_rate = 1.0  # Fast decay (hours)
    elif memory.memory_type == MemoryType.EPISODIC:
        decay_rate = 0.1   # Medium decay (days)
    else:
        decay_rate = 0.01  # Slow decay (months/years)
    
    recency_score = math.exp(-decay_rate * age_hours)
    
    # Importance score: base + reinforcement boost
    reinforcement_bonus = min(memory.reinforcement_count * 0.05, 0.3)
    importance_score = min(memory.importance_score + reinforcement_bonus, 1.0)
    
    # Combine
    score = (
        recency_weight * recency_score +
        importance_weight * importance_score +
        relevance_weight * semantic_similarity
    )
    
    return min(max(score, 0), 1.0)


# ─── Consolidation Logic ───

def should_consolidate(memory: Memory, now: datetime) -> bool:
    """Check if an episodic memory should be consolidated."""
    if memory.memory_type != MemoryType.EPISODIC:
        return False
    if memory.state != MemoryState.ACTIVE:
        return False
    
    age_hours = (now - memory.created_at).total_seconds() / 3600
    return age_hours >= 24  # Consolidate after 24 hours


def create_consolidation_summary(memories: List[Memory]) -> str:
    """Generate a semantic summary from episodic memories."""
    if not memories:
        return ""
    
    # Simple extraction — in production, this would be LLM-based
    topics = set()
    for m in memories:
        for tag in m.tags:
            topics.add(tag)
    
    time_range = f"{memories[0].created_at.strftime('%Y-%m-%d')} to {memories[-1].created_at.strftime('%Y-%m-%d')}"
    
    return (
        f"Period: {time_range}. "
        f"Topics: {', '.join(sorted(topics)[:10])}. "
        f"Key events: {len(memories)} memories captured."
    )


# ─── SQLite Store (MVP) ───

class MemoryStore:
    """
    SQLite-backed memory store for MVP.
    Will migrate to Postgres + Qdrant in Phase 18.
    """
    
    def __init__(self, db_path: str = "sage_memories.db"):
        import sqlite3
        self.db_path = db_path
        self._init_tables()
    
    def _init_tables(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                source_event_id TEXT NOT NULL,
                source_type TEXT DEFAULT 'conversation',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                last_accessed_at TIMESTAMP,
                importance_score REAL DEFAULT 0.5,
                reinforcement_count INTEGER DEFAULT 0,
                confidence REAL DEFAULT 0.7,
                workspace_id TEXT,
                layer TEXT,
                tags TEXT,  -- JSON array
                related_memory_ids TEXT,  -- JSON array
                knowledge_graph_node_id TEXT,
                state TEXT DEFAULT 'active',
                embedding TEXT  -- JSON vector (temporary)
            )
        """)
        
        # Indexes for efficient retrieval
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memories_workspace ON memories(workspace_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memories_layer ON memories(layer)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memories_state ON memories(state)")
        
        conn.commit()
        conn.close()
    
    def write(self, memory: Memory) -> str:
        """Write a memory to the store."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO memories (
                id, memory_type, content, source_event_id, source_type,
                created_at, expires_at, last_accessed_at,
                importance_score, reinforcement_count, confidence,
                workspace_id, layer, tags, related_memory_ids,
                knowledge_graph_node_id, state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory.id, memory.memory_type.value, memory.content,
            memory.source_event_id, memory.source_type,
            memory.created_at.isoformat(),
            memory.expires_at.isoformat() if memory.expires_at else None,
            memory.last_accessed_at.isoformat() if memory.last_accessed_at else None,
            memory.importance_score, memory.reinforcement_count, memory.confidence,
            memory.workspace_id, memory.layer,
            json.dumps(memory.tags),
            json.dumps(memory.related_memory_ids),
            memory.knowledge_graph_node_id,
            memory.state.value
        ))
        
        conn.commit()
        conn.close()
        return memory.id
    
    def get(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a single memory by ID."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = cur.fetchone()
        conn.close()
        
        if row:
            return self._row_to_memory(dict(row))
        return None
    
    def search(
        self,
        query: MemoryQuery,
        now: Optional[datetime] = None
    ) -> MemoryRetrievalResult:
        """
        Search memories with ranking.
        MVP: keyword-based + temporal filtering.
        Future: hybrid (vector + graph + keyword).
        """
        import sqlite3
        start_time = datetime.utcnow()
        now = now or start_time
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Build query
        conditions = ["1=1"]
        params = []
        
        if query.memory_types:
            placeholders = ','.join('?' * len(query.memory_types))
            conditions.append(f"memory_type IN ({placeholders})")
            params.extend([mt.value for mt in query.memory_types])
        
        if query.layers:
            placeholders = ','.join('?' * len(query.layers))
            conditions.append(f"layer IN ({placeholders})")
            params.extend(query.layers)
        
        if not query.include_archived:
            conditions.append("state IN ('active', 'consolidating')")
        
        if query.since:
            conditions.append("created_at >= ?")
            params.append(query.since.isoformat())
        
        # Simple keyword matching on content
        if query.query_text:
            conditions.append("content LIKE ?")
            params.append(f"%{query.query_text}%")
        
        where_clause = " AND ".join(conditions)
        
        cur.execute(f"""
            SELECT * FROM memories 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
        """, params + [query.max_results * 3])  # Fetch extra for scoring
        
        rows = cur.fetchall()
        conn.close()
        
        # Convert and score
        memories = []
        for row in rows:
            mem = self._row_to_memory(dict(row))
            # Simple semantic similarity (keyword overlap)
            query_words = set(query.query_text.lower().split())
            content_words = set(mem.content.lower().split())
            overlap = len(query_words & content_words) / max(len(query_words), 1)
            
            mem.current_score = compute_memory_score(
                mem, now,
                query.recency_weight,
                query.importance_weight,
                query.relevance_weight,
                semantic_similarity=overlap
            )
            memories.append(mem)
        
        # Sort by score and filter
        memories.sort(key=lambda m: m.current_score or 0, reverse=True)
        memories = [m for m in memories if (m.current_score or 0) >= query.min_score]
        memories = memories[:query.max_results]
        
        elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return MemoryRetrievalResult(
            memories=memories,
            total_available=len(rows),
            query_time_ms=elapsed,
            retrieval_mode="keyword+temporal",
            degraded=False
        )
    
    def reinforce(self, memory_id: str) -> bool:
        """Increment reinforcement count when a memory is recalled."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE memories 
            SET reinforcement_count = reinforcement_count + 1,
                last_accessed_at = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), memory_id))
        
        success = cur.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def update_state(self, memory_id: str, state: MemoryState) -> bool:
        """Update memory lifecycle state."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute(
            "UPDATE memories SET state = ? WHERE id = ?",
            (state.value, memory_id)
        )
        
        success = cur.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def get_stale_memories(self, threshold_hours: float = 24) -> List[Memory]:
        """Get episodic memories ready for consolidation."""
        import sqlite3
        cutoff = datetime.utcnow() - timedelta(hours=threshold_hours)
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("""
            SELECT * FROM memories 
            WHERE memory_type = 'episodic'
            AND state = 'active'
            AND created_at <= ?
            ORDER BY created_at ASC
        """, (cutoff.isoformat(),))
        
        rows = cur.fetchall()
        conn.close()
        
        return [self._row_to_memory(dict(row)) for row in rows]
    
    def _row_to_memory(self, row: Dict) -> Memory:
        """Convert SQLite row to Memory model."""
        return Memory(
            id=row["id"],
            memory_type=MemoryType(row["memory_type"]),
            content=row["content"],
            source_event_id=row["source_event_id"],
            source_type=row.get("source_type", "conversation"),
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row.get("expires_at") else None,
            last_accessed_at=datetime.fromisoformat(row["last_accessed_at"]) if row.get("last_accessed_at") else None,
            importance_score=row.get("importance_score", 0.5),
            reinforcement_count=row.get("reinforcement_count", 0),
            confidence=row.get("confidence", 0.7),
            workspace_id=row.get("workspace_id"),
            layer=row.get("layer"),
            tags=json.loads(row.get("tags", "[]")),
            related_memory_ids=json.loads(row.get("related_memory_ids", "[]")),
            knowledge_graph_node_id=row.get("knowledge_graph_node_id"),
            state=MemoryState(row.get("state", "active"))
        )


# Singleton
_store: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    """Get or create the global Memory Store."""
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store
