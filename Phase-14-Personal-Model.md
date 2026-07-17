# Sage — Engineering Handbook
## Phase 14: Personal Model

> Continues from Phase 01 (Foundation) through Phase 13 (Prediction Engine). This phase also incorporates the "Digital Model of Me" requirements from the companion Human Intelligence Model brief — the Personal Model is the concrete architectural home for that vision, not a separate subsystem.

---

## 1. Overview

Every other subsystem in this handbook consumes some notion of "what does Sage know about this specific person." The Personal Model is where that knowledge is actually structured, versioned, and owned — not as a single blob, but as a set of typed sub-models: identity/values, decision patterns, skills, career, knowledge state, and active projects. Phase 09 (Learning Engine) already defined *how* this model changes over time; this phase defines *what it contains* and *how it's structured*.

The companion brief's framing is worth restating as a design constraint, not just inspiration: the goal is not to store facts about the person, but to build a model that improves *how Sage thinks with them* — a model that can eventually explain why the user made a past decision, not just recite what the decision was.

## 2. Goals

- Structure the Personal Model into distinct sub-models (not one flat "user profile" blob) so each can evolve, be queried, and be versioned independently, mirroring the Memory Engine's type-per-table discipline (Phase 02 §6.1).
- Ground every sub-model attribute in the same evidence/confidence discipline as Belief memory (Phase 02 §4.2) — the Personal Model is not exempt from the "describe, don't diagnose" constraint; it never contains unearned clinical or psychological labels.
- Make the Career, Knowledge, and Project sub-models genuinely useful standalone artifacts — e.g., the Career sub-model should be able to answer "what are my demonstrated vs. claimed skills" precisely enough to catch a resume overclaiming something, which is directly relevant to Shubhi's standing hard constraint of never fabricating tools/metrics in professional materials.
- Keep the model addressable by every consumer (Reasoning, Conversation, Prediction, Execution Engines) through one read API, consistent with the single-source-of-truth-per-concern pattern used throughout this handbook.

## 3. Responsibilities

**Owns:** sub-model schemas, the read API (`/model/user`), aggregation logic that keeps sub-models internally consistent (e.g., a claimed skill in the Career sub-model should trace to evidence in the Knowledge sub-model or Project sub-model, not float unsupported).

**Does not own:** how attributes get updated (Learning Engine, Phase 09, owns the update mechanics) or how the model gets applied in a given response (each consuming engine's own logic — the Personal Model is read-only from every consumer's perspective except the Learning Agent).

---

## 4. Sub-Model Architecture

```
PersonalModel {
  identity: IdentityModel
  decision_patterns: DecisionPatternModel
  career: CareerModel
  knowledge: KnowledgeModel
  projects: ProjectModel        # index into Knowledge Graph Project
                                  # entities, Phase 03 §4.1 — not
                                  # duplicated data, a curated view
  communication: CommunicationModel   # already referenced directly
                                       # by Conversation Engine, Phase 11 §7
}
```

Every field within every sub-model uses the same envelope as Belief memory: `{ value, confidence, evidence_refs, last_updated, version }` — there is no attribute in the Personal Model that exists without a confidence score and a trace back to supporting evidence, which is what makes it possible for Sage to answer "why do you think that about me" for any stored attribute, not just the headline ones.

---

## 5. Identity Model

```
IdentityModel {
  mission_statement: VersionedAttribute        # user-articulated, not inferred,
                                                  # unless explicitly built from
                                                  # repeated stated goals
  values: [VersionedAttribute]                   # e.g., "fabrication is a hard
                                                  # constraint," "brutal honesty
                                                  # over validation" — high-
                                                  # confidence because directly
                                                  # and repeatedly stated
  identity_narrative: VersionedAttribute | null    # only populated if the user
                                                    # has explicitly discussed
                                                    # self-narrative — never
                                                    # inferred/constructed by Sage
                                                    # unprompted
  risk_tolerance: VersionedAttribute               # built from Learning Engine
                                                    # behavior signals (Phase 09 §4)
                                                    # over multiple observed
                                                    # decisions, high evidence bar
}
```

The `identity_narrative` restriction is deliberate: this is the one field in the entire Personal Model that Sage does not proactively construct from inference, because unprompted narrative-building about someone's identity crosses from "modeling observed patterns" into "telling someone who they are" — a line the system should not cross uninvited, consistent with the constraint against Sage making claims about the user's internal state.

---

## 6. Decision Pattern Model

```
DecisionPatternModel {
  patterns: [
    {
      pattern_description: text,     # e.g., "tends to favor first-
                                       # principles builds over adopting
                                       # frameworks (ChefBot precedent)"
      evidence_instances: [entity_id | event_id],   # minimum 2, per
                                                       # Phase 09 §6's
                                                       # behavior-signal
                                                       # threshold
      confidence: float,
      domain: str                     # "technical" | "career" |
                                       # "strategic" | ...
    }
  ]
}
```

