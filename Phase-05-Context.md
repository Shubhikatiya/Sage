# Sage — Engineering Handbook
## Phase 05: Context Engine

> Continues from Phases 01–04. Assumes Memory retrieval, Knowledge Graph traversal, and Reasoning trace conventions established there.

---

## 1. Overview

The Context Engine answers one question, continuously: **"given everything Sage knows, what is actually relevant right now?"** It is the subsystem that stands between "Sage has a lot of data" and "Sage said the right thing at the right moment without being asked to search for it."

Where the Memory Engine and Knowledge Graph are passive stores that answer queries, the Context Engine is active — it runs on every turn, resolving a compact, ranked "current context" object that everything else (Conversation Engine, Reasoning Engine, Execution Engine) consumes without having to independently decide what matters.

This is also the subsystem most directly responsible for the north-star experience: "Bring me back" is, mechanically, a Context Engine call with a very wide time aperture and no active conversation to anchor against.

## 2. Goals

- Resolve relevant context in well under a second for normal conversation turns — this sits in the synchronous hot path, unlike most of Memory/Graph's async writes.
- Distinguish multiple *layers* of context (current message, active project, life-stage, environment) and merge them with sane priority, rather than treating "context" as one undifferentiated blob.
- Detect intent well enough to know which layers matter for a given turn — a message about dinner plans shouldn't pull in ACT Fellowship context just because it was recently active.
- Support the wide-aperture "bring me back" mode as a first-class case, not a hack bolted onto normal turn-context resolution.

## 3. Responsibilities

**Owns:** context layer definitions, intent detection, context merging/prioritization, the "current active project/focus" state machine, attention-budget allocation (how much context fits before diminishing returns/token cost dominate).

