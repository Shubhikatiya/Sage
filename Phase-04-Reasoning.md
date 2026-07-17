# Sage — Engineering Handbook
## Phase 04: Reasoning Engine

> Continues from Phase 01 (Foundation), Phase 02 (Memory Engine), Phase 03 (Knowledge Graph). Assumes the retrieval APIs and provenance conventions established there.

---

## 1. Overview

The Reasoning Engine is where Sage stops being a retrieval system and starts being a *thinking* system. Memory and the Knowledge Graph answer "what do I know." The Reasoning Engine answers "given what I know, what follows, what's uncertain, and what should happen next."

This is the subsystem most tempting to over-engineer, because "reasoning" sounds like it should be one clever prompt. It isn't. The design goal here is to make reasoning **decomposable and inspectable** — every conclusion traceable to the evidence and steps that produced it — because an opaque reasoning engine is worse than no reasoning engine for a system whose entire value proposition is trustworthy context reconstruction.

## 2. Goals

- Support multiple distinct reasoning *modes* (multi-step chains, tree search over alternatives, reflection/self-critique) rather than forcing every task through one generic "think step by step" prompt.
- Ground every reasoning step in retrieved evidence (Memory + Knowledge Graph), not model-internal knowledge alone — reasoning that isn't grounded in the user's actual data is just generic LLM output wearing a Sage costume.
- Produce calibrated confidence, not just an answer — every output distinguishes "well-supported by evidence" from "plausible inference" from "guess."
- Make reasoning traces persistent and replayable — a past recommendation should be reconstructable months later ("why did Sage suggest I delay the pivot").

## 3. Responsibilities

