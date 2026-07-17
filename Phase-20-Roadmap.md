# Sage — Engineering Handbook
## Phase 20: Implementation Roadmap

> Final phase. Continues from Phase 01 (Foundation) through Phase 19 (Technology Decisions). This is the capstone — it sequences everything specified in Phases 01–19 into an actual build plan, from today's MVP to the full Raphael-level cognitive operating system described in the original vision brief.

---

## 1. Overview

Nineteen phases have specified *what* to build. This phase specifies *in what order*, and — just as importantly — *what "done" looks like at each stage*, so progress is measurable rather than open-ended. The roadmap is organized into seven build phases (A through G), each producing something independently useful, consistent with the incremental-value principle from Phase 01 §1.5.

The test for every phase boundary below is the same one stated in Phase 01: does this phase's output already beat not having it, on its own, before the next phase exists? Phase A (bare memory + retrieval) should already beat searching your own Notion. Phase D (reasoning + agents) should already be a genuinely useful thinking partner before Prediction or Strategy engines exist. Nothing in this roadmap requires the full system to be valuable at every stage.

## 2. Roadmap at a Glance

```
Phase A: MVP Memory Core
   │  (Phases 02 partial + minimal Conversation Engine)
   ▼
Phase B: Context Continuity
   │  (Phase 05 Context Engine + Phase 06 Bring Me Back)
   ▼
Phase C: Structured Knowledge
   │  (Phase 03 Knowledge Graph + Phase 12 Extraction Pipeline + Phase 07 Research)
   ▼
Phase D: Reasoning & Multi-Agent
   │  (Phase 04 Reasoning + Phase 08 Multi-Agent + Phase 09 Learning + Phase 10 Execution)
   ▼
Phase E: Proactive Intelligence
   │  (Phase 13 Prediction + Phase 15 World/Opportunity/Strategy)
   ▼
Phase F: Full Personal Model
   │  (Phase 14 Personal Model matured + Phase 16 Dashboard)
   ▼
Phase G: Raphael-Level Cognitive OS
      (maturity across every subsystem, Phase 17/18/19 hardened
       to production-grade for a system trusted with years of data)
```

---

## 3. Phase A — MVP Memory Core

**Goal:** Prove the core premise — persistent, retrievable memory beats not having it — with the smallest possible slice.

**Scope (from earlier phases):**
- Phase 02 (Memory Engine): Working, Episodic, Semantic, Document memory types only — defer Procedural, Belief, Reflection, Relationship, Temporal, Image to Phase C/D where they have real consumers.
- Phase 11 (Conversation Engine): basic turn assembly, no Turn Planner classification yet (every turn does simple context-grounded retrieval + generation) — defer the reasoning/research/execution routing to Phase D.
- Phase 01 infrastructure baseline: Postgres + Qdrant, local Ollama, Docker Compose, per Phase 18 §4.

**Explicit non-scope:** No Knowledge Graph, no agents beyond a minimal Memory-write classifier, no prediction, no execution.

**Deliverables:**
- Working conversation loop with persistent memory across sessions.
- `/memory/retrieve` (Phase 02 §9) functioning with basic ranking (similarity + recency only — defer full importance/decay tuning).
- Manual memory browsing (even just a CLI query tool — full Dashboard is Phase F).

**Success criteria:** A week-long gap in usage, followed by a return, produces noticeably better continuity than starting a fresh chat with no memory. This is the minimum bar — not full Bring Me Back yet, just "it remembers."

**Estimated complexity:** Low-moderate. This is the phase most similar to Shubhi's already-existing Sage implementation (RAG, ChromaDB/Qdrant-equivalent, FastAPI) — largely a matter of hardening what may already partially exist rather than building from zero.

**Risks:** Scope creep — the temptation to add Knowledge Graph or agents before memory retrieval quality is actually proven. Resist; Phase A's whole purpose is validating the foundation cheaply.

---

## 4. Phase B — Context Continuity

**Goal:** Deliver the actual north-star experience — "bring me back" — using only what Phase A built plus consolidation and layered context.

