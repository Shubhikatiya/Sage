"""
Sage Event Bus — MVP Implementation
Phase 01: Foundation — replaces direct function calls with async events.
Gracefully falls back to in-memory when Postgres is unavailable.
"""

import json
import asyncio
import threading
import select
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import uuid

# Try to import psycopg2
_HAVE_POSTGRES = False
try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    _HAVE_POSTGRES = True
except ImportError:
    pass


class EventType(str, Enum):
    """Standard event types across all subsystems."""
    MEMORY_WRITTEN = "memory.written"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_CONSOLIDATED = "memory.consolidated"
    GRAPH_ENTITY_CREATED = "graph.entity_created"
    GRAPH_RELATIONSHIP_CREATED = "graph.relationship_created"
    GRAPH_ENTITY_RESOLVED = "graph.entity_resolved"
    DOCUMENT_INGESTED = "document.ingested"
    DOCUMENT_EXTRACTED = "document.extracted"
    DOCUMENT_APPROVED = "document.approved"
    CONVERSATION_TURN = "conversation.turn"
    CONVERSATION_ENDED = "conversation.ended"
    REASONING_STARTED = "reasoning.started"
    REASONING_COMPLETED = "reasoning.completed"
    AGENT_TASK_ASSIGNED = "agent.task_assigned"
    AGENT_TASK_COMPLETED = "agent.task_completed"
    AGENT_TASK_FAILED = "agent.task_failed"
    FEEDBACK_RECEIVED = "learning.feedback_received"
    MODEL_UPDATED = "learning.model_updated"
    SYSTEM_DEGRADED = "system.degraded"
    SYSTEM_RECOVERED = "system.recovered"
    USER_CONNECTED = "user.connected"
    USER_DISCONNECTED = "user.disconnected"


