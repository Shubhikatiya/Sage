# Sage — Engineering Handbook
## Phase 08: Multi-Agent System

> Continues from Phase 01 (Foundation) through Phase 07 (Research Engine).

---

## 1. Overview

Every phase so far has referenced "agents" as callers/consumers of the engines (Extraction Agent, Reflection Agent, Guardian Agent, and so on). This phase formalizes the multi-agent layer itself: what an "agent" means architecturally in Sage, how agents are distinguished from the engines they use, how they're dispatched, and the full per-agent specification the original brief asked for.

The core distinction worth stating clearly: **engines (Phases 02–07) are stateless capability providers; agents are stateful task performers with a specific persona, prompt, and tool access that call engines to get work done.** An engine doesn't have a "point of view" — Memory Engine just stores and retrieves. An agent does have a point of view — the Reflection Agent's entire job is to be adversarial toward a draft answer; that's a role, not a capability.

## 2. Goals

- Give every agent a narrow, well-defined mandate — no agent should be a general-purpose "do anything" fallback, since that's exactly what makes multi-agent systems unmaintainable and undebuggable.
- Make agent failure isolated and legible — one agent misbehaving (e.g., over-eager entity creation) should be traceable to that agent specifically, not diffused across the system.
- Keep orchestration (which agent runs when, with what inputs) separate from agent logic itself — the Planner decides the plan; individual agents don't need to know about each other.

## 3. Responsibilities

**Owns:** agent definitions (persona, inputs, outputs, prompt, tools, memory scope), the Planner's task-decomposition and dispatch logic, inter-agent handoff protocol, agent-level failure handling.

**Does not own:** the underlying engines each agent calls (Phases 02–07) — agents are consumers of those APIs, not reimplementations of their logic.

---

## 4. Architecture Diagram

```
                         ┌───────────────────────┐
    Orchestrator ───────►│      Planner Agent        │
    (Phase 01 §2.2)        │  (decomposes request into  │
                          │   ordered/parallel agent    │
                          │   tasks)                     │
                         └────────────┬──────────────┘
                                      │
        ┌──────────┬──────────┬───────┼───────┬──────────┬──────────┬───────────┐
        ▼          ▼          ▼       ▼       ▼          ▼          ▼           ▼
   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
   │Research │ │ Memory  │ │Knowledge│ │Reflection│ │Execution│ │Scheduler│ │Learning │ │Guardian │
   │ Agent   │ │ Agent   │ │ Agent   │ │ Agent    │ │ Agent   │ │ Agent   │ │ Agent   │ │ Agent   │
   └────┬───┘ └────┬───┘ └────┬───┘ └────┬────┘ └────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘
        │          │          │          │           │          │          │          │
        ▼          ▼          ▼          ▼           ▼          ▼          ▼          ▼
   Research    Memory     Knowledge   Reasoning    Execution  Execution  Learning   (reviews
   Engine      Engine     Graph       Engine       Engine     Engine     Engine     other
   (Ph.07)     (Ph.02)    (Ph.03)     (Ph.04)      (Ph.11)    (Ph.11)    (Ph.10)    agents'
                                                                                     low-confidence
                                                                                     outputs)
```

Each agent calls exactly the engine(s) its mandate requires — no agent has blanket access to every engine, which is itself a safety property (a compromised or malfunctioning Research Agent, for instance, cannot directly write to the Personal Model).

---

## 5. Per-Agent Specification

### 5.1 Planner Agent

| Field | Spec |
|---|---|
| Purpose | Decompose an incoming request into an ordered/parallel set of agent tasks; the only agent that sees the "whole picture" of a request |
| Inputs | User request (or triggering event), resolved context (Phase 05) |
| Outputs | Task graph: `[{agent: str, task: str, depends_on: [task_id]}]` |
| Prompt role | "You are a task decomposer. Given a request and available agents' mandates, produce the minimal task graph needed. Do not perform the task yourself." |
| Tools | None directly — read-only access to the agent registry (mandates, not implementations) |
| Memory scope | None persisted — the task graph is ephemeral, logged for observability but not written as a memory item |
| Failure cases | Over-decomposition (spawning unnecessary agent calls, inflating cost/latency) → mitigated by a max-task-count cap and a "could this be a single Chain Reasoning call instead" check before dispatch |

