# Sage — Engineering Handbook
## Phase 15: World Model, Opportunity Detection Engine & Personal Strategy Engine

> Continues from Phase 01 (Foundation) through Phase 14 (Personal Model). This phase completes the "Human Intelligence Model" companion brief's remaining requirements: modeling the external world, discovering opportunities within it, and providing structured strategic decision support.

---

## 1. Overview

Phase 14 built a model of the user. This phase builds the two things that make that model actionable in the outside world: a **World Model** (what's happening externally, and why it matters to this specific user), an **Opportunity Detection Engine** (surfacing relevant external developments before the user asks), and a **Personal Strategy Engine** (structured support for "should I do this" questions, built on Reasoning Engine's Tree Search mode from Phase 04 §8).

These three are grouped into one phase because they form a single causal chain: the World Model observes → the Opportunity Detection Engine connects observations to the Personal Model and flags relevance → the Personal Strategy Engine helps reason through what, if anything, to do about it. None of the three is useful without the others; none needs its own separate infrastructure beyond what Phases 02–14 already provide.

## 2. Goals

- Continuously observe external developments (research, funding, fellowships, tools, industry trends) relevant to the user's stated domains, without becoming an unbounded general-purpose news aggregator — relevance filtering is the whole design problem here.
- Connect external developments to the Personal Model (Phase 14) and Knowledge Graph (Phase 03) to explain *why* something matters to this specific user, not just that it exists.
- Rank and surface opportunities with the same precision-first discipline as the Prediction Engine (Phase 13 §9) — noise erodes trust exactly the same way here.
- Provide strategic decision support that outputs structured trade-offs, evidence, and confidence — never a bare verdict — consistent with the non-goal established in Phase 01 §1.4 that Sage does not replace human judgment on high-stakes decisions.

## 3. Responsibilities

**Owns:** external-source relevance filtering, the World Model entity layer, opportunity ranking/verification, the Personal Strategy Engine's criteria-elicitation and trade-off synthesis flow.

**Does not own:** the actual web/document fetching mechanics (Research Engine, Phase 07, which the World Model calls), or making a final decision on the user's behalf (never — that boundary is structural, not just a guideline).

---

## 4. World Model

### 4.1 What It Is

