# Sage — Engineering Handbook
## Phase 02: Memory Engine

> Continues from Phase 01 (Foundation). Assumes the subsystem boundaries and stack decisions established there.

---

## 1. Overview

The Memory Engine is the subsystem every other part of Sage depends on. It is responsible for **writing**, **organizing**, **compressing**, **ranking**, and **retrieving** every unit of information the system has ever been given — and for deciding, continuously, how important each unit still is.

The core design tension: raw storage is cheap (store everything, forever), but *relevance* is expensive to compute and decays over time. The Memory Engine's job is to make retrieval fast and precise years into the system's life, not just on day one when there's nothing to search through yet.

## 2. Goals

- Support twelve distinct memory types (below) without forcing them into one generic "note" schema that loses type-specific structure.
- Make every memory item traceable to a source event — no orphaned facts.
- Keep retrieval latency flat as memory volume grows into the hundreds of thousands of items (via compression, tiering, and decay-based pruning of the *hot* retrieval set — never destructive deletion of the *cold* archive).
- Provide a single retrieval API that the Context Engine, Reasoning Engine, and Conversation Engine all call identically, so improvements to ranking benefit every consumer at once.

## 3. Responsibilities (and explicit non-responsibilities)

**Owns:** memory schema, memory writes, embedding generation triggers, compression jobs, decay scoring, retrieval ranking, versioning/snapshots.

**Does not own:** entity/relationship modeling (that's the Knowledge Graph, Phase 03) or deciding *what to do* with a retrieved memory (that's Reasoning/Context Engines). The Memory Engine answers "what do I know and how relevant is it," not "what does it mean" or "what should happen next."

---

## 4. Memory Type Taxonomy

Rather than one flat table, each memory type is modeled with the structure it actually needs. All types share a common envelope; type-specific payloads differ.

### 4.1 Common Envelope (every memory row)

```
MemoryItem {
  id: UUID
  type: MemoryType (enum, see below)
  created_at: timestamp
  source_event_id: UUID          # FK into the append-only event log — mandatory
  content: text | structured      # type-dependent
  embedding: vector(1536)          # nullable until embedding job runs
  importance_score: float          # recomputed periodically, see §7
  decay_rate: float                # type-specific baseline, see §7
  last_accessed_at: timestamp
  access_count: int
  confidence: float                # 0-1, lower for inferred vs. stated facts
  tags: text[]
  supersedes: UUID | null          # points to an older MemoryItem this replaces
  version: int
}
```

### 4.2 The Twelve Types

| Type | What it holds | Write trigger | Retrieval pattern |
|---|---|---|---|
| **Working** | Current session's active scratchpad — the last N turns, current task state | Every conversation turn | Always injected into current context, no ranking needed (it's already "now") |
| **Semantic** | Timeless facts ("Shubhi is Founder of Navgunjara"; "ReRoot uses a learner→maker→earner ladder") | Extracted from conversations/documents by the Knowledge Agent | Vector + keyword hybrid search |
| **Episodic** | Specific events with a when/where ("On July 3 we drafted the ACT essay on risk tolerance") | Every meaningful interaction, tagged with timestamp + context | Time-ranged + semantic search |
| **Procedural** | How-to knowledge — Shubhi's own methods ("three-mode methodology: storytelling → colouring → literacy") | Explicit teaching, or inferred from repeated patterns | Retrieved when a similar task type recurs |
| **Long-term** | Consolidated, compressed summaries of episodic clusters (see §8) | Nightly/weekly consolidation job | Retrieved for "bring me back" and broad context |
| **Conversation** | Raw transcript segments, kept for provenance | Every conversation, chunked | Rarely retrieved directly; mainly the source for extraction into other types |
| **Image** | Extracted descriptions/OCR/embeddings of images and diagrams the user shared | Document/image ingestion pipeline | Multimodal embedding search |
| **Document** | Chunked representations of ingested files (PDFs, resumes, decks) | Document ingestion pipeline | Vector search + linked to Knowledge Graph document entity |
| **Temporal** | Deadlines, recurring events, time-bound commitments | Explicit mention or calendar integration | Queried by the Prediction Engine and Execution Engine directly |
| **Relationship** | Facts about people and Sage's/Shubhi's relationship to them | Extracted whenever a person entity is mentioned | Retrieved when a person is referenced or a relationship-relevant decision is being made |
| **Belief** | The user's stated opinions, values, and evolving positions ("prefers brutal honesty over validation"; "treats fabrication as a hard constraint") | Explicit statement or repeated behavioral pattern, with confidence scoring | Retrieved by Reasoning Engine when tone/approach decisions are made |
| **Reflection** | Sage's own meta-observations about patterns it has noticed ("user tends to over-scope documents when stressed") | Reflection Agent, end of session or nightly | Retrieved by Learning Engine and surfaced to user only when explicitly asked, never silently injected into unrelated conversations |

