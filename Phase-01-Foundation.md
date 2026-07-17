# Sage — Engineering Handbook
## Phase 01: Foundation — Vision & Complete System Architecture

> Status: Living document. This is Phase 1 of an N-phase handbook. Each phase is self-contained but assumes the definitions established here.

---

## 1. System Vision

### 1.1 Mission

Sage is a persistent cognitive partner: a system that accumulates a structured, queryable model of one person's mind, work, and world over years, and uses that model to reconstruct context, surface what matters, and support decisions — without requiring the person to re-explain themselves every time they return.

The test of success is not "does it answer questions." It's: **after a six-month absence, can the person type "bring me back" and receive an accurate, prioritized reconstruction of what mattered, what's unfinished, and what changed?**

### 1.2 Core Philosophy

1. **Memory is the product, not the chat.** The conversational interface is a thin client over a memory and reasoning substrate. If the substrate disappeared, the chat would be worthless.
2. **Structure over vibes.** Every piece of information Sage ingests should eventually resolve to typed entities and relationships, not just embeddings floating in a vector store. Embeddings are a retrieval mechanism, not the source of truth.
3. **Explainability is non-negotiable.** Every claim Sage makes about the user's past, priorities, or recommendations must be traceable to source events. No silent hallucinated context.
4. **Local-first, cloud-optional.** The user's personal model is the most sensitive data they own. Default to local storage and local inference where feasible; treat cloud LLM calls as a stateless compute service, not a data store.
5. **Everything decays and gets re-scored.** Nothing is permanently "important." Memory relevance is a function of recency, reinforcement, and current context — recomputed, not fixed at write time.
6. **Composable over monolithic.** Every subsystem (memory, knowledge graph, reasoning, research, execution) is independently addressable via an API and independently testable. The orchestration layer is replaceable; the subsystems are the durable investment.

### 1.3 Guiding Principles

| Principle | What it means in practice |
|---|---|
| Persistent | State survives across sessions, machines, and months of inactivity by default |
| Context-aware | Every response is conditioned on retrieved memory + current inferred context, not just the current message |
| Self-improving | The system has explicit feedback loops (corrections, outcomes) that update its models, not just its data |
| Modular | Subsystems communicate over defined APIs/events, never through shared mutable state |
| Multi-agent | Distinct reasoning responsibilities (planning, research, memory curation, reflection) are separated into agents with distinct prompts, tools, and failure modes |
| LLM-agnostic | No subsystem hardcodes a specific model provider; all LLM calls go through an abstraction layer (LiteLLM-style router) |
| Privacy-first | PII and personal-model data are encrypted at rest; the user can inspect, export, and delete anything |
| Observable | Every agent action, memory write, and retrieval is logged with enough detail to reconstruct "why did Sage say that" |
| Recoverable | Any subsystem can be rebuilt from an event log; nothing is a single point of unrecoverable truth except the append-only event store |

### 1.4 Non-Goals (Explicitly Out of Scope)

Being explicit about non-goals is as important as the goals, because scope creep is the primary failure mode of a project like this.

- Sage is **not** a general-purpose chatbot competing with ChatGPT/Claude as a product. It is a personal system with one user (architecturally, single-tenant first; multi-tenant is a *possible* later phase, not a requirement).
- Sage does **not** try to achieve AGI-style general reasoning. It orchestrates existing frontier LLMs; it does not train foundation models.
- Sage does **not** replace human judgment on high-stakes decisions (career, financial, legal). It surfaces evidence and trade-offs; it does not issue verdicts.
- Sage is **not** a real-time surveillance system. It ingests what the user explicitly feeds it or explicitly connects (email, calendar, notes) — it does not passively record screen activity, keystrokes, or audio without explicit, revocable consent per source.
- Phase 1 does **not** include a mobile app, multi-user collaboration, or a public API. Those are post-MVP.

### 1.5 Design Constraints

