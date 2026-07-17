# Sage — Engineering Handbook
## Phase 18: Infrastructure

> Continues from Phase 01 (Foundation) through Phase 17 (Security).

---

## 1. Overview

Every prior phase named infrastructure components in passing (Postgres, Qdrant, Kùzu, MinIO, the event bus) as consequences of design decisions made for other reasons. This phase is where those choices become one coherent deployment picture: what runs where, how it's containerized, how it's observed, and how it scales from a single laptop (Phase 1 reality) to whatever the system eventually needs to become.

The governing constraint, restated from Phase 01 §1.5: this is a solo-maintained, cost-ceiling-constrained, local-first system. Infrastructure decisions here are judged against "can Shubhi run and debug this alone, resuming after months away" — not against what a funded, team-maintained SaaS product would choose.

## 2. Goals

- A local-first deployment that runs entirely on one machine with zero required cloud dependencies, with cloud services as strictly optional additions (burst compute, off-device backup, multi-device sync).
- Full observability from day one — logs, traces, and metrics for every subsystem call, since a solo maintainer returning after months away needs the system to be self-explaining, not just functional.
- A CI/CD pipeline that makes the "every subsystem independently testable" principle (Phase 01 §1.3) actually enforced automatically, not just aspirational.
- A migration path that doesn't require re-architecting when/if the system needs to scale beyond a single machine.

## 3. Responsibilities

**Owns:** containerization, deployment topology, the observability stack, CI/CD pipeline definition, environment configuration management.

**Does not own:** application-level logic in any subsystem — infrastructure exists to run and observe the system, not to make decisions about what the system does.

---

## 4. Deployment Topology — MVP (Local-First)

```
┌──────────────────────────────────────────────────────────────┐
│                     Single Machine (Laptop/Home Server)          │
│                                                                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │  API Gateway  │  │  Postgres     │  │  Qdrant       │  │  Kùzu          │  │
│  │  + Conversation│  │  (Docker        │  │  (Docker        │  │  (embedded,     │  │
│  │  Engine (Docker)│  │  container)      │  │  container)      │  │  in-process —    │  │
│  │                │  │                  │  │                  │  │  no container    │  │
│  │                │  │                  │  │                  │  │  needed)          │  │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │
│                                                                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                  │
│  │  MinIO         │  │  Ollama         │  │  Agent/Engine    │                  │
│  │  (Docker,       │  │  (local LLM       │  │  Services         │                  │
│  │  S3-compatible)  │  │  inference)        │  │  (Docker Compose,   │                  │
│  │                │  │                  │  │  one container per    │                  │
│  │                │  │                  │  │  service, per Phase   │                  │
│  │                │  │                  │  │  01 folder structure) │                  │
│  └────────────┘  └────────────┘  └────────────┘                  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │   Observability Stack (§7) — local Grafana/Prometheus,        │  │
│  │   or a lighter-weight alternative for solo-maintainer scale     │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                              │
                    Optional, explicit opt-in:
                              ▼
              ┌────────────────────────────────┐
              │   Cloud LLM Providers (Anthropic,   │
              │   OpenAI, etc.) — via LLM Router,      │
              │   Phase 01 §4 — for burst reasoning      │
              │   quality beyond local model capability   │
              └────────────────────────────────────────┘
```

All services orchestrated via a single `docker-compose.yml` at the MVP stage — no Kubernetes, no multi-node orchestration, consistent with the "boring, well-documented technology over cutting-edge tools that require constant babysitting" principle from Phase 01 §1.5.

---

## 5. Deployment Topology — Cloud-Scaled (Future, Not MVP)

Explicitly deferred, sketched only to confirm the migration path exists without requiring a rewrite:

```
Local machine (still primary — local-first remains the default even
in cloud-scaled mode, per Phase 01 §1.3)
        │
        │  optional sync
        ▼
Cloud deployment (only if multi-device sync or heavier compute is
                   needed):
   - Postgres → managed Postgres (e.g., RDS-equivalent) with the
     same schema, no migration needed beyond connection config
   - Qdrant → managed/clustered Qdrant
   - Kùzu → migrate to Neo4j (per Phase 03 §12's explicit "revisit
     if traversal volume justifies it" flag) — this is the one
     component whose local-first choice doesn't just scale up in
     place, it requires an actual migration, planned for from the
     start rather than discovered as a surprise
   - Container orchestration → Kubernetes only if genuinely running
     multiple services at meaningful scale; for a still-single-user
     system, Docker Compose on a slightly bigger machine is very
     likely sufficient even at "cloud-scaled"
```