**Owns:** reasoning strategy selection, step decomposition, evidence gathering orchestration (calling Memory/Knowledge Graph, not Research — that's a separate engine it *can* invoke), hypothesis generation, self-critique, confidence scoring.

**Does not own:** deciding to act on a conclusion (Execution Engine), fetching new external information (Research Engine, though Reasoning can request it), or storing its own outputs long-term (writes back through the Memory Engine like everything else).

---

## 4. Reasoning Modes

| Mode | When used | Mechanism |
|---|---|---|
| **Chain reasoning** | Straightforward multi-step questions with a clear evidence path ("what's the status of ReRoot's pilot workshop") | Sequential step decomposition, each step grounded in a retrieval call, final synthesis |
| **Tree search** | Decisions with multiple viable paths and no obvious single answer ("should ReRoot launch in Pune or Farrukhabad first") | Generate N candidate branches, evaluate each against weighted criteria, prune, recurse on promising branches |
| **Graph search** | Questions that require traversing relationships, not just facts ("what would delaying Kaal affect downstream") | Operates directly on Knowledge Graph traversal (Phase 03 §8) combined with dependency-aware propagation |
| **Reflection / self-critique** | After any chain or tree reasoning pass, before returning a final answer for high-stakes queries | A second LLM pass explicitly tasked with attacking the first pass's conclusion — see §7 |
| **Simulation** | "What happens if" queries with compounding effects over time ("what happens to my fellowship timeline if I take the SafetyWhat promotion") | Forward-projects known deadlines/dependencies from the Knowledge Graph + Temporal memory, producing a projected timeline with stated assumptions |

The Orchestrator (Phase 01 §2.2) selects a mode based on query classification; a task can also explicitly request a mode via API.

---

## 5. Architecture Diagram

```
                     ┌────────────────────────┐
   Request  ────────►│   Query Classifier        │
                     │  (which reasoning mode?)   │
                     └────────────┬───────────────┘
                                  │
        ┌─────────────┬──────────┼──────────┬─────────────┐
        ▼             ▼          ▼          ▼             ▼
   ┌─────────┐  ┌──────────┐ ┌────────┐ ┌──────────┐ ┌────────────┐
   │  Chain    │  │  Tree     │ │ Graph   │ │Reflection │ │ Simulation   │
   │ Reasoner  │  │  Search   │ │ Search  │ │ /Critique │ │  Engine       │
   └─────┬────┘  └────┬─────┘ └───┬────┘ └────┬─────┘ └─────┬──────┘
         │             │           │           │              │
         └─────────────┴─────┬─────┴───────────┴──────────────┘
                              │
                   ┌──────────▼───────────┐
                   │  Evidence Gatherer      │──► Memory Engine (Phase 02)
                   │  (calls retrieval APIs, │──► Knowledge Graph (Phase 03)
                   │   dedupes, attaches      │──► Research Engine (Phase 07,
                   │   provenance)             │     only if explicitly needed)
                   └──────────┬───────────┘
                              │
                   ┌──────────▼───────────┐
                   │  Confidence Scorer      │
                   │  (evidence coverage ×    │
                   │   agreement × recency)   │
                   └──────────┬───────────┘
                              │
                   ┌──────────▼───────────┐
                   │  Reasoning Trace Store  │──► Postgres (append-only,
                   │  (persisted, replayable)│     linked to source events)
                   └────────────────────────┘
```

---

## 6. Chain Reasoning — Detailed Flow

```
1. Decompose query into an ordered list of sub-questions.
   e.g. "What's blocking the ACT application?" →
     [a] What are the required ACT deliverables?
     [b] Which are complete, per project/task entities?
     [c] Which are incomplete, and why (blocked_by edges)?

2. For each sub-question, call Evidence Gatherer:
     - Memory retrieval (semantic + episodic + temporal)
     - Graph traversal (task entities, blocks/blocked_by edges)

3. Synthesize sub-answers into a draft answer, with each claim
   tagged to its supporting evidence IDs.

4. If query is flagged high-stakes (career/financial/strategic —
   see Phase 06, Personal Strategy Engine boundary), route through
   Reflection/Self-Critique (§7) before returning.

5. Persist full trace: sub-questions, evidence used, draft, final.
```

### 6.1 Reasoning Trace Schema

```
ReasoningTrace {
  id: UUID
  query: text
  mode: enum (chain|tree|graph|simulation)
  steps: [
    { step_number: int, sub_question: text,
      evidence_ids: UUID[], evidence_sources: [memory|graph|research],
      intermediate_conclusion: text, confidence: float }
  ]
  final_answer: text
  overall_confidence: float
  critique_applied: bool
  critique_notes: text | null
  created_at: timestamp
  source_event_id: UUID
}
```

This trace is what makes a Reasoning Engine answer fundamentally different from a raw LLM answer: every claim can be clicked through, in principle, to the memory or graph node that supports it.

---

## 7. Reflection & Self-Critique

A dedicated second pass, run by a distinct agent persona (Reflection Agent, Phase 08), whose only job is to attack the first pass:

```
Critique prompt structure (conceptual, not verbatim):
  - Given: draft answer + evidence used
  - Task: identify (a) claims not actually supported by the cited evidence,
    (b) missing evidence that should have been retrieved but wasn't,
    (c) unstated assumptions, (d) alternative conclusions the evidence
    could also support.
  - Output: a structured critique, not a rewritten answer.

If critique finds material issues:
  → Chain Reasoner re-runs affected steps with the gap addressed.
If critique finds only minor issues:
  → Final answer is annotated with caveats, not silently "fixed."
```

This mirrors the design principle from Phase 01 that explainability is non-negotiable — the critique step exists specifically to catch the failure mode where an LLM produces a fluent, confident-sounding answer that outruns its actual evidence.

---

## 8. Tree Search — Decision Support Flow

Used for genuinely open decisions (this is the mechanism underneath the Personal Strategy Engine in Phase 06 — Reasoning Engine provides the search machinery, Strategy Engine provides the domain framing).

```
                    Root: "Pune or Farrukhabad first?"
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                     ▼
      Branch: Pune                          Branch: Farrukhabad
   ┌───────────────┐                     ┌───────────────┐
   │ Evidence:       │                     │ Evidence:       │
   │ - incubator      │                     │ - existing        │
   │   access (graph)  │                     │   field relation-  │
   │ - higher cost of   │                     │   ships (graph)    │
   │   living (memory)   │                     │ - lower operating   │
   │                     │                     │   cost (memory)      │
   └────────┬──────────┘                     └────────┬──────────┘
            │                                            │
      Score against weighted criteria           Score against weighted criteria
      (from Personal Strategy Engine's           (same criteria set, applied
       criteria set — see Phase 06)                consistently across branches)
            │                                            │
            └──────────────────┬─────────────────────────┘
                                ▼
                    Compare, surface trade-offs explicitly —
                    NOT a single "recommended" verdict.
                    Output includes both branches' evidence,
                    scores per criterion, and stated unknowns.
```

Critical design constraint carried from Phase 01's non-goals: tree search terminates in a **comparison**, not a decision. The system does not output "you should do X" for high-stakes strategic questions — it outputs the structured trade-off (see Phase 06 for the exact output contract).

---

## 9. Confidence Estimation

```
confidence(answer) = f(
    evidence_coverage,     # fraction of sub-questions with ≥1 supporting item
    evidence_agreement,    # do multiple independent sources agree, or is it one thin thread
    evidence_recency,      # is the supporting memory itself decayed/stale (Phase 02 §7)
    critique_outcome       # did self-critique find material gaps
)
```

Confidence is surfaced to the user in plain terms, not just a number — e.g., "well-supported by 3 independent memories from the last month" vs. "based on a single mention 8 months ago, may be outdated." This maps directly to the `confidence` field already present on Memory items (Phase 02) and Knowledge Graph entities (Phase 03) — Reasoning Engine confidence is a rollup of its inputs' confidence, not a separately invented number.

---

## 10. API Design

```
POST /reason/query
{
  "query": "What's blocking the ACT application?",
  "mode": "auto" | "chain" | "tree" | "graph" | "simulation",
  "high_stakes": false,          // forces reflection pass regardless of auto-detection
  "max_evidence_items": 20
}

→ 200 OK
{
  "trace_id": "...",
  "final_answer": "...",
  "overall_confidence": 0.78,
  "confidence_explanation": "...",
  "steps": [ ... ],               // full trace, Phase 04 §6.1 schema
  "critique_applied": true
}

GET /reason/trace/{trace_id}      // full replay of a past reasoning pass
```

---

## 11. Sequence Diagram — High-Stakes Query

```
User      Orchestrator   Reasoning Engine   Evidence Gatherer   Reflection Agent
 │             │                │                   │                  │
 │──query─────►│                │                   │                  │
 │             │──classify─────►│                   │                  │
 │             │  (high-stakes)  │                   │                  │
 │             │                │──sub-questions────►│                  │
 │             │                │                   │──retrieve────────►│ (Memory+Graph)
 │             │                │◄──evidence─────────│                  │
 │             │                │──draft answer──────────────────────────►
 │             │                │                                        │──critique
 │             │                │◄───────────────────critique result────│
 │             │                │ (if gaps: re-run affected steps)       │
 │             │                │──persist trace──► Postgres              │
 │             │◄──final answer + confidence + caveats──                 │
 │◄──response───│                                                         │
```

---

## 12. Technology Choices & Tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Custom decomposition logic vs. framework (LangGraph/CrewAI) | Custom, lightweight | LangGraph | Consistent with Shubhi's existing first-principles precedent (ChefBot); reasoning trace schema and evidence-grounding requirements are specific enough that a general framework adds abstraction cost without matching benefit at this stage — revisit only if orchestration complexity outgrows what's maintainable by hand |
| Always-on reflection vs. reflection only for high-stakes | Conditional (high-stakes or explicit flag) | Always-on | Reflection roughly doubles LLM cost/latency per query; most day-to-day retrieval-style questions ("what's the status of X") don't need adversarial self-critique — reserve it for career/financial/strategic-class queries per Phase 01's cost-ceiling constraint |
| Separate confidence scorer vs. LLM self-reported confidence | Separate, formula-based (§9) | Ask the LLM "how confident are you 1-10" | LLM self-reported confidence is notoriously poorly calibrated; grounding confidence in measurable evidence properties (coverage, agreement, recency) is more trustworthy and auditable |

---

## 13. Scaling Strategy

Reasoning cost scales with evidence volume, not raw memory count, because retrieval (Phase 02/03) already narrows to top-k before reasoning begins. The main scaling risk is tree search branching factor on complex decisions — mitigated by a hard cap on branches (default 4) and depth (default 2), with the option to request deeper search explicitly for genuinely high-stakes decisions where added LLM cost is justified.

## 14. Security

Reasoning traces containing Belief/Reflection-type evidence inherit that data's sensitivity tier (Phase 02 §13). Trace export/delete must cascade correctly — deleting a belief memory that a past trace depended on doesn't delete the trace (historical record), but does flag it as referencing since-removed evidence.

## 15. Testing Strategy

- **Grounding regression tests:** fixed query + fixed memory/graph fixture state → assert every claim in the final answer maps to an evidence ID actually returned by the Evidence Gatherer (catches ungrounded hallucination as a CI failure, not a vibe check).
- **Critique effectiveness:** inject a deliberately flawed draft answer (missing evidence, unstated assumption) into the critique step in isolation, assert it's caught.
- **Confidence calibration spot-checks:** periodic manual review comparing stated confidence to actual outcome accuracy (this is a longer-horizon, Learning Engine-linked test — see Phase 10).

## 16. Failure Recovery

If Evidence Gatherer calls to Memory/Graph fail mid-reasoning (Phase 01 §2.4 degradation modes), the Reasoning Engine returns a partial answer explicitly flagged `evidence_incomplete: true` rather than either failing the whole request or silently reasoning from LLM-internal knowledge as if it were grounded.

## 17. Future Improvements

- Learned branch-pruning for tree search (currently heuristic/LLM-scored; could be replaced by a lightweight learned scorer trained on which past branches led to good outcomes, per Learning Engine feedback).
- Multi-agent debate mode (two independently-prompted reasoners argue opposite conclusions, a judge synthesizes) as a stronger alternative to single-pass reflection for the highest-stakes decisions only.
- Caching of reasoning traces for near-identical repeated queries, with staleness-aware invalidation tied to Memory Engine writes on the relevant entities.

---

*Next: Phase 05 — Context Engine (current/life/project/conversation context resolution, intent detection, attention prioritization).*
