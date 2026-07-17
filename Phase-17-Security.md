# Sage — Engineering Handbook
## Phase 17: Security

> Continues from Phase 01 (Foundation) through Phase 16 (Dashboard Architecture). This phase consolidates and formalizes the security requirements that have been referenced throughout every prior phase's own "Security" section into one coherent policy layer.

---

## 1. Overview

Security has appeared as a per-phase concern throughout this handbook — encryption tiers on Belief/Reflection memory (Phase 02 §13), entity-level redaction for third-party data (Phase 03 §14), scoped credentials for execution (Phase 10 §14), consent-gated source connections (Phase 12 §12), and access-tier consistency for the Dashboard (Phase 16 §14). This phase is where those scattered requirements become one explicit, auditable policy, rather than an emergent property that has to be independently verified per subsystem.

The framing that should govern every decision in this phase, restated from Phase 01 §1.3: **the user's personal model is the most sensitive data they own.** Sage's entire value proposition depends on that data being trustworthy and private; a security failure here isn't just a technical bug, it's a failure of the core premise.

## 2. Goals

- Define one consistent data sensitivity classification, referenced (not reinvented) by every subsystem.
- Make encryption, permissioning, and audit logging structural properties of the data model, not something bolted on per-feature.
- Support genuine offline/local-first operation as a first-class mode, not a degraded fallback (per Phase 01 §1.3's local-first principle).
- Ensure backup and recovery never becomes a security hole — recoverability (a recurring theme across every phase) must not come at the cost of an unencrypted backup sitting somewhere.

## 3. Responsibilities

**Owns:** the data sensitivity classification scheme, encryption key management, the permission/auth model, audit logging infrastructure, backup encryption and rotation, offline-mode data handling.

**Does not own:** per-subsystem business logic about *what* is sensitive (each phase already determined that — e.g., Belief/Reflection memory, third-party Person entities) — this phase owns the *mechanism* that enforces those classifications uniformly.

---

## 4. Data Sensitivity Classification

Consolidating every sensitivity note scattered across Phases 02–16 into one scheme:

| Tier | Examples | Encryption | Access requirement |
|---|---|---|---|
| **Tier 0 — Public/Non-sensitive** | Semantic facts about public entities (e.g., a fellowship's public deadline), World Model entities sourced from public web content | At-rest, standard | Any authenticated session |
| **Tier 1 — Personal, first-party** | Episodic/Procedural/Document memory, Project Model, verified Career Model skills | At-rest, standard | Authenticated session, own-device or authorized remote |
| **Tier 2 — Inferred/sensitive** | Belief memory, Reflection memory, Decision Pattern Model, Identity Model, energy pattern data (Phase 13 §8) | At-rest + application-level (separate key, per Phase 02 §13) | Authenticated session + explicit sensitive-data access flag, logged |
| **Tier 3 — Third-party data** | Relationship memory, Person entities, any data about people other than the user | Same as Tier 2, plus cascading redaction support (Phase 03 §14) | Same as Tier 2, plus subject to the third party's implied privacy interest even though they have no account |

Every subsystem's data model (Memory Engine's per-type tables, Knowledge Graph's Entity types, Personal Model's sub-models) is tagged with its tier at the schema level — this is what makes the classification enforceable by the storage layer itself rather than relying on every engine to remember to check.

---

## 5. Encryption Architecture

```
Key hierarchy:
  Master Key (user-held, e.g., derived from a passphrase or held in
              a local secure enclave — never leaves the user's control,
              never transmitted to any server in plaintext)
       │
       ├──► Tier 0/1 Data Encryption Key (standard at-rest encryption,
       │     Postgres TDE / filesystem-level, per Phase 01 §2.5)
       │
       └──► Tier 2/3 Data Encryption Key (application-level, separate
             from Tier 0/1 — a database-only compromise does not
             expose Belief/Reflection/Personal Model/Relationship data
             without this second key, per Phase 02 §13)

  Backup Encryption Key (derived from Master Key, rotated independently
                          of live data keys so a backup's compromise
                          doesn't necessarily compromise live data
                          decryption, and vice versa)
```

For the local-first MVP (Phase 01 §1.5's single-maintainer, low-cost-ceiling reality), the Master Key lives on the user's device; a future cloud-sync mode (Phase 18) would need a documented key-escrow or multi-device key-sharing design — explicitly flagged as an open question carried into Phase 18, not resolved here, since it depends on infrastructure decisions not yet made.

---

## 6. Permission Model

```
AccessGrant {
  subject: "user" | agent_name             # which agent or the user
                                              # themselves is requesting
  resource_tier: 0 | 1 | 2 | 3
  action: "read" | "write" | "delete"
  scope: text                                # matches the same scope-
                                              # pattern discipline as
                                              # Execution Engine's
                                              # standing permissions
                                              # (Phase 10 §6)
}
```

This directly generalizes the per-agent tool scoping already specified in Phase 08 §10 — every agent's declared tool access (Phase 08 §5, the "Tools" row per agent) is, underneath, a set of `AccessGrant`s enforced at this layer, not just a documentation convention. The Guardian Agent (Phase 08 §5.9) itself has read access across all tiers but write access limited to approve/reject flags — an explicit, auditable `AccessGrant` like any other, not a special-cased exception.

---

## 7. Audit Logging

```
AuditLogEntry {
  timestamp: timestamp
  subject: str                    # user or agent
  action: str
  resource_tier: int
  resource_ref: entity_id | UUID
  outcome: "allowed" | "denied"
  context: jsonb                   # e.g., which reasoning trace or
                                    # task triggered this access
}
```

Every Tier 2/3 access is logged unconditionally (not sampled) — this is deliberately more thorough than Tier 0/1 logging (which can be sampled/aggregated for cost reasons at larger scale) because Tier 2/3 data is exactly where an unnoticed access pattern would matter most. The audit log itself is append-only and stored separately from the data it describes, so a compromise of the primary data store doesn't also let an attacker cover their tracks by editing the log.

---

## 8. AI Safety Boundaries (Sage-Specific)

Beyond generic data security, several safety properties are specific to an AI system with this much personal context, and are worth stating explicitly as security requirements rather than leaving them purely as prompt-level behavior (per the recurring pattern in this handbook of making constraints structural, not just instructed):

- **Belief/Reflection confidence floor** (Phase 02 §4.2): enforced at the write-path level, not just prompt guidance — the Memory Engine schema itself rejects a Belief/Reflection write below the confidence floor without an explicit "unconfirmed" framing flag set.
- **No-verdict schema** (Phase 15 §6.4): `StrategyAnalysis` has no verdict field in its type definition — a structural guarantee, not a convention.
- **Scope-bounded execution** (Phase 10 §4): the `scope` field on every Task is validated against the `ApprovalRecord` before the Execution Agent's tool calls are permitted to run — enforced by the Execution Engine's dispatch layer, not left to agent good behavior alone.
- **Identity narrative restriction** (Phase 14 §5): `identity_narrative` writes are rejected by the Personal Model's write path unless tagged as sourced from an explicit user-authored event, not an inference.

These are grouped here because they share a common architectural pattern: **a safety property that matters is enforced by the data/schema layer, not solely by prompting the model to behave correctly.** This is a stronger guarantee than instruction-following alone, and it's the single most important idea in this phase.

---

## 9. Backup & Recovery

```
Backup strategy:
  - Postgres: continuous WAL archiving (already noted in Phase 02 §15)
    + periodic full snapshots, all encrypted with the Backup Encryption
    Key (§5) — never the live Data Encryption Key, so backup and live
    data compromises are independent events.
  - Blob Storage: versioned object storage with the same backup key.
  - Vector/Graph stores: rebuildable from Postgres + Blob per every
    prior phase's "Failure Recovery" section — not separately backed
    up as primary strategy, though periodic snapshots exist as a
    faster-recovery convenience (Phase 03 §16).

Recovery drill requirement: the `rebuild_index.py` script named in
Phase 02 §15 as a "required Phase A deliverable, not a someday" is
the concrete, testable artifact this phase depends on — security
without a tested recovery path is incomplete, since an untested
backup is not meaningfully different from no backup.
```

---

## 10. Offline Mode

Consistent with the local-first principle (Phase 01 §1.3), Sage should function with reduced but real capability when disconnected:

```
Offline-available (local models via Ollama, per Phase 01 §4):
  - Memory retrieval (Postgres + Qdrant are local by default in the
    local-first MVP)
  - Knowledge Graph traversal (Kùzu is embedded, local)
  - Basic Conversation Engine turns using local LLM inference
  - Execution Engine tasks that don't require external integrations

Offline-unavailable (requires connectivity):
  - Research Engine web fetching (Phase 07)
  - Frontier-model-quality reasoning (if configured to prefer cloud
    models for complex Tree Search/reflection — degrades to local
    model quality offline rather than failing outright, consistent
    with the graceful-degradation pattern from Phase 01 §2.4)
  - External integration sync (calendar, email, connected sources,
    Phase 12 §7)

The system should clearly indicate offline-degraded state (mirroring
the `degraded: true` flag pattern already used throughout the
handbook, e.g., Phase 02 §9, Phase 05 §9) rather than silently
providing lower-quality results without indication.
```

---

## 11. API Design

```
POST /security/access_check          // internal, called by every
                                        // engine before a Tier 2/3
                                        // operation
{ "subject": "...", "resource_tier": 2, "action": "read", "scope": "..." }
→ { "allowed": bool, "audit_logged": true }

GET /security/audit_log?resource_tier=2&from=...&to=...   // user-
                                                             // facing,
                                                             // full
                                                             // transparency
                                                             // into who/
                                                             // what accessed
                                                             // sensitive data

POST /security/export_all             // full data export, Phase 02 §13
POST /security/delete_all              // full data delete, Phase 02 §13
POST /security/rotate_backup_key        // key rotation, §5
```

---

## 12. Sequence Diagram — Guardian Agent Accessing Tier 2 Data for Review

```
Guardian Agent    Security Layer    Audit Log      Memory Engine
      │                  │               │                │
      │──access_check────►│               │                │
      │  (Tier 2, read,     │               │                │
      │   scope: review)     │               │                │
      │                  │──check AccessGrant│               │
      │                  │  (Phase 08 §5.9's  │               │
      │                  │   declared grants)   │               │
      │                  │──log (unconditional)─►│                │
      │◄──allowed─────────│               │                │
      │──read────────────────────────────────────────────►│
      │◄──Tier 2 data─────────────────────────────────────│
```

---

## 13. Technology Choices & Tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Schema-enforced safety constraints (§8) vs. prompt-only enforcement | Schema-enforced | Prompt-only | A structural guarantee (the field doesn't exist, the write is rejected) can't be defeated by a prompt-injection or model inconsistency the way instruction-following alone can — this is the single strongest lesson this phase applies across the whole handbook |
| Separate backup encryption key vs. reusing live data keys for backups | Separate (§9) | Same key | Compromise independence — a leaked backup shouldn't automatically mean live data is also exposed, and vice versa |
| Unconditional Tier 2/3 audit logging vs. sampled logging at all tiers | Unconditional for Tier 2/3, sampled acceptable for Tier 0/1 | Uniform sampling | The cost of full logging is justified specifically where the data is most sensitive; uniform sampling would under-log exactly the accesses that matter most to have a complete record of |

---

## 14. Scaling Strategy

Security overhead (access checks, audit logging) is per-request, not data-volume-dependent, so it scales linearly and predictably with usage — the design priority here is correctness and completeness of coverage, not raw throughput, consistent with this being a single-user system.

## 15. Testing Strategy

- **Tier classification completeness:** every table/entity type across Phases 02–16 must map to a defined tier — tested as a schema-coverage check (no untagged sensitive data slipping through).
- **Schema-enforced constraint tests:** attempt to write a Belief memory item below the confidence floor without the unconfirmed flag, attempt to write an inferred `identity_narrative`, attempt to construct a `StrategyAnalysis` with a verdict field — all should fail at the write/type level, not just be caught by a linter or code review.
- **Audit log completeness:** every Tier 2/3 access in a test scenario must produce exactly one corresponding audit entry — tested as an invariant, not spot-checked.
- **Recovery drill:** the `rebuild_index.py` script (§9) is actually run against a test environment on a defined cadence, not just written and forgotten.

## 16. Failure Recovery

This phase's own most important failure-recovery case is a compromised or lost Master Key — for the local-first MVP, this is treated as unrecoverable by design (no key escrow exists yet, consistent with the local-first, user-held-key principle) and is documented clearly to the user as a real risk they're accepting in exchange for not depending on any third party holding their key — an explicit tradeoff, not an oversight.

## 17. Future Improvements

- Multi-device key sharing/escrow design once cloud-sync (Phase 18) is built — explicitly deferred, not solved here, since it depends on infrastructure decisions not yet made.
- Hardware security module (HSM) or secure-enclave-backed key storage for the Master Key, once the system runs on infrastructure that supports it, as a stronger guarantee than a passphrase-derived key alone.
- Formal third-party security audit once the system handles data volume/sensitivity that justifies the cost — appropriate at a later maturity stage, not at MVP.

---

*Next: Phase 18 — Infrastructure (frontend, backend, database, vector DB, graph DB, blob storage, queues, workers, caching, containers, cloud, monitoring, observability, logging, CI/CD).*