### 5.2 Research Agent

| Field | Spec |
|---|---|
| Purpose | Execute information-gathering tasks handed off by the Planner or Reasoning Engine |
| Inputs | A specific information need (not a vague topic — see Phase 07 §5.1) |
| Outputs | Sourced claims with confidence scores, written to Memory/Knowledge Graph via Research Engine |
| Prompt role | "You are a careful researcher. Prefer primary sources. Never assert a claim from a single low-reputation source without flagging it." |
| Tools | Research Engine API (Phase 07) only |
| Memory scope | Writes document/semantic memory; reads nothing beyond the current task's notebook |
| Failure cases | Query drift (searching for something adjacent but not what was asked) → mitigated by requiring the Research Agent to restate the information need before searching, checked against the original task |

### 5.3 Memory Agent

| Field | Spec |
|---|---|
| Purpose | Classify raw input (conversation turns, ingested documents) into the correct memory type and write it correctly (Phase 02 §4) |
| Inputs | Raw event (conversation turn, document chunk) |
| Outputs | Typed memory writes with correct envelope fields |
| Prompt role | "You are a classifier and structurer. Given raw content, determine which of the twelve memory types it belongs to and extract it into that schema. When uncertain, prefer the more conservative type (episodic over semantic) and lower confidence." |
| Tools | Memory Engine write APIs only |
| Memory scope | Full write access to Memory Engine; no read access beyond what's needed to check for near-duplicate writes |
| Failure cases | Misclassification (e.g., writing an opinion as semantic fact rather than belief) → mitigated by the Guardian Agent's periodic review of low-confidence classifications, and by conservative-default behavior |

### 5.4 Knowledge Agent

| Field | Spec |
|---|---|
| Purpose | Extract entities and relationships from memory writes into the Knowledge Graph (Phase 03 §6-7) |
| Inputs | `memory.written` events |
| Outputs | Entity/relationship writes, including entity-resolution candidate generation |
| Prompt role | "You are an entity and relationship extractor operating under a closed vocabulary of relation types (Phase 03 §5). Never invent new relation types. When an entity might already exist, propose a match rather than assuming a new entity." |
| Tools | Knowledge Graph write APIs, entity resolution candidate search |
| Memory scope | Writes to Knowledge Graph only; reads Memory Engine for the triggering event's content |
| Failure cases | Over-eager entity creation (fragmenting one real entity into several near-duplicates) → this is precisely why entity resolution has a Guardian review gate (Phase 03 §6) rather than trusting the Knowledge Agent's merge decisions unconditionally at low confidence |

### 5.5 Reflection Agent