@dataclass
class SageEvent:
    """Standard event envelope."""
    event_type: EventType
    payload: Dict[str, Any]
    source: str
    timestamp: str = ""
    event_id: str = ""
    correlation_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
    
    def to_json(self) -> str:
        return json.dumps({
            "event_type": self.event_type.value,
            "payload": self.payload,
            "source": self.source,
            "timestamp": self.timestamp,
            "event_id": self.event_id,
            "correlation_id": self.correlation_id
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> "SageEvent":
        data = json.loads(json_str)
        return cls(
            event_type=EventType(data["event_type"]),
            payload=data["payload"],
            source=data["source"],
            timestamp=data["timestamp"],
            event_id=data["event_id"],
            correlation_id=data.get("correlation_id")
        )


class EventBus:
    """
    Event Bus with graceful Postgres → in-memory fallback.
    Phase 01 MVP: Works even without Postgres installed.
    """
    
    def __init__(self, dsn: str = ""):
        self.dsn = dsn or self._get_dsn()
        self._use_postgres = _HAVE_POSTGRES and self._can_connect()
        self._local_handlers: Dict[EventType, List[Callable]] = {}
        self._event_log: List[SageEvent] = []  # In-memory fallback store
        self._listen_thread = None
        self._running = False
        
        if self._use_postgres:
            try:
                self._ensure_table()
                print("EventBus: Postgres mode active")
            except Exception as e:
                print(f"EventBus: Postgres init failed ({e}), falling back to in-memory")
                self._use_postgres = False
        else:
            print("EventBus: In-memory mode (psycopg2 not available)")
    
    def _get_dsn(self) -> str:
        import os
        return os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sage")
    
    def _can_connect(self) -> bool:
        """Test if Postgres is actually reachable."""
        try:
            conn = psycopg2.connect(self.dsn, connect_timeout=2)
            conn.close()
            return True
        except Exception:
            return False
    
    def _ensure_table(self):
        """Ensure event log table exists in Postgres."""
        conn = psycopg2.connect(self.dsn)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS event_log (
                id SERIAL PRIMARY KEY,
                event_type VARCHAR(100) NOT NULL,
                payload JSONB NOT NULL,
                source VARCHAR(100) NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                event_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
                correlation_id UUID,
                processed BOOLEAN DEFAULT FALSE
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_log_type 
            ON event_log(event_type, timestamp DESC)
        """)
        conn.commit()
        cur.close()
        conn.close()
    
    def emit(self, event: SageEvent) -> bool:
        """Emit an event. Stores in DB if available, always triggers local handlers."""
        # Always store in memory log
        self._event_log.append(event)
        
        # Try Postgres if available
        if self._use_postgres:
            try:
                conn = psycopg2.connect(self.dsn)
                conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO event_log (event_type, payload, source, event_id, correlation_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (event.event_type.value, json.dumps(event.payload),
                      event.source, event.event_id, event.correlation_id))
                conn.commit()
                cur.close()
                conn.close()
            except Exception as e:
                print(f"EventBus DB emit failed: {e}")
        
        # Always trigger local handlers
        self._trigger_local_handlers(event)
        return True
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe to an event type."""
        if event_type not in self._local_handlers:
            self._local_handlers[event_type] = []
        self._local_handlers[event_type].append(handler)
    
    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Unsubscribe from an event type."""
        if event_type in self._local_handlers:
            if handler in self._local_handlers[event_type]:
                self._local_handlers[event_type].remove(handler)
    
    def _trigger_local_handlers(self, event: SageEvent):
        """Trigger all local handlers for an event."""
        handlers = self._local_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event))
                else:
                    handler(event)
            except Exception as e:
                print(f"Event handler error: {e}")
    
    def start_listening(self):
        """Start background listener thread (Postgres only)."""
        if not self._use_postgres or self._running:
            return
        self._running = True
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()
    
    def _listen_loop(self):
        """Background LISTEN thread (Postgres only)."""
        try:
            conn = psycopg2.connect(self.dsn)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()
            for et in EventType:
                cur.execute(f"LISTEN {et.value}")
            print("EventBus: Listening for events...")
            while self._running:
                if select.select([conn], [], [], 1) == ([], [], []):
                    continue
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    try:
                        event = SageEvent.from_json(notify.payload)
                        self._trigger_local_handlers(event)
                    except Exception as e:
                        print(f"Event parse error: {e}")
        except Exception as e:
            print(f"EventBus listen error: {e}")
    
    def stop(self):
        self._running = False
    
    def get_events(
        self,
        event_type: Optional[EventType] = None,
        source: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SageEvent]:
        """Query event log."""
        if self._use_postgres:
            try:
                return self._get_events_db(event_type, source, since, limit)
            except Exception:
                pass
        
        # Fallback: query in-memory log
        results = self._event_log[:]
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if source:
            results = [e for e in results if e.source == source]
        if since:
            results = [e for e in results if datetime.fromisoformat(e.timestamp) >= since]
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]
    
    def _get_events_db(self, event_type, source, since, limit) -> List[SageEvent]:
        conn = psycopg2.connect(self.dsn)
        cur = conn.cursor()
        query = "SELECT event_type, payload, source, timestamp, event_id, correlation_id FROM event_log WHERE 1=1"
        params = []
        if event_type:
            query += " AND event_type = %s"
            params.append(event_type.value)
        if source:
            query += " AND source = %s"
            params.append(source)
        if since:
            query += " AND timestamp >= %s"
            params.append(since)
        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        cur.execute(query, params)
        rows = cur.fetchall()
        events = []
        for row in rows:
            events.append(SageEvent(
                event_type=EventType(row[0]), payload=row[1], source=row[2],
                timestamp=row[3].isoformat(), event_id=row[4], correlation_id=row[5]
            ))
        cur.close()
        conn.close()
        return events


# Singleton
_bus: Optional[EventBus] = None


def get_bus() -> EventBus:
    """Get or create the global Event Bus instance."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


def emit_event(
    event_type: EventType,
    payload: Dict[str, Any],
    source: str,
    correlation_id: Optional[str] = None
) -> bool:
    """Quick emit helper."""
    bus = get_bus()
    event = SageEvent(
        event_type=event_type, payload=payload, source=source,
        correlation_id=correlation_id
    )
    return bus.emit(event)
