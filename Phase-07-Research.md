# Sage — Engineering Handbook
## Phase 07: Research Engine

> Continues from Phase 01 (Foundation) through Phase 06 (Bring Me Back Engine).

---

## 1. Overview

The Research Engine is Sage's interface to information it doesn't already have — the web, documents, PDFs, images, and any external source the user points it at. Its job is not just to fetch content but to turn unstructured external material into the same structured, provenance-attributed form everything else in Sage relies on: memory items and knowledge graph entities, never a raw dump of text sitting outside the system's model of the world.

The core discipline here is **source verification and citation integrity**. Sage's credibility depends on never presenting web-sourced claims with more confidence than they deserve, and never blurring the line between "the user said this" and "a website said this."

## 2. Goals

- Ingest heterogeneous source types (web pages, PDFs, images, scanned documents) through one consistent pipeline that ends in the same Memory/Knowledge Graph writes as everything else.
- Track provenance at the source level, not just the extraction level — every fact traces back not only to a `source_event_id` but to a specific URL/document/page, with a retrieval timestamp (web content changes; "true as of when" matters).
- Support a citation graph — which sources support which claims, and which sources cite each other — so the Reasoning Engine (Phase 04) can weigh corroborated claims over single-source ones.
- Keep research bounded and cancellable — a slow or unreliable external source must never block an entire agent turn (this constraint was already flagged as a failure-isolation requirement in Phase 01 §2.4; this phase is where it's actually implemented).

## 3. Responsibilities

**Owns:** web fetching, document ingestion pipelines (PDF/image/OCR), source verification heuristics, citation graph construction, research notebook state (multi-step research sessions).

**Does not own:** deciding what to do with research findings (Reasoning Engine), or long-term storage/ranking of extracted facts (Memory Engine/Knowledge Graph — Research Engine writes to them, doesn't compete with them).

---

## 4. Architecture Diagram

```
        ┌─────────────────────────────────────────────────┐
        │                Research Request                     │
        │   (from Reasoning Engine, Orchestrator, or direct     │
        │    user upload of a document/image)                    │
        └───────────────────────┬─────────────────────────┘
                                 │
                  ┌───────────────┴────────────────┐
                  ▼                                  ▼
        ┌──────────────────┐                ┌──────────────────┐
        │  Web Research Path  │                │  Document Ingestion │
        │                      │                │  Path                │
        │  Search → Fetch →     │                │  PDF/Image/OCR →      │
        │  Extract → Verify      │                │  Extract → Structure   │
        └──────────┬───────────┘                └──────────┬───────────┘
                   │                                        │
                   └───────────────────┬────────────────────┘
                                       ▼
                          ┌─────────────────────────┐
                          │   Source Verification       │
                          │   & Confidence Scoring        │
                          └──────────────┬─────────────┘
                                        ▼
                          ┌─────────────────────────┐
                          │   Citation Graph Builder     │
                          │   (source → source, source →  │
                          │    claim edges)                │
                          └──────────────┬─────────────┘
                                        ▼
                    ┌─────────────────────┴─────────────────────┐
                    ▼                                             ▼
          Memory Engine (Phase 02)                    Knowledge Graph (Phase 03)
          writes: memory_document,                    writes: Document entities,
          memory_image, semantic facts                 citation edges, extracted
          extracted from sources                        entities/relations
```

---

## 5. Web Research Path

```
1. Query formulation
   - Reasoning Engine hands off a specific information need, not a
     vague topic ("what is ACT Fellowship's current application
     deadline for the 2026 cohort" not "tell me about ACT").

2. Search
   - Issue search queries, short/specific (per system-level search
     conventions), retrieve candidate URLs with snippets.

3. Fetch (bounded, cancellable)
   - Hard timeout per fetch (default 8s).
   - Circuit breaker: if a domain fails repeatedly within a session,
     stop retrying it for the remainder of the research task.
   - Fetches run concurrently up to a pool limit, not serially —
     research latency should scale with the slowest acceptable
     source, not the sum of all sources.

4. Extract
   - Convert raw HTML/page content to clean structured text
     (strip nav/ads/boilerplate).
   - Attach: url, fetched_at, page_title, extraction_method.

5. Verify (§7)

6. Emit `research.source_ingested` event → triggers Memory/Graph writes.
```

---

## 6. Document Ingestion Path (PDF / Image / OCR)

```
1. Classify document type on upload:
     text-native PDF | scanned/image PDF | standalone image | slide deck

2. Route:
     text-native PDF   → direct text extraction, page-indexed
     scanned/image PDF → OCR pass (page-by-page), confidence score
                          per page retained (OCR is imperfect — low-
                          confidence pages are flagged, not silently
                          trusted at the same level as clean text)
     standalone image   → vision-model description + OCR if it
                          contains text (e.g., a photo of a whiteboard
                          from a ReRoot field session)
     slide deck (pptx)   → per-slide text + speaker notes extraction

3. Chunk extracted content (semantic chunking, not fixed-size —
   respect section/paragraph boundaries where detectable).

4. Store raw bytes in Blob Storage (Phase 01 §2.5 — Blob Storage is
   the immutable source of truth for anything downstream derives from).

5. Emit `document.ingested` event with blob_ref, chunk list,
   per-chunk confidence.
```

This is the pipeline that also serves the broader Knowledge Extraction Pipeline described in Phase 13 (forward reference) — Research Engine owns the document-ingestion mechanics; Phase 13 owns the wider catalog of source types (email, Notion, calendar, code repos) that feed into the same pipeline shape.

---

## 7. Source Verification & Confidence Scoring

Not every source deserves equal trust. This is a deliberate scoring step, not an afterthought:

```
source_confidence(source) = f(
    domain_reputation,      # rough tiering: primary sources (gov, official
                              org sites, arXiv, company blogs) > established
                              news/reference > aggregators/forums
    corroboration_count,     # how many independent sources state the
                              same claim (via citation graph, §8)
    recency,                  # for time-sensitive claims (deadlines, current
                              roles), how recently was this fetched/published
    extraction_confidence     # OCR confidence, or HTML-extraction cleanliness
                              (garbled extraction = lower trust even from
                              a reputable domain)
)
```

Claims extracted from low-confidence sources are written to Memory/Knowledge Graph with a correspondingly low `confidence` field (Phase 02 §4.1, Phase 03 §4.2) — they don't get filtered out entirely (a single-source claim might still be the only available information), but they inherit the same "surfaced with a caveat, not asserted as settled fact" treatment as tentative graph entities (Phase 03 §6).

---

## 8. Citation Graph

A dedicated layer within the Knowledge Graph (reusing Phase 03's Entity/Relationship model rather than a separate structure):

```
Document/Source entities, connected by:
  `cites`        — source A references source B
  `supports`     — source A's claim is corroborated by source B
  `contradicts`  — source A's claim conflicts with source B's

Claim-level edges:
  extracted fact (a memory_semantic item) --[`derived_from`]--> Source entity
```

This is what lets the Reasoning Engine (Phase 04 §9) compute `evidence_agreement` for confidence scoring — "3 independent sources support this" is a direct query over `supports` edges and distinct `derived_from` sources, not a re-derived heuristic.

### 8.1 Contradiction Handling

When two sources disagree (a `contradicts` edge is detected — e.g., two pages state different deadlines for the same fellowship), Research Engine does **not** pick a winner automatically. It writes both claims with their respective confidence, flags the contradiction explicitly, and surfaces it as an open item for the Reasoning Engine or the user to resolve — silently choosing one source over another would hide a real uncertainty the user should know about.

---

## 9. Research Notebooks

For multi-step research tasks (e.g., "find fellowships matching Navgunjara's profile" — a task that spans many searches over potentially many sessions), Research Engine maintains a **notebook**: a persistent, resumable research session.

```
ResearchNotebook {
  id: UUID
  goal: text                          # the original information need
  status: "active" | "completed" | "abandoned"
  sources_reviewed: [source_id]
  findings: [ { claim: text, source_ids: [UUID], confidence: float } ]
  open_subquestions: [text]           # what's still unanswered
  created_at, updated_at: timestamp
}
```

Notebooks are themselves memory items (a specialization of episodic/document memory) — resumable across sessions, and directly useful for the Bring Me Back flow (Phase 06): an in-progress research notebook is exactly the kind of "stalled, no identified blocker" item that reconstruction should surface if left untouched.

---

## 10. API Design

```
POST /research/web
{
  "query": "ACT Fellowship 2026 application deadline",
  "max_sources": 5,
  "notebook_id": null            // optional, attaches to an existing notebook
}

POST /research/ingest_document
{
  "blob_ref": "...",
  "document_type": "auto"        // auto-detected if omitted
}

GET /research/notebook/{id}
POST /research/notebook/{id}/subquestion   // add a follow-up question to an
                                             // active notebook

→ (web/ingest responses)
{
  "sources": [
    { "url": "...", "title": "...", "confidence": 0.82,
      "extracted_claims": [...] }
  ],
  "contradictions_detected": [...],
  "citation_graph_updates": [...]
}
```

---

## 11. Sequence Diagram — Web Research Requested Mid-Reasoning

```
Reasoning Eng.   Research Engine     Search        Fetch Pool     Verification   Memory+Graph
      │                │                │               │              │              │
      │──need: "ACT     │                │               │              │              │
      │  deadline"─────►│                │               │              │              │
      │                │──query────────►│               │              │              │
      │                │◄──candidate URLs│               │              │              │
      │                │──fetch (bounded,───────────────►│              │              │
      │                │  concurrent, w/ timeout)         │              │              │
      │                │◄──raw content───────────────────│              │              │
      │                │──extract + score────────────────────────────►│              │
      │                │◄──confidence, contradictions───────────────────│              │
      │                │──write claims + citation edges──────────────────────────────►│
      │◄──sources + claims + confidence──│               │              │              │
```

---

## 12. Technology Choices & Tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Confidence-scored ingestion vs. binary accept/reject sources | Confidence-scored (§7) | Filter out anything below a reputation threshold | Binary filtering discards genuinely useful single-source information (common for niche topics like specific fellowship deadlines); scored confidence preserves it while being honest about reliability |
| Explicit contradiction surfacing vs. auto-resolving to "most reputable" source | Explicit surfacing (§8.1) | Auto-pick highest domain_reputation source | Auto-resolution hides real-world uncertainty (sources genuinely do disagree, e.g., outdated vs. updated deadline pages) — surfacing it respects the explainability principle and lets the user apply judgment Sage doesn't have |
| Research Notebooks as memory items vs. a separate research-state store | Reuse Memory Engine | Standalone research database | Same reuse-over-duplication principle as Phase 06 — notebooks benefit automatically from decay/consolidation/Bring-Me-Back integration without extra plumbing |
| Concurrent bounded fetch pool vs. sequential fetching | Concurrent, pooled | Sequential | Research latency must not scale linearly with source count; also directly implements the Phase 01 failure-isolation requirement that one slow source can't block a whole task |

---

## 13. Scaling Strategy

Research volume scales with how often Sage is asked to look things up, not with total memory size — the relevant scaling risk is external rate limits (search APIs, target sites) rather than internal compute. Circuit breakers (§5) and per-domain backoff prevent any single flaky source from degrading overall research throughput.

## 14. Security

- Research Engine must respect the harmful-content-safety boundaries already established for search generally — it does not fetch from or cite sources that are extremist, facilitate illegal activity, or otherwise fall under the standing content-safety constraints; a query with clear harmful intent is declined at the query-formulation step, not filtered after the fact.
- Document ingestion of user-uploaded material (resumes, personal notes) is treated at the same privacy tier as any first-party data — Blob Storage encryption (Phase 01 §2.5) applies uniformly regardless of source.
- Outbound fetches never include personal-model or belief-memory data in request parameters (no accidental exfiltration of sensitive context into search queries sent to third parties).

## 15. Testing Strategy

- **Extraction quality regression:** fixed set of test PDFs/HTML pages with known expected extracted text, run on every extraction-pipeline change.
- **Contradiction detection:** fixture pair of sources with a deliberate factual conflict, assert it's flagged rather than silently resolved.
- **Timeout/circuit-breaker behavior:** simulated slow/failing endpoint, assert the research task completes within its overall bound and doesn't retry the failing domain indefinitely.
- **Confidence calibration:** spot-check that OCR-derived low-confidence content is actually treated as lower-confidence downstream (in Memory Engine writes and Reasoning Engine's evidence weighting).

## 16. Failure Recovery

Blob Storage retains all raw fetched/ingested source material, so re-extraction (with an improved pipeline, or after an extraction bug fix) is always possible without re-fetching from the original (possibly now-changed or removed) web source — this is the research-specific instance of the general recoverability principle from Phase 01.

## 17. Future Improvements

- Scheduled re-verification of time-sensitive claims (a stored deadline fact gets a periodic re-fetch to confirm it hasn't changed, feeding directly into the Prediction Engine's deadline tracking).
- Source-reputation learning (currently a rough static tiering; could improve over time based on how often a given domain's claims get corroborated vs. contradicted across many research tasks).
- Better slide-deck/complex-layout extraction (current pptx/PDF handling is page/slide-level; dense multi-column layouts or heavily graphical decks remain a known weak point worth revisiting).

---

*Next: Phase 08 — Multi-Agent System (Planner, Research Agent, Memory Agent, Knowledge Agent, Reflection Agent, Execution Agent, Scheduler, Learning Agent, Guardian — full per-agent spec).*
