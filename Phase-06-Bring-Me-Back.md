# Sage — Engineering Handbook
## Phase 06: Bring Me Back Engine

> Continues from Phase 01 (Foundation), Phase 02 (Memory), Phase 03 (Knowledge Graph), Phase 04 (Reasoning), Phase 05 (Context Engine).

---

## 1. Overview

This is the north-star capability named explicitly in Phase 01: the user disappears for months, returns, types "bring me back," and receives an accurate, prioritized reconstruction of everything that matters. Every subsystem before this phase exists partly to make this possible — the Bring Me Back Engine is where they compose into one coherent experience.

Architecturally, this is **not** a new data store or a new kind of intelligence. It is a specific, well-defined orchestration of Context Engine, Memory Engine, Knowledge Graph, Reasoning Engine, and Prediction Engine, invoked with a distinct mode and a distinct output contract. Treating it as "just another engine" from scratch would mean re-deriving consolidation, ranking, and synthesis logic that already has to exist for ordinary day-to-day operation — this phase defines the orchestration layer, not new primitives.

## 2. Goals

- Reconstruct, accurately, what was active/unfinished/important as of the last session, scaled correctly whether the gap is 2 days or 2 years.
- Explicitly surface **unknowns and gaps** — things Sage cannot reconstruct with confidence — rather than silently guessing and presenting guesses as fact.
- Generate concrete next-best-actions, not just a summary — the reconstruction should leave the user knowing what to do next, not just what happened.
- Scale reconstruction depth to gap length: a 2-day gap needs a two-line status update; a 6-month gap needs prioritized sections. Same machinery, different granularity.

## 3. Responsibilities

**Owns:** the reconstruction orchestration flow, priority scoring for what to surface, dependency-graph-aware "what's still blocked" detection, missing-information flagging, next-best-action generation.

**Does not own:** any of the underlying retrieval, ranking, or reasoning mechanics — all delegated to Phases 02–05, per the reuse principle established in Phase 05 §11.

---

## 4. Architecture Diagram

```
  "Bring me back" ──► Context Engine (Phase 05)
   or cold-open           │ detects explicit_reconstruction intent,
   detection               │ computes gap_start/gap_end
                           ▼
              ┌─────────────────────────────┐
              │  Bring Me Back Orchestrator     │
              └───────────────┬─────────────────┘
                               │
       ┌───────────┬───────────┼───────────┬────────────┐
       ▼           ▼           ▼           ▼            ▼
  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌───────────┐
  │ Timeline  │ │ Priority   │ │ Dependency│ │ Missing-   │ │ Next-Best-  │
  │ Reconstr. │ │ Scoring    │ │ Graph     │ │ Info       │ │ Action      │
  │           │ │            │ │ Analysis  │ │ Detection  │ │ Generator   │
  └────┬────┘ └────┬─────┘ └────┬────┘ └────┬─────┘ └─────┬─────┘
       │           │           │           │              │
       └───────────┴─────┬─────┴───────────┴──────────────┘
                          ▼
              ┌─────────────────────────┐
              │  Reasoning Engine (Phase 04) │
              │  Chain Reasoning: synthesize   │
              │  into structured output          │
              └───────────────┬─────────────┘
                               ▼
                    Structured Reconstruction
                    (Phase 05 §9 output contract)
```

---

## 5. Timeline Reconstruction

Built directly on the Knowledge Graph timeline projection (Phase 03 §10), but with **granularity that adapts to gap length**:

```
gap_length_to_granularity(gap_days):
    gap_days <= 3      → raw episodic events, no consolidation needed
    gap_days <= 14      → daily consolidated summaries (Phase 02 §8.2)
    gap_days <= 90       → weekly consolidated summaries
    gap_days > 90         → monthly consolidated summaries, with the most
                             recent 2 weeks shown at daily granularity
                             regardless (recency always gets finer detail,
                             even in a long reconstruction)
```

This directly uses the consolidation hierarchy built in Phase 02 §8.2 — a 6-month gap pulling ~6 monthly summaries plus 2 weeks of daily detail is exactly the scenario that hierarchy was designed to make cheap and coherent.

---

## 6. Priority Scoring (Full Detail)

Phase 05 §8.1 introduced this formula; here is the full specification with worked inputs:

