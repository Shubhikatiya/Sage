# Sage — Engineering Handbook
## Phase 16: Dashboard Architecture

> Continues from Phase 01 (Foundation) through Phase 15 (World Model, Opportunity Detection, Personal Strategy Engine).

---

## 1. Overview

Every prior phase defined backend capability. The Dashboard is the first visual, persistent (non-conversational) surface — a place to see Sage's state at a glance rather than asking for it turn by turn. It's explicitly secondary to the Conversation Engine in the north-star vision (Phase 01 §1.1: "the conversational interface is a thin client... memory is the product"), but it earns its place because some things — a knowledge map, a timeline, a relationship graph — are genuinely better understood visually than through prose, and because a returning user benefits from being able to *browse* reconstructed context, not just read a synthesized paragraph.

The design discipline: the Dashboard is a **read-mostly rendering layer** over existing engine APIs. It introduces no new backend logic of its own — every panel is a view over an API already specified in Phases 02–15.

## 2. Goals

- Provide at-a-glance views of the state every engine already computes: knowledge map (Phase 03), timeline (Phase 03 §10), active projects (Phase 14 §9), daily briefing (Phase 06 lightweight variant), memory browsing (Phase 02), analytics on reasoning/learning (Phase 04/09), reflection history (Phase 09 §8), and relationship graph (Phase 03 entity subgraph).
- Keep the Dashboard genuinely thin — no panel should require new backend computation; if a desired view needs new logic, that logic belongs in the relevant engine's API, not dashboard-layer code.
- Support drill-down consistently: every summary view should let the user click through to the underlying evidence/trace, mirroring the explainability discipline already built into Reasoning traces (Phase 04 §6.1) and reconstruction output (Phase 06 §8).

## 3. Responsibilities

**Owns:** panel layout/composition, client-side rendering, drill-down navigation between panels, dashboard-specific caching for read performance.

**Does not own:** any data computation — every panel's data comes from an existing engine API, called as-is.

---

## 4. Panel Inventory

| Panel | Backend source | Primary interaction |
|---|---|---|
| Knowledge Map | `GET /graph/traverse` (Phase 03 §11), rendered as an interactive node graph | Click a node → drill into entity detail + its memory items |
| Timeline | `GET /graph/timeline` (Phase 03 §10) | Scrub across time range, filter by project/entity |
| Mission Dashboard | `GET /model/user` Identity + Career sub-models (Phase 14 §5, §7) | Static overview, links out to full sub-model views |
| Projects | `GET /model/user/projects` (Phase 14 §9) | Per-project card, drill into `per_project_summary` detail incl. rejected alternatives |
| Research | `GET /research/notebook/{id}` list view (Phase 07 §9) | Resume an active notebook directly into a conversation turn |
| Daily Briefing | `POST /bring_me_back` with `depth=brief` (Phase 06 §10) | A lightweight, always-fresh version of full reconstruction — the routine, low-gap-length case of the same mechanism |
| Memory Explorer | `POST /memory/retrieve` (Phase 02 §9) with a search/filter UI over type, tags, time range, confidence | Browse by type; toggle `include_cold_tier` to see decayed/archived memory |
| Analytics | Aggregates over Reasoning traces (Phase 04 §6.1) and Learning Engine calibration history (Phase 09 §7) | Confidence calibration trend, prediction precision over time (Phase 13 §9 logs) |
| Reflection | `GET` on Reflection-type memory (Phase 02 §4.2) + Personal Model version diffs (Phase 09 §8) | "How has Sage's model of me changed this month" |
| Relationship Graph | `GET /graph/traverse` scoped to Person entities (Phase 03 §4.1) | Visualize social/professional network as tracked in the Knowledge Graph |

---

## 5. Architecture Diagram

```
                     ┌───────────────────────────┐
   Browser/Client ──►│      Dashboard Frontend        │
                     │      (Next.js, per Phase 01       │
                     │       stack decisions)              │
                     └──────────────┬───────────────┘
                                    │ REST calls, no new endpoints —
                                    │ every call targets an existing
                                    │ engine API from Phases 02-15
                     ┌──────────────▼───────────────┐
                     │   Dashboard Read-Cache Layer      │  → thin caching
                     │   (short-TTL, per-panel)             │    only, no
                     └──────────────┬───────────────┘    computation
                                    │
        ┌─────────────┬─────────────┼─────────────┬─────────────┐
        ▼             ▼             ▼             ▼             ▼
   Memory Engine  Knowledge     Reasoning     Personal      Prediction/
   (Phase 02)     Graph          Engine        Model         World Model
                  (Phase 03)     (Phase 04)    (Phase 14)    (Phase 13/15)
```

---

## 6. Read-Cache Layer

The one piece of dashboard-specific infrastructure, and deliberately minimal:

```
DashboardCache {
  key: str                        # panel + params hash
  value: jsonb
  computed_at: timestamp
  ttl_seconds: int                 # short — default 60s for most panels,
                                    # longer (e.g., 1hr) for slow-changing
                                    # views like the Relationship Graph
}
```

This exists purely to avoid redundant recomputation when a user has a dashboard tab open and multiple panels poll on similar cadences — it is explicitly **not** a second source of truth; any write-triggering event (Phase 01 §2.3) that affects a cached panel's underlying data invalidates the relevant cache entries rather than waiting out the TTL, keeping the dashboard from ever showing meaningfully stale data after an action the user just took.

---

## 7. Drill-Down Navigation Pattern

Every panel follows the same interaction contract, so the Dashboard's UX stays predictable as new panels are added:

```
Summary view (e.g., Knowledge Map node, Project card)
   │  click
   ▼
Detail view (entity attributes, linked memory items, confidence,
              evidence_refs — same fields already defined on the
              underlying data, Phase 02 §4.1 / Phase 03 §4.2)
   │  click on a specific evidence item
   ▼
Source view (the actual memory item / reasoning trace / research
              source, Phase 04 §6.1 / Phase 07 §8 — the same
              provenance chain used everywhere else in the system,
              now browsable rather than only reachable through
              conversation)
```

This three-level pattern (summary → detail → source) is standardized across every panel — a deliberate consistency decision so users build one mental model for "how do I get to the evidence" regardless of which panel they started in.

---

## 8. Daily Briefing — Relationship to Bring Me Back

Worth calling out explicitly: the Daily Briefing panel is not new logic — it's `POST /bring_me_back` (Phase 06 §9) called with a short, routine gap (since-last-session, typically under a day), rendered as a persistent dashboard panel rather than only triggered by an explicit chat message. This is the same reuse discipline applied one more time: the "routine daily check-in" and the "returning after six months" experience are the same mechanism at different gap lengths, exactly as designed in Phase 06 §5's adaptive granularity.

---

## 9. API Design

The Dashboard introduces no new backend write endpoints. Its only dashboard-specific endpoints are read-cache management:

```
GET /dashboard/panel/{panel_name}?params=...
   → cached (if fresh) or live-computed via the underlying engine
     API, cache populated on response

POST /dashboard/invalidate
{ "affected_entities": [entity_id] }
   → called internally by the Event Bus subscriber (§10) whenever a
     relevant write event fires, not exposed to the frontend directly
```

---

## 10. Cache Invalidation via Event Bus

```
Event Bus subscriber (Dashboard service):
  on memory.written        → invalidate Memory Explorer, Timeline caches
  on graph.entity_updated    → invalidate Knowledge Map, Relationship
                                Graph, Projects caches
  on personal_model.updated   → invalidate Mission Dashboard, Reflection
                                caches
  on prediction.surfaced        → invalidate Analytics cache
```

This subscriber pattern reuses the same async event mechanism established in Phase 01 §2.3 for every other cross-subsystem notification — the Dashboard is just one more consumer of events every other engine already emits, not a special case requiring new plumbing.

---

## 11. Sequence Diagram — Opening the Daily Briefing Panel

```
User    Dashboard Frontend   Read-Cache      Bring Me Back Orchestrator
 │             │                  │                     │
 │──open tab──►│                  │                     │
 │             │──GET panel───────►│                     │
 │             │  daily_briefing    │                     │
 │             │                  │──cache miss/stale───►│
 │             │                  │  (or fresh, return    │
 │             │                  │   cached)              │
 │             │                  │◄──reconstruction───────│
 │             │                  │  (depth=brief,           │
 │             │                  │   Phase 06 §9)             │
 │             │◄──rendered data──│                          │
 │◄──briefing───│                                             │
```

---

## 12. Technology Choices & Tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Thin rendering layer, zero new backend computation vs. dashboard-specific aggregation services | Thin (§3) | New aggregation logic per panel | Keeps a single source of truth for every computation — a panel showing stale/inconsistent data relative to what Conversation Engine would say about the same topic is a trust failure the thin-layer design structurally prevents |
| Short-TTL cache + event-driven invalidation vs. no caching / always-live | Cache + invalidation (§6, §10) | Always call underlying APIs live | Avoids redundant recomputation for panels that don't change every second (Relationship Graph, Mission Dashboard) while event-driven invalidation guarantees no meaningfully-stale views after an action the user just took — best of both |
| Standardized three-level drill-down across all panels vs. bespoke UX per panel | Standardized (§7) | Bespoke per panel | Consistency reduces cognitive load as the panel count grows; also makes adding a new panel cheaper since the interaction pattern is already defined |

---

## 13. Scaling Strategy

Dashboard load is inherently bounded by single-user, few-concurrent-session usage (same reasoning as Conversation Engine's scaling note, Phase 11 §12) — the cache layer exists for responsiveness, not for handling meaningful concurrent load.

## 14. Security

The Dashboard enforces exactly the same access controls as the underlying APIs it calls — it introduces no new authorization surface, and in particular does not bypass the sensitivity tiering already established for Belief/Reflection memory (Phase 02 §13) or the Personal Model (Phase 14 §15). A Reflection panel showing "how has Sage's model of me changed" is exactly the kind of view that should sit behind the same auth tier as direct Belief-memory access.

## 15. Testing Strategy

- **Panel-to-API mapping tests:** for each panel, assert its rendered data matches what a direct call to the underlying engine API returns — this is the primary regression guard against a panel silently reimplementing logic instead of calling the real API.
- **Cache invalidation correctness:** fire a `memory.written` event, assert the relevant cached panels are actually invalidated and the next read reflects the new state.
- **Drill-down integrity:** for each panel, assert the summary → detail → source path resolves correctly and terminates at real, existing evidence (never a broken link into data that doesn't actually exist).

## 16. Failure Recovery

Because the Dashboard holds no authoritative data (§6 — the cache is disposable), recovery from any Dashboard-layer failure is trivial: clear the cache and re-render from the underlying engines, which are already independently recoverable per their own phase specifications.

## 17. Future Improvements

- Customizable panel layout (currently a fixed panel set; a personalizable arrangement once real usage reveals which panels get used most).
- Cross-panel filtering (e.g., selecting a project in the Projects panel filters the Timeline and Knowledge Map to that project's scope) — a genuine UX improvement, deferred until the standalone panels are proven useful first.
- Export views (e.g., exporting the Reflection panel's monthly diffs as a standalone document) — a natural extension of the existing export guarantees (Phase 02 §13) applied at the panel level.

---

*Next: Phase 17 — Security (encryption, permissions, secrets, identity, audit logs, memory privacy, AI safety, backup, recovery, offline mode).*