This sub-model is the most directly useful input to the Reasoning Engine's Tree Search mode (Phase 04 §8) — when generating decision criteria for a genuinely open choice, Reasoning Engine reads decision patterns to weight criteria the way the user has historically weighted them, without ever substituting a pattern for the user's actual judgment on the decision at hand.

---

## 7. Career Model

Directly serving the companion brief's "build a model of my career" requirements, and Shubhi's standing fabrication constraint:

```
CareerModel {
  verified_skills: [
    { skill: str, evidence_refs: [project_entity_id],
      demonstrated_via: text,   # e.g., "built RAG pipeline in Sage
                                 # using ChromaDB + Sentence Transformers"
      confidence: "verified" }   # distinct top-tier confidence level —
                                 # verified means traced to actual code/
                                 # project evidence, not claimed in
                                 # conversation alone
  ],
  claimed_but_unverified_skills: [
    { skill: str, first_mentioned: timestamp, note: text }
    # e.g., a technology mentioned in passing but never traced to
    # an actual project — this list exists specifically to catch
    # exactly the fabrication risk the standing constraint guards
    # against; the Career Model is where "did I actually do this or
    # did I just think about doing this" gets answered precisely
  ],
  skill_gaps: [text],              # explicitly identified missing
                                    # skills relative to stated goals
  career_trajectory: {
    current_roles: [entity_id],     # Organization entities, Phase 03 §4.1
    historical_positioning_shifts: [
      { from: text, to: text, when: timestamp, note: text }
      # e.g., "positioned as grassroots facilitation practitioner
      # (Quest Alliance, SELCO applications) → repositioned toward
      # AI-engineer-plus-founder dual narrative (The/Nudge, ACT)"
    ]
  },
  interview_and_application_performance: [
    { application_ref: entity_id, outcome: text, learnings: [text] }
  ]
}
```

### 7.1 Verified vs. Claimed — The Core Discipline

`verified_skills` requires a direct evidence trace to a Project entity or actual demonstrated artifact (code, deliverable). `claimed_but_unverified_skills` exists precisely so that when Sage helps draft a resume or application, it can flag "you mentioned X but I don't see it traced to an actual project — do you want to substantiate this or drop it" — this is the Career Model doing exactly the job Shubhi has manually enforced across many sessions (excluding LangChain/LangGraph from experience claims, for example), now as a structural, queryable property of the model rather than something that has to be manually re-checked every time.

---

## 8. Knowledge Model

```
KnowledgeModel {
  known_concepts: [
    { concept_entity_id: entity_id,   # Concept entity, Phase 03 §4.1
      mastery_level: "familiar" | "working" | "deep",
      last_engaged: timestamp,
      decay_adjusted_confidence: float }  # concepts not revisited
                                           # decay in confidence using
                                           # the same decay mechanism
                                           # as Memory Engine (Phase 02 §7)
  ],
  partial_or_uncertain_understanding: [
    { concept_entity_id: entity_id, note: text }
    # explicitly flagged — e.g., a concept touched on once in a
    # single conversation, not reinforced since
  ],
  knowledge_gaps: [text],             # concepts relevant to active
                                        # goals but not yet engaged at all
  concept_dependencies: [              # which concepts unlock
    { prerequisite: entity_id, enables: entity_id }   # understanding of
  ]                                                     # others — powers
}                                                        # a learning-path
                                                          # style recommendation
```

`concept_dependencies` reuses the Knowledge Graph's `enables` relation type directly (Phase 03 §5) rather than inventing a parallel structure — the Knowledge Model is substantially a curated *view* over Concept entities already in the graph, with the mastery/decay layer added on top.

---

## 9. Project Model

```
ProjectModel {
  active_projects: [entity_id],        # pointers into Knowledge Graph
                                         # Project entities (Phase 03 §4.1)
  per_project_summary: {
    entity_id: {
      current_state: text,              # kept current via Learning Engine
                                          # updates, not re-derived fresh
                                          # every read
      key_decisions_made: [entity_id],   # Insight/Event entities
      rejected_alternatives: [
        { alternative: text, why_rejected: text, when: timestamp }
      ],
      technical_debt: [text],
      success_probability: float | null   # only populated where enough
                                            # evidence exists to estimate
                                            # meaningfully — explicitly
                                            # absent rather than guessed
                                            # when it isn't
    }
  }
}
```

`rejected_alternatives` is a deliberately preserved field — the companion brief explicitly asks for "why decisions were made" and "rejected ideas," and this is exactly the kind of detail that Bring Me Back reconstruction (Phase 06) benefits most from months later, when the user might otherwise re-litigate a decision they already made a considered choice about.

---

## 10. Communication Model

Already introduced operationally in Phase 11 §7; specified here as data:

```
CommunicationModel {
  tone_preferences: [VersionedAttribute],   # "prefers brutal honesty
                                              # over validation," etc.
  format_preferences: [VersionedAttribute],  # "prefers targeted
                                              # improvements over full
                                              # rewrites," "prefers
                                              # completed deliverables
                                              # over process explanation"
  standing_corrections: [VersionedAttribute]  # explicit corrections to
                                               # Sage's prior behavior,
                                               # highest-confidence tier
                                               # since these are direct
                                               # first-party feedback
                                               # (Phase 09 §4)
}
```