**Scope:**
- Phase 02 §8 (Memory consolidation/compression) — nightly/weekly/monthly hierarchy.
- Phase 05 (Context Engine) — layered context resolution, intent detection.
- Phase 06 (Bring Me Back Engine) — full reconstruction flow, adaptive granularity.

**Deliverables:**
- `POST /bring_me_back` fully functional (Phase 06 §10).
- Consolidation jobs running on schedule.
- Basic intent detection distinguishing conversation-continuation from cold-open.

**Success criteria:** A genuine multi-month gap (real usage, not synthetic test data) produces a reconstruction the user rates as accurate and non-redundant — this is where the precision/recall fidelity testing from Phase 06 §15 gets validated against real data, not just fixtures.

**Estimated complexity:** Moderate. Consolidation and adaptive granularity are the trickiest correctness problems here.

**Dependencies:** Phase A's memory types and retrieval must be stable first — consolidation quality is bounded by the quality of what it's consolidating.

---

## 5. Phase C — Structured Knowledge

**Goal:** Move from flat memory to a genuinely structured model of entities and relationships, and open ingestion beyond conversation.

**Scope:**
- Phase 03 (Knowledge Graph) — entity model, relationship taxonomy, entity resolution, hybrid retrieval.
- Phase 12 (Knowledge Extraction Pipeline) — adapter framework, starting with 2-3 source types (e.g., PDF/document upload + one connected integration like GitHub or Notion — not all ten+ at once).
- Phase 07 (Research Engine) — web research, citation graph.
- Additional Memory types activated: Procedural, Relationship, Temporal (now that Knowledge Graph gives them somewhere meaningful to connect to).

**Deliverables:**
- Working entity resolution pipeline with Guardian review queue (even if Guardian is still a simple rule-based gate at this stage, not yet a full agent — Phase D formalizes the agent).
- At least one connected integration adapter beyond manual upload, proving the adapter pattern (Phase 12 §4) generalizes.
- `/graph/hybrid_retrieve` (Phase 03 §9) measurably improving retrieval quality over Phase A's vector-only search.

**Success criteria:** Multi-hop queries ("what does X have to do with Y") return correct, evidence-traced answers that pure vector search in Phase A/B could not have produced.

**Estimated complexity:** High. Entity resolution correctness is the single hardest problem in the whole roadmap up to this point — budget real iteration time here, not a fixed sprint.

**Risks:** Bad entity resolution silently corrupting retrieval quality for everything downstream — this is exactly why Phase 03 §6's review-gate design exists; don't skip it to move faster.

---

## 6. Phase D — Reasoning & Multi-Agent

**Goal:** Move from retrieval to genuine reasoning, decomposed across specialized agents, with the ability to take approved actions.

**Scope:**
- Phase 04 (Reasoning Engine) — chain reasoning first, then tree search and reflection once chain reasoning is validated.
- Phase 08 (Multi-Agent System) — formalize the nine agents; Phase C's ad-hoc extraction logic becomes the real Knowledge Agent, Guardian becomes a full agent.
- Phase 09 (Learning Engine) — signal ingestion, threshold-gated updates.
- Phase 10 (Execution Engine) — task/approval model, starting with low-risk actions (creating tasks, drafting content) before higher-risk external integrations (sending emails, calendar writes).
- Phase 11 (Conversation Engine) matures: Turn Planner classification now has real Reasoning/Research/Execution paths to route to.

**Deliverables:**
- Full Reasoning Trace schema (Phase 04 §6.1) in production use.
- All nine agents operational with defined tool scopes.
- At least one full Execution Engine workflow end-to-end (proposal → approval → execution → outcome logged → Learning Engine signal).

**Success criteria:** A genuinely open, multi-step question ("what's blocking the ACT application, and what should I do next") gets a grounded, evidence-traced answer with an actionable, approved-then-executed next step — the full loop from Phase 04 through Phase 10 working together.

**Estimated complexity:** High. This is the largest single phase in the roadmap — consider splitting into D1 (Reasoning + read-only agents) and D2 (Execution + write-capable agents) as an internal sub-sequencing if needed.

