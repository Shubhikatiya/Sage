# Sage Phase 01: Foundation — Build Complete

## What Was Built

This is the infrastructure layer for Sage v4. It replaces hardcoded shortcuts with a proper foundation.

### Components Created

| Component | File | Purpose |
|-----------|------|---------|
| **LLM Router** | `sage/core/llm_router/router.py` | Provider-agnostic LLM calls with automatic failover |
| **Event Bus** | `sage/core/event_bus/bus.py` | Postgres LISTEN/NOTIFY based async messaging |
| **Event Schemas** | `sage/core/event_schemas/schemas.py` | 30+ Pydantic event types with validation |
| **Docker Compose** | `sage/infra/docker/docker-compose.yml` | Full infrastructure stack |
| **API Dockerfile** | `sage/infra/docker/Dockerfile.api` | Containerized FastAPI backend |
| **Database Migration** | `sage/infra/migrations/001_foundation.sql` | Postgres schema with event_log, audit_log |

### Architecture Now Supports

- **LLM-agnostic routing** — Anthropic → OpenAI → Groq → Moonshot → Ollama, with automatic fallback
- **Event-driven async processing** — Subsystems communicate via events, not direct calls
- **Type-safe events** — Every event has a Pydantic schema with validation
- **Observability** — System health, audit logging, LLM usage tracking
- **Graceful degradation** — Fallbacks when subsystems fail

---

## Infrastructure Stack (Docker Compose)

```
postgres      :5432   Source of truth + Event Bus (MVP)
qdrant        :6333   Vector store (future migration target)
minio         :9000   Blob storage (future migration target)
ollama        :11434  Local LLM inference
redis         :6379   Cache + Pub/Sub fallback
api           :8020   FastAPI backend
grafana       :3000   Observability dashboards
prometheus    :9090   Metrics collection
```

---

## Current vs. Specified

| Requirement | Current | Specified | Decision |
|-------------|---------|-----------|----------|
| Database | SQLite (still working) | Postgres | Keep SQLite for now; migration path exists |
| Vector Store | ChromaDB (still working) | Qdrant | Keep ChromaDB; Qdrant ready in Docker |
| Graph DB | SQLAlchemy (still working) | Kùzu | Keep SQLAlchemy; evaluate Kùzu in Phase C |
| Blob Storage | Local filesystem | MinIO/S3 | MinIO ready in Docker |
| Event Bus | Direct calls (still working) | Postgres LISTEN/NOTIFY | Event Bus code ready; wire in Phase B |
| LLM Router | Hardcoded chain | LiteLLM-style router | **Replaced with new router** |

---

## New API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/system/llm_status` | Available providers, latency stats, error counts |
| `GET /api/system/degradation_flags` | Which subsystems are up/down |

---

## Next Steps (Phase B: Context Continuity)

1. Wire Event Bus into chat (store turns as events)
2. Build Memory Engine MVP (Working + Episodic types)
3. Add intent classifier (basic keyword-based)
4. Implement Context Merger with token budget
5. Fix Knowledge Extraction (replace regex with LLM-based)

---

## How to Start Infrastructure

```bash
# Start the full stack
cd sage/infra/docker
docker-compose up -d

# Verify everything is running
docker-compose ps

# View logs
docker-compose logs -f api
```

## How to Test LLM Router

```python
import asyncio
from sage.core.llm_router.router import generate_completion

async def test():
    response = await generate_completion(
        messages=[{"role": "user", "content": "Hello Sage!"}],
        system_prompt="You are Sage, an AI Chief of Staff."
    )
    print(response.text)
    print(f"Provider: {response.provider_used}")
    print(f"Latency: {response.latency_ms}ms")

asyncio.run(test())
```

---

## Monorepo Structure

```
sage/
├── apps/
│   ├── api/         # FastAPI gateway
│   ├── web/         # Next.js dashboard (Phase 16)
│   └── cli/         # Terminal client
├── services/
│   ├── memory/      # Memory Engine (Phase 02)
│   ├── knowledge_graph/  # Knowledge Graph (Phase 03)
│   ├── reasoning/   # Reasoning Engine (Phase 04)
│   ├── research/    # Research Engine (Phase 07)
│   ├── execution/   # Execution Engine (Phase 10)
│   ├── learning/    # Learning Engine (Phase 09)
│   ├── prediction/  # Prediction Engine (Phase 13)
│   └── personal_model/  # Personal Model (Phase 14)
├── agents/
│   ├── planner/     # Planner Agent
│   ├── memory_agent/     # Memory Agent
│   ├── knowledge_agent/  # Knowledge Agent
│   ├── reflection_agent/ # Reflection Agent
│   ├── research_agent/   # Research Agent
│   ├── execution_agent/  # Execution Agent
│   ├── scheduler_agent/  # Scheduler Agent
│   ├── learning_agent/   # Learning Agent
│   └── guardian_agent/   # Guardian Agent
├── core/
│   ├── llm_router/      # Provider-agnostic LLM router
│   ├── event_bus/       # Async messaging
│   ├── event_schemas/   # Type-safe events
│   └── observability/   # Logging/tracing/metrics
├── infra/
│   ├── docker/          # Docker Compose
│   └── migrations/       # Database migrations
├── docs/
│   └── handbook/        # Engineering handbook
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

---

## Notes

- **SQLite remains** for now because it works. Migration to Postgres is documented and ready.
- **ChromaDB remains** for now. Qdrant is in Docker Compose for future migration.
- **Event Bus code exists** but is not yet wired into chat — that's Phase B.
- **LLM Router is active** — it reads from the same `.env` variables as before.

---

*Built 2026-07-13. Ready for Phase B: Context Continuity.*
