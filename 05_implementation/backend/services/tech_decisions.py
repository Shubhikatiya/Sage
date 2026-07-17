"""
Sage Technology Decisions — Phase 19
Consolidated reference for technology choices across all 20 phases.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TechnologyChoice:
    """A single technology decision."""
    component: str = ""
    chosen: str = ""
    alternatives: List[str] = field(default_factory=list)
    rationale: str = ""
    tradeoffs: str = ""
    escalation_path: str = ""
    confidence: str = "high"  # high, medium, low
    phase: str = ""


class TechnologyDecisionRegistry:
    """
    Phase 19: Technology Decisions.
    Documents all architectural choices made across the 20-phase build.
    """
    
    def __init__(self):
        self.decisions: List[TechnologyChoice] = []
        self._load_decisions()
    
    def _load_decisions(self):
        """Load all technology decisions from the build."""
        
        # Phase 01: Foundation
        self.decisions.extend([
            TechnologyChoice(
                component="Web Framework",
                chosen="FastAPI (Python)",
                alternatives=["Django", "Flask", "Node.js/Express", "Go/Gin"],
                rationale="FastAPI provides native async support, automatic OpenAPI generation, and excellent type safety via Pydantic. This aligns with Sage's need for streaming responses (Phase 11) and concurrent engine calls.",
                tradeoffs="Python GIL limits true parallelism for CPU-bound tasks, but Sage is I/O-bound (LLM calls, database queries).",
                escalation_path="If Python performance becomes a bottleneck, consider Rust/Tokio for the event bus or Go for the API gateway.",
                phase="Phase 01"
            ),
            TechnologyChoice(
                component="Database",
                chosen="SQLite (MVP) → Postgres (Production)",
                alternatives=["MySQL", "MongoDB", "CockroachDB", "DuckDB"],
                rationale="SQLite requires zero configuration for MVP, is file-backed (easy backup), and supports full SQL. Postgres chosen for production for LISTEN/NOTIFY (Phase 01 Event Bus), JSONB support, and ecosystem maturity.",
                tradeoffs="SQLite has write concurrency limits (WAL mode helps). Postgres adds operational complexity.",
                escalation_path="Use Postgres Docker container from sage/infra/docker-compose.yml. For hyperscale, consider CockroachDB or YugabyteDB.",
                phase="Phase 01"
            ),
            TechnologyChoice(
                component="Vector Store",
                chosen="ChromaDB",
                alternatives=["Qdrant", "Pinecone", "Weaviate", "Milvus", "pgvector"],
                rationale="ChromaDB is embedded-friendly (no external service required), supports metadata filtering, and has a simple Python API. Chosen for MVP simplicity.",
                tradeoffs="ChromaDB is not battle-tested at massive scale. Query latency can degrade with millions of vectors.",
                escalation_path="Switch to Qdrant (already configured in Docker Compose) or pgvector when scale demands it. Qdrant offers better performance and filter composition.",
                phase="Phase 01"
            ),
            TechnologyChoice(
                component="Graph Store",
                chosen="SQLAlchemy + adjacency list",
                alternatives=["Neo4j", "Kùzu", "Apache TinkerPop", "RDF triple store"],
                rationale="For MVP, a relational graph model (nodes + edges tables) with SQLAlchemy ORM provides sufficient graph traversal without adding another database. Single database simplifies backups.",
                tradeoffs="Recursive queries are verbose in SQL. Complex graph algorithms (PageRank, community detection) require application-layer implementation.",
                escalation_path="Migrate to Kùzu (embedded graph DB, configured in Docker) when complex graph analytics are needed. Kùzu is local-first and fast.",
                phase="Phase 01"
            ),
            TechnologyChoice(
                component="LLM Router",
                chosen="Custom Python router with async failover",
                alternatives=["LangChain", "LlamaIndex", "LiteLLM Proxy", "Ollama native"],
                rationale="Custom router provides full control over failover logic, cost tracking, and provider-specific parameter tuning. Avoids dependency bloat from full frameworks.",
                tradeoffs="Must maintain adapter code for each provider API. No built-in prompt caching or batching.",
                escalation_path="Evaluate LiteLLM Proxy if provider count exceeds 5 or team wants unified API key management.",
                phase="Phase 01"
            ),
            TechnologyChoice(
                component="Event Bus",
                chosen="Python in-memory with Postgres LISTEN/NOTIFY upgrade path",
                alternatives=["Redis Pub/Sub", "RabbitMQ", "Apache Kafka", "NATS"],
                rationale="In-memory event bus requires zero infrastructure for MVP. Postgres LISTEN/NOTIFY provides durable, restart-safe messaging when operational requirements demand it.",
                tradeoffs="In-memory bus loses events on restart. LISTEN/NOTIFY doesn't handle backpressure well.",
                escalation_path="Redis Streams (already in Docker Compose) for persistence and horizontal scaling. Kafka only if Sage becomes a multi-instance deployment.",
                phase="Phase 01"
            ),
            TechnologyChoice(
                component="Frontend",
                chosen="React + Vite + Tailwind CSS",
                alternatives=["Vue.js", "Svelte", "Next.js", "Plain HTML/JS"],
                rationale="React is the team's existing skill. Vite provides fast dev server and optimized builds. Tailwind enables rapid UI iteration without CSS files.",
                tradeoffs="React bundle size is larger than Svelte/Vue. No server-side rendering (not needed for a local-first app).",
                escalation_path="If SSR or static generation becomes needed (e.g., sharing dashboards), migrate to Next.js or Astro.",
                phase="Phase 01"
            ),
        ])
        
        # Phase 02: Memory Engine
        self.decisions.append(TechnologyChoice(
            component="Memory Storage",
            chosen="SQLite + ChromaDB hybrid",
            alternatives=["Pure vector DB", "Pure relational", "Redis"],
            rationale="Episodic and semantic memories stored in SQLite for structured querying (time ranges, types). Vector embeddings in ChromaDB for semantic similarity search. Hybrid gives best of both worlds.",
            tradeoffs="Dual-write consistency risk. Must keep SQLite and ChromaDB in sync on memory creation/deletion.",
            escalation_path="Migrate to Postgres + pgvector for unified storage, or use Qdrant's metadata filtering to consolidate.",
            phase="Phase 02"
        ))
        
        # Phase 08: Multi-Agent System
        self.decisions.append(TechnologyChoice(
            component="Agent Orchestration",
            chosen="Custom Python orchestrator with event bus",
            alternatives=["CrewAI", "AutoGen", "LangGraph", "Prefect"],
            rationale="Custom orchestrator gives full control over agent selection, handoff protocols, and observability. No framework magic means predictable behavior. Agents are thin wrappers over engine APIs.",
            tradeoffs="Must implement retry, timeout, and circuit breaker logic manually (though FastAPI provides some).",
            escalation_path="If agent workflows become complex DAGs, evaluate LangGraph or Prefect for workflow management. Keep Sage's agent definitions separate from workflow engine.",
            phase="Phase 08"
        ))
        
        # Phase 17: Security
        self.decisions.append(TechnologyChoice(
            component="Authentication",
            chosen="Not implemented (single-user local-first)",
            alternatives=["JWT", "OAuth2", "API Keys", "mTLS"],
            rationale="Sage v4 is explicitly local-first and single-user. Authentication adds complexity without security benefit when app runs on localhost.",
            tradeoffs="No multi-user support. Cannot expose API to internet without adding auth layer.",
            escalation_path="Add JWT-based auth with refresh tokens if multi-user or cloud deployment is needed. OAuth2 integration for enterprise SSO.",
            phase="Phase 17"
        ))
    
    def get_decisions(self, phase: Optional[str] = None) -> List[TechnologyChoice]:
        """Get decisions, optionally filtered by phase."""
        if phase:
            return [d for d in self.decisions if d.phase == phase]
        return self.decisions
    
    def get_by_component(self, component: str) -> List[TechnologyChoice]:
        """Get decisions for a specific component."""
        return [d for d in self.decisions if component.lower() in d.component.lower()]
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Export all decisions as structured data."""
        return {
            "version": "v4.0.0",
            "phases_covered": "01-20",
            "total_decisions": len(self.decisions),
            "decisions": [
                {
                    "phase": d.phase,
                    "component": d.component,
                    "chosen": d.chosen,
                    "alternatives": d.alternatives,
                    "rationale": d.rationale,
                    "tradeoffs": d.tradeoffs,
                    "escalation_path": d.escalation_path,
                    "confidence": d.confidence
                }
                for d in self.decisions
            ]
        }
    
    def to_markdown(self) -> str:
        """Generate a markdown reference document."""
        lines = [
            "# Sage Technology Decisions (Phase 19)",
            "",
            f"**Version:** v4.0.0  ",
            f"**Phases Covered:** 01-20  ",
            f"**Total Decisions:** {len(self.decisions)}",
            "",
            "---",
            ""
        ]
        
        for d in self.decisions:
            lines.extend([
                f"## {d.component}",
                "",
                f"**Phase:** {d.phase}",
                f"**Chosen:** {d.chosen}",
                f"**Confidence:** {d.confidence}",
                "",
                "### Alternatives Considered",
                "" + "\n".join(f"- {alt}" for alt in d.alternatives) + "",
                "",
                "### Rationale",
                d.rationale,
                "",
                "### Tradeoffs",
                d.tradeoffs,
                "",
                "### Escalation Path",
                d.escalation_path,
                "",
                "---",
                ""
            ])
        
        return "\n".join(lines)


# Singleton
_tech_registry: Optional[TechnologyDecisionRegistry] = None


def get_tech_registry() -> TechnologyDecisionRegistry:
    """Get or create the global Technology Decision Registry."""
    global _tech_registry
    if _tech_registry is None:
        _tech_registry = TechnologyDecisionRegistry()
    return _tech_registry