**Dependencies:** Requires Phase C's Knowledge Graph to be reasonably mature — Reasoning Engine's evidence-grounding quality is bounded by graph quality, same as Phase B was bounded by memory quality.

---

## 7. Phase E — Proactive Intelligence

**Goal:** Move from reactive (answering when asked) to proactive (surfacing what matters before being asked) — the point at which Sage starts to feel like a genuine cognitive partner rather than a very good search tool.

**Scope:**
- Phase 13 (Prediction Engine) — forgotten work, deadline risk, bottleneck detection first; energy patterns deferred as opt-in, lower priority.
- Phase 15 (World Model, Opportunity Detection, Personal Strategy Engine) — starting with a narrow, explicitly-configured monitoring scope (Phase 15 §4.2), not broad coverage.

**Deliverables:**
- Daily prediction job running, with the precision-tuned surfacing gate (Phase 13 §9) validated against real feedback, not just fixtures.
- At least one working monitoring domain in the World Model (e.g., "social impact fellowships") with verified opportunity surfacing.
- Personal Strategy Engine handling at least one real, structured strategic question with the no-verdict output contract.

**Success criteria:** The user reports Sage surfaced something genuinely useful (a forgotten task, a real opportunity) without being asked, at a false-positive rate low enough that they don't want to turn the feature off — this is a subjective but critical bar, directly tied to Phase 13 §2's precision-first design goal.

**Estimated complexity:** Moderate-high, mostly in tuning (thresholds, confidence gates) rather than raw build complexity — budget time for iteration against real usage feedback, not just initial implementation.

**Risks:** Shipping this before the surfacing gate is well-tuned risks exactly the "cries wolf, gets ignored" failure named in Phase 13 §1 — err toward under-surfacing initially and loosening thresholds as confidence in precision grows, not the reverse.

---

## 8. Phase F — Full Personal Model & Dashboard

**Goal:** Make the accumulated intelligence visible and directly useful for the highest-value real use cases — career materials, project retrospectives, self-understanding over time.

**Scope:**
- Phase 14 (Personal Model) fully populated — Identity, Decision Patterns, Career (verified/unverified split), Knowledge, Project, Communication sub-models all active with real evidence trails.
- Phase 16 (Dashboard) — all ten panels, built as thin views over now-mature backend APIs.

**Deliverables:**
- Career Model's verified/unverified skill separation actively used in real resume/application drafting workflows (Phase 14 §7.1) — this is a direct, high-value payoff of the whole architecture for Shubhi's actual current work.
- Dashboard fully operational with drill-down navigation across all panels.
- Reflection panel showing genuine multi-month Personal Model evolution — only meaningful once Phases A-E have been running long enough to have real history to show.

**Success criteria:** The Career Model catches at least one real instance of an unverified claim before it reaches a resume or application — the concrete test of whether Phase 14 §7.1's design actually works in practice, not just in the abstract.

**Estimated complexity:** Moderate. Much of this phase is surfacing/UI work over already-built backend capability (Phases A-E) rather than new core logic.

**Dependencies:** Genuinely benefits from calendar time, not just engineering time — the Reflection panel and Decision Pattern Model need real accumulated history to be worth looking at.

---

## 9. Phase G — Raphael-Level Cognitive Operating System

**Goal:** Not a discrete new capability phase — this is the maturity phase, where every subsystem built in Phases A-F is hardened, tuned against years of real accumulated data, and trusted enough to be a genuine daily cognitive partner rather than an impressive demo.

**Scope:**
- Phase 17 (Security) hardened to production-grade: real key management, tested recovery drills running on schedule, full audit coverage validated against real usage patterns rather than just test fixtures.
- Phase 18 (Infrastructure) scaled if/when genuinely needed (the Kùzu→Neo4j migration, cloud sync) — not preemptively, per Phase 18 §12's explicit "local-first indefinitely" default.
- Phase 19 (Technology Decisions) periodically revisited as flagged in its own §13 — LLM provider landscape, framework adoption decisions, none of them permanent.
- Cross-cutting maturity: Learning Engine's calibration (Phase 09 §7) genuinely well-tuned from a year-plus of real feedback; Prediction Engine's precision proven over many real surfacing events, not just initial tuning; Personal Model's Decision Pattern and Identity sub-models reflecting years, not months, of evidence.