| Field | Spec |
|---|---|
| Purpose | Adversarially critique reasoning outputs (Phase 04 §7); also runs end-of-session/nightly meta-observation passes producing Reflection-type memory |
| Inputs | A draft reasoning answer + its evidence trace, OR a session transcript (for nightly reflection) |
| Outputs | Structured critique (§7 schema from Phase 04), or a Reflection memory item |
| Prompt role | "You are a skeptical reviewer, not a collaborator. Your only job is to find what's wrong, missing, or unsupported. Do not soften findings to be agreeable." |
| Tools | Read-only access to Memory/Knowledge Graph (to verify cited evidence actually says what it's claimed to say) |
| Memory scope | Writes Reflection-type memory only; never writes Belief memory directly (that requires the higher-confidence-bar path — see Phase 02 §4.2 note on Belief/Reflection sensitivity) |
| Failure cases | Over-critique (flagging trivial non-issues, adding noise) → mitigated by requiring critique findings to be classified `material` vs. `minor`, with only `material` findings triggering a re-run (Phase 04 §7) |

### 5.6 Execution Agent

| Field | Spec |
|---|---|
| Purpose | Carry out approved tasks/workflows (Phase 11) — the only agent that takes actions with external side effects |
| Inputs | An approved task with explicit parameters (never a vague goal — Execution Agent does not improvise scope) |
| Outputs | Action results, logged execution trace |
| Prompt role | "You execute exactly the approved task. If the task is ambiguous or the approval doesn't cover an edge case you encounter, stop and request clarification rather than assuming." |
| Tools | Execution Engine API, external integrations (calendar, email — scoped per Phase 11's permission model) |
| Memory scope | Writes Episodic memory (the action taken) and Temporal memory (if it affects deadlines) |
| Failure cases | Scope creep during execution (doing more than approved) → mitigated by the human-approval-loop design (Phase 01, Phase 11) requiring explicit scope, and by Execution Agent treating anything outside that scope as a hard stop, not a judgment call |

### 5.7 Scheduler Agent

| Field | Spec |
|---|---|
| Purpose | Manage time-based triggers — recurring jobs (nightly consolidation, weekly reflection), deadline-driven reminders, and scheduling of other agents' async work |
| Inputs | Time-based triggers, Temporal memory entries |
| Outputs | Dispatch events to other agents at the right time |
| Prompt role | N/A — largely deterministic/rule-based, not LLM-driven (scheduling logic doesn't need generative reasoning) |
| Tools | Event Bus (Phase 01 §2.3) |
| Memory scope | Reads Temporal memory; writes nothing directly |
| Failure cases | Missed triggers on system downtime → mitigated by persisting schedule state in Postgres (not in-memory only) so a restart recovers pending triggers rather than silently dropping them |

### 5.8 Learning Agent

| Field | Spec |
|---|---|
| Purpose | Consume feedback/outcome events and update importance weights, Personal Model attributes, and ranking parameters (Phase 10 detail) |
| Inputs | Correction events, outcome events (did a suggestion get acted on and succeed) |
| Outputs | Updated importance scores, Personal Model deltas (versioned, per Phase 15) |
| Prompt role | "You update models based on evidence of what worked, not on assumption. A single data point is not a pattern — require repetition or explicit correction before updating confidently-held model attributes." |
| Tools | Memory Engine (importance score updates), Personal Model write API |
| Memory scope | Full write access to importance/confidence fields across memory types; does not create new factual memory itself |
| Failure cases | Overfitting to a single recent interaction (treating one correction as if it invalidates a well-established pattern) → mitigated by requiring a minimum evidence threshold before high-confidence Personal Model attributes are revised, detailed in Phase 10 |

### 5.9 Guardian Agent

| Field | Spec |
|---|---|
| Purpose | The system's internal safety/consistency reviewer — reviews low-confidence entity merges (Phase 03 §6), flags Belief/Reflection writes that lack sufficient evidence, and is the backstop against any other agent's overreach |
| Inputs | Queued low-confidence writes from other agents (entity resolution candidates, tentative beliefs) |
| Outputs | Approve / reject / escalate-to-user decisions on queued items |
| Prompt role | "You are the last check before uncertain information becomes part of Sage's model of the user or the world. When genuinely uncertain, escalate to the user rather than guessing — a wrong silent merge is worse than a slower pipeline." |
| Tools | Read access across all engines; write access limited to approve/reject flags, not content creation |
| Memory scope | Does not create memory or graph content; only gates it |
| Failure cases | Becoming a bottleneck if too much is routed through review → mitigated by tuning the confidence thresholds that trigger review (Phase 03 §6, Phase 02 confidence floors) so only genuinely uncertain items reach the queue, not routine writes |

---

## 6. Inter-Agent Handoff Protocol

To keep agents decoupled (per the Phase 01 modularity principle), handoffs happen exclusively through the Planner's task graph and the Event Bus — never agent-to-agent direct calls:

```
TaskHandoff {
  task_id: UUID
  from_agent: str | "planner"
  to_agent: str
  task_description: text
  inputs: jsonb                    # structured, not free-text where avoidable
  depends_on: [task_id]
  status: "pending" | "in_progress" | "completed" | "failed" | "escalated"
  result_ref: UUID | null           # points to whatever the agent produced
                                     # (a memory item, a graph write, a trace)
}
```

Any agent can mark a task `escalated` rather than `completed` — this is the standard path for "I can't do this confidently" (e.g., Knowledge Agent escalates an ambiguous entity match to Guardian instead of guessing).

---

## 7. Sequence Diagram — A Request Spanning Multiple Agents

```
User    Planner    Research Agent   Knowledge Agent   Reflection Agent   Guardian
 │          │             │                │                  │              │
 │──request►│             │                │                  │              │
 │          │──task graph:│                │                  │              │
 │          │  [research, │                │                  │              │
 │          │   extract,  │                │                  │              │
 │          │   critique] │                │                  │              │
 │          │──dispatch──►│                │                  │              │
 │          │             │──findings──────►│                  │              │
 │          │             │                │──low-confidence──────────────────►│
 │          │             │                │  entity merge                     │
 │          │             │                │◄──approved/rejected───────────────│
 │          │             │                │──extraction done─►│              │
 │          │             │                │                  │──critique─────►
 │          │             │                │                  │  (if material,│
 │          │             │                │                  │   task re-run)│
 │◄──final synthesis (via Reasoning Engine, not shown)──────────────────────────│
```

---

## 8. Technology Choices & Tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Narrow, single-mandate agents vs. fewer general-purpose agents | Narrow (9 distinct agents) | 2-3 general agents that "do research and writing and reflection" | Narrow mandates make failure attribution possible — when something goes wrong, the agent responsible is identifiable, not diffused across a general-purpose agent doing five jobs at once |
| Task-graph + Event Bus handoff vs. direct agent-to-agent calls | Task-graph/Event Bus | Direct calls | Keeps agents independently testable in isolation (Phase 01 principle) — an agent's tests never need another agent running, only the task-graph contract |
| Custom Planner vs. framework-provided orchestration (LangGraph/CrewAI) | Custom | Framework | Consistent with the Phase 04 §12 decision and Shubhi's first-principles precedent; task graph schema here is simple enough (DAG with dependency edges) that a framework's abstraction overhead isn't justified yet |
| Guardian as a distinct agent vs. inline validation in each agent | Distinct agent | Inline checks per agent | Centralizing the "is this trustworthy enough to commit" judgment in one place makes the confidence-threshold policy auditable and tunable in one location, rather than scattered and potentially inconsistent across nine agents |

---

## 9. Scaling Strategy

Agent dispatch scales with request complexity, not data volume — the Planner's task-graph size is naturally bounded by the max-task-count cap (§5.1). The main scaling consideration is LLM call volume: each agent invocation is (at least) one LLM call, so the Orchestrator should prefer smaller/faster models for narrow, low-ambiguity agent tasks (Memory Agent classification, Scheduler triggers) and reserve frontier-model calls for agents doing genuine judgment work (Reflection, Reasoning-adjacent Research synthesis) — mirroring the cost-tiering already established for intent detection in Phase 05 §11.

## 10. Security

Per-agent tool scoping (§4, "each agent calls exactly the engines its mandate requires") is itself the primary security control at this layer — it limits blast radius the same way least-privilege access control does in any system. Execution Agent in particular is the only agent with external side-effect capability and is therefore the only agent whose actions require the human-approval gate (Phase 01, Phase 11) before running.

## 11. Testing Strategy

- **Per-agent unit tests:** each agent tested in isolation against fixed inputs and mocked engine responses — directly enabled by the narrow-mandate design.
- **Task graph validation:** Planner outputs tested against expected decompositions for a fixed set of representative requests; assert no agent is dispatched outside its declared tool scope.
- **Escalation path tests:** deliberately ambiguous inputs (entity resolution, borderline belief confidence) fed to the relevant agent, assert `escalated` status is produced rather than a guessed `completed`.
- **Guardian threshold tuning tests:** measure review-queue volume against a fixed test corpus when confidence thresholds change, to catch the bottleneck failure mode from §5.9 before it ships.

## 12. Failure Recovery

Task graph state persists in Postgres (not just in-memory), so an Orchestrator restart mid-request resumes from the last completed task rather than restarting the whole request — consistent with the recoverability principle applied at the orchestration layer specifically.

## 13. Future Improvements

- Dynamic agent selection confidence (Planner currently uses fixed agent mandates; could eventually learn which agent combinations produce the best outcomes for which request types, feeding into the Learning Agent).
- Parallel Guardian reviewers for different domains (entity merges vs. belief confidence vs. execution scope) if review volume grows enough to warrant specialization within the Guardian role.
- Formal agent capability negotiation (agents declaring version-tagged capabilities) if the agent roster grows beyond the current nine and inter-agent compatibility becomes a real concern.

---

*Next: Phase 09 — Learning Engine (learning from conversations, corrections, feedback, behavior, outcomes; reflection loops).*
