# Sage — Engineering Handbook
## Phase 03: Knowledge Graph

> Continues from Phase 01 (Foundation) and Phase 02 (Memory Engine). Assumes the memory taxonomy and event-log conventions established there.

---

## 1. Overview

If the Memory Engine answers "what has been said or observed," the Knowledge Graph answers "how does everything connect." It is where raw memory gets resolved into typed **entities** (people, projects, documents, goals, ideas, organizations, tasks, questions, insights, timeline events) and typed **relationships** between them (works-on, funds, blocks, mentors, cites, supersedes, motivates).

The Knowledge Graph is what makes "bring me back" more than a chronological summary — it's what lets Sage answer "what does the ACT fellowship have to do with ReRoot" or "who else has touched the Kaal pitch deck" by traversal, not by re-reading everything.

## 2. Goals

- Every entity is deduplicated and canonical — "Navgunjara," "Navgunjara Foundation," and "the NGO" all resolve to one node.
- Every relationship is attributed to a source event (same provenance discipline as Memory Engine — no ungrounded edges).
- Support both graph traversal (multi-hop: "what connects to what") and hybrid retrieval (semantic search *combined with* graph proximity — a document about "care leavers" should rank higher for a ReRoot query because it's graph-adjacent, not just because of text similarity).
- Stay cheap to query at interactive latency (<200ms for a 2-hop traversal) even at tens of thousands of nodes, since the graph backs live conversation, not just batch jobs.

## 3. Responsibilities

**Owns:** entity schema and canonicalization, relationship schema, graph traversal queries, entity resolution/deduplication, timeline construction.

**Does not own:** deciding an entity is important (that's importance scoring, still Memory Engine's job on the corresponding memory items) or generating new insights from graph structure (that's the Reasoning Engine, which *queries* the graph but doesn't own it).

---

## 4. Entity Model

### 4.1 Core Entity Types

| Entity type | Examples from Shubhi's actual domain | Key attributes |
|---|---|---|
| Person | Shubhi, a mentor, a fellowship program officer | role, relationship_to_user, first_mentioned, contact_info (optional) |
| Organization | Navgunjara Foundation, SafetyWhat, The/Nudge Institute, ACT, Acumen | type (employer/nonprofit/funder/school), status |
| Project | ReRoot, Sage, Kaal, ChefBot, Edge AI Deployment Stack | status (active/paused/shipped), owner, start_date |
| Document | ACT Concept Note, Kaal pitch deck, resume v5 | doc_type, version, storage_ref (Blob Storage pointer) |
| Goal | "Get accepted to ACT Fellowship," "Ship Sage Phase A" | horizon (short/long-term), status, owning_project |
| Task | "Draft ReRoot Learning Memo," "Fix Kaal slide 12" | status, due_date, blocking/blocked_by |
| Idea | "Use Jyotish Dasha as symbolic interpretive layer" | maturity (raw/validated/implemented), origin_project |
| Question | "Should ReRoot target Pune or Farrukhabad first?" | status (open/resolved), resolution_ref |
| Insight | "Care leaver population has no structural support pipeline" | derived_from (source memories), confidence |
| Event | "ACT essay submission," "Redrob Ideathon judging" | occurred_at, participants |
| Concept | "Vimshottari Dasha system," "RAG," "learner-maker-earner ladder" | domain, definition_summary |

### 4.2 Entity Schema

```
Entity {
  id: UUID
  type: EntityType
  canonical_name: text
  aliases: text[]                     # "Navgunjara" / "the NGO" / "Navgunjara Foundation"
  attributes: jsonb                    # type-specific fields per table above
  embedding: vector(1536)               # for semantic entity resolution, see §6
  created_at: timestamp
  first_source_event_id: UUID
  status: text                          # active | archived | superseded
  confidence: float
}

Relationship {
  id: UUID
  source_entity_id: UUID
  target_entity_id: UUID
  relation_type: text                   # see §5
  source_event_id: UUID                 # provenance — mandatory
  weight: float                          # strength/confidence of the edge
  valid_from: timestamp
  valid_until: timestamp | null          # null = still current
  created_at: timestamp
}
```

Note `valid_until` — relationships are time-bound, not permanent. "Shubhi works at SafetyWhat" has a `valid_from`; if that ever changes, the old edge gets `valid_until` set rather than deleted, preserving the same point-in-time-reconstruction property the Memory Engine has for facts.

---

## 5. Relationship Taxonomy

| Category | Relation types |
|---|---|
| Structural | `works_on`, `owns`, `part_of`, `contains`, `derived_from` |
| Temporal | `preceded_by`, `followed_by`, `occurred_during` |
| Causal | `motivates`, `blocks`, `enables`, `caused_by` |
| Social | `mentors`, `collaborates_with`, `reports_to`, `introduced_by` |
| Epistemic | `cites`, `contradicts`, `supports`, `supersedes`, `answers` |
| Evaluative | `applies_to` (e.g., a fellowship applies_to a project), `funds`, `evaluates` |

Keeping relation types in a closed, documented vocabulary (rather than letting the extraction LLM invent free-text relation strings) is what makes graph traversal queries reliable — `MATCH (p:Project)-[:BLOCKS]->(t:Task)` only works if `BLOCKS` is a controlled term, not one of forty synonyms an LLM generated across different sessions.

---

## 6. Entity Resolution & Deduplication

This is the hardest correctness problem in the Knowledge Graph, and it gets its own pipeline stage rather than being folded into extraction.

```
New mention "the NGO" appears in conversation
        │
        ▼
┌─────────────────────┐
│ Candidate generation  │  → exact alias match, then embedding similarity
│ (search existing       │     search over existing entity embeddings
│  entities for match)   │     (top-5 candidates, threshold > 0.82)
└──────────┬────────────┘
           │
┌──────────▼────────────┐
│ Disambiguation          │  → if exactly one high-confidence candidate,
│                          │     auto-merge (add alias, bump confidence)
│                          │  → if multiple plausible candidates or none
│                          │     above threshold, create new entity with
│                          │     status "tentative" and queue for review
└──────────┬────────────┘
           │
┌──────────▼────────────┐
│ Guardian Agent review    │  → low-confidence merges/creates surfaced in a
│ (batch, async)            │     lightweight review queue rather than
│                            │     silently guessed — wrong merges are worse
│                            │     than a slower graph, since they corrupt
│                            │     retrieval for everything downstream
└────────────────────────┘
```

---

## 7. Architecture Diagram

```
   Memory Engine ──(memory.written event)──► Extraction Agent
                                                     │
                                       ┌─────────────┴──────────────┐
                                       │                              │
                              Entity Resolution              Relationship Extraction
                              (§6 pipeline)                  (typed relation, source
                                       │                       event attached)
                                       ▼                              ▼
                              ┌─────────────────────────────────────────┐
                              │           Graph Store (Kùzu)               │
                              │  nodes: Entity   edges: Relationship        │
                              └──────────────────┬──────────────────────┘
                                                  │
                          ┌───────────────────────┼───────────────────────┐
                          ▼                        ▼                        ▼
                Context Engine              Reasoning Engine        Prediction Engine
                (resolve "what's           (multi-hop traversal    (dependency graph,
                 connected to the           for hypothesis          bottleneck detection)
                 current project")          grounding)
```

---

## 8. Database Design

Kùzu (embedded, columnar graph DB) for the local-first MVP; the same Cypher-like query surface ports to Neo4j if/when cloud-scale multi-device sync is needed (Phase 18 decision).

```cypher
// Entity node table
CREATE NODE TABLE Entity (
  id UUID PRIMARY KEY,
  type STRING,
  canonical_name STRING,
  aliases STRING[],
  attributes STRING,       -- JSON-encoded, type-specific
  confidence DOUBLE,
  status STRING,
  created_at TIMESTAMP
);

// Relationship edge table — typed per relation for query performance,
// OR a single generic REL table with a `relation_type` property.
// MVP choice: single generic edge table (simpler migrations early on;
// revisit if traversal performance demands typed edge tables — see §12).
CREATE REL TABLE RELATED_TO (
  FROM Entity TO Entity,
  relation_type STRING,
  source_event_id UUID,
  weight DOUBLE,
  valid_from TIMESTAMP,
  valid_until TIMESTAMP
);
```

### 8.1 Example Traversal

```cypher
// "Everything connected to the ACT Fellowship application, 2 hops out"
MATCH (start:Entity {canonical_name: "ACT Fellowship"})
      -[r:RELATED_TO*1..2]-(connected:Entity)
WHERE r.valid_until IS NULL
RETURN connected.canonical_name, connected.type, r.relation_type
```

This is the literal query pattern behind "what does the ACT fellowship have to do with ReRoot" — traversal finds the `applies_to` edge to ReRoot, the `derived_from` edges to the essays and concept note, and the `part_of` edge linking ReRoot to Navgunjara, in one call.

---

## 9. Hybrid Retrieval (Graph + Vector, Combined)

Pure vector search misses structurally-relevant-but-lexically-different results (a document about "care leavers who age out of institutions" should surface for a ReRoot query even without shared vocabulary). Pure graph traversal misses anything not yet explicitly linked. Hybrid retrieval combines both:

```
POST /graph/hybrid_retrieve
{
  "query": "ReRoot livelihood pipeline",
  "seed_entities": ["ReRoot"],     // optional: anchor traversal here
  "max_hops": 2,
  "top_k": 15
}

Scoring:
  final_score = α * vector_similarity(memory_item, query)
              + β * graph_proximity(memory_item.linked_entity, seed_entities)
              + γ * importance_score (from Memory Engine)

  graph_proximity = 1 / (1 + hop_distance)   # closer entities score higher
```

This is the mechanism referenced in Phase 01's system map as "hybrid retrieval" — it's implemented here, jointly querying the Vector Store (Phase 02) and the Graph Store, then merging ranked lists rather than treating them as separate features.

---

## 10. Timeline Construction

The graph also powers a derived **timeline view** — a chronological reconstruction of everything that happened on a project, built by querying all `Event` entities and time-bound relationships (`occurred_during`, `preceded_by`) connected to a given entity, ordered by `valid_from`/`occurred_at`. This is a read-time projection, not a separately stored structure — it's always consistent with the graph because it's computed from it, not maintained in parallel.

```
GET /graph/timeline?entity=Kaal&from=2026-01-01&to=2026-07-01
→ [
   { date: "2026-02-14", event: "Ideathon registration", type: "Event" },
   { date: "2026-03-02", event: "Design system finalized (Cormorant/DM Sans)", type: "Insight" },
   { date: "2026-04-18", event: "Simulated judging panel scored deck 83/100", type: "Event" },
   ...
  ]
```

---

## 11. API Design (Summary)

| Endpoint | Purpose |
|---|---|
| `POST /graph/entity` | Create/update an entity (used by Extraction Agent) |
| `POST /graph/relationship` | Create a typed, attributed edge |
| `GET /graph/entity/{id}` | Fetch entity + immediate (1-hop) relationships |
| `POST /graph/traverse` | Multi-hop traversal query |
| `POST /graph/hybrid_retrieve` | Combined vector + graph retrieval (§9) |
| `GET /graph/timeline` | Chronological projection for an entity |
| `POST /graph/resolve_entity` | Run entity resolution for a candidate mention, returns match or "new" |
| `GET /graph/review_queue` | Tentative/low-confidence entities and edges awaiting Guardian Agent review |

---

## 12. Technology Choices & Tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Kùzu vs. Neo4j for MVP | Kùzu | Neo4j | Embedded, zero-ops, fits local-first single-user constraint from Phase 01; Neo4j reserved for the point multi-device sync or dramatically larger graphs justify running a server |
| Generic edge table vs. typed edge tables per relation | Generic (MVP) | Typed per relation | Faster to iterate on relation vocabulary early; revisit if traversal query planning on a generic table becomes a measured bottleneck — this is an explicit "cheap now, revisit if proven slow" tradeoff, not a permanent decision |
| LLM-based vs. rule-based entity resolution | LLM + embedding similarity, with Guardian Agent review gate | Pure rule-based (exact string match) | Rule-based misses "the NGO" ≡ "Navgunjara"; pure LLM without a review gate risks silent bad merges — the hybrid with human-reviewable tentative status is the balance |
| Closed relation vocabulary vs. free-text relations | Closed, documented enum | LLM-generated free text | Reliable graph queries require a controlled schema; free text relation types make `MATCH` queries unreliable within months |

---

## 13. Scaling Strategy

At single-user scale (thousands to low tens of thousands of entities over years), Kùzu embedded handles this comfortably on a laptop. The scaling risk is not node count — it's **edge fan-out** on hub entities (e.g., "Shubhi" or "Navgunjara" will eventually have thousands of edges). Mitigation: cap default traversal depth at 2 hops for interactive queries, require explicit opt-in for deeper traversal, and pre-materialize the most common "hub entity summary" (top-N most important connected entities) as a cached read rather than a live traversal on every context resolution.

## 14. Security

Same encryption-at-rest posture as Memory Engine. Relationship data about people (Relationship-type entities and `mentors`/`collaborates_with` edges) is treated with the same sensitivity tier as `memory_belief` — it's information about third parties, not just the user, so export/delete requests must be able to selectively redact a specific person's node and edges without corrupting the rest of the graph (cascading soft-delete, not hard delete, to preserve provenance of everything else).

## 15. Testing Strategy

- **Entity resolution regression set:** a fixed list of known alias pairs ("the NGO" → Navgunjara Foundation, "the pitch deck" in a Kaal-context conversation → the specific Kaal deck entity) that must resolve correctly on every extraction pipeline change.
- **Traversal correctness:** synthetic graph fixtures with known expected multi-hop results.
- **Hybrid retrieval ranking:** given a fixed query and fixed graph/vector state, assert ranking order is stable and matches expected weighting behavior.

## 16. Failure Recovery

Rebuildable from Postgres event log (same principle as Phase 02) by replaying all `memory.written` and `document.ingested` events through the Extraction Agent — expensive (LLM cost) but never data-losing. A nightly incremental graph snapshot (Kùzu supports export) is taken regardless, so a full LLM-cost rebuild is a last resort, not the only recovery path.

## 17. Future Improvements

- Typed edge tables once traversal volume justifies the migration cost (see §12).
- Graph-based anomaly detection (a project with unusually high `blocks` edges and no recent `followed_by` progress = a stalled-project signal) feeding directly into the Prediction Engine (Phase 14).
- Community detection / clustering algorithms to auto-suggest "these entities probably belong to a project you haven't explicitly grouped yet."

---

*Next: Phase 04 — Reasoning Engine (multi-step reasoning, planning, tree/graph search, self-critique, confidence estimation).*