---

## 11. API Design

```
GET /model/user
GET /model/user/career
GET /model/user/knowledge
GET /model/user/projects
GET /model/user/decision_patterns

GET /model/user/attribute_history/{path}     // same versioned history
                                               // pattern as Phase 09 §9

POST /model/user/career/flag_unverified       // explicit tool used
                                               // during resume/application
                                               // drafting to check a
                                               // claimed skill against
                                               // verified_skills
{
  "skill": "LangGraph",
}
→ { "status": "unverified", "note": "No project evidence found.
     Excluded from experience claims per standing constraint." }
```

---

## 12. Sequence Diagram — Resume Drafting Consulting the Career Model

```
User    Conversation Eng.   Reasoning Engine   Career Model    Execution
 │            │                    │                │              │
 │──draft      │                   │                │              │
 │  resume────►│                   │                │              │
 │            │──reasoning call───►│                │              │
 │            │                   │──fetch verified──►│              │
 │            │                   │  + claimed skills   │              │
 │            │                   │◄──skill lists────────│              │
 │            │                   │  (verified vs.         │              │
 │            │                   │   unverified, flagged)   │              │
 │            │                   │──draft, excluding         │              │
 │            │                   │  unverified claims          │              │
 │            │◄──draft + note: "excluded LangGraph, no         │              │
 │            │   project evidence found"                        │              │
 │◄──response───│                                                  │              │
```

---

## 13. Technology Choices & Tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Distinct sub-models vs. one flat user-profile object | Distinct (§4) | Flat profile | Independent evolution/versioning per concern, mirroring Memory Engine's per-type design (Phase 02 §6.1); also lets consumers fetch only the sub-model they need (`/model/user/career` vs. the whole model) |
| Explicit verified-vs-claimed skill separation vs. a single skills list | Separate lists (§7.1) | Single skills list with a confidence field | The distinction is load-bearing for a hard, explicitly-stated constraint (never fabricate claims in professional materials) — a single list with a confidence field buried in it is too easy to overlook during fast drafting; a structurally separate list makes it impossible to accidentally cite an unverified skill as fact |
| No unprompted identity narrative construction vs. Sage proactively synthesizing a "who you are" narrative | Restricted (§5) | Proactive synthesis | Directly respects the constraint against Sage making unearned claims about someone's identity/psychology — modeling patterns is appropriate; authoring someone's self-narrative for them is not |

---

## 14. Scaling Strategy

The Personal Model is inherently small relative to raw Memory/Graph volume (it's a curated, aggregated view, not a bulk store) — scaling is a non-issue at single-user scope; the design priority here is correctness and evidence-traceability, not throughput.

## 15. Security

The entire Personal Model sits at the same sensitivity tier as Belief/Reflection memory (Phase 02 §13) by default — it is, definitionally, Sage's most concentrated model of the user. Export and delete guarantees apply at the sub-model level (a user can request deletion of just the Decision Pattern Model, for instance, without affecting the Career Model) as well as the whole-model level.

## 16. Testing Strategy

- **Verified/unverified separation integrity:** fixture project evidence + claimed skills, assert the Career Model correctly places each skill in the right list, and that `flag_unverified` returns accurate results against a known fixture.
- **Evidence-trace completeness:** every populated attribute across all sub-models must have at least one `evidence_ref` — tested as a structural invariant, not per-attribute.
- **Identity narrative restriction:** assert no automated process ever writes to `identity_narrative` without an explicit user-authored source event (this is a hard invariant worth its own dedicated test, given its sensitivity).
- **Cross-sub-model consistency:** spot-check that Project Model summaries stay consistent with the underlying Knowledge Graph Project entities they index (no drift between the curated view and the source of truth).

## 17. Failure Recovery

Because every sub-model is fundamentally a curated, versioned view over Memory Engine and Knowledge Graph data (with the Learning Engine's update mechanics, Phase 09, as the only write path), the Personal Model is fully rebuildable by replaying the same event log used for every other derived store in this handbook — no separate backup strategy required beyond what Phases 02–03 already provide.

## 18. Future Improvements

- Confidence-weighted skill recommendations (once `skill_gaps` and `concept_dependencies` are populated enough, surface a genuinely prioritized "learn this next" recommendation rather than a flat gap list).
- Cross-referencing Career Model against live market signals (salary benchmarks, in-demand skills) — this is explicitly a Research Engine + Prediction Engine integration point, deferred until those subsystems have enough maturity to feed it reliably.
- Richer `rejected_alternatives` querying — surfacing "have I considered this before and rejected it" proactively when a similar idea resurfaces, directly useful for avoiding re-litigating settled decisions.

---

*Next: Phase 15 — World Model, Opportunity Detection Engine & Personal Strategy Engine (observing external developments, discovering and ranking opportunities, structured decision support for "should I do this" questions).*