```
priority(item) =
      w1 * recency_of_last_activity_within_gap
    + w2 * item.importance_score               (Memory Engine / Graph entity)
    + w3 * unresolved_flag                       (open Task/Question status)
    + w4 * deadline_proximity                     (Temporal memory + Prediction Engine,
                                                     Phase 14 — items with deadlines
                                                     that fell inside/near the gap
                                                     score highest)
    + w5 * dependency_centrality                   (§7 — items many other things
                                                       depend on score higher)
    - w6 * confidence_penalty                       (tentative/unreviewed Knowledge
                                                       Graph entities, per Phase 03 §6,
                                                       are surfaced lower and flagged,
                                                       never presented as equally
                                                       certain as reviewed facts)
```

Default weights favor **unresolved + deadline-proximate + high-dependency-centrality** items — this is deliberately tuned toward "what did I leave hanging" over "what did I do a lot of," since the former is what a returning user actually needs to know.

---

## 7. Dependency Graph Analysis — "What's Still Blocked"

Uses the Knowledge Graph's causal relation types (`blocks`, `blocked_by`, `enables` — Phase 03 §5) to answer not just "what's unfinished" but "what's unfinished *and why*":

```
For each open Task/Goal entity as of gap_end:
    traverse blocked_by edges
    if blocking entity also unresolved:
        → surface as "still blocked on X"
    if blocking entity was resolved during the gap (per timeline):
        → surface as "no longer blocked — X was resolved on [date],
           this may be ready to proceed"
    if no blocked_by edges but no activity during gap:
        → surface as "stalled, no identified blocker" (a distinct,
           useful signal — the Prediction Engine, Phase 14, treats this
           pattern as a "likely forgotten" candidate)
```

`dependency_centrality` in §6 is computed from graph in-degree on `enables`/`blocks` edges — an entity that many other tasks depend on ranks higher in the reconstruction even if it isn't itself marked high-importance, because unblocking it has outsized downstream effect.

---

## 8. Missing-Information Detection

A reconstruction is only trustworthy if it's honest about its gaps. This is a deliberate, first-class output category, not an omission:

```
missing_information_flags:
  - Entities with status "tentative" (Phase 03 §6) still unresolved
    as of gap_end → "Sage isn't fully sure this refers to X or Y"
  - Task/Goal entities with no recorded outcome and no recent graph
    activity → "unclear if this was completed, abandoned, or just
    not logged"
  - Any period within the gap with zero ingested events (a true gap
    in Sage's own knowledge, distinct from "nothing happened") →
    explicitly noted as "no record of this period" rather than
    silently treated as inactive
```

This directly implements the Phase 01 principle that explainability is non-negotiable, applied to its inverse: knowing what Sage *doesn't* know is as important as what it does.

---

## 9. Next-Best-Action Generation

The final synthesis stage doesn't stop at "here's what happened" — it proposes what to do about the highest-priority unresolved items, using Reasoning Engine's Chain mode grounded in the same evidence already gathered:

```
For top-N unresolved items by priority score:
    generate a concrete, single-step suggested action
    (not a plan — that's Execution Engine's job if the user opts in)

    e.g.:
      item: "ACT essay on risk tolerance — status: draft, unresolved"
      suggested_action: "Review and finalize the risk-tolerance essay
        draft — it's the only ACT deliverable still marked incomplete"

      item: "ReRoot Pune vs. Farrukhabad — status: open question,
        stalled 3 months, no blocker identified"
      suggested_action: "This decision has been open for months with
        no new evidence gathered — worth revisiting with the Personal
        Strategy Engine (Phase 06 of the original module list /
        Phase 15+ in this handbook) or explicitly deprioritizing"
```

Each suggested action carries its own evidence trace (Phase 04 §6.1 schema) and is handed to the Execution Engine (Phase 11) only if the user chooses to act on it — generation and execution stay decoupled, consistent with the human-approval-loop principle from Phase 01's subsystem inventory.

---

## 10. API Design

```
POST /bring_me_back
{
  "gap_start": "auto",     // or explicit ISO date
  "depth": "auto",          // auto | brief | full — auto scales by gap length
  "include_next_actions": true
}

→ 200 OK
{
  "gap_days": 178,
  "granularity_used": "monthly+recent_daily",
  "reconstruction": {
    "whats_new": [...],
    "active_projects": [
      { "entity": "ReRoot", "status_summary": "...", "priority_score": 0.91 }
    ],
    "still_blocked": [
      { "item": "...", "blocked_by": "...", "since": "..." }
    ],
    "stalled_no_blocker": [...],
    "deadlines": [...],
    "missing_information": [
      { "flag": "no_record", "period": "2026-03-01 to 2026-03-09" }
    ],
    "suggested_next_actions": [
      { "item": "...", "action": "...", "evidence_trace_id": "..." }
    ]
  },
  "reasoning_trace_id": "..."
}
```