> Design note: Belief and Reflection memory are the most sensitive types — they represent inferences *about* the user, not facts *stated by* them. These are the only two types with a mandatory `confidence` floor below which they cannot be surfaced without a "Sage believes, unconfirmed" framing. This exists specifically to prevent the system from confidently asserting things about the user's psychology that were never actually said (an explicit anti-pattern, since Sage should describe, not diagnose).

---

## 5. Architecture Diagram

```
                    ┌────────────────────┐
   Conversation ───►│  Ingestion Router    │◄─── Document/Image Pipeline (Phase 13)
   Turn Ends         │  (classifies raw     │
                     │   input → type)      │
                     └──────────┬───────────┘
                                │
                     ┌──────────▼───────────┐
                     │   Write Path           │
                     │  1. Persist envelope    │
                     │     to Postgres          │
                     │  2. Emit `memory.written`│
                     │     event                 │
                     └──────────┬───────────────┘
                                │ (async)
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────────┐  ┌───────────────────┐
    │ Embedding Job  │  │ Extraction Agent   │  │ Consolidation Job   │
    │ → Qdrant write │  │ → entities/relations│  │ (nightly, see §8)   │
    │                │  │   → Knowledge Graph  │  │                     │
    └──────────────┘  └──────────────────┘  └───────────────────┘

                     ┌────────────────────┐
   Context Engine ──►│   Retrieval API       │
   Reasoning Engine   │  (hybrid search +      │
   Conversation Eng.  │   ranking, see §9)      │
                     └──────────┬───────────┘
                                │
                     ┌──────────▼───────────┐
                     │  Ranker                │
                     │  score = f(similarity, │
                     │   importance, recency, │
                     │   decay, access_count) │
                     └────────────────────────┘
```

---

## 6. Database Design

### 6.1 Postgres (source of truth)

```sql
-- One table per memory type keeps type-specific columns typed and indexable,
-- rather than a single JSONB blob table that becomes unqueryable at scale.

CREATE TABLE memory_semantic (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_event_id UUID NOT NULL REFERENCES event_log(id),
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 1.0,
    importance_score FLOAT NOT NULL DEFAULT 0.5,
    decay_rate FLOAT NOT NULL DEFAULT 0.01,
    embedding_id UUID,              -- FK reference into Qdrant point (stored as UUID)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_accessed_at TIMESTAMPTZ,
    access_count INT NOT NULL DEFAULT 0,
    supersedes UUID REFERENCES memory_semantic(id),
    version INT NOT NULL DEFAULT 1,
    tags TEXT[] DEFAULT '{}'
);

CREATE TABLE memory_episodic (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_event_id UUID NOT NULL REFERENCES event_log(id),
    occurred_at TIMESTAMPTZ NOT NULL,
    summary TEXT NOT NULL,
    full_context_ref UUID,          -- pointer to raw conversation chunk if needed
    importance_score FLOAT NOT NULL DEFAULT 0.5,
    decay_rate FLOAT NOT NULL DEFAULT 0.03,   -- decays faster than semantic by default
    embedding_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    tags TEXT[] DEFAULT '{}'
);

-- (memory_procedural, memory_belief, memory_reflection, memory_relationship,
--  memory_temporal, memory_document, memory_image follow the same pattern,
--  each with type-appropriate columns — full DDL in appendix, omitted here
--  for length; the point is structural typing, not a single generic table.)

CREATE TABLE memory_consolidated (   -- "Long-term" type: output of nightly job
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    summary TEXT NOT NULL,
    source_episodic_ids UUID[] NOT NULL,   -- provenance, always
    embedding_id UUID,
    importance_score FLOAT NOT NULL DEFAULT 0.6
);

CREATE INDEX idx_semantic_tags ON memory_semantic USING GIN (tags);
CREATE INDEX idx_episodic_occurred ON memory_episodic (occurred_at DESC);
```

### 6.2 Qdrant (vector index)

One collection per memory type (`memory_semantic`, `memory_episodic`, etc.) rather than one giant collection — this lets retrieval queries target only the relevant type(s) and keeps HNSW graphs smaller and faster per collection.

```
Collection: memory_semantic
  vector_size: 1536
  distance: Cosine
  payload_schema: { postgres_id: uuid, importance_score: float,
                     created_at: datetime, tags: [string] }
```

Payload fields are indexed so Qdrant can pre-filter (e.g., `importance_score > 0.4 AND tags CONTAINS "navgunjara"`) before the vector similarity pass — hybrid retrieval, not pure kNN.