This section exists specifically to answer the open question flagged in Phase 03 §17 and Phase 02 §16 ("where does the line sit between local Postgres and syncing across devices") — the answer is: local remains primary indefinitely; cloud is an additive sync/burst layer, not a replacement, and Kùzu→Neo4j is the one genuinely non-trivial migration in the whole stack, planned for explicitly rather than assumed away.

---

## 6. Event Bus — MVP vs. Scaled

Already flagged in Phase 01 §4: Postgres `LISTEN/NOTIFY` for MVP, NATS if/when scaled.

```
MVP: Postgres LISTEN/NOTIFY
  - Zero additional infrastructure — the database Sage already runs
    doubles as the event bus.
  - Sufficient throughput for single-user event volume (memory
    writes, agent dispatches, scheduled triggers) by a wide margin.
  - Limitation: no built-in replay/durability beyond what's already
    logged in the event_log table itself (Phase 01 §2.5) — acceptable
    since that table is the durability mechanism regardless of
    transport.

Scaled: NATS
  - Adopted only if event volume or multi-service fan-out genuinely
    outgrows LISTEN/NOTIFY's practical limits — not adopted
    preemptively, consistent with the "boring technology, proven
    need before added complexity" principle.
```

---

## 7. Observability Stack

Three pillars, each mapped to how they're actually used in this system:

```
Logging:
  - Structured JSON logs per service, correlated by a request_id
    that threads through every subsystem call in a single turn
    (Conversation Engine → Context → Reasoning → Memory, etc.) —
    this is what makes "why did Sage say that" (Phase 01 §1.3's
    explainability principle) debuggable at the infrastructure
    level, not just via the Reasoning Trace's own application-level
    record (Phase 04 §6.1) — logs and traces serve complementary
    purposes: traces explain reasoning, logs explain system behavior.

Tracing:
  - OpenTelemetry spans per engine call, so a single conversation
    turn's full call graph (which engines were invoked, in what
    order, how long each took) is inspectable — directly useful for
    diagnosing the "why is this turn slow" question against the
    latency budgets set in Phase 05 §2 (~300ms context resolution)
    and Phase 11.

Metrics:
  - Per-subsystem: request volume, latency percentiles, error rates.
  - Sage-specific: memory write volume by type, decay/consolidation
    job duration (Phase 02 §8), prediction surfacing rate and
    false-positive-feedback rate (Phase 13 §9), confidence
    calibration drift (Phase 09 §7) — these are the metrics that
    matter for judging whether Sage is actually working well, not
    just whether it's up.
```

---

## 8. CI/CD Pipeline

```
On every commit:
  1. Lint + type-check (per-service, since each service in
     services/* is independently testable per Phase 01 §3's
     folder structure).
  2. Unit tests per service (Phases 02-17 each specified their own
     unit test suites — this is where they actually run).
  3. Integration tests (cross-service, e.g., write → embed → retrieve
     round-trips from Phase 02 §14).

On merge to main:
  4. Build containers for changed services only (not a full rebuild
     every time — keeps iteration fast for a solo maintainer).
  5. Deploy to a local staging profile first (docker-compose with a
     staging config) before any production/primary-instance deploy —
     even for a single-user system, this catches migration issues
     before they hit the live data.

Scheduled (not commit-triggered):
  6. The recovery drill (Phase 17 §15 — running rebuild_index.py
     against a test environment on a defined cadence) runs as a
     scheduled CI job, not something remembered manually.
```

---

## 9. Environment Configuration

```
.env-based configuration per environment (local dev / staging /
primary), with:
  - LLM provider credentials (never committed, loaded via a secrets
    manager appropriate to deployment — even a simple local
    encrypted file at MVP scale, consistent with Phase 17 §5's key
    hierarchy)
  - Per-service connection strings (Postgres, Qdrant)
  - Feature flags for optional subsystems (e.g., energy pattern
    detection's opt-in default-off state from Phase 13 §8 is
    itself a config-level flag, not just an application-level check)
```

---

## 10. Sequence Diagram — A Deployment (Local Dev → Staging → Primary)