**"Deliverables"** at this phase are less about new features and more about a qualitative shift: the system reconstructing genuinely complex multi-year context accurately, catching real risks and opportunities the user would have missed, and being trusted enough that the user actually relies on it for the north-star "I disappear for six months, I return, I type bring me back" experience — not as a tested capability, but as lived, routine reality.

**Success criteria:** This phase doesn't have a fixed completion date — it's the ongoing state the system reaches and then continues to live in, consistent with Phase 01 §1.5's framing: "think in decades, not months."

---

## 10. Cross-Phase Dependency Summary

```
Phase A ──► Phase B ──► Phase C ──► Phase D ──► Phase E ──► Phase F ──► Phase G
   │            │            │            │            │            │
   └── each phase's quality bounds the next phase's ceiling ────────┘

Specifically:
  - B's reconstruction quality is bounded by A's retrieval quality
  - C's reasoning-readiness is bounded by B's context layering being solid
  - D's reasoning grounding is bounded by C's Knowledge Graph quality
  - E's prediction precision is bounded by D's agent/execution reliability
    (a Prediction Engine surfacing "forgotten work" that Execution can't
    reliably act on erodes trust just as much as a bad prediction would)
  - F's Personal Model richness is bounded by E's proactive signal volume
    (Decision Patterns need real strategic-question history to draw from)
  - G is not bounded by any single prior phase — it's the compounding
    effect of all of them maturing together over real calendar time
```

This dependency chain is the practical argument for building in this order rather than, say, starting with the Dashboard (Phase F) or Prediction Engine (Phase E) because they're more visible/exciting — each phase's ceiling is set by what came before it, and skipping ahead produces an impressive-looking feature built on a shaky foundation.

---

## 11. Risks Across the Whole Roadmap

| Risk | Where it bites hardest | Mitigation (already designed in) |
|---|---|---|
| Entity resolution errors compounding silently | Phase C onward | Guardian review gate (Phase 03 §6), never trusted blindly |
| Overfitting Personal Model to recent/noisy signal | Phase D-F | Asymmetric threshold gate (Phase 09 §6) |
| Prediction/Opportunity surfacing eroding trust via false positives | Phase E | Precision-first surfacing gate (Phase 13 §9), narrow default monitoring scope (Phase 15 §4.2) |
| Execution Engine taking unintended action | Phase D onward | Explicit scope field + approval gate (Phase 10 §4, §6), never optional |
| Solo-maintainer burnout from operational complexity | Every phase | "Boring technology" discipline (Phase 01 §1.5, reiterated in every Phase 19 decision) |
| Scope creep — building Phase E/F capability before Phase A/B foundation is solid | Especially tempting given the ambition of the original vision brief | This roadmap's explicit phase gating and "does this beat not having it, alone" test (§1) |

---

## 12. Closing Note

This handbook — twenty phases, covering vision, memory, knowledge graph, reasoning, context, reconstruction, research, multi-agent orchestration, learning, execution, conversation, extraction, prediction, personal modeling, world modeling, opportunity detection, strategy, dashboards, security, infrastructure, and technology decisions — is the complete architecture specification requested at the outset. Every phase is independently readable, independently buildable, and cross-referenced back to the design principles established in Phase 01 §1.3, which every subsequent decision has been checked against: persistent, context-aware, self-improving, modular, multi-agent, LLM-agnostic, privacy-first, local-first where possible, cloud scalable, observable, explainable, recoverable, composable, event-driven, version-controlled, continuously learning.

The roadmap in this final phase is the bridge from "complete specification" to "actual system" — and, consistent with Phase 01's own framing, the point is not to build all twenty phases as fast as possible, but to build Phase A well enough that it's already worth having, and let every phase after that compound on a foundation solid enough to still be trustworthy years from now.

---

*This concludes the Sage Engineering Handbook, Phases 01–20.*