---

## 7. Memory Ranking & Decay

### 7.1 Scoring Formula

```
score(item, query, now) =
      w1 * cosine_similarity(item.embedding, query.embedding)
    + w2 * normalized(item.importance_score)
    + w3 * recency_factor(item.created_at, now, item.decay_rate)
    + w4 * log(1 + item.access_count)
    - w5 * redundancy_penalty(item, already_selected_items)
```

- `recency_factor` uses exponential decay: `exp(-decay_rate * days_since_created)`. Semantic memory decays slowly (long half-life — facts stay true); episodic memory decays faster unless reinforced (repeated access resets part of the decay clock, modeling "things you keep coming back to stay salient").
- `redundancy_penalty` (Maximal Marginal Relevance-style) prevents returning five near-duplicate memories about the same fact — deliberately trading a little recall for context-window efficiency.
- Weights (`w1..w5`) are per-consumer-configurable: the Context Engine building a "bring me back" summary weights recency and importance heavily; the Reasoning Engine answering a specific factual question weights similarity heavily.

### 7.2 Decay Is Never Deletion

Decay lowers an item's rank in the *hot* retrieval path. It never deletes data. Below a configurable importance floor, items move to a **cold tier** (same Postgres table, excluded from the default Qdrant hot collection, still fully searchable via an explicit "search everything, including archived" flag). This mirrors human memory: things fade from easy recall but aren't gone, and an explicit cue ("remember when...") can still surface them.

### 7.3 Importance Scoring Inputs

Importance is not just LLM-guessed at write time — it's a function that's recomputed:

- Explicit user signal (pinned, marked important, corrected by user — corrections spike importance and mark `confidence` as user-verified)
- Structural signal (referenced by many other memories / connected to many Knowledge Graph entities → likely important)
- Outcome signal (memory was retrieved and led to an action that succeeded → reinforced by the Learning Engine, Phase 10)

---

## 8. Memory Compression & Consolidation

### 8.1 Why

Without consolidation, episodic memory grows unbounded and retrieval quality degrades (more near-duplicate noise per query). Consolidation is how raw episodes become durable long-term memory — analogous to sleep-based memory consolidation in humans, and the direct mechanism behind "bring me back" working well after long gaps.

### 8.2 Nightly Consolidation Job

```
1. Pull all episodic memories from the last 24h not yet consolidated.
2. Cluster by project/entity overlap (via Knowledge Graph links) and by
   temporal proximity.
3. For each cluster, LLM-summarize into one `memory_consolidated` row,
   preserving source_episodic_ids for full provenance.
4. Weekly job: consolidate daily summaries into weekly summaries.
   Monthly job: weekly → monthly. This creates a summarization hierarchy,
   so "bring me back after 6 months" retrieves ~6 monthly summaries,
   not 180 daily ones.
5. Original episodic rows are never deleted — they move to cold tier
   once consolidated, retrievable on demand for provenance/drill-down.
```

### 8.3 Memory Versioning & Snapshots

Every write that supersedes a prior fact creates a new row with `supersedes` pointing backward, rather than an in-place update. This gives:

- Full history of belief change ("Sage used to think X, learned Y, now believes Z" — directly useful for the Reflection memory type and for explaining past decisions).
- Point-in-time snapshot capability: `GET /memory/snapshot?as_of=2026-01-15` reconstructs what Sage "knew" at that date by filtering to the latest version as of that timestamp — critical for the "why did I decide this in January" reconstruction use case.

---

## 9. Retrieval API

```
POST /memory/retrieve
{
  "query": "ACT fellowship risk tolerance essay",
  "types": ["semantic", "episodic", "belief"],   // optional filter
  "time_range": null,                              // optional
  "tags": ["act_fellowship"],                       // optional pre-filter
  "top_k": 12,
  "include_cold_tier": false,
  "ranking_profile": "conversation_default"          // maps to weight preset
}

→ 200 OK
{
  "items": [
    {
      "id": "...", "type": "episodic", "content": "...",
      "score": 0.87, "confidence": 1.0,
      "source_event_id": "...", "created_at": "..."
    },
    ...
  ],
  "degraded": false   // true if vector store was unavailable and this is keyword-only fallback
}
```

Every consumer subsystem calls this one endpoint. Type-specific write endpoints exist (`POST /memory/semantic`, `POST /memory/episodic`, etc.) but retrieval is unified — this is the single most important API design decision in this subsystem, because it means ranking improvements are global, not per-consumer.

---

## 10. Sequence Diagram — A Conversation Turn Writing Memory