- **Single-user, multi-device.** Architecture assumes one human's data graph, accessed from multiple devices (laptop, phone, server). This simplifies auth and sharding decisions significantly versus a SaaS multi-tenant design.
- **Cost ceiling.** Because this is a personal system, not a funded product, every design must degrade gracefully to zero/low marginal cost (local models, free-tier infra) while still supporting a "burst to frontier LLM" mode for hard reasoning tasks.
- **Solo-maintainer reality.** Shubhi is (at least initially) the only engineer. Architecture must favor boring, well-documented technology over cutting-edge tools that require constant babysitting. Every subsystem needs to be resumable after months of not being touched — the same property Sage provides to its user, the codebase must provide to its maintainer.
- **Incremental value.** Every phase must produce something independently useful. Phase 1 with just memory + retrieval should already beat "searching your own Notion" before reasoning/agents/prediction exist.

---

## 2. Complete System Architecture

### 2.1 System Map (ASCII)

```
                                   ┌────────────────────────────┐
                                   │        CLIENT LAYER         │
                                   │  CLI / Web UI / Mobile(later)│
                                   └──────────────┬───────────────┘
                                                   │ HTTPS / WS
                                   ┌──────────────▼───────────────┐
                                   │        API GATEWAY            │
                                   │  Auth · Rate limit · Routing  │
                                   └──────────────┬───────────────┘
                                                   │
                     ┌─────────────────────────────┼─────────────────────────────┐
                     │                              │                              │
           ┌─────────▼─────────┐        ┌──────────▼──────────┐         ┌─────────▼─────────┐
           │ CONVERSATION ENGINE│        │   ORCHESTRATOR /     │         │  EXECUTION ENGINE  │
           │ (dialogue, persona,│◄──────►│   MULTI-AGENT ROUTER │◄───────►│ (tasks, workflows,  │
           │  streaming, state) │        │  (planner, dispatch) │         │  scheduling, human  │
           └─────────┬─────────┘        └──────────┬──────────┘         │  approval loops)    │
                     │                              │                    └─────────┬─────────┘
                     │            ┌─────────────────┼─────────────────┐            │
                     │            │                 │                 │            │
           ┌─────────▼───┐ ┌──────▼──────┐ ┌────────▼───────┐ ┌───────▼──────┐ ┌───▼────────┐
           │ CONTEXT      │ │  MEMORY     │ │  KNOWLEDGE     │ │  REASONING   │ │  RESEARCH   │
           │ ENGINE       │ │  ENGINE     │ │  GRAPH         │ │  ENGINE      │ │  ENGINE     │
           │ (who/what/   │ │ (working,   │ │ (entities,     │ │ (plan, tree  │ │ (web, PDF,  │
           │  where now)  │ │  episodic,  │ │  relations,    │ │  search,     │ │  OCR, cite  │
           │              │ │  semantic…) │ │  timeline)     │ │  reflection) │ │  graph)     │
           └──────┬───────┘ └──────┬──────┘ └────────┬───────┘ └──────┬───────┘ └─────┬──────┘
                  │                │                 │                │               │
                  └────────────────┴────────┬────────┴────────────────┴───────────────┘
                                             │
                                  ┌──────────▼───────────┐
                                  │   EVENT BUS (async)    │
                                  │  Kafka/NATS/Postgres    │
                                  │  LISTEN-NOTIFY (MVP)    │
                                  └──────────┬───────────┘
                                             │
                     ┌────────────────────────┼────────────────────────┐
                     │                        │                        │
           ┌─────────▼─────────┐   ┌──────────▼──────────┐  ┌──────────▼──────────┐
           │  RELATIONAL STORE  │   │    VECTOR STORE      │  │     GRAPH STORE       │
           │  Postgres          │   │    Qdrant             │  │     Kùzu / Neo4j       │
           │  (source of truth, │   │    (semantic search,  │  │     (entities,         │
           │   events, audit)   │   │     hybrid retrieval) │  │      relationships)    │
           └────────────────────┘   └───────────────────────┘  └────────────────────────┘
                     │
           ┌─────────▼─────────┐
           │   BLOB STORAGE      │
           │   MinIO/S3           │
           │   (raw docs, images, │
           │    PDFs, audio)       │
           └───────────────────────┘

  Cross-cutting (touch every layer above):
  ┌────────────────────────────────────────────────────────────────────────┐
  │ LEARNING ENGINE · PREDICTION ENGINE · PERSONAL MODEL · SECURITY LAYER   │
  │ OBSERVABILITY (logs/traces/metrics) · LLM ROUTER (LiteLLM-style)        │
  └────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Subsystem Inventory

| Subsystem | Responsibility | Depends on | Exposes |
|---|---|---|---|
| Client Layer | UI surfaces (chat, dashboard, CLI) | API Gateway | — |
| API Gateway | AuthN/Z, rate limiting, request routing | — | REST + WS |
| Conversation Engine | Dialogue state, persona, streaming responses, tool-call orchestration for a single turn | Context Engine, Memory Engine, LLM Router | `/chat` |
| Context Engine | Resolves "what's relevant right now" — merges current conversation, active project, time of day, recent events | Memory Engine, Knowledge Graph | `/context/resolve` |
| Memory Engine | Stores/retrieves all memory types; owns compression, decay, ranking | Postgres, Vector Store | `/memory/*` (see Phase 02) |
| Knowledge Graph | Entity/relationship store; powers graph traversal + hybrid retrieval | Graph Store | `/graph/*` |
| Reasoning Engine | Multi-step reasoning, planning, self-critique, hypothesis generation | LLM Router, Memory, Knowledge Graph | `/reason/*` |
| Research Engine | Web/document research, ingestion, citation tracking | Blob Storage, external web | `/research/*` |
| Orchestrator / Multi-Agent Router | Decomposes a request into agent tasks, dispatches, merges results | All engines | internal (event bus) |
| Execution Engine | Tasks, scheduling, workflows, human-approval gates | Orchestrator, external integrations (calendar, email) | `/execute/*` |
| Learning Engine | Consumes feedback/outcome events, updates personal model + memory weights | Event Bus | internal |
| Prediction Engine | Forecasts deadlines, risks, forgotten work from graph + memory state | Knowledge Graph, Memory | `/predict/*` |
| Personal Model | Structured, versioned model of the user (values, skills, patterns) | Learning Engine | `/model/user` |
| Security Layer | Encryption, secrets, audit log, permissioning | — | cross-cutting |
| LLM Router | Provider-agnostic completion/embedding calls, cost/latency-aware routing | External LLM APIs / local models | `/llm/complete`, `/llm/embed` |
| Observability | Logging, tracing, metrics for every subsystem call | — | dashboards |

### 2.3 Communication Paths & Boundaries

Two mechanisms only — this constraint is deliberate, to keep a solo-maintained system debuggable:

1. **Synchronous request/response** for anything the user is waiting on (a chat turn, a `/context/resolve` call). Implemented as plain HTTP/gRPC internally.
2. **Asynchronous events** for anything that happens *because of* a synchronous action but doesn't need to block it — a memory write triggering re-embedding, a conversation ending triggering a reflection pass, a document ingestion triggering knowledge-graph extraction.

No subsystem is allowed to reach into another subsystem's database directly. Postgres is the only store multiple subsystems may read for **audit/event data**, but each subsystem owns its own tables/schema and other subsystems access it only through its API.

### 2.4 Failure Isolation

| Failure | Blast radius without isolation | Isolation strategy |
|---|---|---|
| Vector store down | Semantic search fails everywhere | Memory Engine falls back to keyword/graph retrieval; degrade, don't crash |
| LLM provider outage | All reasoning/conversation halts | LLM Router has ≥2 configured providers + local model fallback (Ollama) for degraded-mode responses |
| Graph DB down | Context reconstruction incomplete | Context Engine returns memory-only context with a flag `graph_unavailable: true`; UI shows partial reconstruction, not silence |
| Research Engine hangs on a slow site | Blocks the whole agent turn | All external fetches run with hard timeouts + circuit breakers; orchestrator treats research as cancellable, not blocking |
| Event bus backlog | Learning/prediction updates lag | Async by design — acceptable staleness window (documented, initially 24h) rather than a system requirement |
| Bad extraction poisons knowledge graph | Wrong facts propagate into future context | All graph writes are versioned and attributed to a source event; a "quarantine" review queue holds low-confidence extractions before they affect retrieval ranking |

### 2.5 Data Ownership Boundaries

- **Postgres** = source of truth for structured records + the append-only event log. If every other store were deleted, Postgres + Blob Storage could rebuild them.
- **Vector Store** = derived index. Rebuildable from Postgres/Blob at any time; never authoritative.
- **Graph Store** = derived index of entities/relationships, extracted from Postgres records. Also rebuildable, but rebuild is expensive (LLM extraction cost), so it's still backed up independently rather than only relying on replay.
- **Blob Storage** = raw source material (original PDFs, images, audio). Never modified after write; everything downstream is a derivation of these bytes.

---

## 3. Folder Structure (Monorepo, MVP)

```
sage/
├── apps/
│   ├── api/                  # FastAPI gateway + conversation engine
│   ├── web/                  # Next.js dashboard (Phase 16)
│   └── cli/                  # "bring me back" terminal client
├── services/
│   ├── memory/                # Memory Engine (own DB migrations, own tests)
│   ├── knowledge_graph/
│   ├── reasoning/
│   ├── research/
│   ├── execution/
│   ├── learning/
│   ├── prediction/
│   └── personal_model/
├── agents/
│   ├── planner/
│   ├── memory_agent/
│   ├── knowledge_agent/
│   ├── reflection_agent/
│   ├── research_agent/
│   ├── execution_agent/
│   ├── scheduler_agent/
│   ├── learning_agent/
│   └── guardian_agent/        # safety/consistency checks on other agents' outputs
├── core/
│   ├── llm_router/             # provider-agnostic completion/embedding client
│   ├── event_bus/
│   ├── event_schemas/          # versioned Pydantic schemas for every event type
│   └── observability/
├── infra/
│   ├── docker/
│   ├── migrations/
│   └── terraform/ (later, if cloud-scaled)
├── docs/
│   └── handbook/                # this document set
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

Each `services/*` directory is independently runnable and independently testable — a hard requirement from the design principles, and also what makes it possible for a solo maintainer to return to one subsystem after months away without reloading the whole system in their head.

---

## 4. Technology Stack — Decisions at a Glance

Full tradeoff tables live in Phase 19 (Technology Decisions). Summary for Phase 1 orientation:

| Layer | MVP choice | Why (one line) |
|---|---|---|
| API framework | FastAPI | Async-native, typed, minimal ceremony, huge ecosystem overlap with AI tooling |
| Relational DB | Postgres | Battle-tested, supports JSONB for semi-structured events, `LISTEN/NOTIFY` doubles as MVP event bus |
| Vector DB | Qdrant | Self-hostable, fast, good hybrid (sparse+dense) search support, low ops burden |
| Graph DB | Kùzu (MVP) → Neo4j (scale) | Kùzu is embedded/local, zero-ops, perfect for single-user local-first; Neo4j if/when cloud-scaled multi-device sync is needed |
| Blob storage | MinIO (local) / S3 (cloud) | S3-compatible API either way, no migration cost later |
| Event bus | Postgres LISTEN/NOTIFY (MVP) → NATS (scale) | Don't operate Kafka for a single-user system on day one |
| LLM access | LiteLLM-style router | Provider-agnostic from day one, so "LLM-agnostic" isn't a Phase 20 retrofit |
| Local inference | Ollama | Fallback + privacy-sensitive tasks (personal model updates) run local |
| Orchestration | Custom lightweight orchestrator (not LangGraph/CrewAI initially) | Matches Shubhi's existing first-principles approach (see ChefBot precedent); avoids framework lock-in before requirements are proven |

---

## 5. Roadmap Overview (Detail in Phase 20)

```
MVP (Phase A) ──► Context Continuity (Phase B) ──► Knowledge Graph + Hybrid Retrieval (Phase C)
     │                                                            │
     ▼                                                            ▼
Reasoning + Multi-Agent (Phase D) ──► Prediction + Opportunity Detection (Phase E)
     │                                                            │
     ▼                                                            ▼
Full Personal Model + Strategy Engine (Phase F) ──► Raphael-level Cognitive OS (Phase G)
```

Phase A is deliberately small: ingest conversations + documents, store in Postgres + Qdrant, support semantic search and a basic "bring me back" summary. Everything else in this handbook is built *on top of* a working Phase A, not before it.

---

## 6. Open Questions Carried Into Later Phases

- Where exactly does the line sit between "Knowledge Graph" and "Memory Engine" ownership of a fact? (Addressed in Phase 03.)
- Single local Postgres vs. syncing across devices — CRDT-based sync vs. simple cloud-primary-with-local-cache? (Addressed in Phase 18.)
- How much of the Personal Model should ever leave the local machine, even encrypted? (Addressed in Phase 17, Security.)

---

*Next: Phase 02 — Memory Engine (full type taxonomy, storage design, compression/decay/ranking, retrieval API).*