---

## 11. Sequence Diagram

```
User    Context Engine   BMB Orchestrator   Memory+Graph    Prediction Eng.   Reasoning Eng.
 │            │                  │                │                │                │
 │──"bring    │                  │                │                │                │
 │  me back"─►│                  │                │                │                │
 │            │──gap detected,───►│                │                │                │
 │            │  mode=bring_me_back│                │                │                │
 │            │                  │──timeline+priority─►│                │                │
 │            │                  │◄──ranked items, dependency graph──│                │
 │            │                  │──deadlines, forgotten-work flags──────────────────►│
 │            │                  │◄──predictions───────────────────────│                │
 │            │                  │──synthesize (chain reasoning,───────────────────────►│
 │            │                  │  incl. missing-info + next actions) │                │
 │            │                  │◄──structured reconstruction + trace───────────────│
 │◄───────────│◄─────────────────│                                                     │
```

---

## 12. Technology Choices & Tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Adaptive granularity vs. fixed summary length | Adaptive (§5) | Always return, say, "last 10 events" | A fixed-size reconstruction is either too sparse for a 6-month gap or wastefully verbose for a 2-day gap; adaptive granularity is what makes the same engine work at both extremes |
| Explicit missing-information section vs. silent best-effort summary | Explicit (§8) | Just summarize what's known, say nothing about gaps | Directly serves the explainability/trust principle — a user burned once by a confidently-wrong reconstruction will stop trusting the feature entirely; an honest "I don't have a record of this" is more valuable long-term |
| Reusing Phase 02–05 machinery vs. dedicated reconstruction data model | Reuse | Dedicated "snapshot" data model built specifically for this feature | Avoids maintaining two parallel representations of "what's important" (one for live context, one for reconstruction) that would inevitably drift out of sync |

---

## 13. Scaling Strategy

The dominant cost driver is Reasoning Engine synthesis over a large evidence set for long gaps. Mitigated by the granularity adaptation (§5) — the synthesis step never actually processes raw per-day data for a multi-month gap, only the already-consolidated summaries, keeping token cost roughly constant regardless of absolute gap length beyond the ~90-day threshold.

## 14. Security

Reconstruction output is one of the highest-value targets for accidental oversharing, since it deliberately surfaces the most life-level, cross-project view of the user's data in one place. Access to `/bring_me_back` should require the same auth tier as direct Belief/Reflection memory access (Phase 02 §13) — this endpoint is architecturally a superset of the most sensitive data in the system.

## 15. Testing Strategy

- **Granularity boundary tests:** fixtures at 2 days, 13 days, 89 days, 91 days gap length, assert correct granularity tier selected.
- **Dependency-blocked detection:** fixture graph with known blocked/unblocked/stalled tasks, assert §7 logic classifies each correctly.
- **Missing-information honesty test:** fixture with a deliberate data gap (no ingested events for a period), assert it's flagged rather than silently skipped.
- **End-to-end fidelity:** the single most important test suite in this phase — a full synthetic multi-month history with known "correct" reconstruction, scored for precision (nothing irrelevant surfaced) and recall (nothing important missed).

## 16. Failure Recovery

Because this phase is pure orchestration with no owned data store, failure recovery is entirely about graceful degradation of its dependencies — every dependency failure mode already defined in Phase 01 §2.4 and Phase 05 §15 applies directly; the Orchestrator's job is to keep assembling the best reconstruction possible from whichever subsystems are actually available, with clear flags on what's missing.

## 17. Future Improvements

- User-adjustable reconstruction depth/style (some users want prose narrative, some want a terse bulleted status board — currently one default format).
- Comparative reconstruction ("what's different about how I'm approaching things now vs. a year ago") — a natural extension once enough historical Personal Model snapshots (Phase 15) exist.
- Voice/audio reconstruction delivery for genuinely long absences, where reading a dense structured output may itself be a re-entry friction point.

---

*Next: Phase 07 — Research Engine (web/document research, ingestion, OCR, citation graph, source verification).*