```
Developer    CI Pipeline    Container Registry    Staging Compose    Primary Compose
    │              │                  │                    │                  │
    │──commit─────►│                  │                    │                  │
    │              │──lint/test──────►│                    │                  │
    │              │◄──pass───────────│                    │                  │
    │              │──build changed────►│                    │                  │
    │              │  service images     │                    │                  │
    │              │                   │──push images────────►│                  │
    │              │                   │                    │──deploy──────────►│
    │              │                   │                    │  (staging config)  │
    │              │                   │                    │──run integration──►│
    │              │                   │                    │  tests against       │
    │              │                   │                    │  staging data          │
    │              │                   │                    │◄──pass──────────────│
    │              │──manual promote (solo-maintainer's own call,───────────────►│
    │              │  not automatic — deliberate gate for a single-user system)   │
```

---

## 11. Technology Choices & Tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Docker Compose vs. Kubernetes for MVP | Docker Compose | Kubernetes | K8s overhead (cluster management, YAML sprawl) is unjustified for a single-machine, single-user deployment — matches the "boring technology" principle explicitly stated in Phase 01 §1.5 and reiterated for the event bus decision here |
| Postgres LISTEN/NOTIFY vs. NATS/Kafka for MVP event bus | LISTEN/NOTIFY (already decided Phase 01 §4, reaffirmed here) | NATS/Kafka from day one | Operating a message broker for single-user event volume is pure overhead; the migration path to NATS is well-understood and deferred until actually needed |
| Staged manual-promote deployment vs. full auto-deploy to primary | Manual promote (§10) | Fully automated deploy on merge | For a system holding the most sensitive personal data the user owns (Phase 17 §1), a deliberate human gate before touching primary data is worth the small friction cost — this is a security-adjacent infrastructure decision, not just a process preference |

---

## 12. Scaling Strategy

The explicit scaling path is: **local-first indefinitely, cloud as an additive layer, Kùzu→Neo4j as the one true migration.** Every other component (Postgres, Qdrant, MinIO, the container orchestration) scales by moving to a managed/clustered version of the same technology, not by replacing it — a deliberate consequence of choosing S3-compatible, Postgres-compatible, and otherwise portable technologies throughout every earlier phase's stack decisions.

## 13. Security

Infrastructure-level security is where Phase 17's key hierarchy and access model actually get deployed — container secrets management, network isolation between services (only the API Gateway is externally exposed; internal services communicate on a private Docker network), and TLS for any traffic that does cross a network boundary (including local traffic where the deployment includes multiple physical devices).

## 14. Testing Strategy

- **Container build reproducibility:** every service's Dockerfile produces a deterministic, versioned image — tested by rebuilding from a clean environment and diffing.
- **Staging parity:** staging compose config is tested to genuinely mirror primary (same service versions, same migration state) before any promote, specifically to catch the "worked in staging, broke in primary" failure mode.
- **Observability coverage:** a test asserting every engine API call actually produces a trace span and a structured log entry — observability itself needs a regression guard, or it silently degrades as new endpoints get added without instrumentation.

## 15. Failure Recovery

Full-system recovery (a new machine, after total loss of the original) is: restore Postgres from backup (Phase 17 §9), restore Blob Storage from backup, run `rebuild_index.py` (Phase 02 §15) to reconstruct Qdrant and Kùzu from the restored Postgres/Blob data — this end-to-end path is exactly what the scheduled recovery drill (§8, Phase 17 §15) exists to keep continuously verified, not just documented and hoped-to-work.

## 16. Future Improvements

- Multi-device local sync (two of the user's own machines staying in sync without a cloud intermediary) as a middle ground between pure single-machine local-first and full cloud-scaled — worth exploring before jumping straight to cloud sync, since it preserves more of the local-first privacy posture.
- Cost-monitoring dashboard for cloud LLM burst usage (Phase 01 §4's LLM Router already tracks provider calls; surfacing cost trends explicitly would help enforce the cost-ceiling constraint from Phase 01 §1.5 concretely rather than just aspirationally).
- Evaluate lighter-weight observability tooling if the full Grafana/Prometheus stack proves to be more operational overhead than a solo maintainer wants to carry — the goal is insight, not a specific toolset.

---

*Next: Phase 19 — Technology Decisions (comprehensive tradeoff tables across every major technology choice referenced throughout this handbook, consolidated in one place).*