```
User          Conversation      Ingestion       Postgres       Qdrant      Knowledge
              Engine            Router                                     Agent
 │                │                 │              │              │            │
 │──message──────►│                 │              │              │            │
 │                │──raw turn──────►│              │              │            │
 │                │                 │──classify────►              │            │
 │                │                 │  (working +   │              │            │
 │                │                 │   candidate    │              │            │
 │                │                 │   episodic)    │              │            │
 │                │                 │──insert──────►│              │            │
 │                │                 │◄──event id────│              │            │
 │                │                 │──emit event───────────────────────────────►│
 │                │                 │                              │  (async)   │
 │                │                 │──embed job────────────────────►│          │
 │                │◄──ack (turn stored)──                           │          │
 │◄──response──────│                                                 │          │
 │                │                 │                              │   extract entities,
 │                │                 │                              │   write to Knowledge Graph
```

Note the response to the user is never blocked on embedding or extraction — both are async. This is the concrete application of the async-events-for-non-blocking-work principle from Phase 01 §2.3.

---

## 11. State Machine — Lifecycle of a Memory Item

```
   [written] ──(embedding job)──► [indexed] ──(access over time,
       │                                        decay recomputed)──► [hot]
       │                                                                │
       │                                                       (importance < floor)
       │                                                                ▼
       │                                                            [cold]
       │                                                                │
       │                                                     (referenced explicitly,
       │                                                      or re-clustered into
       │                                                      a consolidation job)
       │                                                                ▼
       └──(superseded by newer fact)──► [superseded, retained for history] ◄──┘
```

---

## 12. Technology Choices & Tradeoffs

| Decision | Chosen | Alternative | Why chosen |
|---|---|---|---|
| Per-type tables vs. one generic table | Per-type | Single JSONB `memories` table | Type-specific columns are indexable and enforce schema at write time; a generic table pushes all validation into application code and makes SQL-level analytics (e.g. "average confidence of belief memories") painful |
| Per-type Qdrant collections vs. one collection with a `type` payload filter | Per-type collections | Single collection | Smaller HNSW graphs per collection = faster search; type is almost always known at query time anyway, so the split costs nothing in practice |
| Decay-based cold tiering vs. TTL deletion | Cold tiering | Hard delete after N days | Aligns with the "recoverable, nothing destructive" design principle in Phase 01; storage cost of text is negligible compared to the cost of an unrecoverable false negative in "bring me back" |
| Versioned rows vs. in-place updates | Versioned (append-only per fact) | UPDATE in place | Required for point-in-time snapshots and belief-change history — a core differentiator, not a nice-to-have |

---

## 13. Security

- All memory tables are encrypted at rest (Postgres transparent data encryption or filesystem-level encryption for the local-first MVP).
- `memory_belief` and `memory_reflection` tables carry an additional application-level encryption layer (separate key), since these are the most sensitive inferred-about-the-user data — a compromise of the DB alone should not expose Sage's psychological model of the user without the separate key.
- Full export (`GET /memory/export`) and full delete (`DELETE /memory/all`) are first-class, tested endpoints — not an afterthought — matching the privacy-first principle.

## 14. Testing Strategy

- **Unit:** ranking formula given fixed inputs produces expected ordering; decay math is correct at boundary conditions (0 days, very old items).
- **Integration:** write → embed job → retrieve round-trip returns the written item within expected latency.
- **Consolidation correctness:** a synthetic week of episodic memories consolidates into a summary that an LLM-as-judge confirms preserves the key facts (regression-tested against a fixed fixture set, not just eyeballed).
- **Degradation:** kill Qdrant in a test environment, confirm `/memory/retrieve` still returns keyword-based results with `degraded: true` rather than erroring.

## 15. Failure Recovery

- Postgres is backed up continuously (WAL archiving); Qdrant and the Graph Store are rebuildable from Postgres + Blob Storage by replaying `memory.written` and `document.ingested` events through the embedding/extraction pipelines.
- A `rebuild_index.py` operational script is a required Phase A deliverable, not a "someday" — the first real test of the recoverability principle should happen deliberately in a staging environment, not accidentally in production during an actual outage.

## 16. Future Improvements

- Cross-device memory sync (CRDT-based) once Sage runs on more than one machine — deferred to Phase 18 (Infrastructure).
- Learned, per-user ranking weights (small model trained on which retrieved memories the user actually found useful) instead of fixed `w1..w5` constants — a Phase F (Personal Model maturity) improvement.
- Multi-modal embeddings unifying text/image/audio into one retrieval space, once Image/Document memory volume justifies the added complexity.

---

*Next: Phase 03 — Knowledge Graph (entity model, relationship types, graph traversal, hybrid retrieval with Memory Engine).*
