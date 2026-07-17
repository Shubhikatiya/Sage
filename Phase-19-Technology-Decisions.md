# Sage — Engineering Handbook
## Phase 19: Technology Decisions

> Continues from Phase 01 (Foundation) through Phase 18 (Infrastructure). This phase consolidates every technology choice referenced across Phases 01–18 into one reference, and covers the remaining named comparisons from the original brief that hadn't come up naturally in context.

---

## 1. Overview

Every prior phase made a technology decision in service of that phase's specific problem (Memory Engine needed a vector DB, so Phase 02 picked one; Knowledge Graph needed a graph DB, so Phase 03 picked one). This phase is the reference document — one place to see every choice, its alternatives, and the reasoning, without having to reconstruct it by reading eighteen prior documents. It also resolves several named comparisons from the original brief that are relevant to Sage's future but hadn't been directly needed by any specific phase yet.

The consistent decision philosophy across all of these, worth stating once instead of repeating in every row: **prefer boring, well-documented, self-hostable technology that a solo maintainer can run and debug alone; adopt more sophisticated tooling only when a specific, demonstrated need outgrows the boring option** — not preemptively.

## 2. Consolidated Decisions (Already Made, Cross-Referenced)

| Category | Chosen | Alternative(s) | Phase decided | One-line why |
|---|---|---|---|---|
| API framework | FastAPI | Django | Phase 01 §4 | Async-native, typed, minimal ceremony |
| Relational DB | Postgres | MongoDB | Phase 01 §4 | JSONB flexibility + relational integrity + doubles as event bus (LISTEN/NOTIFY) |
| Vector DB | Qdrant | Weaviate | Phase 01 §4 | Self-hostable, low ops, strong hybrid search |
| Graph DB (MVP) | Kùzu | Neo4j | Phase 01 §4, Phase 03 §12 | Embedded, zero-ops, fits local-first single-user constraint |
| Graph DB (scaled) | Neo4j | Memgraph | Phase 18 §5 | Mature ecosystem, well-documented migration path from Kùzu's Cypher-like surface |
| Blob storage | MinIO / S3 | — | Phase 01 §4 | S3-compatible either way, zero migration cost |
| Event bus (MVP) | Postgres LISTEN/NOTIFY | NATS, Kafka | Phase 01 §4, Phase 18 §6 | Zero added infra for single-user event volume |
| Event bus (scaled) | NATS | Kafka | Phase 18 §6 | Lighter-weight than Kafka for the throughput Sage would plausibly need even at "scaled" |
| LLM access layer | LiteLLM-style router | Direct per-provider SDKs | Phase 01 §4 | LLM-agnostic from day one, not a Phase 20 retrofit |
| Local inference | Ollama | vLLM (self-hosted) | Phase 01 §4, below | Simpler ops for local/single-GPU-or-CPU use; see §4 for when vLLM becomes the better choice |
| Orchestration (containers) | Docker Compose | Kubernetes | Phase 18 §11 | No cluster-management overhead justified at single-user scale |
| Multi-agent orchestration | Custom lightweight orchestrator | LangGraph, CrewAI | Phase 04 §12, Phase 08 §8 | Matches first-principles precedent (ChefBot); avoids framework lock-in before requirements are proven |
| Observability | OpenTelemetry + Grafana/Prometheus | Proprietary APM | Phase 18 §7 | Open standard, self-hostable, no vendor lock-in |

---

## 3. LLM Provider Comparison — OpenAI vs. Anthropic vs. Gemini vs. Open-Source

This is deliberately not resolved as a single winner — it's the direct justification for the LLM Router abstraction (Phase 01 §4) existing at all:

| Provider class | Strength for Sage's use cases | Weakness | Where it fits |
|---|---|---|---|
| Anthropic (Claude family) | Strong instruction-following and long-context reasoning; well-suited to the Reflection/Critique adversarial pass (Phase 04 §7) and structured-output-heavy tasks (Reasoning Traces, StrategyAnalysis schema) | Cost at frontier tier | Default for Reasoning Engine's chain/tree/reflection modes, and Conversation Engine's persona-toned generation |
| OpenAI (GPT family) | Broad tool-calling ecosystem maturity, strong general capability | Similar cost profile to Anthropic at frontier tier | Configured as a fallback provider in the LLM Router (Phase 01 §2.4's provider-outage degradation requires ≥2 configured providers) |
| Google (Gemini family) | Strong long-context and multimodal (useful for Phase 07's image/document ingestion, Phase 12's video/audio adapters) | Ecosystem less mature for some agentic tool-calling patterns at time of writing | Candidate for document/image-heavy extraction tasks specifically |
| Open-source (local, via Ollama/vLLM) | Zero marginal cost, full privacy (never leaves the device), fits the local-first principle directly | Lower capability ceiling than frontier proprietary models, especially for genuinely hard multi-step reasoning | Default for high-frequency, low-ambiguity tasks (Phase 05 §11's intent detection, Phase 08 §9's Memory/Scheduler agent classification) and the offline mode baseline (Phase 17 §10) |

The LLM Router's job (Phase 01 §4) is making this table operational: a config-driven routing policy per task type (e.g., `intent_detection → local`, `reasoning.reflection → anthropic`, `document_extraction.multimodal → gemini`), swappable without code changes to any consuming engine.

---

## 4. Ollama vs. vLLM

Both already referenced (Phase 01 §4 chose Ollama as the default); the full comparison:

| | Ollama | vLLM |
|---|---|---|
| Setup complexity | Very low — single binary, simple model management | Higher — requires more explicit GPU/serving configuration |
| Best fit | Single-user, single-machine local inference (Sage's MVP reality) | Higher-throughput serving, multiple concurrent requests, production-grade serving |
| Sage's actual need | Matches — one user, modest concurrent request volume | Overkill at MVP scale |
| When to revisit | If local inference becomes a genuine latency bottleneck under real usage, or if Sage ever serves more than one user/device concurrently at meaningful volume | — |

**Decision:** Ollama for MVP and for the foreseeable single-user future; vLLM is the documented escalation path if local inference throughput genuinely becomes a bottleneck, not a default choice made preemptively.

---

## 5. DuckDB / Parquet — Where They Fit

Not previously referenced directly because no phase's core operational path needed them, but relevant for a specific, real use case: analytical queries over the Analytics dashboard panel (Phase 16 §4) and the Learning Engine's calibration history (Phase 09 §7).

| Use case | Fits DuckDB/Parquet? | Why |
|---|---|---|
| Live operational queries (memory retrieval, graph traversal) | No | Postgres/Qdrant/Kùzu already serve these; DuckDB isn't a replacement for the operational stores |
| Periodic analytical rollups (e.g., "confidence calibration trend over the last year," "memory write volume by type over time") | Yes | DuckDB excels at exactly this — columnar analytical queries over historical data, run infrequently, not on the hot path |
| Long-term cold-tier memory archive export | Yes (Parquet specifically) | A natural, portable, compressed format for exporting cold-tier memory (Phase 02 §7.2) for either analysis or genuine long-term archival outside the live system |

**Decision:** Introduce DuckDB as a lightweight analytical layer specifically for the Dashboard's Analytics panel and periodic reporting, reading from periodic Parquet exports of relevant Postgres tables — not as a replacement for any operational store, and not needed until the Dashboard phase's Analytics panel is actually being built.

---

## 6. Temporal vs. the Scheduler Agent's Current Approach

| | Temporal (workflow engine) | Current approach (Scheduler Agent + persisted trigger state, Phase 08 §5.7) |
|---|---|---|
| Capability | Full durable-workflow execution with complex retry/compensation semantics | Simpler persisted-trigger + task-graph model (Phase 08 §6, Phase 10 §4) |
| Operational cost | Running a Temporal cluster is real infrastructure overhead | Already covered by Postgres-persisted state, no new infrastructure |
| Sage's actual workflow complexity | Currently linear/DAG task graphs with human approval gates — well within what the current approach handles | Sufficient |

**Decision:** Not adopted. The current Task/Workflow model (Phase 10 §4) combined with Postgres-persisted Scheduler state (Phase 08 §5.7) covers Sage's actual workflow complexity without the operational overhead of running Temporal. Revisit only if workflows grow genuinely complex compensating-transaction requirements that the current model can't express cleanly.

## 7. Ray — Where It Would Fit (and Why It Doesn't, Yet)

Ray is built for distributed compute at a scale Sage doesn't currently have — single-user agent dispatch (Phase 08) and research fetch pooling (Phase 07 §5) are already adequately served by simple async concurrency (Python asyncio, bounded worker pools) without needing a distributed compute framework. **Not adopted.** Flagged here only because it's a named comparison in the original brief, not because Sage has a gap it fills.

## 8. MCP and A2A

Both directly relevant to Sage's actual architecture, not hypothetical:

| Protocol | Relevance to Sage |
|---|---|
| **MCP (Model Context Protocol)** | Directly applicable to the Research Engine (Phase 07) and any future third-party tool integrations — MCP is the natural interface for connecting Sage's agents to external tools/services in a standardized way, rather than each integration adapter (Phase 12 §4) inventing its own protocol. Precedent: Shubhi's existing MCP Server Suite project is a directly relevant, already-demonstrated pattern this handbook's Research/Execution integrations should build on rather than duplicate. |
| **A2A (Agent-to-Agent protocol)** | Less immediately relevant — Sage's Phase 08 multi-agent system is explicitly single-process, single-user, with the Planner/Event Bus handling all inter-agent coordination internally (Phase 08 §6). A2A matters more for cross-organization or cross-system agent interoperability, which isn't a current Sage requirement. Worth revisiting only if Sage's agents ever need to interoperate with agents outside Sage's own process — not needed for the vision as scoped through Phase 15. |

**Decision:** Adopt MCP for external tool/integration connections (natural fit with existing precedent); do not adopt A2A at this stage (no cross-system agent interoperability requirement yet).

## 9. OpenTelemetry — Already Decided

Confirmed in Phase 18 §7; included here for completeness of the consolidated reference. No alternative seriously considered — OpenTelemetry is the open, vendor-neutral standard, and vendor lock-in is specifically what the "everything replaceable" principle (Phase 01 §1.3) argues against.

## 10. GraphRAG

Directly relevant to the hybrid retrieval design already built in Phase 03 §9 — worth being explicit that Sage's hybrid graph+vector retrieval **is, architecturally, a GraphRAG pattern**, not a separate technology choice layered on top. The decision already made in Phase 03 (combine vector similarity with graph proximity scoring) is the GraphRAG approach, implemented with Sage's own chosen stack (Qdrant + Kùzu) rather than adopting a packaged GraphRAG framework/library. This is called out explicitly so the connection to the broader industry pattern is legible, not because a different decision needs to be made here.

## 11. DSPy and PydanticAI

| Tool | Relevance | Decision |
|---|---|---|
| **DSPy** | A prompt-optimization/compilation framework — potentially relevant to the Reasoning Engine's step decomposition (Phase 04 §6) or Learning Engine's calibration (Phase 09 §7) if prompt quality becomes a measured bottleneck | Not adopted at MVP — the custom, explicit prompt structures already defined per-agent (Phase 08 §5) are legible and debuggable by a solo maintainer; DSPy's automatic prompt optimization trades that legibility for potential quality gains that haven't yet been shown necessary. Worth revisiting once enough real usage data exists to know which prompts would actually benefit from optimization. |
| **PydanticAI** | A typed-output-focused agent framework — relevant given how central typed schemas (ReasoningTrace, StrategyAnalysis, MemoryItem envelopes) already are throughout this handbook | Not adopted as a framework, but its core idea (strict Pydantic-schema-validated LLM outputs) is already the de facto pattern used throughout every phase's API design sections — Sage achieves the same discipline directly via Pydantic schemas in FastAPI without adopting PydanticAI's additional agent-orchestration layer, consistent with the custom-orchestrator decision in Phase 08 §8 |

---

## 12. Consolidated Tradeoff Summary Table

| Decision axis | Sage's consistent answer | Why (one phrase) |
|---|---|---|
| Managed framework vs. custom code | Custom, where the framework's abstraction cost exceeds its benefit at current scale | Solo-maintainer legibility |
| Distributed infra vs. single-machine | Single-machine until a specific, demonstrated need | Cost ceiling + local-first |
| Proprietary vs. open standard | Open standard (OpenTelemetry, MCP, Postgres/S3-compatible APIs) | No vendor lock-in, "everything replaceable" |
| Preemptive scaling vs. scale-when-needed | Scale-when-needed, with the migration path pre-identified (e.g., Kùzu→Neo4j) | Avoids premature complexity while not being blind to future needs |

---

## 13. Future Improvements

- Revisit the LangGraph/CrewAI decision (§2) once the custom orchestrator's task-graph complexity genuinely grows beyond what a hand-maintained implementation handles comfortably.
- Revisit DSPy (§11) once enough reasoning-trace/calibration history (Phase 09 §7) exists to identify specific, high-value prompts worth automatically optimizing.
- Revisit vLLM (§4) if local inference throughput becomes a measured bottleneck under real multi-session or multi-device usage.
- Periodically re-run this comparison table as the LLM provider landscape shifts — the Phase 19 §3 comparison is a snapshot, not a permanent ranking, and the LLM Router's config-driven design (Phase 01 §4) is specifically what makes updating it low-cost.

---

*Next: Phase 20 — Implementation Roadmap (phased build plan from today's MVP to a Raphael-level cognitive operating system, with goals, deliverables, dependencies, milestones, and success criteria per phase).*