**Does not own:** retrieval mechanics (delegates to Memory Engine and Knowledge Graph), deciding what to say with the resolved context (Conversation/Reasoning Engines), or long-horizon prediction (Prediction Engine, Phase 14, though it consumes Context Engine's project-state output).

---

## 4. Context Layers

| Layer | Question it answers | Refresh cadence | Primary source |
|---|---|---|---|
| **Conversation context** | What's been said in this session so far | Every turn | Working memory (Phase 02 §4.2) |
| **Current context** | What is the user doing/asking about right now | Every turn | Intent detection (§5) on the current message |
| **Project context** | What project is active, and what's its current state | Sticky across a session, re-evaluated on topic shift | Knowledge Graph project entity + its recent episodic memory |
| **Life context** | What's the broader life-stage situation (e.g., "final semester + job + NGO founder, high concurrency") | Slow-changing, updated by Learning Engine | Personal Model (Phase 15) |
| **Historical context** | What's the relevant backstory for the current topic, arbitrarily far back | Pulled on demand, expensive | Long-term consolidated memory (Phase 02 §8) + graph timeline (Phase 03 §10) |
| **Environmental context** | Time of day, day of week, upcoming deadlines | Every turn, cheap | Temporal memory (Phase 02) + system clock |
| **Attention context** | What has the user been focused on across recent sessions (not just this one) | Rolling window (last 7/30 days) | Access-pattern data (which memories/entities were retrieved/discussed most) |

---

## 5. Intent Detection

Intent detection decides *which layers to activate* — this is the mechanism that keeps a casual message from dragging in irrelevant heavyweight context.

```
Intent Classifier (lightweight, fast model — not the main reasoning LLM)
   Input: current message + last 2 turns
   Output: {
     intent_type: enum (
       casual | factual_recall | task_execution | strategic_decision |
       document_request | reflection_request | bring_me_back
     ),
     topic_entities: [entity_id, ...],     // resolved via quick Knowledge Graph lookup
     activates_layers: [layer names]
   }
```

| Intent type | Layers typically activated |
|---|---|
| Casual | Conversation only |
| Factual recall ("when did I submit the ACT essay") | Conversation + targeted Memory retrieval, no full project context needed |
| Task execution ("draft the follow-up email") | Conversation + Project context + relevant Document memory |
| Strategic decision ("should I take the SafetyWhat promotion") | Conversation + Project + Life + Historical (routes to Reasoning Engine's tree search, Phase 04 §8) |
| Reflection request ("how have I been doing lately") | Life + Attention + Reflection memory |
| Bring me back | All layers, wide time aperture — see §8 |

This classification step deliberately runs on a small/cheap model — it gates expensive retrieval, so it needs to be fast, not maximally accurate; false positives (activating an unneeded layer) cost latency, false negatives (missing a needed layer) cost relevance, and the system tunes toward slightly over-activating for anything ambiguous.

---

## 6. Architecture Diagram

```
                    ┌────────────────────────┐
   Current Msg ────►│   Intent Classifier        │
                    │  (fast model, §5)           │
                    └────────────┬───────────────┘
                                 │ activates_layers[]
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
     ┌─────────────┐  ┌──────────────────┐  ┌────────────────┐
     │ Conversation   │  │  Project Context   │  │  Life/Attention  │
     │ Context         │  │  Resolver           │  │  Context Resolver│
     │ (working mem)   │  │  (Graph + episodic)  │  │  (Personal Model)│
     └──────┬──────┘  └────────┬─────────┘  └───────┬────────┘
            │                    │                     │
            └────────────────────┼─────────────────────┘
                                 ▼
                    ┌────────────────────────┐
                    │   Context Merger            │
                    │  - dedupe overlapping items  │
                    │  - apply per-layer weight     │
                    │  - trim to attention budget    │
                    │    (token limit aware)          │
                    └────────────┬───────────────┘
                                 ▼
                    ┌────────────────────────┐
                    │  Resolved Context Object    │──► Conversation Engine
                    │  (ranked, budgeted, tagged   │──► Reasoning Engine
                    │   by layer + source)          │──► Execution Engine
                    └────────────────────────┘
```

---

## 7. Attention Budget Allocation

Every context resolution call has a token budget (configurable per consumer — a chat turn has a smaller budget than a Reasoning Engine deep-dive). The Context Merger allocates that budget across active layers rather than greedily filling it from one layer:

```
budget_allocation(active_layers, total_budget):
  base_split = total_budget / len(active_layers)
  # then adjust: Conversation context always gets a guaranteed minimum
  # (recent turns are cheap and high-value); remaining budget distributed
  # by layer priority weight for the detected intent type.
  # e.g., for "strategic_decision" intent:
  #   Conversation: 15%, Project: 30%, Life: 20%, Historical: 35%
  # vs. "factual_recall" intent:
  #   Conversation: 40%, targeted Memory: 60%, other layers: 0%
```

This budget-aware merging is what prevents the classic RAG failure mode of stuffing the context window with everything retrieved regardless of whether it's the highest-value information for the current turn.

---

## 8. "Bring Me Back" as Wide-Aperture Context Resolution

This deserves explicit treatment since it's the system's defining use case (full engine detailed in Phase 06, but the context-resolution mechanics live here):

```
GET /context/resolve?mode=bring_me_back&gap_start=2026-01-15&gap_end=2026-07-12

1. Determine the gap window (last known session end → now).
2. Pull consolidated long-term memory summaries covering the gap
   (Phase 02 §8 — monthly/weekly summaries, not raw episodic replay).
3. Pull Knowledge Graph timeline for all active-status projects across
   the gap (Phase 03 §10).
4. Diff project/task status: what was "in progress" at gap_start that
   has no corresponding "completed" event → surfaced as unfinished work.
5. Pull Temporal memory for anything with a due_date inside or just past
   the gap → surfaced as missed/upcoming deadlines.
6. Rank everything by importance_score × recency-within-gap, not global
   recency (a thing from week 1 of a 6-month gap that's still unresolved
   outranks a thing from week 5 that got closed out).
7. Return a structured reconstruction object — NOT a single essay-style
   summary — so the consuming layer (Conversation Engine) can present it
   progressively rather than one giant wall of text.
```

### 8.1 Bring-Me-Back Output Contract

```
{
  "gap_duration_days": 178,
  "unfinished_work": [
    { "entity": "ReRoot Learning Memo", "status": "draft, incomplete",
      "last_touched": "2026-02-03", "importance": 0.81 }
  ],
  "missed_or_upcoming_deadlines": [
    { "entity": "ACT Fellowship application", "due_date": "2026-08-01",
      "status": "in_progress" }
  ],
  "notable_developments": [
    { "summary": "Kaal pitch deck completed, judging panel scored 83/100",
      "period": "2026-04" }
  ],
  "suggested_next_actions": [ ... ]   // populated by Reasoning Engine,
                                       // Context Engine only supplies the
                                       // ranked facts, not the recommendation
}
```

Note the explicit boundary: Context Engine assembles *what happened*; it hands off to the Reasoning Engine (Phase 04) for *what to do about it*. This keeps the layer that's supposed to be a fast, mechanical resolver from also being a slow, judgment-laden reasoner.

---

## 9. Sequence Diagram — Normal Turn vs. Bring Me Back

```
NORMAL TURN                              BRING ME BACK
User: "draft the follow-up email"        User: "bring me back"
     │                                        │
     ▼                                        ▼
Intent Classifier                        Intent Classifier
  → task_execution                          → bring_me_back
  → activates: Conversation,                → activates: ALL layers,
    Project, targeted Document                wide time aperture
     │                                        │
     ▼                                        ▼
Fast resolution (<500ms target)          Slower resolution (seconds,
  small, targeted retrieval                acceptable — this is an
                                            explicit, infrequent request,
                                            not a hot-path chat turn)
     │                                        │
     ▼                                        ▼
Resolved Context → Conversation Engine   Resolved Context → Reasoning Engine
  drafts the email directly                (adds suggested_next_actions)
                                            → Conversation Engine presents
                                              progressively
```

---

## 10. API Design

```
POST /context/resolve
{
  "message": "current user message, if any",
  "session_id": "...",
  "mode": "turn" | "bring_me_back" | "explicit_deep_dive",
  "token_budget": 4000
}

→ 200 OK
{
  "activated_layers": ["conversation", "project"],
  "context_items": [
    { "layer": "project", "source": "graph", "content": "...", "weight": 0.4 },
    ...
  ],
  "degraded": false,
  "graph_unavailable": false     // per Phase 01 §2.4 failure isolation flags
}
```

---

## 11. Technology Choices & Tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Fast/cheap intent classifier separate from main reasoning LLM | Separate small model (local, e.g. via Ollama) | Use the main LLM for classification too | Intent detection runs on every single turn — using the expensive frontier model here would dominate cost/latency for a task that doesn't need frontier-level reasoning |
| Budget-aware layer merging | Weighted allocation by intent type (§7) | Simple top-k across all retrieved items regardless of source layer | Prevents one verbose layer (e.g., Historical) from crowding out cheap high-value Conversation context; matches the attention-protection design principle from Phase 01 |
| Structured bring-me-back output vs. single narrative summary | Structured object, rendered progressively | One LLM-generated paragraph | A single narrative is harder to verify against evidence and harder for the UI to make interactive (e.g., click into "unfinished work" item for detail) |

---

## 12. Scaling Strategy

Turn-level context resolution must stay fast regardless of total memory volume — this is guaranteed structurally because it never does a full scan; it always goes through Memory Engine's ranked retrieval (Phase 02 §9) and Knowledge Graph's capped traversal (Phase 03 §13), both of which are designed to return bounded result sets regardless of total store size. Bring-me-back mode is explicitly allowed to be slower since it's a rare, deliberate action, not a per-turn cost.

## 13. Security

Context resolution respects the same sensitivity tiers as its source data — Belief/Reflection memory only enters a resolved context object for consumers explicitly permitted to see it (Reasoning Engine, yes; a hypothetical future shared/collaborative view, no). This boundary is enforced at the Context Merger, not left to downstream consumers to self-police.

## 14. Testing Strategy

- **Intent classification accuracy:** labeled fixture set of messages → expected intent type + activated layers, run as a regression suite on classifier changes.
- **Budget allocation correctness:** given a fixed set of candidate context items and a token budget, assert output respects the budget and the layer-weighting rules.
- **Bring-me-back reconstruction accuracy:** synthetic multi-month fixture (known unfinished tasks, known deadlines) → assert the output contract correctly surfaces all of them, with no silent omissions (this is the single most important test in this phase, given the north-star use case).

## 15. Failure Recovery

If Project Context Resolver (Knowledge Graph-dependent) fails, Context Engine degrades to Conversation + targeted Memory only, flags `graph_unavailable: true` (per Phase 01 §2.4), and lets downstream consumers decide whether to proceed with partial context or ask a clarifying question — it never silently pretends full context was available.

## 16. Future Improvements

- Learned intent classification (replace/augment the prompted small model with a fine-tuned classifier once enough labeled interaction data exists via the Learning Engine).
- Predictive pre-resolution: begin resolving likely-next-context speculatively during idle time between turns, to shave latency on high-probability follow-ups.
- Personalized layer-weighting (the intent-type → layer-weight table in §7 becomes user-specific over time rather than a fixed default, once the Personal Model, Phase 15, is mature enough to inform it).

---

*Next: Phase 06 — Bring Me Back Engine (full reconstruction architecture, priority scoring, dependency graph, next-best-action generation — building on the context resolution mechanics defined here).*
