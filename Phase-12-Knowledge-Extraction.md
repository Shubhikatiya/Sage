# Sage — Engineering Handbook
## Phase 12: Knowledge Extraction Pipeline

> Continues from Phase 01 (Foundation) through Phase 11 (Conversation Engine).

---

## 1. Overview

Phase 07 defined how Research Engine ingests documents and web content when Sage goes looking for information. This phase defines the wider pipeline: the standard shape every external source — PDFs, images, videos, audio, emails, notes, GitHub, Notion, Obsidian, calendar, messages, code repositories, research papers — passes through on its way to becoming structured memory and knowledge graph entities, regardless of *how* it entered Sage (explicit upload, connected integration, or passive sync).

The architectural point of this phase is that there is **one pipeline shape**, not N source-specific pipelines. Every source type differs only in its **adapter** (how to fetch/parse it); everything downstream of "raw content + basic structure" is identical across all of them. This is what keeps adding a new source type (say, a new note-taking app) a bounded, adapter-only change rather than a new subsystem.

## 2. Goals

- One pipeline shape: `Adapter → Normalize → Chunk → Extract → Resolve → Write`, reused across every source type.
- Each source adapter is independently pluggable and testable — adding Notion support should never require touching the PDF adapter's code.
- Preserve source-type-specific structure where it matters (a code repository's file/function structure, an email's thread structure, a calendar event's time-bound nature) rather than flattening everything into generic text.
- Respect explicit, revocable consent per source — this pipeline only processes what the user has explicitly connected or uploaded, per the non-goals stated in Phase 01 §1.4 (no passive surveillance-style ingestion).

## 3. Responsibilities

**Owns:** the adapter registry and interface contract, the shared normalize/chunk/extract/resolve/write pipeline stages, per-source-type sync scheduling (for connected integrations, as opposed to one-off uploads).

**Does not own:** the actual extraction intelligence (Knowledge Agent, Phase 08 §5.4, and Memory Agent, Phase 08 §5.3, do the classification/structuring work within the pipeline) or long-term storage (Memory Engine/Knowledge Graph, as with every other ingestion path).

---

## 4. The Adapter Interface

```
SourceAdapter {
  source_type: str                    # "pdf" | "email" | "github" | ...
  connection_type: "upload" | "sync"    # one-off vs. ongoing connected integration

  fetch() -> RawContent[]               # pulls new/changed content since last sync
  parse(raw: RawContent) -> NormalizedDocument
  supports_incremental_sync: bool        # can it fetch only what's new, or
                                           # does every sync re-pull everything
}

NormalizedDocument {
  source_type: str
  source_ref: str                        # URL, file path, message ID, commit
                                           # hash — whatever uniquely identifies
                                           # this item within its source
  title: str | null
  content: text | structured              # structured preserved where the
                                           # source type has meaningful structure
                                           # (see §6)
  metadata: jsonb                          # author, timestamps, source-specific
                                           # fields
  fetched_at: timestamp
}
```

Every adapter implements this same interface; the pipeline stages after `parse()` never need to know which adapter produced the `NormalizedDocument` they're processing.

---

## 5. Architecture Diagram

```
  ┌───────┐ ┌───────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐ ┌────────┐
  │  PDF   │ │ Image │ │  Video  │ │  Audio  │ │  Email  │ │  Notes   │ │ GitHub  │  ...
  │Adapter │ │Adapter│ │ Adapter │ │ Adapter │ │ Adapter │ │ Adapter  │ │Adapter  │
  └───┬───┘ └───┬───┘ └───┬────┘ └───┬────┘ └───┬────┘ └────┬────┘ └───┬────┘
      │         │         │          │          │           │          │
      └─────────┴─────────┴──────────┴──────────┴───────────┴──────────┘
                                      │
                          ┌───────────▼────────────┐
                          │   Normalize                │  → NormalizedDocument,
                          │   (shared, source-agnostic)  │    consistent envelope
                          └───────────┬────────────┘
                                      ▼
                          ┌───────────────────────┐
                          │   Chunk                    │  → semantic chunking,
                          │   (source-structure-aware)   │    respecting source-type
                          └───────────┬────────────┘     structure (§6)
                                      ▼
                          ┌───────────────────────┐
                          │   Extract                   │──► Memory Agent (Phase 08 §5.3)
                          │   (classify into memory       │     classifies into memory types
                          │    types, extract entities)     │
                          │                                │──► Knowledge Agent (Phase 08 §5.4)
                          │                                │     extracts entities/relations
                          └───────────┬────────────┘
                                      ▼
                          ┌───────────────────────┐
                          │   Resolve                   │──► Entity Resolution pipeline
                          │   (dedupe against existing     │     (Phase 03 §6), Guardian
                          │    entities/memory)              │     review gate for low-confidence
                          └───────────┬────────────┘
                                      ▼
                          ┌───────────────────────┐
                          │   Write                     │──► Memory Engine + Knowledge Graph
                          └───────────────────────────┘
```

---

## 6. Source-Type-Specific Structure Preservation

The `Chunk` stage is where generic flattening would lose valuable structure — each source type gets a chunking strategy suited to its shape, while still producing the same `NormalizedDocument` → chunk output contract downstream stages expect:

| Source type | Structure preserved | Chunking strategy |
|---|---|---|
| PDF | Page boundaries, section headers if detectable | Semantic (paragraph/section), page-indexed |
| Image | N/A (single unit) | Whole-image vision description + OCR text as one chunk, linked as Image memory (Phase 02 §4.2) |
| Video | Scene/transcript timestamps | Transcript chunked by topic segment, each chunk timestamp-linked back to the source video for drill-down |
| Audio | Speaker turns, timestamps | Transcript chunked by speaker turn or topic shift |
| Email | Thread structure, sender/recipient | One chunk per message within a thread, thread relationship preserved as a graph edge (`part_of` thread) |
| Notes (Obsidian/Notion) | Note-to-note links, headers | Chunked by header/section, existing note-to-note links become candidate Knowledge Graph relationships directly (a note linking to another note is strong signal for an `related_to` or `part_of` edge) |
| Calendar | Event time-bounds, recurrence | Each event becomes a Temporal memory item (Phase 02 §4.2) directly, not generic text chunking |
| Messages (Slack/etc.) | Channel/thread context, timestamps | Chunked by conversational thread, similar to email |
| Code repositories | File/function/module structure | Chunked by function/class where parseable, file-level otherwise; commit history optionally chunked separately as Episodic memory ("what changed and why," from commit messages) |
| Research papers | Section structure (abstract/methods/results), citations | Chunked by section; citation list feeds directly into the Citation Graph (Phase 07 §8) as `cites` edges |

This table is the concrete answer to the brief's instruction that "everything should become structured knowledge" — structure isn't discarded in favor of a lowest-common-denominator text blob; it's mapped, per source type, onto the memory/graph primitives already defined in Phases 02–03.

---

## 7. Sync Scheduling for Connected Integrations

Distinct from one-off uploads (which run through the pipeline immediately on receipt), connected integrations (GitHub, Notion, calendar, email) need ongoing sync:

```
1. Initial connection: full historical pull (bounded — e.g., last 12
   months by default, configurable), user-consented per source
   (Phase 01 §1.4 — explicit, revocable per source).

2. Ongoing sync: Scheduler Agent (Phase 08 §5.7) triggers periodic
   incremental fetches per adapter's `supports_incremental_sync`:
     - true  → fetch only new/changed items since last sync cursor
     - false → full re-fetch, diffed against previously-ingested
               source_refs to identify what's actually new (avoids
               reprocessing unchanged content through the full
               pipeline unnecessarily)

3. Deletion/revocation handling: if the user disconnects a source,
   already-ingested memory/graph content derived from it is NOT
   automatically deleted (it's now part of Sage's history) unless
   the user explicitly requests removal — disconnecting stops future
   ingestion, it doesn't retroactively erase context, consistent
   with the "memory is never silently deleted" principle from
   Phase 02 §7.2, while still respecting an explicit deletion request
   if made (Phase 02 §13 export/delete guarantees).
```

---

## 8. API Design

```
POST /extraction/upload
{
  "file_ref": "...",           // Blob Storage reference after upload
  "source_type": "auto"          // auto-detected if omitted
}

POST /extraction/connect_source
{
  "source_type": "github",
  "credentials_ref": "...",       // handled via Execution Engine's
                                    // credential scoping, Phase 10 §14
  "sync_scope": "..."               // e.g., specific repos, date range
}

GET /extraction/source/{id}/status    // last sync time, items processed,
                                        // items pending Guardian review

DELETE /extraction/source/{id}         // revoke connection (§7)
```

---

## 9. Sequence Diagram — Connecting a New Notion Workspace

```
User    Extraction API   Notion Adapter   Normalize/Chunk   Memory+Knowledge Agents   Guardian
 │            │                │                │                    │                   │
 │──connect──►│                │                │                    │                   │
 │  Notion      │                │                │                    │                   │
 │            │──fetch()───────►│                │                    │                   │
 │            │◄──raw pages──────│                │                    │                   │
 │            │──parse per page──────────────────►│                    │                   │
 │            │◄──NormalizedDocuments, chunked────│                    │                   │
 │            │──extract────────────────────────────────────────────►│                   │
 │            │                                                        │──low-confidence──►│
 │            │                                                        │  entity matches     │
 │            │                                                        │◄──approved/queued───│
 │            │◄──write complete, N items processed, M queued for review│                   │
 │◄──status────│                                                                              │
```

---

## 10. Technology Choices & Tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| One shared pipeline with pluggable adapters vs. per-source-type pipelines | Shared pipeline (§4-5) | N independent pipelines | Directly serves the "adding a new source is a bounded, adapter-only change" goal — duplicated pipelines would mean every improvement (better chunking, better entity resolution) has to be reapplied N times |
| Structure-aware chunking per source type vs. uniform text chunking | Structure-aware (§6) | Uniform | Flattening a code repository or calendar into generic text chunks would lose exactly the structure that makes those sources valuable — the whole point of "everything becomes structured knowledge" is preserving structure, not discarding it |
| Non-destructive disconnection vs. auto-delete on source disconnect | Non-destructive (§7) | Auto-delete | A disconnected source's already-extracted knowledge is now part of Sage's understanding of the user's history; auto-deleting it would undermine the persistence goals in Phase 01 §1.1 — explicit user-requested deletion remains available and honored |

---

## 11. Scaling Strategy

Initial historical pulls for a newly connected source are the main burst-load scenario (potentially thousands of items at once) — these run as background batch jobs through the Event Bus (Phase 01 §2.3), not synchronously, with the extraction pipeline naturally rate-limited by LLM call throughput rather than needing separate queueing infrastructure at single-user scale.

## 12. Security

- Source credentials are scoped and stored per Execution Engine's credential-handling discipline (Phase 10 §14) even though extraction is read-mostly (fetching, not acting) — read access to email/GitHub/Notion is still sensitive and warrants the same least-privilege treatment.
- Explicit per-source consent (§7) is enforced at the API layer — `POST /extraction/connect_source` cannot silently expand scope beyond what the user configured (e.g., a GitHub connection scoped to specific repos cannot later pull from repos outside that scope without a fresh grant).

## 13. Testing Strategy

- **Adapter contract compliance:** every adapter tested against the shared `SourceAdapter` interface with a standard test harness, so a new adapter can be validated without hand-writing pipeline-integration tests each time.
- **Structure preservation regression:** fixture documents per source type (a sample email thread, a sample code repo) with known expected chunk structure and expected graph edges (e.g., thread relationships, note-to-note links).
- **Incremental sync correctness:** simulate a source with new items since last sync, assert only the new items are processed, not a full re-pull, when `supports_incremental_sync=true`.
- **Consent/scope enforcement:** attempt to fetch outside a connection's configured `sync_scope`, assert it's rejected.

## 14. Failure Recovery

Raw fetched content is written to Blob Storage before extraction begins (same pattern as Phase 07 §16) — an extraction pipeline bug or crash mid-processing never requires re-fetching from the external source, only re-running extraction against already-stored raw content.

## 15. Future Improvements

- Real-time sync (webhook-driven) for sources that support it, rather than periodic polling — reduces latency between something happening externally and Sage knowing about it, once the polling-based MVP proves the pipeline shape is correct.
- Smarter incremental diffing for sources without native change-tracking (currently full re-fetch + diff against known `source_ref`s; could be optimized per source with content hashing to avoid even the re-fetch where possible).
- Cross-source entity resolution quality improvements (a person mentioned in email and in a GitHub commit author field should resolve to the same Person entity — currently relies on the general entity resolution pipeline from Phase 03 §6, worth dedicated tuning as more source types come online).

---

*Next: Phase 13 — Prediction Engine (predicting forgotten work, risks, deadlines, opportunities, energy, project bottlenecks).*