A specialized region of the Knowledge Graph (Phase 03) — not a separate store — populated by Research Engine (Phase 07) monitoring external domains the user has indicated relevance for (AI research, startups/funding, grants/fellowships, the specific technical ecosystem Sage itself is built in, and Navgunjara's sector: care leaver support, NGO/social-impact funding, education).

```
WorldEntity {
  // Same Entity schema as Phase 03 §4.2, with world-specific types added:
  type: "ResearchPaper" | "Fellowship" | "Grant" | "Company" |
        "OpenSourceProject" | "Trend" | "Conference" | "JobPosting"
  relevance_domains: [str]        # which of the user's stated domains
                                    # this connects to — used for
                                    # filtering, §5
  observed_at: timestamp
  source_refs: [entity_id]         # Document/Source entities, Phase 07 §8
                                     # citation graph — every WorldEntity
                                     # traces to its actual source
}
```

### 4.2 Monitoring Scope Configuration

The relevance-domain list is explicit and user-configured, not inferred broadly — this is the primary defense against scope creep into "general news aggregator":

```
MonitoringScope {
  domains: [
    { name: "AI/ML engineering", keywords: [...], sources: [...] },
    { name: "social impact fellowships", keywords: [...], sources: [...] },
    { name: "care leaver / youth livelihood sector", keywords: [...],
      sources: [...] }
  ],
  refresh_cadence: "daily" | "weekly"
}
```

A domain is only monitored if explicitly added — the World Model does not autonomously expand its own scope based on inferred interest; scope expansion is itself a user-approved action (consistent with the explicit-consent discipline already established for source connections in Phase 12 §12).

### 4.3 Connecting World to Personal

Every WorldEntity that matches a `relevance_domain` gets an explicit candidate relationship proposed to relevant Personal Model / Knowledge Graph entities:

```
e.g., a new fellowship WorldEntity with relevance_domains including
"social impact fellowships" gets a candidate `applies_to` edge
proposed toward Navgunjara / ReRoot Project entities — reviewed
by the same Guardian Agent low-confidence gate (Phase 03 §6, Phase
08 §5.9) as any other tentative graph edge before it's treated as
established.
```

---

## 5. Opportunity Detection Engine

### 5.1 Detection Flow

```
1. World Model ingests a new WorldEntity (via Research Engine's
   monitoring, Phase 07, running as a scheduled job per Phase 08 §5.7).

2. Relevance Filter: does this WorldEntity's relevance_domains
   intersect the user's active MonitoringScope AND connect (even
   tentatively) to an active Project/Goal in the Personal Model?
   → if no meaningful connection, discard (logged, not surfaced —
     same "log everything, surface selectively" pattern as Phase 13 §9)

3. Ranking (reuses Prediction Engine's confidence-scoring discipline,
   Phase 13 §9, applied to opportunity-specific inputs):
   opportunity_score = f(
       relevance_strength,       # how directly it connects to an
                                   # active Project/Goal
       timeliness,                 # deadline proximity if applicable
                                   # (e.g., a fellowship with a near
                                   # application deadline ranks higher
                                   # than an evergreen resource)
       source_confidence,           # from Research Engine's source
                                   # verification, Phase 07 §7
       novelty                       # has something highly similar
                                   # already been surfaced and
                                   # dismissed/acted on (avoid
                                   # redundant surfacing, same as
                                   # Phase 13 §9's redundancy check)
   )

4. Verification: for high-stakes opportunity types (fellowships,
   grants — anything the user might commit real time/effort to),
   a verification pass confirms the WorldEntity's key facts
   (deadline, eligibility) against the primary source directly,
   not just a secondary aggregator — mirroring Research Engine's
   domain-reputation tiering (Phase 07 §7).

5. Surfacing Gate: same precision-first bias as Phase 13 §9 — only
   opportunities clearing a confidence threshold reach the user;
   everything else stays logged for potential later resurfacing if
   new evidence strengthens it.
```

### 5.2 Output Contract

```
Opportunity {
  world_entity_ref: entity_id
  connected_to: [entity_id]          # Project/Goal entities it relates to
  why_it_matters: text                 # explicit, evidence-grounded
                                        # explanation — never just "this
                                        # exists," always "this connects
                                        # to X because Y"
  deadline: timestamp | null
  opportunity_score: float
  verification_status: "verified" | "unverified_single_source"
  suggested_action: text | null         # e.g., "review eligibility
                                         # criteria" — same next-best-
                                         # action pattern as Phase 06 §9,
                                         # not an auto-executed step
}
```

---

## 6. Personal Strategy Engine

### 6.1 What It Is

The domain-specific framing layer over Reasoning Engine's Tree Search mode (Phase 04 §8) — Reasoning Engine provides the generic search/comparison machinery; the Strategy Engine provides the criteria structure and output contract specific to "should I do this" questions (career moves, project pivots, time-investment decisions).

### 6.2 Criteria Elicitation

Before running Tree Search, the Strategy Engine assembles the criteria set the decision should be evaluated against — drawn from the Personal Model, not invented generically each time:

```
criteria_set = merge(
    Identity Model values (Phase 14 §5)  — e.g., if "fabrication is
      a hard constraint" is a stated value, any strategy branch that
      would require overstating something scores down on that
      criterion explicitly,
    Decision Pattern Model (Phase 14 §6) — historically-weighted
      criteria, e.g., if the user has consistently favored first-
      principles builds over adopting frameworks, "does this
      preserve that kind of ownership" is a live criterion,
    explicit criteria stated for this specific decision (if the
      user has already indicated what matters to them for this
      particular choice — first-party input always takes priority
      over inferred pattern-based criteria)
)
```

### 6.3 Strategic Reasoning Flow

```
1. Frame the decision as a Tree Search query (Phase 04 §8) with the
   assembled criteria_set as the explicit weighted comparison basis.

2. For each branch, gather evidence from Memory/Knowledge Graph
   (Phase 02/03) AND, where relevant, the World Model (§4) — e.g.,
   "should I take the SafetyWhat promotion" pulls in not just
   internal Project Model state but external market/industry signal
   if available.

3. Score each branch per criterion, surfacing the full comparison —
   never collapsed into a single number or a bare recommendation.

4. Explicitly enumerate: assumptions made, unknowns that would
   change the analysis if resolved, and possible outcomes per branch
   (best case / worst case / most likely, where evidence supports
   even a rough characterization — and explicitly stated as absent
   where it doesn't).

5. Output structure — deliberately mirrors an investment-memo
   register (a format Shubhi has already used effectively for the
   ACT Fellowship Concept Note), since structured trade-off analysis
   in that register is a demonstrated strength worth reusing here:
     - Decision framing
     - Options considered
     - Evidence per option
     - Criteria comparison table
     - Stated assumptions and unknowns
     - Long-term impact considerations
     - Explicitly: NO verdict — the analysis ends at "here's the
       structured comparison," not "here's what you should do"
```

### 6.4 Output Contract

```
StrategyAnalysis {
  decision_framing: text
  options: [
    {
      option: text,
      evidence: [evidence_ref],
      criteria_scores: { criterion: score },
      assumptions: [text],
      possible_outcomes: { best_case, worst_case, most_likely }
    }
  ]
  unknowns_that_would_change_analysis: [text]
  reasoning_trace_id: str        # full replayable trace, Phase 04 §6.1
}
```

This structural refusal to output a verdict is not a hedge — it's the same non-goal stated explicitly in Phase 01 §1.4 ("Sage does not replace human judgment on high-stakes decisions... it surfaces evidence and trade-offs; it does not issue verdicts"), made concrete as an enforced output schema rather than just a stated intention.

---

## 7. Architecture Diagram

```
   Research Engine ──► World Model (Knowledge Graph region, §4)
   (scheduled                │
    monitoring,               ▼
    Phase 07/08)     Opportunity Detection Engine (§5)
                                │
                    relevance-filtered, ranked,
                    verified opportunities
                                │
                                ▼
                    Surfaced to Conversation Engine
                    (proactive) or Dashboard (Phase 16)


   User: "should I take X"
                │
                ▼
   Personal Strategy Engine (§6)
                │
      ┌──────────┴──────────┐
      ▼                      ▼
  Personal Model         Reasoning Engine
  (criteria, Phase 14)    Tree Search mode (Phase 04 §8)
      │                      │
      └──────────┬───────────┘
                 ▼
      Structured StrategyAnalysis (§6.4)
      — no verdict, full evidence + trade-offs
```

---

## 8. API Design

```
POST /world/monitoring_scope           // configure/update domains, §4.2
GET  /world/opportunities                // ranked, surfaced opportunities
POST /world/opportunities/{id}/feedback   // same feedback loop pattern as
                                            // Phase 13 §10, feeds Learning Engine

POST /strategy/analyze
{
  "decision": "Should ReRoot launch in Pune or Farrukhabad first?",
  "options": ["Pune", "Farrukhabad"],       // optional explicit framing;
                                              // Strategy Engine can also
                                              // generate candidate options
                                              // if not provided
  "explicit_criteria": [...]                  // optional, merged with
                                               // Personal Model criteria
}
→ StrategyAnalysis (§6.4)
```

---

## 9. Technology Choices & Tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Explicit, user-configured MonitoringScope vs. autonomous broad monitoring | Explicit (§4.2) | Autonomous scope expansion based on inferred interest | Prevents the World Model from drifting into an unbounded general-news feature, and keeps monitoring cost and noise predictable — directly serves the "not a general-purpose news aggregator" goal from §2 |
| Strategy Engine as a framing layer over existing Tree Search vs. a separate decision-support engine | Framing layer (§6.1) | Standalone engine with its own search machinery | Same reuse discipline as Phase 06's Bring Me Back and Phase 13's Prediction Engine — duplicating Tree Search logic would mean improvements to reasoning quality don't automatically benefit strategic decisions |
| Hard no-verdict output contract vs. an optional "recommended option" field | Hard constraint, structurally enforced (§6.4 schema has no verdict field at all) | Optional recommendation field | An optional field invites drift toward always filling it in; omitting it from the schema entirely makes the non-goal a structural property of the system, not a discipline that has to be remembered every time |

---

## 10. Scaling Strategy

World Model monitoring cost scales with the number of configured domains and refresh cadence — bounded and predictable by design (§4.2), unlike an open-ended crawl. Strategy Engine cost scales with decision complexity (branch count in the underlying Tree Search, Phase 04 §13) rather than data volume.

## 11. Security

Opportunity data connecting external WorldEntities to Project/Goal entities is subject to the same Guardian review gate as any tentative graph edge (Phase 03 §6) before being treated as established — an opportunity's "why it matters" framing should never overstate a connection the Guardian hasn't validated. Strategy analyses that draw on Belief/Reflection-tier Personal Model criteria (Phase 14 §13) inherit that sensitivity tier.

## 12. Testing Strategy

- **Relevance filter precision:** fixture WorldEntities, some genuinely relevant to configured domains and some deliberately adjacent-but-irrelevant, assert correct filtering.
- **No-verdict schema enforcement:** a structural test asserting `StrategyAnalysis` never contains a recommendation/verdict field — a schema-level guarantee, not just a prompt-behavior spot check.
- **Criteria assembly correctness:** given a fixed Personal Model fixture (known values, known decision patterns), assert the assembled `criteria_set` for a test decision includes the expected criteria.
- **Opportunity redundancy suppression:** verify a near-duplicate opportunity to a recently-surfaced-and-dismissed one is correctly suppressed, mirroring Phase 13's redundancy tests.

## 13. Failure Recovery

Both World Model entities and Opportunity records are Knowledge Graph/Memory Engine data at their core, so they inherit the same rebuild-from-event-log recoverability as everything else in Phases 02–03 — no separate recovery mechanism needed.

## 14. Future Improvements

- Cross-opportunity synthesis (recognizing that several small signals together suggest a larger pattern — e.g., multiple fellowship rejections in the same category might suggest a positioning issue worth surfacing as its own strategic question, connecting Opportunity Detection back into the Strategy Engine).
- Collaborative filtering-style relevance tuning once enough opportunity feedback history exists (Phase 09-style calibration, but applied specifically to opportunity ranking rather than general reasoning confidence).
- Expanded criteria-elicitation dialogue — currently criteria are assembled automatically from the Personal Model; a richer version could let the user interactively adjust weights before the Strategy Engine runs its analysis, for decisions where the default criteria don't feel complete.

---

*Next: Phase 16 — Dashboard Architecture (knowledge map, timeline, mission dashboard, projects, research, daily briefing, memory explorer, analytics, reflection, relationship graph).*
